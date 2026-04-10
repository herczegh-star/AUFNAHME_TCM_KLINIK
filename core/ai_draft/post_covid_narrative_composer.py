"""
post_covid_narrative_composer.py
----------------------------------
Dedicated composer for Post-COVID-Syndrom cluster.

Narrative structure (up to 8 sentences; only rendered when data present):
  S1: post-COVID framing (post_covid_course) + anchor
  S2: fatigue_core + fatigue_capacity (capacity/exhaustion sentence)
  S3: post_exertional_worsening  (crash/PEM sentence)
  S4: brain_fog_symptoms          ("Brain-Fog-Symptomatik mit ...")
  S5: sleep_nonrestorative        (quality + optional morning sentence)
  S6: post_covid_sensory_emotional
  S7: post_covid_vegetative
  S8: functional_impact           (first item, capitalised)

Rules:
  - No diagnosis generation
  - Only render what is explicitly present in shared_items
  - Filter sentinel values ("keine")
  - Post-COVID context must be established in S1
  - Brain Fog and PEM/Crash rendered as distinct named entities when present
  - Do not frame as ME/CFS or Depression
  - Verdichtungsstil: short, clinically natural German

Duration is handled by Route B in pilot_draft_service (inserted as
"seit X" before first sentence period) — not consumed here.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Render maps
# ---------------------------------------------------------------------------

# Opening framing phrase based on COVID course context
_COVID_INTRO: dict[str, str] = {
    "nach COVID-19-Infektion":
        "Vor dem Hintergrund einer durchgemachten COVID-19-Infektion",
    "seit COVID-19-Infektion":
        "Seit einer durchgemachten COVID-19-Infektion",
    "nach mehreren COVID-19-Infektionen":
        "Vor dem Hintergrund mehrerer durchgemachter COVID-19-Infektionen",
}

# Fatigue core: dative/genitive noun for "Es bestehen ..." construction
_FATIGUE_CORE_NOUN: dict[str, str] = {
    "erschöpft":         "ausgeprägte Erschöpfbarkeit",
    "energielos":        "Energielosigkeit",
    "rasch erschöpfbar": "rasche Erschöpfbarkeit",
    "chronisch erschöpft": "chronische Erschöpfung",
}

# Fatigue capacity + drive: nominative for "Es bestehen ..."
_FATIGUE_CAPACITY_NOUN: dict[str, str] = {
    "reduzierte Belastbarkeit":          "verminderte Belastbarkeit",
    "verminderte Leistungsfähigkeit":    "verminderte Leistungsfähigkeit",
    "Belastungsgrenze schneller erreicht": "früh erreichte Belastungsgrenze",
    "verminderter Antrieb":              "verminderter Antrieb",
}

# PEM / crash: noun phrase after "Zudem kommt es zu ..."
_PEW_NOUN: dict[str, str] = {
    "Crash-Phasen":
        "wiederkehrenden Crash-Phasen",
    "postbelastungsinduzierte Verschlechterung":
        "postbelastungsinduzierten Verschlechterungen",
    "starke Leistungseinbrüche nach Belastung":
        "starken Leistungseinbrüchen nach Belastung",
    "Erschöpfung nach körperlicher Aktivität":
        "Erschöpfung nach körperlicher Aktivität",
    "Erschöpfung nach geistiger Aktivität":
        "Erschöpfung nach geistiger Aktivität",
}

# Brain fog: dative noun after "Brain-Fog-Symptomatik mit ..."
_BRAIN_FOG_NOUN: dict[str, str] = {
    "kognitive Verlangsamung":    "kognitiver Verlangsamung",
    "Konzentrationsstörungen":    "Konzentrationsstörungen",
    "Merkfähigkeitsstörungen":    "Merkfähigkeitsstörungen",
    "Wortfindungsstörungen":      "Wortfindungsstörungen",
    "geistige Benommenheit":      "geistiger Benommenheit",
    "verminderte Aufmerksamkeit": "verminderter Aufmerksamkeit",
}

# Sleep quality: phrase after "Der Schlaf ist ..."
_SLEEP_QUALITY_PHRASE: dict[str, str] = {
    "nicht erholsamer Schlaf": "nicht erholsam",
    "Durchschlafstörungen":    "durch Durchschlafstörungen beeinträchtigt",
}

# Sleep morning: individual sentence
_SLEEP_MORNING_SENTENCE: dict[str, str] = {
    "morgens wie gerädert":  "Morgens besteht das Gefühl, wie gerädert zu sein.",
    "erschöpftes Erwachen":  "Das Erwachen am Morgen ist von ausgeprägter Erschöpfung geprägt.",
}

# Sensory/emotional: noun in "Begleitend bestehen ..."
_SENSORY_EMOTIONAL_NOUN: dict[str, str] = {
    "emotionale Empfindlichkeit": "erhöhte emotionale Empfindlichkeit",
    "Reizüberflutung":            "Reizüberflutung",
    "Geräuschsensibilität":       "Geräuschsensibilität",
    "innere Unruhe":              "innere Unruhe",
}

# Vegetative: noun in "Begleitend bestehen vegetative Beschwerden im Sinne von ..."
_VEGETATIVE_NOUN: dict[str, str] = {
    "Kälteempfindlichkeit":       "Kälteempfindlichkeit",
    "Herzrasen":                  "Herzrasen",
    "Schwindel":                  "Schwindel",
    "Übelkeit":                   "Übelkeit",
    "verschleimt nach Belastung": "Schleimbildung nach Belastung",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compose_post_covid_narrative(shared_items: dict[str, list[str]]) -> str:
    """
    Build a German clinical description from shared_items.

    Returns 1–8 sentences ending with '.'.
    Never raises; returns "Post-COVID-Symptomatik." as minimal fallback.
    """
    sentences: list[str] = []

    # ── S1: COVID framing + anchor ────────────────────────────────────────
    course = _clean(shared_items.get("post_covid_course", []))
    if course:
        intro = _COVID_INTRO.get(course[0], "Vor dem Hintergrund einer durchgemachten COVID-19-Infektion")
        s1 = f"{intro} besteht eine persistierende Post-COVID-Symptomatik"
    else:
        s1 = "Persistierende Post-COVID-Symptomatik"
    sentences.append(s1 + ".")

    # ── S2: fatigue core + capacity ───────────────────────────────────────
    core_raw     = _clean(shared_items.get("fatigue_core",     []))
    capacity_raw = _clean(shared_items.get("fatigue_capacity", []))

    core_nouns     = [_FATIGUE_CORE_NOUN.get(v, v)     for v in core_raw[:2]]
    capacity_nouns = [_FATIGUE_CAPACITY_NOUN.get(v, v) for v in capacity_raw[:2]]
    all_fatigue = core_nouns + capacity_nouns
    if all_fatigue:
        sentences.append("Es bestehen " + _und(all_fatigue) + ".")

    # ── S3: post-exertional worsening / crash ─────────────────────────────
    pew = _clean(shared_items.get("post_exertional_worsening", []))
    if pew:
        nouns = [_PEW_NOUN.get(v, v) for v in pew[:3]]
        sentences.append("Zudem kommt es zu " + _und(nouns) + ".")

    # ── S4: brain fog ─────────────────────────────────────────────────────
    fog = _clean(shared_items.get("brain_fog_symptoms", []))
    if fog:
        nouns = [_BRAIN_FOG_NOUN.get(v, v) for v in fog[:4]]
        sentences.append("Weiterhin besteht eine Brain-Fog-Symptomatik mit " + _und(nouns) + ".")

    # ── S5: sleep ─────────────────────────────────────────────────────────
    sleep = _clean(shared_items.get("sleep_nonrestorative", []))
    if sleep:
        quality_phrases = [_SLEEP_QUALITY_PHRASE[v] for v in sleep
                           if v in _SLEEP_QUALITY_PHRASE]
        if quality_phrases:
            sentences.append("Der Schlaf ist " + _und(quality_phrases) + ".")
        for v in sleep:
            sent = _SLEEP_MORNING_SENTENCE.get(v)
            if sent:
                sentences.append(sent)
                break  # only first morning sentence

    # ── S6: sensory / emotional sensitivity ──────────────────────────────
    sens = _clean(shared_items.get("post_covid_sensory_emotional", []))
    if sens:
        nouns = [_SENSORY_EMOTIONAL_NOUN.get(v, v) for v in sens[:3]]
        sentences.append("Begleitend bestehen " + _und(nouns) + ".")

    # ── S7: vegetative symptoms ───────────────────────────────────────────
    veg = _clean(shared_items.get("post_covid_vegetative", []))
    if veg:
        nouns = [_VEGETATIVE_NOUN.get(v, v) for v in veg[:3]]
        sentences.append(
            "Begleitend bestehen vegetative Beschwerden im Sinne von "
            + _und(nouns) + "."
        )

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
