"""
generic_narrative_composer.py
------------------------------
Data-driven fallback composer for clusters without a dedicated Python composer.

Used by narrative_dispatcher when no cluster-specific composer is registered.
Does NOT contain any LWS- or HWS-specific logic.

Naming convention for new clusters
-----------------------------------
For the generic composer to resolve phrases, the cluster JSON must follow:

  render_maps section name == shared_items_key

Example:
  form.fields: [{ "id": "character", "shared_items_key": "pain_character", ... }]
  render_maps: { "pain_character": { "ziehend": "ziehende Schmerzen" } }

Phrase values in render_maps should be complete renderable fragments, not bare
nouns/adjectives — the generic composer concatenates them as-is without adding
grammatical connectives like "verstärkt bei" or "gebessert durch". Those
connectives belong either inside the phrase value itself or in a dedicated
cluster-specific composer.

Sentence structure
------------------
  <anchor>[, phrase1[, phrase2...]].

Phrases are appended in the order sections appear in render_maps.
At most one phrase is taken per section (first resolved value).

Anchor source (in order of preference):
  1. cluster.preferred_phrases["anchor"][0]
  2. cluster.name

If no phrases resolve, returns the anchor sentence alone. Never raises.
"""

from __future__ import annotations


def compose_generic_narrative(
    shared_items: dict[str, list[str]],
    render_maps:  dict[str, dict[str, str]],
    anchor:       str,
) -> str:
    """
    Build a German clinical sentence from shared_items + render_maps + anchor.

    Parameters
    ----------
    shared_items :
        Dict of slot → list of canonical values.
        Section name in render_maps must match the slot name for lookup to work.
    render_maps :
        Cluster render_maps dict.  Keys are section names; values are
        canonical → renderable phrase dicts.
    anchor :
        Base noun phrase used as the sentence core
        (e.g. "Beschwerden im Schulter-Bereich").

    Returns
    -------
    str
        One sentence ending with ".".  Capital first letter guaranteed.
        Never None, never raises.
    """
    phrases: list[str] = []

    for section_key, section_map in render_maps.items():
        values = shared_items.get(section_key, [])
        for v in values[:1]:           # at most one phrase per section
            if not v or v == "keine":
                continue
            phrase = section_map.get(v)
            if phrase:
                phrases.append(phrase)

    if phrases:
        sentence = anchor + ", " + ", ".join(phrases)
    else:
        sentence = anchor

    sentence = sentence.strip()
    if not sentence.endswith("."):
        sentence += "."
    return sentence[0].upper() + sentence[1:]
