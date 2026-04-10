"""
muedigkeitssymptomatik_narrative_composer.py
---------------------------------------------
Dedicated composer for Müdigkeitssymptomatik / chronische Erschöpfung cluster.

Narrative structure (up to 6 sentences; only rendered when data present):
  S1: anchor + fatigue_core + fatigue_capacity + drive_reduction  (combined)
  S2: fatigue_cognition
  S3: sleep_nonrestorative
  S4: fatigue_emotional_overlay
  S5: fatigue_vegetative
  S6: functional_impact  (first item, capitalised)

Rules:
  - No diagnosis generation
  - Only render what is explicitly present in shared_items
  - Filter sentinel values ("keine")
  - Exhaustion character — not psychiatric, not ME/CFS, not Post-COVID framing
  - Emotional overlay: brief and secondary, never dominant
  - Verdichtungsstil: short, clinically natural German

Duration is handled by Route B in pilot_draft_service (inserted as
"seit X" before first sentence period) — not consumed here.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Render maps
# ---------------------------------------------------------------------------

# Dative/genitive noun for "mit ..." construction in S1
_FATIGUE_CORE_NOUN: dict[str, str] = {
    "erschöpft":       "ausgeprägter Erschöpfbarkeit",
    "müde":            "anhaltender Müdigkeit",
    "energielos":      "Energielosigkeit",
    "rasch erschöpfbar": "rascher Erschöpfbarkeit",
    "chronisch erschöpft": "chronischer Erschöpfung",
}

_FATIGUE_CAPACITY_NOUN: dict[str, str] = {
    "reduzierte Belastbarkeit":          "verminderter Belastbarkeit",
    "verminderte Leistungsfähigkeit":    "verminderter Leistungsfähigkeit",
    "Belastungsgrenze schneller erreicht": "früh erreichter Belastungsgrenze",
    "kaum alltagsfähig":                 "stark eingeschränkter Alltagsfähigkeit",
    "schafft nur das Nötigste":          "stark eingeschränkter Alltagsfähigkeit",
}

_DRIVE_NOUN: dict[str, str] = {
    "verminderter Antrieb":   "vermindertem Antrieb",
    "antriebslos":            "Antriebslosigkeit",
    "erschwerte Aktivierung": "erschwerter Aktivierung",
}

# Sleep: items that describe main sleep quality → phrase after "Der Schlaf ist ..."
_SLEEP_QUALITY_PHRASE: dict[str, str] = {
    "nicht erholsamer Schlaf": "nicht erholsam",
    "Durchschlafstörungen":    "durch Durchschlafstörungen beeinträchtigt",
}

# Sleep: morning-experience items → rendered as separate sentence
_SLEEP_MORNING_SENTENCE: dict[str, str] = {
    "morgens wie gerädert": "Morgens besteht das Gefühl, wie gerädert zu sein.",
    "erschöpftes Erwachen": "Das Erwachen am Morgen ist von ausgeprägter Erschöpfung geprägt.",
}

# Emotional overlay → noun in "Begleitend bestehen ..."
_EMOTIONAL_NOUN: dict[str, str] = {
    "innere Unruhe":          "innere Unruhe",
    "emotionale Instabilität": "emotionale Instabilität",
    "Abschalten erschwert":   "Schwierigkeiten beim Abschalten",
    "gedrückte Stimmung":     "phasenweise gedrückte Stimmung",
    "schwankende Stimmung":   "schwankende Stimmung",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compose_muedigkeitssymptomatik_narrative(shared_items: dict[str, list[str]]) -> str:
    """
    Build a German clinical description from shared_items.

    Returns 1–6 sentences ending with '.'.
    Never raises; returns "Müdigkeitssymptomatik." as minimal fallback.
    """
    sentences: list[str] = []

    # ── S1: anchor + core exhaustion + capacity + drive ───────────────────
    core_raw     = _clean(shared_items.get("fatigue_core",     []))
    capacity_raw = _clean(shared_items.get("fatigue_capacity", []))
    drive_raw    = _clean(shared_items.get("drive_reduction",  []))

    core_nouns     = [_FATIGUE_CORE_NOUN.get(v, v)     for v in core_raw[:2]]
    capacity_nouns = [_FATIGUE_CAPACITY_NOUN.get(v, v) for v in capacity_raw[:2]]
    drive_nouns    = [_DRIVE_NOUN.get(v, v)             for v in drive_raw[:1]]

    all_nouns = core_nouns + capacity_nouns + drive_nouns
    if all_nouns:
        s1 = "Chronische Müdigkeitssymptomatik mit " + _und(all_nouns)
    else:
        s1 = "Chronische Müdigkeitssymptomatik"
    sentences.append(s1 + ".")

    # ── S2: cognition ─────────────────────────────────────────────────────
    cogn = _clean(shared_items.get("fatigue_cognition", []))
    if cogn:
        sentences.append("Zudem bestehen " + _und(cogn[:3]) + ".")

    # ── S3: sleep ─────────────────────────────────────────────────────────
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

    # ── S4: emotional overlay ─────────────────────────────────────────────
    emotional = _clean(shared_items.get("fatigue_emotional_overlay", []))
    if emotional:
        nouns = [_EMOTIONAL_NOUN.get(v, v) for v in emotional[:3]]
        sentences.append("Begleitend bestehen " + _und(nouns) + ".")

    # ── S5: vegetative symptoms ───────────────────────────────────────────
    veg = _clean(shared_items.get("fatigue_vegetative", []))
    if veg:
        sentences.append(
            "Begleitend bestehen vegetative Beschwerden im Sinne von "
            + _und(veg[:3]) + "."
        )

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
