"""
lws_narrative_composer.py
-------------------------
Pilot narrative composer for LWS-Syndrom.

Renders shared_pain_items_selected into a single German clinical sentence.
Verdichtungsstil — short, structured, no diagnostic inference.

Supported modules:
  pain_temporality, pain_character, pain_laterality,
  pain_radiation, aggravating_mechanical, relieving_passive

All other modules are silently ignored.

ORDERING PRINCIPLE
------------------
Input keys are alpha-sorted (internal deterministic order — selector convention).
This composer applies clinical narrative order regardless of input key order:
  1. temporality   (adjective prefix, if present)
  2. character     (integrated into anchor noun phrase)
  3. anchor        "Schmerzen im LWS-Bereich"
  4. laterality    (appended to anchor)
  5. radiation     (prepositional phrase, no comma)
  6. aggravating   ("verstärkt bei ...")
  7. relieving     ("gebessert durch ...")

API
---
  from core.ai_draft.lws_narrative_composer import compose_lws_narrative

  result = compose_lws_narrative(shared_items)   # str

ISOLATION
---------
No dependency on DraftComposer.
No side effects on draft_text or blocks_used.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Render maps  (canonical id → German phrase fragment)
# ---------------------------------------------------------------------------

# Adjective forms for pain character (agrees with "Schmerzen", nominative plural)
_CHARACTER_ADJECTIVE: dict[str, str] = {
    "ziehend":        "ziehende",
    "stechend":       "stechende",
    "dumpf":          "dumpfe",
    "brennend":       "brennende",
    "krampfartig":    "krampfartige",
    "drueckend":      "drückende",
    "elektrisierend": "elektrisierende",
    "pulsierend":     "pulsierende",
}

# Radiation: full prepositional phrase
_RADIATION_PHRASE: dict[str, str] = {
    "radiation":             "mit Ausstrahlung",
    "Bein":                  "mit Ausstrahlung ins Bein",
    "Gesäß":                 "mit Ausstrahlung ins Gesäß",
    "Arm":                   "mit Ausstrahlung in den Arm",
    "Schulter":              "mit Ausstrahlung in die Schulter",
    "Leiste":                "mit Ausstrahlung in die Leiste",
    "Unterbauch":            "mit Ausstrahlung in den Unterbauch",
    # LWS-specific extended targets
    "linkes_bein_bis_ferse": "mit Ausstrahlung ins linke Bein bis zur Ferse",
    "rechtes_bein_bis_ferse":"mit Ausstrahlung ins rechte Bein bis zur Ferse",
    "linkes_bein":           "mit Ausstrahlung ins linke Bein",
    "rechtes_bein":          "mit Ausstrahlung ins rechte Bein",
    "gesaess_links":         "mit Ausstrahlung ins linke Gesäß",
    "gesaess_rechts":        "mit Ausstrahlung ins rechte Gesäß",
}

# Aggravating mechanical: dative object after "verstärkt bei ..."
_AGG_MECH_DATIVE: dict[str, str] = {
    "langes_sitzen":   "langem Sitzen",
    "langes_stehen":   "langem Stehen",
    "langes_gehen":    "langem Gehen",
    "buecken":         "Bücken",
    "treppensteigen":  "Treppensteigen",
    "belastung":       "körperlicher Belastung",
}

# Relieving passive: noun after "gebessert durch ..."
_RELIEVING_NOUN: dict[str, str] = {
    "waerme":    "Wärme",
    "ruhe":      "Ruhe",
    "liegen":    "Liegen",
    "bewegung":  "leichter Bewegung",
}

# Temporality: adjective prefix (agrees with "Schmerzen", nominative plural)
_TEMPORALITY_ADJECTIVE: dict[str, str] = {
    "chronisch":           "Chronische",
    "intermittierend":     "Intermittierende",
    "belastungsabhaengig": "Belastungsabhängige",
    "progredient":         "Progrediente",
}

_ANCHOR = "Schmerzen im LWS-Bereich"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compose_lws_narrative(shared_items: dict[str, list[str]]) -> str:
    """
    Render shared_pain_items_selected into a single German clinical sentence.

    Input: dict with alpha-sorted keys and values (selector convention).
    Output: one sentence, Verdichtungsstil, ending with '.'.

    Unknown canonicals in any module are silently skipped.
    Returns the anchor sentence "Schmerzen im LWS-Bereich." if no items match.
    """
    # ── 1. Temporality ───────────────────────────────────────────────────
    temporality_adj = _resolve_temporality(shared_items.get("pain_temporality", []))

    # ── 2. Character adjectives ──────────────────────────────────────────
    char_adjs = _resolve_character(shared_items.get("pain_character", []))

    # ── 3+4. Anchor noun phrase (character + anchor + laterality) ────────
    noun_phrase = _build_noun_phrase(temporality_adj, char_adjs, shared_items.get("pain_laterality", []))

    # ── 5. Radiation ─────────────────────────────────────────────────────
    radiation_phrase = _resolve_radiation(shared_items.get("pain_radiation", []))

    # ── 6. Aggravating ───────────────────────────────────────────────────
    agg_phrase = _resolve_aggravating(shared_items.get("aggravating_mechanical", []))

    # ── 7. Relieving ─────────────────────────────────────────────────────
    rel_phrase = _resolve_relieving(shared_items.get("relieving_passive", []))

    # ── Assemble ─────────────────────────────────────────────────────────
    return _assemble(noun_phrase, radiation_phrase, agg_phrase, rel_phrase)


# ---------------------------------------------------------------------------
# Private: segment resolvers
# ---------------------------------------------------------------------------

def _resolve_temporality(items: list[str]) -> str | None:
    """Return adjective form of the first recognised temporality item, or None."""
    for item in items:
        adj = _TEMPORALITY_ADJECTIVE.get(item)
        if adj:
            return adj
    return None


def _resolve_character(items: list[str]) -> list[str]:
    """Return adjective forms for recognised character items (max 2)."""
    result: list[str] = []
    for item in items[:2]:
        adj = _CHARACTER_ADJECTIVE.get(item)
        if adj:
            result.append(adj)
    return result


def _resolve_radiation(items: list[str]) -> str | None:
    """Return the radiation prepositional phrase, or None.

    The bare canonical 'radiation' (no specific anatomical target) is
    intentionally suppressed — it signals presence in the block selector
    but carries no renderable target for Verdichtungsstil narrative.
    """
    for item in items[:1]:
        if item == "radiation":
            return None  # no specific target — suppress
        phrase = _RADIATION_PHRASE.get(item)
        if phrase:
            return phrase
    return None


def _resolve_aggravating(items: list[str]) -> str | None:
    """Return 'verstärkt bei <dative>' for the first recognised item, or None."""
    for item in items[:1]:
        dative = _AGG_MECH_DATIVE.get(item)
        if dative:
            return f"verstärkt bei {dative}"
    return None


def _resolve_relieving(items: list[str]) -> str | None:
    """Return 'gebessert durch <noun>' for the first recognised item, or None."""
    for item in items[:1]:
        noun = _RELIEVING_NOUN.get(item)
        if noun:
            return f"gebessert durch {noun}"
    return None


# ---------------------------------------------------------------------------
# Private: noun phrase builder
# ---------------------------------------------------------------------------

def _build_noun_phrase(
    temporality_adj: str | None,
    char_adjs:       list[str],
    laterality:      list[str],
) -> str:
    """
    Build the core noun phrase:
      [Temporality, ][Character ]Schmerzen im LWS-Bereich[ laterality]

    Temporality and character are adjective modifiers on "Schmerzen":
      - with both:    "Chronische, ziehende Schmerzen im LWS-Bereich"
      - temporality only: "Chronische Schmerzen im LWS-Bereich"
      - character only:   "Ziehende Schmerzen im LWS-Bereich"
      - neither:          "Schmerzen im LWS-Bereich"
    """
    adjectives: list[str] = []

    if temporality_adj:
        adjectives.append(temporality_adj)
    if char_adjs:
        if len(char_adjs) == 1:
            adjectives.append(char_adjs[0])
        else:
            # "stechende und ziehende" — join with " und ", lowercase all but first
            adjectives.append(f"{char_adjs[0]} und {char_adjs[1]}")

    if adjectives:
        # First adjective is capitalised (sentence start), rest lowercase
        adj_str = _join_adjectives(adjectives)
        noun_phrase = f"{adj_str} Schmerzen im LWS-Bereich"
    else:
        noun_phrase = _ANCHOR  # "Schmerzen im LWS-Bereich"

    # Append laterality
    if laterality:
        side = laterality[0]
        if side in {"links", "rechts", "beidseits"}:
            noun_phrase += f" {side}"

    return noun_phrase


def _join_adjectives(adjectives: list[str]) -> str:
    """
    Join adjective list into a comma-separated string suitable for sentence start.
    e.g. ["Chronische", "ziehende"] → "Chronische, ziehende"
         ["Chronische"]             → "Chronische"
    """
    if not adjectives:
        return ""
    # First element capitalised, rest lowercase (they are mid-phrase modifiers)
    parts = [adjectives[0]] + [a[0].lower() + a[1:] for a in adjectives[1:]]
    return ", ".join(parts)


# ---------------------------------------------------------------------------
# Private: sentence assembler
# ---------------------------------------------------------------------------

def _assemble(
    noun_phrase:      str,
    radiation_phrase: str | None,
    agg_phrase:       str | None,
    rel_phrase:       str | None,
) -> str:
    """
    Assemble the final sentence.

    Structure:
      <noun_phrase>[ <radiation_phrase>][, <agg_phrase>][, <rel_phrase>].

    Radiation attaches directly to the noun phrase (no comma — it is a
    prepositional attribute of the noun, not a separate predicate).
    Aggravating and relieving are comma-separated predicates.
    """
    sentence = noun_phrase

    if radiation_phrase:
        sentence += f" {radiation_phrase}"

    predicates = [p for p in (agg_phrase, rel_phrase) if p]
    if predicates:
        sentence += ", " + ", ".join(predicates)

    sentence += "."

    # Ensure capital first letter (guard for edge cases)
    return sentence[0].upper() + sentence[1:]
