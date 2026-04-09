"""
pilot_draft_service.py
----------------------
3-stage draft pipeline for the Cluster-Pilot screen.

Stage 1 — raw      : deterministic, cluster-agnostic via narrative_dispatcher
Stage 2 — refined  : LLM grammar/flow cleanup (no content changes)
Stage 3 — final    : strict Verdichtungsstil LLM pass

All LLM calls are non-blocking from the caller's perspective — the
screen passes callbacks and calls generate_* from a thread.

LLM integration uses the same OpenAI-compatible client already
present in the project (core/llm_client.py if it exists, otherwise
a minimal inline call).  Falls back gracefully to the raw stage if
LLM is unavailable.
"""

from __future__ import annotations

import re
import threading
from typing import Callable

from models.unified_cluster import UnifiedCluster
from core.ai_draft.narrative_dispatcher import compose_narrative

# Try to import the project LLM client; fall back to a no-op stub.
# HAS_LLM is intentionally public so the UI can show honest labels.
try:
    from core.llm_client import call_llm as _call_llm_backend  # type: ignore
    _HAS_LLM = True
except ImportError:
    _HAS_LLM = False

#: Public flag — read by ScreenPilotComposer to show honest LLM capability labels in UI.
HAS_LLM: bool = _HAS_LLM


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_raw(cluster: UnifiedCluster, form_data: dict) -> str:
    """
    Stage 1: deterministic sentence construction from form_data (UI form keys).
    Dispatches to the cluster-specific narrative composer via narrative_dispatcher.
    Falls back to generic_narrative_composer for clusters without a dedicated one.

    Fields that feed the main sentence (via shared_items):
      pain_temporality, character, side, radiation,
      aggravating_factor, relieving_factor

    Fields appended as plain-text suffix (generic, no cluster-specific logic):
      duration       → „seit <value>" prepended before first sentence
      additional_notes → appended as second sentence

    All other form fields are not yet rendered (see TODO in _form_data_to_shared_items).
    """
    shared_items = _form_data_to_shared_items(cluster, form_data)
    core_sentence = compose_narrative(cluster.id, shared_items, cluster=cluster)
    validated = _validate_output(core_sentence, cluster)

    # --- duration suffix — inserted into the FIRST sentence only ---
    # When the composer produces two sentences (e.g. main clause + functional
    # impact), duration must attach to the first sentence, not the last.
    # We find the first period and insert before it.
    duration = (form_data.get("duration") or "").strip()
    if duration and duration.lower() != "keine":
        # Apply German dative correction: plural time units after "seit" need -n
        # "2 Jahre" → "2 Jahren", "6 Monate" → "6 Monaten", "10 Tage" → "10 Tagen"
        duration = re.sub(r"\b(Jahr|Monat|Tag)e\b", r"\1en", duration)
        first_dot = validated.find(".")
        if first_dot > 0:
            # Normal case: "Schmerzen." → "Schmerzen, seit 3 Wochen."
            validated = (
                validated[:first_dot]
                + f", seit {duration}."
                + validated[first_dot + 1:]
            )
        elif first_dot == 0:
            # Degenerate: validated is just "." — avoid leading comma
            validated = f"Seit {duration}." + validated[1:]
        else:
            validated = validated + f", seit {duration}."

    # --- additional_notes as a second sentence ---
    notes = (form_data.get("additional_notes") or "").strip()
    if notes and notes.lower() != "keine":
        suffix = notes if notes.endswith(".") else notes + "."
        validated = validated + " " + suffix

    return validated


def generate_raw_from_shared_items(cluster: UnifiedCluster, shared_items: dict) -> str:
    """
    Stage 1 variant: accepts shared_items dict directly (composer key format).
    Used by the cluster test runner so tests can specify shared_items directly.
    """
    raw = compose_narrative(cluster.id, shared_items, cluster=cluster)
    return _validate_output(raw, cluster)


def generate_refined(
    cluster: UnifiedCluster,
    raw_text: str,
    on_done: Callable[[str], None],
    on_error: Callable[[str], None],
) -> None:
    """
    Stage 2: LLM grammar/flow cleanup.
    Calls on_done(result) or on_error(message) in a background thread.
    """
    def _run() -> None:
        try:
            if not _HAS_LLM:
                on_done(raw_text)
                return
            system = (
                "Du bist ein medizinischer Redakteur. "
                "Korrigiere nur Grammatik und Satzfluss. "
                "Aendere KEINEN medizinischen Inhalt. "
                "Antworte ausschliesslich mit dem korrigierten Satz."
            )
            result = _call_llm_backend(system=system, user=raw_text, temperature=0.2)
            validated = _validate_output(result, cluster, check_anchor=True)
            on_done(validated)
        except ValueError:
            # Anchor missing in LLM output — fall back to raw input unchanged
            on_done(raw_text)
        except Exception as exc:
            on_error(str(exc))

    threading.Thread(target=_run, daemon=True).start()


