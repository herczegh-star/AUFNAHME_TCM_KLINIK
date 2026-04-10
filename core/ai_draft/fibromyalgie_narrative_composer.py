"""
fibromyalgie_narrative_composer.py
------------------------------------
Dedicated composer for Fibromyalgie / Ganzkörperschmerzen cluster.

Narrative structure (up to 7 sentences; only rendered when data present):
  S1: anchor + pain_distribution_fibro
      (+ separate "kein Hauptschmerz" sentence when selected)
  S2: pain_character + fibro_pain_pattern  (character/mode sentence)
  S3: fibro_main_areas                     ("Besonders betroffen sind ...")
  S4: fibro_tenderness                     ("Es besteht ...")
  S5: fibro_aggravating_factors + relieving_factors  (combined)
  S6: fibro_stiffness + fibro_seasonality
  S7: functional_impact                    (first item, capitalised)

Rules:
  - No diagnosis generation
  - Only render what is explicitly present in shared_items
  - Filter sentinel values ("keine")
  - Diffuse / multilocular nature must come through in the opening
  - Druckempfindlichkeit rendered as a named entity when present
  - Wärme/Kälte contrast rendered when both sides are present
  - Verdichtungsstil: short, clinically natural German

Duration is handled by Route B in pilot_draft_service (inserted as
"seit X" before first sentence period) — not consumed here.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Render maps
# ---------------------------------------------------------------------------

# Distribution qualifiers → adjective fragment used in S1
# Only values that work as pre-noun adjectives are listed here.
# "wechselnde Schmerzlokalisation" and "Ganzkörperschmerzen" are handled
# as suffixes / anchor noun respectively, not as adjectives.
_DISTRIBUTION_ADJ: dict[str, str] = {
    "diffuse Schmerzen": "diffuse",
    "multilokulär":      "multilokuläre",
}
# "kein Hauptschmerz" is handled separately below

_CHARACTER_ADJECTIVE: dict[str, str] = {
    "brennend":    "brennender",
    "stechend":    "stechender",
    "drückend":    "drückender",
    "ziehend":     "ziehender",
    "dumpf":       "dumpfer",
    "bohrend":     "bohrender",
    "krampfartig": "krampfartiger",
}

# Pain pattern → noun phrase in "Die Beschwerden treten ... auf"
_PAIN_PATTERN_PHRASE: dict[str, str] = {
    "dauerhaft":              "dauerhaft",
    "attackenartig":          "attackenartig",
    "wechselnde Schmerzqualität": "mit wechselnder Intensität und Qualität",
    "Muskelkatergefühl":      "begleitet von Muskelkatergefühl",
}

# Main areas → phrase in "Besonders betroffen sind ..."
_AREA_PHRASE: dict[str, str] = {
    "gesamte Wirbelsäule":     "die gesamte Wirbelsäule",
    "Schultern / Arme":        "die Schultern und Arme",
    "Oberschenkel":            "die Oberschenkel",
    "Beine":                   "die Beine",
    "Knie":                    "die Knie",
    "Füße / Mittelfußbereich": "die Füße und den Mittelfußbereich",
}

# Aggravating: phrase after "bei ..."
_AGG_PHRASE: dict[str, str] = {
    "dynamische Belastung":      "dynamischer Belastung",
    "längeres Gehen":            "längerem Gehen",
    "längeres Sitzen":           "längerem Sitzen",
    "unveränderte Körperposition": "unveränderter Körperposition",
    "Kälte":                     "Kälte",
}

_RELIEVING_NOUN: dict[str, str] = {
    "Wärme":         "Wärme",
    "Ruhe":          "Ruhe",
    "Schonung":      "Schonung",
    "Bewegung":      "leichte Bewegung",
    "Physiotherapie": "Physiotherapie",
    "Entspannung":   "Entspannung",
}

# Stiffness → noun in "Begleitend bestehen ..."
_STIFFNESS_NOUN: dict[str, str] = {
    "Morgensteifigkeit":              "Morgensteifigkeit",
    "Steifigkeit nach längerem Sitzen": "Steifigkeit nach längerem Sitzen",
    "Steifigkeit nach Inaktivität":   "Steifigkeit nach längerer Inaktivität",
}

# Seasonality → complete sentence
_SEASONALITY_SENTENCE: dict[str, str] = {
    "in warmer Jahreszeit milder":
        "In der wärmeren Jahreszeit sind die Beschwerden milder.",
    "in kalter Jahreszeit stärker":
        "In der kalten Jahreszeit verstärken sich die Beschwerden.",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compose_fibromyalgie_narrative(shared_items: dict[str, list[str]]) -> str:
    """
    Build a German clinical description from shared_items.

    Returns 1–8 sentences ending with '.'.
    Never raises; returns "Ganzkörperschmerzen." as minimal fallback.
    """
    sentences: list[str] = []

    # ── S1: anchor + distribution ─────────────────────────────────────────
    dist_raw = _clean(shared_items.get("pain_distribution_fibro", []))
    no_main  = "kein Hauptschmerz" in dist_raw
    dist_filtered = [v for v in dist_raw if v != "kein Hauptschmerz"]

    adjs = [_DISTRIBUTION_ADJ[v] for v in dist_filtered if v in _DISTRIBUTION_ADJ]
    has_wechselnd = "wechselnde Schmerzlokalisation" in dist_filtered

    if adjs:
        s1 = ", ".join(adjs).capitalize() + " Ganzkörperschmerzen"
    else:
        s1 = "Ganzkörperschmerzen"
    if has_wechselnd:
        s1 += " mit wechselnder Lokalisation"
    sentences.append(s1 + ".")

    if no_main:
        sentences.append("Ein führender Einzelschmerz lässt sich nicht benennen.")

    # ── S2: pain character + pain pattern ────────────────────────────────
    char_raw    = _clean(shared_items.get("pain_character",    []))
    pattern_raw = _clean(shared_items.get("fibro_pain_pattern", []))

    char_adjs    = [_CHARACTER_ADJECTIVE.get(v, v) for v in char_raw[:3]]
    pattern_phrases = [_PAIN_PATTERN_PHRASE.get(v, v) for v in pattern_raw[:2]]

    if char_adjs and pattern_phrases:
        sentences.append(
            "Die Schmerzen sind von " + _und(char_adjs) + " Qualität"
            + " und treten " + _und(pattern_phrases) + " auf."
        )
    elif char_adjs:
        sentences.append("Die Schmerzen sind von " + _und(char_adjs) + " Qualität.")
    elif pattern_phrases:
        sentences.append("Die Beschwerden treten " + _und(pattern_phrases) + " auf.")

    # ── S3: main areas ────────────────────────────────────────────────────
    areas = _clean(shared_items.get("fibro_main_areas", []))
    if areas:
        area_phrases = [_AREA_PHRASE.get(v, v) for v in areas[:4]]
        sentences.append("Besonders betroffen sind " + _und(area_phrases) + ".")

    # ── S4: tenderness ────────────────────────────────────────────────────
    tenderness = _clean(shared_items.get("fibro_tenderness", []))
    if tenderness:
        sentences.append("Es besteht " + tenderness[0] + ".")

    # ── S5: aggravating + relieving ───────────────────────────────────────
    agg = _clean(shared_items.get("fibro_aggravating_factors", []))
    rel = _clean(shared_items.get("relieving_factors",         []))

    agg_phrases = [_AGG_PHRASE.get(v, v) for v in agg[:3]]
    rel_nouns   = [_RELIEVING_NOUN.get(v, v) for v in rel[:3]]

    if agg_phrases and rel_nouns:
        sentences.append(
            "Die Beschwerden verstärken sich bei " + _und(agg_phrases)
            + "; Linderung bringen " + _und(rel_nouns) + "."
        )
    elif agg_phrases:
        sentences.append("Die Beschwerden verstärken sich bei " + _und(agg_phrases) + ".")
    elif rel_nouns:
        sentences.append("Linderung bringen " + _und(rel_nouns) + ".")

    # ── S6: stiffness + seasonality ───────────────────────────────────────
    stiffness  = _clean(shared_items.get("fibro_stiffness",   []))
    seasonality = _clean(shared_items.get("fibro_seasonality", []))

    if stiffness:
        nouns = [_STIFFNESS_NOUN.get(v, v) for v in stiffness[:3]]
        verb = "besteht" if len(nouns) == 1 else "bestehen"
        sentences.append(f"Begleitend {verb} " + _und(nouns) + ".")

    if seasonality:
        sent = _SEASONALITY_SENTENCE.get(seasonality[0])
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
