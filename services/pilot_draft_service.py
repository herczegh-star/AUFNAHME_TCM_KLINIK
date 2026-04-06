"""
pilot_draft_service.py
----------------------
3-stage draft pipeline for the Cluster-Pilot screen.

Stage 1 — raw      : deterministic, uses lws_narrative_composer
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

# Try to import the project LLM client; fall back to a no-op stub.
# HAS_LLM is intentionally public so the UI can show honest labels.
try:
    from core.llm_client import call_llm as _call_llm_backend  # type: ignore
    _HAS_LLM = True
except ImportError:
    _HAS_LLM = False

#: Public flag — read by ScreenClusterPilot to show/hide LLM capability in UI.
HAS_LLM: bool = _HAS_LLM


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_raw(cluster: UnifiedCluster, form_data: dict) -> str:
    """
    Stage 1: deterministic sentence construction from form_data (UI form keys).
    Uses lws_narrative_composer (cluster-specific composer lookup planned
    for future clusters; LWS is hardcoded for the pilot).

    Fields that feed the main sentence (via shared_items):
      pain_temporality, character, side, radiation,
      aggravating_factor, relieving_factor

    Fields appended as plain-text suffix (generic, no cluster-specific logic):
      duration       → „seit <value>" prepended before first sentence
      additional_notes → appended as second sentence

    All other form fields are not yet rendered (see TODO in _form_data_to_shared_items).
    """
    from core.ai_draft.lws_narrative_composer import compose_lws_narrative

    shared_items = _form_data_to_shared_items(cluster, form_data)
    core_sentence = compose_lws_narrative(shared_items)
    validated = _validate_output(core_sentence, cluster)

    # --- duration prefix ---
    duration = (form_data.get("duration") or "").strip()
    if duration:
        # Insert "seit <duration>" at the end of the core sentence (before period)
        # e.g. "Chronische Schmerzen im LWS-Bereich, seit 3 Wochen."
        if validated.endswith("."):
            validated = validated[:-1] + f", seit {duration}."
        else:
            validated = validated + f", seit {duration}."

    # --- additional_notes as a second sentence ---
    notes = (form_data.get("additional_notes") or "").strip()
    if notes:
        suffix = notes if notes.endswith(".") else notes + "."
        validated = validated + " " + suffix

    return validated


def generate_raw_from_shared_items(cluster: UnifiedCluster, shared_items: dict) -> str:
    """
    Stage 1 variant: accepts shared_items dict directly (composer key format).
    Used by the cluster test runner so tests can specify shared_items directly.
    """
    from core.ai_draft.lws_narrative_composer import compose_lws_narrative

    raw = compose_lws_narrative(shared_items)
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
                "Du bist ein klinischer Dokumentationsexperte (Verdichtungsstil).\n"
                f"Stilregeln:\n{rules_text}\n"
                f"Verbotene Woerter: {forbidden}\n"
                f"Beispiele:\n{examples_text}\n"
                "Gib ausschliesslich den ueberarbeiteten Satz zurueck."
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
    Convert flat form_data dict into the shared_items dict expected by
    lws_narrative_composer.compose_lws_narrative().

    Field mapping (form field id → shared_items key):
      pain_temporality  → pain_temporality
      character         → pain_character
      side              → pain_laterality
      radiation         → pain_radiation
      aggravating_factor → aggravating_mechanical
      relieving_factor   → relieving_passive
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

    # TODO (next sprint): the field→shared_items key mapping below is currently
    # hardcoded for LWS.  For generalisation across clusters, this mapping should
    # be declared in the cluster JSON (e.g. form.fields[*].shared_items_key) and
    # resolved here dynamically.
    #
    # Fields NOT mapped here (not yet rendered in the core sentence):
    #   intensity_vas, onset, neurological_signs, previous_treatment,
    #   functional_limitations
    # duration and additional_notes are handled as plain-text suffix in generate_raw().
    return {
        "pain_temporality":   _normalize("", form_data.get("pain_temporality")),
        "pain_character":     _normalize("character", form_data.get("character")),
        "pain_laterality":    _normalize("side", form_data.get("side")),
        "pain_radiation":     _to_list(form_data.get("radiation")),
        "aggravating_mechanical": _normalize("aggravating", form_data.get("aggravating_factor")),
        "relieving_passive":  _normalize("relieving", form_data.get("relieving_factor")),
    }


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