def generate_final(
    cluster: UnifiedCluster,
    refined_text: str,
    on_done: Callable[[str], None],
    on_error: Callable[[str], None],
) -> None:
    """
    Stage 3: strict Verdichtungsstil pass.
    Applies cluster style rules and preferred_phrases via LLM.
    Calls on_done(result) or on_error(message) in a background thread.
    """
    def _run() -> None:
        try:
            if not _HAS_LLM:
                on_done(refined_text)
                return
            rules_text = "\n".join(f"- {r}" for r in cluster.rules)
            examples_text = _format_examples(cluster.examples)
            forbidden = ", ".join(cluster.forbidden_words)
            system = (
                "Du bist ein klinischer Dokumentationsexperte. "
                "Deine einzige Aufgabe ist es, den gegebenen Text in den Verdichtungsstil zu ueberfuehren.\n\n"
                "Strikte Sicherheitsregeln — keine Ausnahmen:\n"
                "- Du fügst keine Fakten hinzu, die nicht im Eingabetext stehen.\n"
                "- Du stellst keine Diagnosen und formulierst keine diagnostischen Schlussfolgerungen.\n"
                "- Du gibst keine Therapieempfehlungen.\n"
                "- Du spekulierst nicht ueber fehlende Informationen.\n"
                "- Du interpretierst keine unausgesprochenen Zusammenhaenge.\n"
                "- Wenn eine Information nicht im Eingabetext steht, laesst du sie vollstaendig weg.\n\n"
                f"Stilregeln:\n{rules_text}\n\n"
                f"Verbotene Woerter: {forbidden}\n\n"
                f"Beispiele:\n{examples_text}\n\n"
                "Gib ausschliesslich den ueberarbeiteten Text zurueck. "
                "Keine Kommentare, keine Erklaerungen, kein Metakommentar."
            )
            result = _call_llm_backend(system=system, user=refined_text, temperature=0.1)
            validated = _validate_output(result, cluster, check_anchor=True)
            on_done(validated)
        except ValueError:
            # Anchor missing in LLM output — fall back to refined input unchanged
            on_done(refined_text)
        except Exception as exc:
            on_error(str(exc))

    threading.Thread(target=_run, daemon=True).start()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _form_data_to_shared_items(
    cluster: UnifiedCluster, form_data: dict
) -> dict[str, list[str]]:
    """
    Convert flat form_data dict into the shared_items dict expected by the
    narrative composer.

    Mapping is driven entirely by form.fields[*].shared_items_key in the cluster
    JSON — no hardcoded field names here.  Fields with shared_items_key=null are
    skipped (duration and additional_notes are handled as plain-text suffix in
    generate_raw(); intensity_vas, onset, neurological_signs, previous_treatment
    are not yet part of the draft sentence).

    Normalization is applied when form.fields[*].normalization_map is set —
    the value is a key into cluster.normalization_maps.
    """
    def _to_list(val) -> list[str]:
        if val is None:
            return []
        if isinstance(val, list):
            return [v for v in val if v and v != "keine"]
        s = str(val).strip()
        return [s] if s and s != "keine" else []

    # Apply cluster normalization maps
    norm = cluster.normalization_maps

    def _normalize(key: str, val) -> list[str]:
        alias_map = norm.get(key, {})
        tokens = _to_list(val)
        result = []
        for t in tokens:
            canonical = alias_map.get(t.lower(), alias_map.get(t, t))
            result.append(canonical)
        return result

    result: dict[str, list[str]] = {}
    for field in cluster.form_fields:
        sik = field.get("shared_items_key")
        if not sik:
            continue
        fid      = field["id"]
        norm_key = field.get("normalization_map")
        val      = form_data.get(fid)
        result[sik] = _normalize(norm_key, val) if norm_key else _to_list(val)
    return result


def _validate_output(
    text: str,
    cluster: UnifiedCluster,
    *,
    check_anchor: bool = False,
) -> str:
    """
    Post-process and validate a draft sentence:
      1. Strip forbidden words (regex, case-insensitive).
      2. Collapse double spaces introduced by removal.
      3. Ensure sentence ends with a period.
      4. Anchor check (only when check_anchor=True): if the cluster defines
         preferred_phrases.anchor[0], verify the output contains it.
         If not (e.g. LLM hallucinated a completely different sentence),
         raises ValueError so the caller can fall back to the raw stage.

    check_anchor=False for the deterministic raw stage (anchor is guaranteed
    by the composer).  check_anchor=True for LLM stages 2 and 3.

    The anchor check is a hard-miss guard only — it does NOT validate grammar
    or Verdichtungsstil quality.
    """
    for word in cluster.forbidden_words:
        pattern = re.compile(re.escape(word), re.IGNORECASE)
        text = pattern.sub("", text)

    text = re.sub(r"  +", " ", text).strip()

    if not text.endswith("."):
        text += "."

    if check_anchor:
        anchor_candidates = cluster.preferred_phrases.get("anchor", [])
        if anchor_candidates:
            anchor = anchor_candidates[0]
            if anchor not in text:
                raise ValueError(
                    f"LLM output missing required anchor '{anchor}'. "
                    f"Got: {text!r}"
                )

    return text


def _format_examples(examples: list[dict]) -> str:
    parts = []
    for i, ex in enumerate(examples[:3], 1):
        inp = ex.get("input", "")
        out = ex.get("output", "")
        parts.append(f"{i}. Input: {inp}\n   Output: {out}")
    return "\n".join(parts)
