"""
reizdarm_narrative_composer.py
-------------------------------
Dedicated composer for Reizdarm / funktionelle Verdauungsbeschwerden cluster.

Narrative structure (up to 6 sentences; only rendered when data present):
  S1: anchor + abdominal_location_pattern + pain_character
  S2: gi_associated_symptoms
  S3: bowel_pattern
  S4: gi_course_frequency + food_relation
  S5: relieving_factors
  S6: functional_impact  (first item, capitalised)

Rules:
  - No diagnosis generation
  - Only render what is explicitly present in shared_items
  - Filter sentinel values ("keine")
  - Functional/non-inflammatory character — not CED, not IBD language
  - Verdichtungsstil: short, clinically natural German

Duration is handled by Route B in pilot_draft_service (inserted as
"seit X" before first sentence period) — not consumed here.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Render maps
# ---------------------------------------------------------------------------

# Prepositional phrase: "im Bereich <phrase>"
_LOCATION_PREP: dict[str, str] = {
    "diffuser Bauch":    "des Abdomens, diffus",
    "Unterbauch":        "des Unterbauchs",
    "Oberbauch":         "des Oberbauchs",
    "rechtsseitig":      "des Abdomens, rechtsseitig",
    "linksseitig":       "des Abdomens, linksseitig",
    "postprandial betont": "des Abdomens, postprandial betont",
}

_CHARACTER_ADJECTIVE: dict[str, str] = {
    "krampfartig": "krampfartigem",
    "drückend":    "drückendem",
    "ziehend":     "ziehendem",
    "stechend":    "stechendem",
    "dumpf":       "dumpfem",
    "kolikartig":  "kolikartigem",
}

# Bowel pattern: full noun phrase used in "Zudem bestehen wechselnde Stuhlgewohnheiten mit ..."
_BOWEL_NOUN: dict[str, str] = {
    "weicher Stuhl":              "weichem Stuhl",
    "breiiger Stuhl":             "breiigem Stuhl",
    "wechselhafte Stuhlkonsistenz": "wechselhafter Stuhlkonsistenz",
    "erhöhte Stuhlfrequenz":      "erhöhter Stuhlfrequenz",
    "Diarrhoeneigung":            "Diarrhoeneigung",
    "Verstopfungsneigung":        "Verstopfungsneigung",
}

# Course/frequency: noun phrase used in "Die Beschwerden zeigen einen ... Verlauf."
_COURSE_PHRASE: dict[str, str] = {
    "unregelmäßig":               "unregelmäßigen",
    "häufig":                     "häufigen",
    "schubartig":                 "schubartigen",
    "phasenweise":                "phasenweisen",
    "3–4× täglich":               "schubartigen",
    "über Wochen anhaltende Schübe": "schubartigen, über Wochen anhaltenden",
}

_RELIEVING_NOUN: dict[str, str] = {
    "Ruhe":           "Ruhe",
    "Wärme":          "Wärme",
    "Schonung":       "Schonung",
    "Nahrungskarenz": "Nahrungskarenz",
    "Entspannung":    "Entspannung",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compose_reizdarm_narrative(shared_items: dict[str, list[str]]) -> str:
    """
    Build a German clinical description from shared_items.

    Returns 1–6 sentences ending with '.'.
    Never raises; returns "Funktionelle Verdauungsbeschwerden." as minimal fallback.
    """
    sentences: list[str] = []

    # ── S1: anchor + location + pain character ────────────────────────────
    loc_raw  = _clean(shared_items.get("abdominal_location_pattern", []))
    char_raw = _clean(shared_items.get("pain_character", []))

    loc_phrases  = [_LOCATION_PREP.get(v, v) for v in loc_raw[:2]]
    char_adjs    = [_CHARACTER_ADJECTIVE.get(v, v) for v in char_raw[:2]]

    s1 = "Funktionelle Verdauungsbeschwerden"
    if loc_phrases:
        s1 += " im Bereich " + _und(loc_phrases)
    if char_adjs:
        s1 += ", von " + _und(char_adjs) + " Charakter"
    sentences.append(s1 + ".")

    # ── S2: GI associated symptoms ────────────────────────────────────────
    syms = _clean(shared_items.get("gi_associated_symptoms", []))
    if syms:
        sentences.append("Begleitend bestehen " + _und(syms[:4]) + ".")

    # ── S3: bowel pattern ─────────────────────────────────────────────────
    bowel = _clean(shared_items.get("bowel_pattern", []))
    if bowel:
        nouns = [_BOWEL_NOUN.get(v, v) for v in bowel[:3]]
        sentences.append(
            "Zudem bestehen wechselnde Stuhlgewohnheiten mit " + _und(nouns) + "."
        )

    # ── S4: course/frequency + food relation ──────────────────────────────
    course = _clean(shared_items.get("gi_course_frequency", []))
    food   = _clean(shared_items.get("food_relation", []))

    # Filter out the "no relation" sentinel for food
    food = [v for v in food if v != "keine klare Nahrungsabhängigkeit"]

    if course or food:
        parts: list[str] = []
        if course:
            adj = _COURSE_PHRASE.get(course[0], "schubartigen")
            parts.append(f"Die Beschwerden zeigen einen {adj} Verlauf")
        if food:
            food_phrase = _und(food[:2])
            if "postprandial" in food_phrase or "nahrungsabhängig" in food_phrase:
                parts.append("teilweise treten sie postprandial verstärkt auf")
            else:
                parts.append(f"mit {food_phrase}")
        combined = "; ".join(parts)
        sentences.append(combined[0].upper() + combined[1:] + ".")

    # ── S5: relieving factors ─────────────────────────────────────────────
    rel = _clean(shared_items.get("relieving_factors", []))
    if rel:
        post_stuhlgang = "nach Stuhlgang" in rel
        standard = [_RELIEVING_NOUN.get(v, v) for v in rel if v != "nach Stuhlgang"]
        if standard:
            sentences.append("Linderung bringen " + _und(standard[:3]) + ".")
        if post_stuhlgang:
            sentences.append("Teilweise Linderung nach Stuhlgang.")

    # ── S6: functional impact ─────────────────────────────────────────────
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
