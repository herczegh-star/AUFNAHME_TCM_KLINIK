"""
rheuma_narrative_composer.py
-----------------------------
Dedicated composer for entzündlich-rheumatologische Gelenkbeschwerden /
Polyarthritis cluster.

Narrative structure (up to 7 sentences; only rendered when data present):
  S1: rheuma_background (disease anchor)
  S2: rheuma_joint_distribution (affected joints)
  S3: pain_character + rheuma_flare_pattern (combined)
  S4: rheuma_inflammatory_signs (in flare phases)
  S5: rheuma_morning_stiffness
  S6: rheuma_function_specific + rheuma_aggravating_factors + relieving_factors
  S7: functional_impact (first item, capitalised)

Rules:
  - No diagnosis generation
  - Only render what is explicitly present in shared_items
  - Filter sentinel values ("keine")
  - Must read as inflammatory-rheumatologic, not degenerative-mechanical
  - Morning stiffness / startup difficulty rendered as named entity
  - Warmth/cold contrast rendered naturally when both sides present
  - Verdichtungsstil: short, clinically natural German

Duration is handled by Route B in pilot_draft_service (inserted as
"seit X" before first sentence period) — not consumed here.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Render maps
# ---------------------------------------------------------------------------

# Rheumatologic background → opening phrase
_BACKGROUND_PHRASE: dict[str, str] = {
    "rheumatoide Arthritis":    "eine rheumatoide Arthritis",
    "chronische Polyarthritis": "eine chronische Polyarthritis",
    "Psoriasis-Arthritis":      "eine Psoriasis-Arthritis",
    "HLA-B27-assoziiert":       "HLA-B27-assoziierte entzündlich-rheumatologische Beschwerden",
}

# Joint distribution → phrase used after "Betroffen sind vor allem ..."
_JOINT_PHRASE: dict[str, str] = {
    "Hand- und Fingergelenke": "die Hand- und Fingergelenke",
    "Fuß- und Zehengelenke":   "die Fuß- und Zehengelenke",
    "Schultergelenke":         "die Schultergelenke",
    "Hüftgelenke":             "die Hüftgelenke",
}
_JOINT_BILATERAL = "beidseits"

# Pain character → predicative form (used after "sind")
_CHAR_ADJ: dict[str, str] = {
    "stechend":        "stechend",
    "ziehend":         "ziehend",
    "drückend":        "drückend",
    "brennend":        "brennend",
    "dumpf":           "dumpf",
    "messerstichartig": "messerstichartig",
}

# Flare pattern → phrase fragments
_FLARE_INTRO = "Der Verlauf ist schubförmig"
_FLARE_DURATION: dict[str, str] = {
    "Schübe über Tage":                   "Schübe halten teils mehrere Tage an",
    "Schübe über Wochen":                 "Schübe halten teils mehrere Wochen an",
    "mehrmals täglich kurz einschießend": "mit mehrmals täglich kurz einschießenden Beschwerden",
}

# Inflammatory signs → adjectives used in "sind die Gelenke ... und ..."
_INFLAM_ADJ: dict[str, str] = {
    "geschwollen":      "geschwollen",
    "überwärmt":        "überwärmt",
    "druckschmerzhaft": "druckschmerzhaft",
    "schmerzhaft":      "schmerzhaft",
}

# Morning stiffness → noun/phrase for natural listing
_STIFFNESS_NOUN: dict[str, str] = {
    "Morgensteifigkeit wenige Minuten": "Morgensteifigkeit von wenigen Minuten",
    "Morgensteifigkeit ca. 45 Minuten": "Morgensteifigkeit von ca. 45 Minuten",
    "Anlaufschwierigkeiten":            "Anlaufschwierigkeiten",
    "morgendliches Steifigkeitsgefühl": "morgendliches Steifigkeitsgefühl",
}

# Specific functional limitation → sentence fragment
_FUNC_SPEC_PHRASE: dict[str, str] = {
    "eingeschränkte Geschicklichkeit": "eine eingeschränkte Geschicklichkeit der Hände",
    "Bewegungsblockierung":            "zeitweise Bewegungsblockierungen",
    "eingeschränkte Handfunktion":     "eine eingeschränkte Handfunktion",
}

# Aggravating factors
_AGG_NOUN: dict[str, str] = {
    "Belastung": "Belastung",
    "Kälte":     "Kälte",
    "Nässe":     "Nässe",
}

# Relieving factors
_REL_NOUN: dict[str, str] = {
    "Wärme":         "Wärme",
    "Ruhe":          "Ruhe",
    "Schonung":      "Schonung",
    "Kühlung":       "Kühlung",
    "Physiotherapie": "Physiotherapie",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compose_rheuma_narrative(shared_items: dict[str, list[str]]) -> str:
    """
    Build a German clinical description from shared_items.

    Returns 1–7 sentences ending with '.'.
    Never raises; returns "Entzündlich-rheumatologische Gelenkbeschwerden." as minimal fallback.
    """
    sentences: list[str] = []

    # ── S1: disease anchor ────────────────────────────────────────────────
    bg_raw = _clean(shared_items.get("rheuma_background", []))
    bg_items = [v for v in bg_raw if v in _BACKGROUND_PHRASE]

    if bg_items:
        phrase = _BACKGROUND_PHRASE[bg_items[0]]
        sentences.append(f"Bei der Patientin ist {phrase} bekannt.")
    else:
        sentences.append(
            "Es bestehen chronische entzündlich-rheumatologische Gelenkbeschwerden."
        )

    # ── S2: joint distribution ────────────────────────────────────────────
    joint_raw = _clean(shared_items.get("rheuma_joint_distribution", []))
    joint_items = [v for v in joint_raw if v in _JOINT_PHRASE]
    bilateral   = _JOINT_BILATERAL in joint_raw

    if joint_items:
        phrases = [_JOINT_PHRASE[v] for v in joint_items[:3]]
        s2 = "Betroffen sind vor allem " + _und(phrases)
        if bilateral:
            s2 += " beidseits"
        sentences.append(s2 + ".")

    # ── S3: pain character + flare pattern ───────────────────────────────
    char_raw  = _clean(shared_items.get("pain_character",       []))
    flare_raw = _clean(shared_items.get("rheuma_flare_pattern", []))

    char_adjs = [_CHAR_ADJ.get(v, v) for v in char_raw[:3]]
    is_schubfoermig  = "schubförmig" in flare_raw
    duration_items   = [v for v in flare_raw if v in _FLARE_DURATION]

    if char_adjs:
        sentences.append("Die Schmerzen sind " + _und(char_adjs) + ".")

    if is_schubfoermig:
        if duration_items:
            dur = _FLARE_DURATION[duration_items[0]]
            sentences.append(f"{_FLARE_INTRO}; {dur}.")
        else:
            sentences.append(f"{_FLARE_INTRO}.")
    elif duration_items:
        # flare duration without the "schubförmig" tag
        dur = _FLARE_DURATION[duration_items[0]]
        sentences.append(f"Der Verlauf ist {dur}.")

    # ── S4: inflammatory signs ────────────────────────────────────────────
    inflam_raw = _clean(shared_items.get("rheuma_inflammatory_signs", []))
    if inflam_raw:
        adjs = [_INFLAM_ADJ.get(v, v) for v in inflam_raw[:4]]
        sentences.append(
            "In Schubphasen sind die betroffenen Gelenke " + _und(adjs) + "."
        )

    # ── S5: morning stiffness ─────────────────────────────────────────────
    stiff_raw = _clean(shared_items.get("rheuma_morning_stiffness", []))
    if stiff_raw:
        nouns = [_STIFFNESS_NOUN.get(v, v) for v in stiff_raw[:3]]
        sentences.append("Begleitend bestehen " + _und(nouns) + ".")

    # ── S6: specific function + aggravating/relieving ─────────────────────
    func_spec = _clean(shared_items.get("rheuma_function_specific",  []))
    agg_raw   = _clean(shared_items.get("rheuma_aggravating_factors", []))
    rel_raw   = _clean(shared_items.get("relieving_factors",          []))

    if func_spec:
        phrases = [_FUNC_SPEC_PHRASE.get(v, v) for v in func_spec[:2]]
        verb = "bestehen" if len(phrases) > 1 else "besteht"
        sentences.append(f"Zudem {verb} " + _und(phrases) + ".")

    agg_nouns = [_AGG_NOUN.get(v, v) for v in agg_raw[:3]]
    rel_nouns = [_REL_NOUN.get(v, v) for v in rel_raw[:3]]

    if agg_nouns and rel_nouns:
        rel_verb = "lindern" if len(rel_nouns) > 1 else "lindert"
        agg_verb = "führen" if len(agg_nouns) > 1 else "führt"
        sentences.append(
            _und(rel_nouns) + f" {rel_verb} die Beschwerden"
            + "; " + _und(agg_nouns) + f" {agg_verb} zu einer Verschlechterung."
        )
    elif agg_nouns:
        agg_verb = "führen" if len(agg_nouns) > 1 else "führt"
        sentences.append(_und(agg_nouns) + f" {agg_verb} zu einer Verschlechterung.")
    elif rel_nouns:
        sentences.append("Linderung bringen " + _und(rel_nouns) + ".")

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
