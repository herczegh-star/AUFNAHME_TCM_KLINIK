"""
hws_narrative_composer.py
-------------------------
Pilot narrative composer for HWS-Syndrom.

Renders shared_pain_items_selected into a single German clinical sentence.
Verdichtungsstil — short, structured, no diagnostic inference.

Supported modules:
  pain_temporality, pain_character, pain_laterality,
  pain_radiation, aggravating_mechanical, relieving_passive,
  neuro_sensory, cephalgic_features

Overlay rule:
  neuro_sensory and cephalgic_features are rendered ONLY when
  explicitly present in shared_items. No speculative addition.

ORDERING PRINCIPLE
------------------
Input keys are alpha-sorted (selector convention — internal deterministic order).
This composer applies clinical narrative order:
  1. temporality      (adjective prefix)
  2. character        (integrated into anchor)
  3. anchor           "Schmerzen im HWS-Bereich"
  4. laterality       (appended to anchor)
  5. radiation        (prepositional phrase, no comma)
  6. aggravating      ("verstärkt bei ...")
  7. relieving        ("gebessert durch ...")
  8. neuro_sensory    (overlay addendum)
  9. cephalgic        (overlay addendum)

OVERLAY ATTACHMENT RULE
-----------------------
If the sentence already contains radiation or predicates (aggravating/relieving)
when the overlay is attached:
  → use ", begleitet von X [sowie Y]"
Otherwise (overlay follows bare anchor only):
  → use " mit begleitendem X [sowie Y]"

This avoids the awkward double-"mit" construction.

API
---
  from core.ai_draft.hws_narrative_composer import compose_hws_narrative

  result = compose_hws_narrative(shared_items)   # str

ISOLATION
---------
No dependency on DraftComposer or DraftPipeline.
No side effects on draft_text or blocks_used.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Render maps
# ---------------------------------------------------------------------------

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

_TEMPORALITY_ADJECTIVE: dict[str, str] = {
    "chronisch":           "Chronische",
    "intermittierend":     "Intermittierende",
    "belastungsabhaengig": "Belastungsabhängige",
    "progredient":         "Progrediente",
}

# Full prepositional phrase
_RADIATION_PHRASE: dict[str, str] = {
    "radiation":            "mit Ausstrahlung",
    # Shared layer standard targets
    "Arm":                  "mit Ausstrahlung in den Arm",
    "Schulter":             "mit Ausstrahlung in die Schulter",
    "Kopf":                 "mit Ausstrahlung in den Kopf",
    "Bein":                 "mit Ausstrahlung ins Bein",          # uncommon for HWS but present
    "Leiste":               "mit Ausstrahlung in die Leiste",
    "Unterbauch":           "mit Ausstrahlung in den Unterbauch",
    # HWS-specific lateralised targets
    "rechte_schulter":      "mit Ausstrahlung in die rechte Schulter",
    "linke_schulter":       "mit Ausstrahlung in die linke Schulter",
    "rechter_arm":          "mit Ausstrahlung in den rechten Arm",
    "linker_arm":           "mit Ausstrahlung in den linken Arm",
    "rechte_hand":          "mit Ausstrahlung in die rechte Hand",
    "linke_hand":           "mit Ausstrahlung in die linke Hand",
    "hinterkopf":           "mit Ausstrahlung in den Hinterkopf",
    "Hinterkopf":           "mit Ausstrahlung in den Hinterkopf",
    "okziput":              "mit Ausstrahlung in die okzipitale Region",
}

# Dative object after "verstärkt bei ..."
_AGG_MECH_DATIVE: dict[str, str] = {
    "langes_sitzen":   "langem Sitzen",
    "langes_stehen":   "langem Stehen",
    "langes_gehen":    "langem Gehen",
    "buecken":         "Bücken",
    "treppensteigen":  "Treppensteigen",
    "belastung":       "körperlicher Belastung",
    # HWS-specific
    "rotation":        "Rotation",
    "kopfrotation":    "Kopfrotation",
    "bildschirm":      "Bildschirmarbeit",
    "bildschirmarbeit": "Bildschirmarbeit",
}

# Noun after "gebessert durch ..."
_RELIEVING_NOUN: dict[str, str] = {
    "waerme":    "Wärme",
    "ruhe":      "Ruhe",
    "liegen":    "Liegen",
    "bewegung":  "leichter Bewegung",
}

# ---------------------------------------------------------------------------
# Overlay render maps — two forms per item
#
# _MIT_FORM:  used as "mit begleitendem/r/en X"  (when no prior "mit" in sentence)
# _VON_FORM:  used as "begleitet von X"            (when sentence already has content)
# ---------------------------------------------------------------------------

_NEURO_MIT_FORM: dict[str, str] = {
    "kribbeln":      "begleitendem Kribbeln",
    "taubheit":      "begleitendem Taubheitsgefühl",
    "paraesthesien": "begleitenden Parästhesien",
}

_NEURO_VON_FORM: dict[str, str] = {
    "kribbeln":      "Kribbeln",
    "taubheit":      "Taubheitsgefühl",
    "paraesthesien": "Parästhesien",
}

_CEPHALGIC_MIT_FORM: dict[str, str] = {
    "okzipitale_kopfschmerzen": "begleitenden okzipitalen Kopfschmerzen",
    "uebelkeit":                "begleitender Übelkeit",
    "lichtempfindlichkeit":     "begleitender Lichtempfindlichkeit",
    "laermempfindlichkeit":     "begleitender Lärmempfindlichkeit",
    "kopfschmerzen":            "begleitenden Kopfschmerzen",
}

_CEPHALGIC_VON_FORM: dict[str, str] = {
    "okzipitale_kopfschmerzen": "okzipitalen Kopfschmerzen",
    "uebelkeit":                "Übelkeit",
    "lichtempfindlichkeit":     "Lichtempfindlichkeit",
    "laermempfindlichkeit":     "Lärmempfindlichkeit",
    "kopfschmerzen":            "Kopfschmerzen",
}

_ANCHOR = "Schmerzen im HWS-Bereich"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compose_hws_narrative(shared_items: dict[str, list[str]]) -> str:
    """
    Render shared_pain_items_selected into a single German clinical sentence.

    Input: dict with alpha-sorted keys and values (selector convention).
    Output: one sentence, Verdichtungsstil, ending with '.'.

    Unknown canonicals are silently skipped.
    Returns "Schmerzen im HWS-Bereich." if nothing matches.
    """
    # ── 1. Temporality ───────────────────────────────────────────────────
    temporality_adj = _resolve_temporality(shared_items.get("pain_temporality", []))

    # ── 2+3. Character adjectives ────────────────────────────────────────
    char_adjs = _resolve_character(shared_items.get("pain_character", []))

    # ── 3+4. Anchor noun phrase ──────────────────────────────────────────
    noun_phrase = _build_noun_phrase(
        temporality_adj,
        char_adjs,
        shared_items.get("pain_laterality", []),
    )

    # Track whether content has been appended after the noun phrase.
    # Used by overlay attachment to choose "mit begleitendem" vs ", begleitet von".
    has_appended: bool = False

    # ── 5. Radiation ─────────────────────────────────────────────────────
    radiation_phrase = _resolve_radiation(shared_items.get("pain_radiation", []))

    # ── 6+7. Predicates ──────────────────────────────────────────────────
    agg_phrase = _resolve_aggravating(shared_items.get("aggravating_mechanical", []))
    rel_phrase  = _resolve_relieving(shared_items.get("relieving_passive", []))

    if radiation_phrase or agg_phrase or rel_phrase:
        has_appended = True

    # ── 8+9. Overlays ────────────────────────────────────────────────────
    neuro_items     = shared_items.get("neuro_sensory",      [])
    cephalgic_items = shared_items.get("cephalgic_features", [])
    overlay_segment = _build_overlay_segment(
        neuro_items, cephalgic_items, has_appended
    )

    # ── Assemble ─────────────────────────────────────────────────────────
    return _assemble(noun_phrase, radiation_phrase, agg_phrase, rel_phrase, overlay_segment)


# ---------------------------------------------------------------------------
# Private: segment resolvers
# ---------------------------------------------------------------------------

def _resolve_temporality(items: list[str]) -> str | None:
    for item in items:
        adj = _TEMPORALITY_ADJECTIVE.get(item)
        if adj:
            return adj
    return None


def _resolve_character(items: list[str]) -> list[str]:
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
    for item in items[:1]:
        dative = _AGG_MECH_DATIVE.get(item)
        if dative:
            return f"verstärkt bei {dative}"
    return None


def _resolve_relieving(items: list[str]) -> str | None:
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
      [Temporality[, ]][Character ]Schmerzen im HWS-Bereich[ laterality]
    """
    adjectives: list[str] = []

    if temporality_adj:
        adjectives.append(temporality_adj)

    if char_adjs:
        if len(char_adjs) == 1:
            adjectives.append(char_adjs[0])
        else:
            adjectives.append(f"{char_adjs[0]} und {char_adjs[1]}")

    if adjectives:
        adj_str = _join_adjectives(adjectives)
        noun_phrase = f"{adj_str} Schmerzen im HWS-Bereich"
    else:
        noun_phrase = _ANCHOR

    if laterality:
        side = laterality[0]
        if side in {"links", "rechts", "beidseits"}:
            noun_phrase += f" {side}"

    return noun_phrase


