"""
gelenkbeschwerden_narrative_composer.py
----------------------------------------
Dedicated composer for Gelenkbeschwerden (Arthrose) cluster.

Narrative structure (up to 8 sentences; only rendered when data present):
  S1: anchor + joint_location + laterality_distribution
  S2: pain_character + pain_intensity
  S3: mechanical_pattern  (belastungsabhängig / Anlaufschmerz / situations)
  S4: range_of_motion_limitation
  S5: morning_stiffness   (sentinel "keine" filtered)
  S6: swelling_irritation (sentinel "keine" filtered)
  S7: relieving_factors
  S8: functional_impact   (first item, capitalised)

Rules:
  - No diagnosis generation
  - Only render what is explicitly present in shared_items
  - Filter sentinel values ("keine")
  - Verdichtungsstil: short, clinically natural German
  - Output must read as mechanically/degeneratively patterned joint
    complaints, not inflammatory polyarthritis

Duration is handled by Route B in pilot_draft_service (inserted as
"seit X" before first sentence period) — not consumed here.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Render maps
# ---------------------------------------------------------------------------

# Prepositional phrase: "im Bereich <phrase>"
_LOCATION_PREP: dict[str, str] = {
    "Knie":                "der Kniegelenke",
    "Hüfte":               "der Hüfte",
    "Schulter":            "der Schulter",
    "Ellenbogen":          "des Ellenbogens",
    "Handgelenke":         "der Handgelenke",
    "Fingergelenke":       "der Fingergelenke",
    "Sprunggelenke":       "der Sprunggelenke",
    "Füße / Zehengelenke": "der Füße und Zehengelenke",
    "mehrere Gelenke":     "mehrerer Gelenke",
}

_CHARACTER_ADJECTIVE: dict[str, str] = {
    "ziehend":     "ziehender",
    "drückend":    "drückender",
    "dumpf":       "dumpfer",
    "stechend":    "stechender",
    "brennend":    "brennender",
    "bohrend":     "bohrender",
    "krampfartig": "krampfartiger",
}

_INTENSITY_PHRASE: dict[str, str] = {
    "leicht":      "leichter Intensität",
    "mittelstark": "mittelstarker Intensität",
    "stark":       "starker Intensität",
    "sehr stark":  "sehr starker Intensität",
}

# Noun form for "Typisch sind ..." sentence
_MECH_NOUN: dict[str, str] = {
    "belastungsabhängig":        "Belastungsabhängigkeit",
    "beim Gehen":                "Beschwerden beim Gehen",
    "beim Treppensteigen":       "Beschwerden beim Treppensteigen",
    "bei längerer Belastung":    "Beschwerden bei längerer Belastung",
    "Anlaufschmerz":             "Anlaufschmerzen",
    "im Tagesverlauf zunehmend": "Zunahme im Tagesverlauf",
}

# ROM limitation: phrase after "Zudem bestehen ..."
_ROM_PHRASE: dict[str, str] = {
    "eingeschränkte Beweglichkeit":        "eine eingeschränkte Beweglichkeit",
    "reduzierte Belastbarkeit":            "eine reduzierte Belastbarkeit",
    "eingeschränkte Gehstrecke":           "eine eingeschränkte Gehstrecke",
    "Schwierigkeiten beim Treppensteigen": "Schwierigkeiten beim Treppensteigen",
    "Probleme beim Aufstehen":             "Probleme beim Aufstehen",
}

# Morning stiffness: full sentence
_MORNING_STIFFNESS_SENTENCE: dict[str, str] = {
    "kurzzeitig": "Eine kurzzeitige Morgensteifigkeit besteht.",
    "vorhanden":  "Eine Morgensteifigkeit ist vorhanden.",
}

# Swelling/irritation: noun after "Gelegentlich besteht ..."
_SWELLING_NOUN: dict[str, str] = {
    "gelegentliche Schwellung":       "Schwellung",
    "belastungsabhängige Schwellung":  "belastungsabhängige Schwellung",
    "Reizzustand":                    "ein Reizzustand",
}

_RELIEVING_NOUN: dict[str, str] = {
    "Ruhe":          "Ruhe",
    "Wärme":         "Wärme",
    "Schonung":      "Schonung",
    "Kühlung":       "Kühlung",
    "Physiotherapie": "Physiotherapie",
    "Analgetika":    "Analgetika",
    "Entlastung":    "Entlastung",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compose_gelenkbeschwerden_narrative(shared_items: dict[str, list[str]]) -> str:
    """
    Build a German clinical description from shared_items.

    Returns 1–8 sentences ending with '.'.
    Never raises; returns "Gelenkbeschwerden." as minimal fallback.
    """
    sentences: list[str] = []

    # ── S1: anchor + location + laterality ───────────────────────────────
    loc_raw = _clean(shared_items.get("joint_location",           []))
    lat_raw = _clean(shared_items.get("laterality_distribution",  []))

    loc_phrases = [_LOCATION_PREP.get(v, v) for v in loc_raw[:2]]
    lat = lat_raw[0] if lat_raw else None

    if loc_phrases:
        s1 = "Arthrosebedingte Gelenkbeschwerden im Bereich " + _und(loc_phrases)
        if lat:
            s1 += f" {lat}"
    elif lat:
        s1 = f"Arthrosebedingte Gelenkbeschwerden {lat}"
    else:
        s1 = "Arthrosebedingte Gelenkbeschwerden"
    sentences.append(s1 + ".")

    # ── S2: pain character + intensity ───────────────────────────────────
    char_raw = _clean(shared_items.get("pain_character", []))
    intens   = _clean(shared_items.get("pain_intensity", []))

    char_adjs    = [_CHARACTER_ADJECTIVE.get(v, v) for v in char_raw[:2]]
    intens_phrase = _INTENSITY_PHRASE.get(intens[0]) if intens else None

    if char_adjs or intens_phrase:
        parts: list[str] = []
        if char_adjs:
            parts.append("von " + _und(char_adjs) + " Qualität")
        if intens_phrase:
            parts.append(intens_phrase)
        sentences.append("Die Beschwerden sind " + ", ".join(parts) + ".")

    # ── S3: mechanical pattern ────────────────────────────────────────────
    mech = _clean(shared_items.get("mechanical_pattern", []))
    if mech:
        nouns = [_MECH_NOUN.get(v, v) for v in mech[:3]]
        sentences.append("Typisch sind " + _und(nouns) + ".")

    # ── S4: range of motion ───────────────────────────────────────────────
    rom = _clean(shared_items.get("range_of_motion_limitation", []))
    if rom:
        phrases = [_ROM_PHRASE.get(v, v) for v in rom[:3]]
        sentences.append("Zudem bestehen " + _und(phrases) + ".")

    # ── S5: morning stiffness ─────────────────────────────────────────────
    stiffness = _clean(shared_items.get("morning_stiffness", []))
    if stiffness:
        sent = _MORNING_STIFFNESS_SENTENCE.get(stiffness[0])
        if sent:
            sentences.append(sent)

    # ── S6: swelling / irritation ─────────────────────────────────────────
    swelling = _clean(shared_items.get("swelling_irritation", []))
    if swelling:
        nouns = [_SWELLING_NOUN.get(v, v) for v in swelling[:2]]
        sentences.append("Gelegentlich besteht " + _und(nouns) + ".")

    # ── S7: relieving factors ─────────────────────────────────────────────
    rel = _clean(shared_items.get("relieving_factors", []))
    if rel:
        nouns = [_RELIEVING_NOUN.get(v, v) for v in rel[:3]]
        sentences.append("Linderung bringen " + _und(nouns) + ".")

    # ── S8: functional impact ─────────────────────────────────────────────
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
