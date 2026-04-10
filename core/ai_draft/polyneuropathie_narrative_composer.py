"""
polyneuropathie_narrative_composer.py
---------------------------------------
Dedicated composer for Polyneuropathische Beschwerden / Polyneuropathie cluster.

Narrative structure (up to 8 sentences; only rendered when data present):
  S1: anchor + distribution (location + lateral modifiers)
      (+ "Hände mitbetroffen" sentence when selected)
  S2: sensory symptoms + pain quality
      (+ Wattegefühl/Strumpfgefühl sentence when selected)
  S3: neuropathy_night_sleep
  S4: neuropathy_gait_motor
  S5: neuropathy_progression
  S6: relieving_factors
  S7: functional_impact  (first item, capitalised)

Rules:
  - No diagnosis generation
  - Only render what is explicitly present in shared_items
  - Filter sentinel values ("keine")
  - Distal/ascending distribution must come through clearly in S1
  - Sensory symptoms as main clinical entity
  - Night-related symptoms and progression rendered as named entities
  - No etiology, no medication history, no diagnostic speculation
  - Verdichtungsstil: short, clinically natural German

Duration is handled by Route B in pilot_draft_service (inserted as
"seit X" before first sentence period) — not consumed here.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Render maps
# ---------------------------------------------------------------------------

# Primary location items → prepositional phrase after "im Bereich ..."
_LOC_PHRASE: dict[str, str] = {
    "Zehen / Füße":         "der Zehen und Füße",
    "Unterschenkel":        "der Unterschenkel",
    "bis unterhalb der Knie": "bis unterhalb der Kniegelenke",
}

# Lateral/side modifiers → appended to S1
_LATERAL_MOD: set[str] = {"beidseits", "linksbetont"}

# Sensory symptoms: main group (listed directly)
_SENSORY_MAIN_NOUN: dict[str, str] = {
    "Kribbelparästhesien":           "Kribbelparästhesien",
    "Dysästhesien":                  "Dysästhesien",
    "Taubheitsgefühl":               "Taubheitsgefühle",
    "elektrisierende Missempfindungen": "elektrisierende Missempfindungen",
    "Engegefühl":                    "Engegefühl",
    "Kältegefühl":                   "Kältegefühl",
}

# Sensory symptoms: special "texture/covering" group → separate sentence
_SENSORY_SPECIAL: set[str] = {"Wattegefühl", "Strumpfgefühl"}

# Pain quality → adjective before "Schmerzen"
_PAIN_QUALITY_ADJ: dict[str, str] = {
    "brennend":                  "brennende",
    "stechend":                  "stechende",
    "elektrisierend":            "elektrisierende",
    "belastungsabhängig brennend": "belastungsabhängig brennende",
}

# Gait/motor → noun for "Zudem bestehen ..."
_GAIT_NOUN: dict[str, str] = {
    "Gangunsicherheit":              "Gangunsicherheit",
    "Stolpern":                      "Stolperneigung",
    "unsicheres Gehen":              "unsicheres Gehen",
    "schweres Gefühl in den Beinen": "Schweregefühl in den Beinen",
    "Gehen erschwert":               "eingeschränkte Gehfähigkeit",
}

# Night/sleep → phrase for "Nachts ist der Schlaf durch ... beeinträchtigt."
_NIGHT_NOUN: dict[str, str] = {
    "nachts verstärkt":      "Missempfindungen",
    "unruhige Beine nachts": "unruhige Beine",
    "Schlafunterbrechungen": "Schlafunterbrechungen",
    "schlafstörend":         "Schlafstörungen durch Missempfindungen",
}

# Progression → complete sentence
_PROGRESSION_SENTENCE: dict[str, str] = {
    "schleichend progredient":    "Die Symptomatik zeigt einen schleichend progredienten Verlauf.",
    "zunehmende Beschwerden":     "Die Beschwerden nehmen im Verlauf zu.",
    "aufsteigende Ausbreitung":   "Die Ausbreitung der Symptomatik erfolgt aufsteigend.",
    "Trend zur Verschlechterung": "Es besteht ein Trend zur Verschlechterung.",
}

_RELIEVING_NOUN: dict[str, str] = {
    "Ruhe":          "Ruhe",
    "Wärme":         "Wärme",
    "Kühlung":       "Kühlung",
    "Hochlagerung":  "Hochlagerung der Beine",
    "Wasserbad":     "lokale Maßnahmen (Wasserbad)",
    "Schonung":      "Schonung",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compose_polyneuropathie_narrative(shared_items: dict[str, list[str]]) -> str:
    """
    Build a German clinical description from shared_items.

    Returns 1–8 sentences ending with '.'.
    Never raises; returns "Polyneuropathische Beschwerden." as minimal fallback.
    """
    sentences: list[str] = []

    # ── S1: anchor + distribution ─────────────────────────────────────────
    dist_raw = _clean(shared_items.get("neuropathy_distribution", []))

    loc_items   = [_LOC_PHRASE[v]   for v in dist_raw if v in _LOC_PHRASE]
    lateral     = [v               for v in dist_raw if v in _LATERAL_MOD]
    ascending   = "aufsteigend"      in dist_raw
    hands       = "Hände mitbetroffen" in dist_raw

    s1 = "Polyneuropathische Beschwerden"
    if loc_items:
        s1 += " im Bereich " + _und(loc_items)
    if ascending:
        s1 += ", aufsteigend"
    if lateral:
        s1 += ", " + _und(lateral)
    sentences.append(s1 + ".")

    if hands:
        sentences.append("Zeitweise sind auch die Hände mitbetroffen.")

    # ── S2: sensory symptoms + pain quality ───────────────────────────────
    sensory_raw  = _clean(shared_items.get("neuropathy_sensory_symptoms", []))
    pain_raw     = _clean(shared_items.get("neuropathy_pain_quality",     []))

    special = [v for v in sensory_raw if v in _SENSORY_SPECIAL]
    main    = [_SENSORY_MAIN_NOUN.get(v, v) for v in sensory_raw if v not in _SENSORY_SPECIAL]
    pain_adjs = [_PAIN_QUALITY_ADJ.get(v, v) for v in pain_raw[:2]]

    symptom_parts: list[str] = []
    if pain_adjs:
        symptom_parts.append(_und(pain_adjs) + " Schmerzen")
    symptom_parts.extend(main[:3])

    if symptom_parts:
        sentences.append("Im Vordergrund stehen " + _und(symptom_parts) + ".")

    if special:
        # "Wattegefühl" and/or "Strumpfgefühl" → natural compound form
        if len(special) == 2:
            texture = "ein Watte- bzw. Strumpfgefühl"
        elif special[0] == "Wattegefühl":
            texture = "ein Wattegefühl"
        else:
            texture = "ein Strumpfgefühl"
        sentences.append(f"Teilweise besteht {texture} an den Füßen.")

    # ── S3: night / sleep ─────────────────────────────────────────────────
    night = _clean(shared_items.get("neuropathy_night_sleep", []))
    if night:
        nouns = [_NIGHT_NOUN.get(v, v) for v in night[:3]]
        sentences.append("Nachts ist der Schlaf durch " + _und(nouns) + " beeinträchtigt.")

    # ── S4: gait / motor ──────────────────────────────────────────────────
    gait = _clean(shared_items.get("neuropathy_gait_motor", []))
    if gait:
        nouns = [_GAIT_NOUN.get(v, v) for v in gait[:3]]
        verb = "besteht" if len(nouns) == 1 else "bestehen"
        sentences.append(f"Zudem {verb} " + _und(nouns) + ".")

    # ── S5: progression ───────────────────────────────────────────────────
    progr = _clean(shared_items.get("neuropathy_progression", []))
    if progr:
        sent = _PROGRESSION_SENTENCE.get(progr[0])
        if sent:
            sentences.append(sent)

    # ── S6: relieving factors ─────────────────────────────────────────────
    rel = _clean(shared_items.get("relieving_factors", []))
    if rel:
        nouns = [_RELIEVING_NOUN.get(v, v) for v in rel[:3]]
        sentences.append("Linderung bringen " + _und(nouns) + ".")

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