def _join_adjectives(adjectives: list[str]) -> str:
    """
    First element capitalised; subsequent elements lowercase.
    Joined by ", ".
    e.g. ["Chronische", "ziehende"] → "Chronische, ziehende"
    """
    if not adjectives:
        return ""
    parts = [adjectives[0]] + [a[0].lower() + a[1:] for a in adjectives[1:]]
    return ", ".join(parts)


# ---------------------------------------------------------------------------
# Private: overlay builder
# ---------------------------------------------------------------------------

def _build_overlay_segment(
    neuro_items:     list[str],
    cephalgic_items: list[str],
    has_appended:    bool,
) -> str | None:
    """
    Build the overlay addendum segment.

    has_appended=False  →  " mit begleitendem X [sowie Y]"
    has_appended=True   →  ", begleitet von X [sowie Y]"

    Combination rule when both overlays present:
      neuro items joined by " und "; neuro+cephalgic joined by " sowie ".
    """
    if not neuro_items and not cephalgic_items:
        return None

    if has_appended:
        return _overlay_von_form(neuro_items, cephalgic_items)
    else:
        return _overlay_mit_form(neuro_items, cephalgic_items)


def _overlay_mit_form(neuro_items: list[str], cephalgic_items: list[str]) -> str:
    """
    Overlay as "mit begleitendem X [und Y] [sowie Z]".

    First resolved neuro item: full _NEURO_MIT_FORM ("begleitendem Kribbeln").
    Additional neuro items: plain VON form joined by " und ".
    Cephalgic items: full _CEPHALGIC_MIT_FORM, joined via " sowie ".
    """
    neuro_phrases:     list[str] = []
    cephalgic_phrases: list[str] = []

    for i, item in enumerate(neuro_items[:2]):
        if i == 0:
            phrase = _NEURO_MIT_FORM.get(item)
        else:
            phrase = _NEURO_VON_FORM.get(item)
        if phrase:
            neuro_phrases.append(phrase)

    for item in cephalgic_items[:1]:
        phrase = _CEPHALGIC_MIT_FORM.get(item)
        if phrase:
            cephalgic_phrases.append(phrase)

    if not neuro_phrases and not cephalgic_phrases:
        return None  # type: ignore[return-value]

    parts: list[str] = []
    if neuro_phrases:
        parts.append(" und ".join(neuro_phrases))
    if cephalgic_phrases:
        parts.append(cephalgic_phrases[0])

    return " mit " + " sowie ".join(parts)


