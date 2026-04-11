"""
tinnitus_narrative_composer.py
--------------------------------
Dedicated composer for Tinnitus aurium cluster.

Narrative structure (3–4 sentences; only rendered when data present):
  S1: laterality + tinnitus_character  → "Es besteht ein [lat] Tinnitus aurium in Form [char]."
  S2: tinnitus_presence                → presence / intensity pattern
  S3: tinnitus_triggers                → aggravating factors

Rules:
  - No diagnosis generation
  - Only render what is explicitly present in shared_items
  - Filter sentinel values ("keine")
  - Verdichtungsstil: concise, clinically natural German

Duration is handled by Route B in pilot_draft_service (inserted as
"seit X" before first sentence period) — not consumed here.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Render maps
# ---------------------------------------------------------------------------

# Laterality → adjective preceding "Tinnitus aurium"
_LATERAL_ADJ: dict[str, str] = {
    "beidseitig": "beidseitiger",
    "links":      "linksseitiger",
    "rechts":     "rechtsseitiger",
}

# Sound character → genitive phrase after "in Form ..."
_CHARACTER_GEN: dict[str, str] = {
    "hohes Pfeifen":      "eines hohen Pfeifens",
    "hochtoniges Pfeifen": "eines hochtonigen Pfeifens",
    "Rauschen":           "eines Rauschens",
    "hohes Rauschen":     "eines hohen Rauschens",
    "Summen":             "eines Summens",
    "Zischen":            "eines Zischens",
}

# Presence items → phrase used inside S2
_PRESENCE_PHRASE: dict[str, str] = {
    "kontinuierlich vorhanden": "kontinuierlich präsent",
    "Tag und Nacht vorhanden":  "Tag und Nacht vorhanden",
    "wechselnde Intensität":    "wechselnde Intensität",
    "intermittierend":          "intermittierend auftretend",
}

# Trigger → dative/genitive phrase after "unter ... / bei ..."
_TRIGGER_PHRASE: dict[str, str] = {
    "Stress":                  "Stress",
    "psychische Belastung":    "psychischer Belastung",
    "berufliche Belastung":    "beruflicher Belastung",
    "aktuelle psychische Lage": "der aktuellen psychischen Lage",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compose_tinnitus_narrative(shared_items: dict[str, list[str]]) -> str:
    """
    Build a German clinical description from shared_items.

    Returns 1–3 sentences ending with '.'.
    Never raises; returns "Tinnitus aurium." as minimal fallback.
    """
    sentences: list[str] = []

    # ── S1: laterality + character ────────────────────────────────────────
    lat_raw  = _clean(shared_items.get("tinnitus_laterality", []))
    char_raw = _clean(shared_items.get("tinnitus_character",  []))

    lat_adj    = _LATERAL_ADJ.get(lat_raw[0]) if lat_raw else None
    char_items = [_CHARACTER_GEN[v] for v in char_raw[:2] if v in _CHARACTER_GEN]

    if lat_adj:
        s1 = f"Es besteht ein {lat_adj} Tinnitus aurium"
    else:
        s1 = "Es besteht ein Tinnitus aurium"

    if len(char_items) == 1:
        s1 += f" in Form {char_items[0]}"
    elif len(char_items) == 2:
        # "in Form eines Rauschens beziehungsweise hochtonigen Pfeifens"
        s1 += f" in Form {char_items[0]} beziehungsweise {char_items[1]}"

    sentences.append(s1 + ".")

    # ── S2: presence / intensity ──────────────────────────────────────────
    pres_raw = _clean(shared_items.get("tinnitus_presence", []))
    if pres_raw:
        phrases = [_PRESENCE_PHRASE.get(v, v) for v in pres_raw[:3]]
        # Split presence vs intensity into natural sentence
        # "Die Ohrgeräusche sind [presence]; sie zeigen [intensity]."
        presence_parts = [p for p in phrases if p != "wechselnde Intensität"]
        has_wechselnde = "wechselnde Intensität" in phrases

        if presence_parts and has_wechselnde:
            sentences.append(
                "Die Ohrgeräusche sind " + _und(presence_parts)
                + " und zeigen eine wechselnde Intensität."
            )
        elif presence_parts:
            sentences.append("Die Ohrgeräusche sind " + _und(presence_parts) + ".")
        elif has_wechselnde:
            sentences.append("Die Intensität der Ohrgeräusche ist wechselnd.")

    # ── S3: triggers ──────────────────────────────────────────────────────
    trig_raw = _clean(shared_items.get("tinnitus_triggers", []))
    if trig_raw:
        phrases = [_TRIGGER_PHRASE.get(v, v) for v in trig_raw[:3]]
        sentences.append(
            "Eine Zunahme der Beschwerden zeigt sich vor allem unter "
            + _und(phrases) + "."
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
