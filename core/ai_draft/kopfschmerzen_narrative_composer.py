"""
kopfschmerzen_narrative_composer.py
------------------------------------
Dedicated composer for Kopfschmerzen cluster.

Narrative structure (2–4 sentences; only produced when data present):
  S1: Kopfschmerzen + headache_localisation + pain_character
  S2: frequency_pattern + episode_duration
  S3: aggravating_factors + relieving_factors
  S4: accompanying_symptoms

Rules:
  - No diagnosis generation
  - No migraine-specific interpretation
  - Only render what is explicitly present in shared_items
  - Filter sentinel values ("keine")
  - Verdichtungsstil: short, clinically natural German

Duration is handled by Route B in pilot_draft_service (inserted as
"seit X" before first sentence period) — not consumed here.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Render maps
# ---------------------------------------------------------------------------

_LOCALISATION_PHRASE: dict[str, str] = {
    "frontal":               "frontal",
    "temporal":              "temporal",
    "okzipital":             "okzipital",
    "diffus":                "diffus",
    "Schläfenbereich":       "im Schläfenbereich",
    "einseitig rechts":      "einseitig rechts",
    "einseitig links":       "einseitig links",
    "beidseits":             "beidseits",
    "wechselnd rechts / links": "wechselnd rechts/links",
}

_CHARACTER_ADJECTIVE: dict[str, str] = {
    "ziehend":    "ziehender",
    "drückend":   "drückender",
    "pochend":    "pochender",
    "pulsierend": "pulsierender",
    "stechend":   "stechender",
    "dumpf":      "dumpfer",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compose_kopfschmerzen_narrative(shared_items: dict[str, list[str]]) -> str:
    """
    Build a German clinical description from shared_items.

    Returns 1–4 sentences ending with '.'.
    Never raises; returns "Kopfschmerzen." as minimal fallback.
    """
    sentences: list[str] = []

    # ── S1: anchor + localisation + character ────────────────────────────
    loc_raw  = _clean(shared_items.get("headache_localisation", []))
    char_raw = _clean(shared_items.get("pain_character", []))

    loc_phrases  = [_LOCALISATION_PHRASE.get(v, v) for v in loc_raw[:2]]
    char_adjs    = [_CHARACTER_ADJECTIVE.get(v, v) for v in char_raw[:3]]

    s1 = "Kopfschmerzen"
    if loc_phrases:
        s1 += " " + ", ".join(loc_phrases)
    if char_adjs:
        s1 += " von " + _und(char_adjs) + " Qualität"
    sentences.append(s1 + ".")

    # ── S2: frequency + episode_duration ─────────────────────────────────
    freq = _clean(shared_items.get("frequency_pattern", []))
    ep   = _clean(shared_items.get("episode_duration",  []))

    if freq and ep:
        sentences.append(f"Diese treten {freq[0]} auf und halten {ep[0]} an.")
    elif freq:
        sentences.append(f"Diese treten {freq[0]} auf.")
    elif ep:
        sentences.append(f"Die Episoden halten {ep[0]} an.")

    # ── S3: aggravating + relieving ───────────────────────────────────────
    agg = _clean(shared_items.get("aggravating_factors", []))
    rel = _clean(shared_items.get("relieving_factors",   []))

    if agg or rel:
        parts: list[str] = []
        if agg:
            parts.append(f"verstärkt durch {_und(agg[:2])}")
        if rel:
            parts.append(f"gebessert durch {_und(rel[:2])}")
        s3 = ", ".join(parts)
        sentences.append(s3[0].upper() + s3[1:] + ".")

    # ── S4: accompanying symptoms ─────────────────────────────────────────
    acc = _clean(shared_items.get("accompanying_symptoms", []))
    if acc:
        sentences.append(f"Teilweise mit {_und(acc[:3])} verbunden.")

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
