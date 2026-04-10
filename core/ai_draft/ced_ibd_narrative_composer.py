"""
ced_ibd_narrative_composer.py
-------------------------------
Dedicated composer for CED / IBD (Morbus Crohn / Colitis ulcerosa) cluster.

Narrative structure (up to 7 sentences; only rendered when data present):
  S1: disease anchor (Morbus Crohn / Colitis ulcerosa / CED) + course modifier
  S2: pain location + character
  S3: stool frequency + consistency
  S4: blood / mucus
  S5: associated symptoms
  S6: temporal triggers + pattern triggers (separate)
  S7: functional_impact  (first item, capitalised)

Rules:
  - No diagnosis generation
  - Only render what is explicitly present in shared_items
  - Filter sentinel values ("keine")
  - CED type clearly named in opening sentence
  - Stool data (frequency, consistency, blood/mucus) rendered precisely
  - Phenomenological: only what is explicitly stated
  - Verdichtungsstil: short, clinically natural German

Duration is handled by Route B in pilot_draft_service (inserted as
"seit X" before first sentence period) — not consumed here.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Render maps
# ---------------------------------------------------------------------------

# IBD type → noun phrase for S1 ("... ist [TYPE_PHRASE] bekannt")
_TYPE_PHRASE: dict[str, str] = {
    "Morbus Crohn":    "ein Morbus Crohn",
    "Colitis ulcerosa": "eine Colitis ulcerosa",
}

# Course modifiers → appended to S1 with comma
_COURSE_MOD: dict[str, str] = {
    "chronisch-aktiver Verlauf": "im chronisch-aktiven Verlauf",
    "schubweiser Verlauf":       "mit schubweisem Verlauf",
}

# Pain location → prepositional phrase after "vorwiegend im ..."
_LOCATION_PHRASE: dict[str, str] = {
    "Oberbauch":        "Oberbauch",
    "rechter Unterbauch": "rechten Unterbauch",
    "diffuser Bauch":   "gesamten Abdomen",
}

# Pain character → adjective
_CHAR_ADJ: dict[str, str] = {
    "drückend":   "drückender",
    "krampfartig": "krampfartiger",
    "dumpf":      "dumpfer",
    "stechend":   "stechender",
    "ziehend":    "ziehender",
    "kolikartig": "kolikartiger",
}

# Stool frequency → phrase fragment
_FREQ_PHRASE: dict[str, str] = {
    "1–2× täglich": "1–2",
    "2–3× täglich": "2–3",
    "4–5× täglich": "4–5",
}

# Stool consistency → adjective before "Stuhlgänge"
_CONSISTENCY_ADJ: dict[str, str] = {
    "breiiger Stuhl": "breiige",
    "fester Stuhl":   "feste",
}

# Blood/mucus: negative markers (both needed for combined negation)
_BLOOD_NEG  = "keine Blutbeimengungen"
_MUCUS_NEG  = "keine Schleimbeimengungen"
_BLOOD_POS  = "Blutbeimengungen"
_MUCUS_POS  = "Schleimbeimengungen"
_MUCUS_RARE = "selten Schleim"

# Temporal triggers → phrase after "Die Beschwerden treten ... auf"
_TEMPORAL_TRIGGER: dict[str, str] = {
    "nach Mahlzeiten":          "vor allem nach Mahlzeiten",
    "nach Verdauung":           "vor allem nach der Verdauung",
    "gegen Abend":              "bevorzugt gegen Abend",
    "nach längerem Sitzen":     "nach längerem Sitzen",
    "beim Bücken":              "beim Bücken",
    "beim Laufen":              "beim Laufen",
}

# Pattern triggers → own sentence
_PATTERN_SENTENCE: dict[str, str] = {
    "stressbedingt":              "Schübe werden von der Patientin teilweise als stressbedingt beschrieben.",
    "schubweise":                 "Die Beschwerden treten schubweise auf.",
    "zufällig auftretende Schübe": "Die Schübe treten ohne erkennbares Muster auf.",
}

# Associated symptoms → direct nouns
_ASSOC_NOUN: dict[str, str] = {
    "Blähungen":              "Blähungen",
    "Übelkeit":               "Übelkeit",
    "Erbrechen":              "Erbrechen",
    "Druckgefühl im Oberbauch": "Druckgefühl im Oberbauch",
}
# Nouns that are grammatically plural even as single items
_ASSOC_PLURAL: set[str] = {"Blähungen"}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compose_ced_ibd_narrative(shared_items: dict[str, list[str]]) -> str:
    """
    Build a German clinical description from shared_items.

    Returns 1–8 sentences ending with '.'.
    Never raises; returns "Chronisch-entzündliche Darmerkrankung." as minimal fallback.
    """
    sentences: list[str] = []

    # ── S1: disease anchor + course modifier ─────────────────────────────
    type_raw   = _clean(shared_items.get("ibd_type_background", []))
    type_items = [v for v in type_raw if v in _TYPE_PHRASE]
    course_items = [v for v in type_raw if v in _COURSE_MOD]

    if type_items:
        type_phrase = _TYPE_PHRASE[type_items[0]]
        s1 = f"Bei der Patientin ist {type_phrase} bekannt"
        if course_items:
            s1 += ", " + _COURSE_MOD[course_items[0]]
        sentences.append(s1 + ".")
    else:
        sentences.append("Bei der Patientin ist eine chronisch-entzündliche Darmerkrankung bekannt.")

    # ── S2: pain location + character ─────────────────────────────────────
    loc_raw  = _clean(shared_items.get("ibd_pain_location", []))
    char_raw = _clean(shared_items.get("pain_character",    []))

    loc_phrases = [_LOCATION_PHRASE.get(v, v) for v in loc_raw[:2]]
    char_adjs   = [_CHAR_ADJ.get(v, v)        for v in char_raw[:3]]

    if loc_phrases and char_adjs:
        sentences.append(
            "Im Vordergrund stehen Bauchschmerzen, vorwiegend im "
            + _und(loc_phrases)
            + ", von " + _und(char_adjs) + " Qualität."
        )
    elif loc_phrases:
        sentences.append(
            "Im Vordergrund stehen Bauchschmerzen, vorwiegend im "
            + _und(loc_phrases) + "."
        )
    elif char_adjs:
        sentences.append(
            "Im Vordergrund stehen Bauchschmerzen von " + _und(char_adjs) + " Qualität."
        )

    # ── S3: stool frequency + consistency ────────────────────────────────
    bowel_raw = _clean(shared_items.get("ibd_bowel_pattern", []))
    freq_items  = [v for v in bowel_raw if v in _FREQ_PHRASE]
    cons_items  = [v for v in bowel_raw if v in _CONSISTENCY_ADJ]

    if freq_items:
        freq = _FREQ_PHRASE[freq_items[0]]
        adj  = _CONSISTENCY_ADJ.get(cons_items[0], "") if cons_items else ""
        if adj:
            sentences.append(f"Aktuell bestehen {freq} {adj} Stuhlgänge täglich.")
        else:
            sentences.append(f"Aktuell bestehen {freq} Stuhlgänge täglich.")
    elif cons_items:
        adj = _CONSISTENCY_ADJ[cons_items[0]]
        sentences.append(f"Aktuell bestehen {adj} Stuhlgänge.")

    # ── S4: blood / mucus ────────────────────────────────────────────────
    bm_raw = _clean(shared_items.get("ibd_blood_mucus", []))
    if bm_raw:
        has_blood_neg  = _BLOOD_NEG  in bm_raw
        has_mucus_neg  = _MUCUS_NEG  in bm_raw
        has_blood_pos  = _BLOOD_POS  in bm_raw
        has_mucus_pos  = _MUCUS_POS  in bm_raw
        has_mucus_rare = _MUCUS_RARE in bm_raw

        if has_blood_neg and has_mucus_neg:
            sentences.append("Es bestehen keine Blut- oder Schleimbeimengungen.")
        elif has_blood_neg and has_mucus_rare:
            sentences.append("Es bestehen keine Blutbeimengungen und nur selten Schleim.")
        elif has_blood_neg:
            sentences.append("Es bestehen keine Blutbeimengungen.")
        elif has_mucus_neg:
            sentences.append("Es bestehen keine Schleimbeimengungen.")

        pos_parts: list[str] = []
        if has_blood_pos:
            pos_parts.append("Blutbeimengungen")
        if has_mucus_pos:
            pos_parts.append("Schleimbeimengungen")
        if has_mucus_rare:
            pos_parts.append("selten Schleim")
        if pos_parts and not (has_blood_neg or has_mucus_neg):
            sentences.append("Es bestehen " + _und(pos_parts) + ".")

    # ── S5: associated symptoms ───────────────────────────────────────────
    assoc_raw = _clean(shared_items.get("ibd_associated_symptoms", []))
    if assoc_raw:
        nouns = [_ASSOC_NOUN.get(v, v) for v in assoc_raw[:4]]
        is_plural = len(nouns) > 1 or any(n in _ASSOC_PLURAL for n in nouns)
        verb = "bestehen" if is_plural else "besteht"
        sentences.append(f"Begleitend {verb} " + _und(nouns) + ".")

    # ── S6: triggers (temporal + pattern) ────────────────────────────────
    trigger_raw = _clean(shared_items.get("ibd_trigger_pattern", []))
    temporal = [_TEMPORAL_TRIGGER[v] for v in trigger_raw if v in _TEMPORAL_TRIGGER]
    patterns = [v for v in trigger_raw if v in _PATTERN_SENTENCE]

    if temporal:
        sentences.append("Die Beschwerden treten " + _und(temporal) + " auf.")
    for p in patterns[:2]:
        sentences.append(_PATTERN_SENTENCE[p])

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
