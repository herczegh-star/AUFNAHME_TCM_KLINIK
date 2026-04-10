"""
migraene_narrative_composer.py
-------------------------------
Dedicated composer for Migräne cluster.

Narrative structure (up to 7 sentences; only rendered when data present):
  S1: anchor + pain_location + pain_character + pain_intensity
  S2: migraine_frequency  (Migränetage-aware special rendering)
  S3: migraine_attack_duration
  S4: migraine_associated_symptoms
  S5: migraine_aura  (only when non-empty and not "keine")
  S6: aggravating_factors + relieving_factors
  S7: functional_impact  (first item, capitalised)

Rules:
  - No diagnosis generation
  - Only render what is explicitly present in shared_items
  - Filter sentinel values ("keine")
  - Verdichtungsstil: short, clinically natural German

Special rule — migraine_frequency:
  If value contains "Migränetage":
    render as "Es bestehen etwa [X] Migränetage pro Monat."
  Otherwise:
    render as "Die Attacken treten [value] auf."
  This prevents unnatural output like "Die Attacken treten
  3–6 Migränetage/Monat auf."

Duration is handled by Route B in pilot_draft_service (inserted as
"seit X" before first sentence period) — not consumed here.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Render maps
# ---------------------------------------------------------------------------

_LOCATION_PHRASE: dict[str, str] = {
    "temporal":                 "temporal",
    "einseitig rechts":         "einseitig rechts",
    "einseitig links":          "einseitig links",
    "wechselnd rechts / links": "wechselnd rechts/links",
    "beidseits":                "beidseits",
    "frontal":                  "frontal",
    "okzipital":                "okzipital",
    "diffus":                   "diffus",
}

_CHARACTER_ADJECTIVE: dict[str, str] = {
    "pochend":    "pochender",
    "pulsierend": "pulsierender",
    "stechend":   "stechender",
    "drückend":   "drückender",
    "dumpf":      "dumpfer",
    "ziehend":    "ziehender",
}

_INTENSITY_PHRASE: dict[str, str] = {
    "leicht":      "leichter Intensität",
    "mittelstark": "mittelstarker Intensität",
    "stark":       "starker Intensität",
    "sehr stark":  "sehr starker Intensität",
}

_ATTACK_DURATION_PHRASE: dict[str, str] = {
    "wenige Stunden":  "wenige Stunden",
    "mehrere Stunden": "mehrere Stunden",
    "einen Tag lang":  "einen Tag",
    "1–2 Tage":        "1–2 Tage",
    "bis zu 3 Tage":   "bis zu 3 Tagen",
}

_AURA_DATIVE: dict[str, str] = {
    "visuelle Aura": "visueller Aura",
    "sensible Aura": "sensibler Aura",
    "andere Aura":   "andersartiger Aura",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compose_migraene_narrative(shared_items: dict[str, list[str]]) -> str:
    """
    Build a German clinical description from shared_items.

    Returns 1–7 sentences ending with '.'.
    Never raises; returns "Migränebeschwerden." as minimal fallback.
    """
    sentences: list[str] = []

    # ── S1: anchor + location + character + intensity ─────────────────────
    loc_raw  = _clean(shared_items.get("pain_location",  []))
    char_raw = _clean(shared_items.get("pain_character", []))
    intens   = _clean(shared_items.get("pain_intensity", []))

    loc_phrases  = [_LOCATION_PHRASE.get(v, v)      for v in loc_raw[:2]]
    char_adjs    = [_CHARACTER_ADJECTIVE.get(v, v)   for v in char_raw[:2]]
    intens_phrase = _INTENSITY_PHRASE.get(intens[0]) if intens else None

    s1 = "Anfallsartige Migränebeschwerden"
    if loc_phrases:
        s1 += " " + ", ".join(loc_phrases)
    if char_adjs:
        s1 += " von " + _und(char_adjs) + " Qualität"
    if intens_phrase:
        s1 += ", " + intens_phrase
    sentences.append(s1 + ".")

    # ── S2: migraine_frequency ────────────────────────────────────────────
    freq = _clean(shared_items.get("migraine_frequency", []))
    if freq:
        sentences.append(_render_frequency(freq[0]))

    # ── S3: migraine_attack_duration ──────────────────────────────────────
    dur = _clean(shared_items.get("migraine_attack_duration", []))
    if dur:
        phrase = _ATTACK_DURATION_PHRASE.get(dur[0], dur[0])
        sentences.append(f"Die Attacken dauern jeweils etwa {phrase} an.")

    # ── S4: associated symptoms ───────────────────────────────────────────
    syms = _clean(shared_items.get("migraine_associated_symptoms", []))
    if syms:
        sentences.append(f"Begleitend bestehen {_und(syms[:4])}.")

    # ── S5: aura ──────────────────────────────────────────────────────────
    aura = _clean(shared_items.get("migraine_aura", []))
    if aura:
        aura_dative = _AURA_DATIVE.get(aura[0], aura[0])
        sentences.append(
            f"Teilweise geht die Symptomatik mit {aura_dative} einher."
        )

    # ── S6: aggravating + relieving ───────────────────────────────────────
    agg = _clean(shared_items.get("aggravating_factors", []))
    rel = _clean(shared_items.get("relieving_factors",   []))
    if agg or rel:
        parts: list[str] = []
        if agg:
            parts.append(f"verstärkt durch {_und(agg[:2])}")
        if rel:
            parts.append(f"gebessert durch {_und(rel[:2])}")
        s6 = ", ".join(parts)
        sentences.append(s6[0].upper() + s6[1:] + ".")

    # ── S7: functional impact ─────────────────────────────────────────────
    func = _clean(shared_items.get("functional_impact", []))
    if func:
        phrase = func[0].strip()
        sentences.append(
            phrase[0].upper() + phrase[1:] + ("" if phrase.endswith(".") else ".")
        )

    return " ".join(sentences)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _render_frequency(value: str) -> str:
    """
    Render migraine frequency in clinically natural German.

    Values containing "Migränetage" use the "Migränetage pro Monat" form;
    all other values use the "Attacken treten X auf" form.

    Example inputs and outputs:
      "3–6 Migränetage/Monat" → "Es bestehen etwa 3–6 Migränetage pro Monat."
      "1–2× monatlich"        → "Die Attacken treten 1–2× monatlich auf."
      "wöchentlich"           → "Die Attacken treten wöchentlich auf."
    """
    if "Migränetage" in value:
        clean_val = value.replace("/Monat", "").strip()
        return f"Es bestehen etwa {clean_val} pro Monat."
    return f"Die Attacken treten {value} auf."


def _clean(items: list[str]) -> list[str]:
    """Remove empty and sentinel values."""
    return [v for v in items if v and v.lower() != "keine"]


def _und(items: list[str]) -> str:
    """Join: 'A', 'A und B', 'A, B und C'."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} und {items[1]}"
    return ", ".join(items[:-1]) + f" und {items[-1]}"
