"""
neurodermitis_narrative_composer.py
-------------------------------------
Dedicated composer for Neurodermitis / atopisches Ekzem cluster.

Narrative structure (up to 7 sentences; only rendered when data present):
  S1: eczema_course (background / pattern)
  S2: eczema_pruritus (leading symptom)
  S3: eczema_locations (affected areas)
  S4: eczema_skin_findings (skin changes)
  S5: eczema_sleep_impact
  S6: eczema_aggravating_factors + relieving_factors
  S6b: eczema_associated_features
  S7: functional_impact (first item, capitalised)

Rules:
  - No diagnosis generation
  - Only render what is explicitly present in shared_items
  - Filter sentinel values ("keine")
  - Pruritus is the leading symptom — always rendered first after S1
  - Evening/night timing rendered naturally in pruritus sentence
  - Sleep disturbance rendered as its own sentence
  - Verdichtungsstil: short, clinically natural German

Duration is handled by Route B in pilot_draft_service (inserted as
"seit X" before first sentence period) — not consumed here.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Render maps
# ---------------------------------------------------------------------------

# Disease/course items that name the entity (used in S1)
_COURSE_ENTITY: dict[str, str] = {
    "Neurodermitis":   "eine Neurodermitis",
    "atopisches Ekzem": "ein atopisches Ekzem",
}

# Course modifiers → appended to entity
_COURSE_MOD: dict[str, str] = {
    "schubförmig":           "mit schubförmigem Verlauf",
    "Exazerbation":          "in akuter Exazerbation",
    "Besserungstendenz":     "mit aktueller Besserungstendenz",
    "Verschlechterungstendenz": "mit aktueller Verschlechterungstendenz",
}

# Pruritus intensity/type → phrase before timing
_PRURITUS_NOUN: dict[str, str] = {
    "stark ausgeprägter Juckreiz": "stark ausgeprägter Juckreiz",
    "anfallsartiger Juckreiz":     "anfallsartig auftretender Juckreiz",
}
_DEFAULT_PRURITUS = "Juckreiz"

# Pruritus quality (stechend/brennend) → adjective
_PRURITUS_QUALITY: dict[str, str] = {
    "stechend": "stechend",
    "brennend":  "brennend",
}

# Pruritus timing → used in "der vor allem ... auftritt"
_PRURITUS_TIMING: dict[str, str] = {
    "abendbetont": "abends",
    "nachtbetont": "nachts",
}

# Location → direct name (used as-is)
_LOCATION_DISPLAY: dict[str, str] = {
    "Hände":           "Hände",
    "Arme":            "Arme",
    "Gesicht":         "Gesicht",
    "Kopfhaut":        "Kopfhaut",
    "oberer Rücken":   "oberer Rücken",
    "Dekolleté / Brust": "Dekolleté und Brustbereich",
    "mehrere Areale":  "mehrere Körperstellen",
}

# Skin findings → adjective (used in "gerötete, entzündete ... Hautveränderungen")
_FINDING_ADJ: dict[str, str] = {
    "gerötet":       "gerötete",
    "entzündet":     "entzündete",
    "offene Stellen": "teils offene",
    "Kratzspuren":   None,   # handled separately as noun
    "Bläschenbildung": None, # handled separately as noun
    "verdickte Haut": None,  # handled separately
}

# Skin findings → noun when they don't work as adjectives before "Hautveränderungen"
_FINDING_NOUN: dict[str, str] = {
    "trockene Haut":   "trockener Haut",
    "Schuppung":       "Schuppung",
    "Kratzspuren":     "Kratzspuren",
    "Bläschenbildung": "Bläschenbildung",
    "verdickte Haut":  "verdickten Hautarealen",
}

# Sleep impact → noun for "durch ... beeinträchtigt"
_SLEEP_NOUN: dict[str, str] = {
    "Nachtschlaf beeinträchtigt":        None,   # handled as whole-sentence trigger
    "nächtliches Kratzen":               "nächtliches Kratzen",
    "Einschlafstörung durch Juckreiz":   "Einschlafstörungen",
    "Durchschlafstörung durch Juckreiz": "Durchschlafstörungen",
}

# Aggravating factors
_AGG_NOUN: dict[str, str] = {
    "Wärme":         "Wärme",
    "Überforderung": "Überforderung",
    "Müdigkeit":     "Müdigkeit",
    "Stress":        "Stress",
    "Herbst / Winter": "Herbst und Winter",
}

# Relieving factors
_REL_NOUN: dict[str, str] = {
    "Kühlung":           "Kühlung",
    "Ruhe":              "Ruhe",
    "Schonung":          "Schonung",
    "Wärme":             "Wärme",
    "Feuchtigkeitspflege": "Feuchtigkeitspflege",
}

# Associated features → sentence
_ASSOC_SENTENCE: dict[str, str] = {
    "Gesichtsschwellungen":  "Teilweise bestehen Gesichtsschwellungen.",
    "Hitzegefühl im Gesicht": "Begleitend wird ein Hitzegefühl im Gesicht beschrieben.",
    "psychisch belastend":   "Die Erkrankung wird als deutlich psychisch belastend beschrieben.",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compose_neurodermitis_narrative(shared_items: dict[str, list[str]]) -> str:
    """
    Build a German clinical description from shared_items.

    Returns 1–8 sentences ending with '.'.
    Never raises; returns "Neurodermitis." as minimal fallback.
    """
    sentences: list[str] = []

    # ── S1: course / background ───────────────────────────────────────────
    course_raw = _clean(shared_items.get("eczema_course", []))
    entity_items = [v for v in course_raw if v in _COURSE_ENTITY]
    mod_items    = [v for v in course_raw if v in _COURSE_MOD]

    if entity_items:
        entity = _COURSE_ENTITY[entity_items[0]]
        if mod_items:
            mod = _COURSE_MOD[mod_items[0]]
            sentences.append(f"Es besteht {entity} {mod}.")
        else:
            sentences.append(f"Es besteht {entity}.")
    else:
        sentences.append("Es bestehen chronische Hautbeschwerden im Sinne einer Neurodermitis.")

    # ── S2: pruritus ──────────────────────────────────────────────────────
    prurit_raw = _clean(shared_items.get("eczema_pruritus", []))
    if prurit_raw:
        # Determine noun
        prurit_noun = _DEFAULT_PRURITUS
        for v in prurit_raw:
            if v in _PRURITUS_NOUN:
                prurit_noun = _PRURITUS_NOUN[v]
                break

        # Quality modifiers (stechend/brennend)
        qualities = [_PRURITUS_QUALITY[v] for v in prurit_raw if v in _PRURITUS_QUALITY]

        # Timing
        timings = [_PRURITUS_TIMING[v] for v in prurit_raw if v in _PRURITUS_TIMING]

        if qualities:
            prurit_noun = f"teils {_und(qualities)} empfundener {prurit_noun}"

        s2 = f"Im Vordergrund steht {prurit_noun}"
        if timings:
            s2 += ", der vor allem " + _und(timings) + " auftritt"
        sentences.append(s2 + ".")

    # ── S3: affected areas ────────────────────────────────────────────────
    loc_raw = _clean(shared_items.get("eczema_locations", []))
    if loc_raw:
        display = [_LOCATION_DISPLAY.get(v, v) for v in loc_raw[:5]]
        sentences.append("Betroffen sind insbesondere " + _und(display) + ".")

    # ── S4: skin findings ─────────────────────────────────────────────────
    find_raw = _clean(shared_items.get("eczema_skin_findings", []))
    if find_raw:
        # Adjective group → "gerötete, entzündete Hautveränderungen"
        adj_group  = [_FINDING_ADJ[v]  for v in find_raw if v in _FINDING_ADJ and _FINDING_ADJ[v] is not None]
        # Noun group → listed after with "bei ..." or directly
        noun_group = [_FINDING_NOUN[v] for v in find_raw if v in _FINDING_NOUN]

        if adj_group and noun_group:
            sentences.append(
                "Begleitend bestehen "
                + _und(adj_group) + " Hautveränderungen"
                + " bei " + _und(noun_group) + "."
            )
        elif adj_group:
            sentences.append("Begleitend bestehen " + _und(adj_group) + " Hautveränderungen.")
        elif noun_group:
            sentences.append("Begleitend bestehen " + _und(noun_group) + ".")

    # ── S5: sleep impact ──────────────────────────────────────────────────
    sleep_raw = _clean(shared_items.get("eczema_sleep_impact", []))
    if sleep_raw:
        nouns = [_SLEEP_NOUN[v] for v in sleep_raw if v in _SLEEP_NOUN and _SLEEP_NOUN[v] is not None]
        has_night_impaired = "Nachtschlaf beeinträchtigt" in sleep_raw

        if nouns:
            sentences.append("Der Nachtschlaf ist durch " + _und(nouns) + " beeinträchtigt.")
        elif has_night_impaired:
            sentences.append("Der Nachtschlaf ist durch den Juckreiz beeinträchtigt.")

    # ── S6: aggravating + relieving ───────────────────────────────────────
    agg_raw = _clean(shared_items.get("eczema_aggravating_factors", []))
    rel_raw = _clean(shared_items.get("relieving_factors",          []))

    agg_nouns = [_AGG_NOUN.get(v, v) for v in agg_raw[:4]]
    rel_nouns = [_REL_NOUN.get(v, v) for v in rel_raw[:3]]

    if agg_nouns:
        sentences.append("Die Beschwerden werden durch " + _und(agg_nouns) + " verstärkt.")
    if rel_nouns:
        verb = "bringen" if len(rel_nouns) > 1 else "bringt"
        sentences.append(f"Linderung {verb} " + _und(rel_nouns) + ".")

    # ── S6b: associated features ──────────────────────────────────────────
    assoc_raw = _clean(shared_items.get("eczema_associated_features", []))
    for v in assoc_raw[:2]:
        sent = _ASSOC_SENTENCE.get(v)
        if sent:
            sentences.append(sent)

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