def _overlay_von_form(neuro_items: list[str], cephalgic_items: list[str]) -> str:
    """
    Overlay as ", begleitet von X [und Y] [sowie Z]".

    All items in plain VON form. Neuro joined by " und ", then " sowie " before cephalgic.
    """
    neuro_phrases:     list[str] = []
    cephalgic_phrases: list[str] = []

    for item in neuro_items[:2]:
        phrase = _NEURO_VON_FORM.get(item)
        if phrase:
            neuro_phrases.append(phrase)

    for item in cephalgic_items[:1]:
        phrase = _CEPHALGIC_VON_FORM.get(item)
        if phrase:
            cephalgic_phrases.append(phrase)

    if not neuro_phrases and not cephalgic_phrases:
        return None  # type: ignore[return-value]

    parts: list[str] = []
    if neuro_phrases:
        parts.append(" und ".join(neuro_phrases))
    if cephalgic_phrases:
        parts.append(cephalgic_phrases[0])

    return ", begleitet von " + " sowie ".join(parts)


# ---------------------------------------------------------------------------
# Private: sentence assembler
# ---------------------------------------------------------------------------

def _assemble(
    noun_phrase:      str,
    radiation_phrase: str | None,
    agg_phrase:       str | None,
    rel_phrase:       str | None,
    overlay_segment:  str | None,
) -> str:
    """
    Final sentence assembly:

      <noun_phrase>[ <radiation>][, <agg>][, <rel>][<overlay>].

    Radiation: no comma (prepositional attribute of noun phrase).
    Predicates: comma-separated.
    Overlay: either " mit ..." (no comma) or ", begleitet von ..." (with comma).
      The leading comma / space is already included in overlay_segment.
    """
    sentence = noun_phrase

    if radiation_phrase:
        sentence += f" {radiation_phrase}"

    predicates = [p for p in (agg_phrase, rel_phrase) if p]
    if predicates:
        sentence += ", " + ", ".join(predicates)

    if overlay_segment:
        sentence += overlay_segment

    sentence += "."
    return sentence[0].upper() + sentence[1:]
