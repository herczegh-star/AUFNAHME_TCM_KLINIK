"""
lws_narrative_composer.py
-------------------------
Pilot narrative composer for LWS-Syndrom.

Renders shared_pain_items_selected into a single German clinical sentence.
Verdichtungsstil — short, structured, no diagnostic inference.

Supported modules:
  pain_temporality, pain_character, pain_laterality,
  pain_radiation, aggravating_mechanical, relieving_passive,
  functional_impact

All other modules are silently ignored.

RENDER MAPS
-----------
All phrase lookups are driven by cluster.render_maps loaded from
data/unified_clusters/lws_syndrom_v1_1.json (or its .edited.json override).
The Python code contains only structural/ordering logic — no German phrases.

Sections used from render_maps:
  character_adjective   — canonical → adjective form ("ziehend" → "ziehende")
  radiation_phrase      — canonical → prepositional phrase
  aggravating_dative    — canonical → dative object after "verstärkt bei"
  relieving_noun        — canonical → noun after "gebessert durch"
  temporality_adjective — canonical → adjective prefix
  functional_phrase     — canonical → functional sentence fragment

Missing section: all items in that module silently produce no output (empty map).
Missing key within a section: that specific canonical is silently skipped.
This is intentional — unknown canonicals are always silent no-ops.

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
  8. functional    (second sentence: "Sitztoleranz eingeschränkt." etc.)

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
# Render maps — loaded lazily from the LWS unified cluster JSON.
# All phrase output is driven from cluster.render_maps, not from Python dicts.
# ---------------------------------------------------------------------------

_render_maps: dict | None = None


def _get_render_maps() -> dict:
    """
    Return the render_maps dict from the LWS unified cluster.
    Loaded on first call; cached for the process lifetime.
    Bust the cache by calling _invalidate_render_maps_cache() (tests only).
    """
    global _render_maps
    if _render_maps is None:
        from services.unified_cluster_service import load_lws
        _render_maps = load_lws().render_maps
    return _render_maps


def _invalidate_render_maps_cache() -> None:
    """Force render_maps reload on next call. For tests only."""
    global _render_maps
    _render_maps = None


# Anchor is the stable clinical identity of this cluster — not a render phrase.
_ANCHOR = "Schmerzen im LWS-Bereich"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compose_lws_narrative(shared_items: dict[str, list[str]]) -> str:
    """
    Render shared_pain_items_selected into a single German clinical sentence.

    Input: dict with alpha-sorted keys and values (selector convention).
    Output: one or two sentences, Verdichtungsstil, ending with '.'.

    Unknown canonicals in any module are silently skipped.
    Returns the anchor sentence "Schmerzen im LWS-Bereich." if no items match.
    """
    rm = _get_render_maps()

    # ── 1. Temporality ───────────────────────────────────────────────────
    temporality_adj = _resolve_temporality(
        shared_items.get("pain_temporality", []),
        rm.get("temporality_adjective", {}),
    )

    # ── 2. Character adjectives ──────────────────────────────────────────
    char_adjs = _resolve_character(
        shared_items.get("pain_character", []),
        rm.get("character_adjective", {}),
    )

    # ── 3+4. Anchor noun phrase (character + anchor + laterality) ────────
    noun_phrase = _build_noun_phrase(
        temporality_adj, char_adjs, shared_items.get("pain_laterality", [])
    )

    # ── 5. Radiation ─────────────────────────────────────────────────────
    radiation_phrase = _resolve_radiation(
        shared_items.get("pain_radiation", []),
        rm.get("radiation_phrase", {}),
    )

    # ── 6. Aggravating ───────────────────────────────────────────────────
    agg_phrase = _resolve_aggravating(
        shared_items.get("aggravating_mechanical", []),
        rm.get("aggravating_dative", {}),
    )

    # ── 7. Relieving ─────────────────────────────────────────────────────
    rel_phrase = _resolve_relieving(
        shared_items.get("relieving_passive", []),
        rm.get("relieving_noun", {}),
    )

    # ── 8. Functional impact ─────────────────────────────────────────────
    functional_sentence = _resolve_functional(
        shared_items.get("functional_impact", []),
        rm.get("functional_phrase", {}),
    )

    # ── Assemble ─────────────────────────────────────────────────────────
    result = _assemble(noun_phrase, radiation_phrase, agg_phrase, rel_phrase)
    if functional_sentence:
        result = result + " " + functional_sentence
    return result


# ---------------------------------------------------------------------------
# Private: segment resolvers
# ---------------------------------------------------------------------------

def _resolve_temporality(items: list[str], map_: dict[str, str]) -> str | None:
    """Return adjective form of the first recognised temporality item, or None."""
    for item in items:
        adj = map_.get(item)
        if adj:
            return adj
    return None


def _resolve_character(items: list[str], map_: dict[str, str]) -> list[str]:
    """Return adjective forms for recognised character items (max 2)."""
    result: list[str] = []
    for item in items[:2]:
        adj = map_.get(item)
        if adj:
            result.append(adj)
    return result


def _resolve_radiation(items: list[str], map_: dict[str, str]) -> str | None:
    """Return the radiation prepositional phrase, or None.

    The bare canonical 'radiation' (no specific anatomical target) is
    intentionally suppressed — it signals presence in the block selector
    but carries no renderable target for Verdichtungsstil narrative.
    """
    for item in items[:1]:
        if item == "radiation":
            return None  # no specific target — suppress
        phrase = map_.get(item)
        if phrase:
            return phrase
    return None


def _resolve_aggravating(items: list[str], map_: dict[str, str]) -> str | None:
    """Return 'verstärkt bei <dative>' for the first recognised item, or None."""
    for item in items[:1]:
        dative = map_.get(item)
        if dative:
            return f"verstärkt bei {dative}"
    return None


def _resolve_relieving(items: list[str], map_: dict[str, str]) -> str | None:
    """Return 'gebessert durch <noun>' for the first recognised item, or None."""
    for item in items[:1]:
        noun = map_.get(item)
        if noun:
            return f"gebessert durch {noun}"
    return None


def _resolve_functional(items: list[str], map_: dict[str, str]) -> str | None:
    """
    Return a second sentence fragment for up to 2 functional limitations.
    Unknown canonicals are silently skipped.

    Examples:
      ["sitting_tolerance"]                     → "Sitztoleranz eingeschränkt."
      ["sitting_tolerance", "walking_distance"]  → "Sitztoleranz eingeschränkt, Gehstrecke eingeschränkt."
    """
    phrases: list[str] = []
    for item in items[:2]:
        phrase = map_.get(item)
        if phrase:
            phrases.append(phrase)
    if not phrases:
        return None
    return ", ".join(phrases) + "."


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
      - with both:        "Chronische, ziehende Schmerzen im LWS-Bereich"
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
