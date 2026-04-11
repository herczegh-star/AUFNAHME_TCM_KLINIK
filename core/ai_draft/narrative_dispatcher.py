"""
narrative_dispatcher.py
-----------------------
Cluster-aware dispatcher for narrative composers.

Provides a single entry point:

    compose_narrative(cluster_id, shared_items, *, cluster=None) -> str

Dispatches to the appropriate pilot composer based on cluster_id.
Falls back to generic_narrative_composer when no dedicated composer is
registered. Never returns None.

IMPORTANT: Not yet integrated into DraftPipeline. This module is a
design stub. Integration will be done in a separate step after all
pilot composers are validated.

Cluster ID normalisation:
  Accepts both display form ("LWS-Syndrom") and internal form ("lws_syndrom").
  Normalisation: lowercased, spaces and hyphens collapsed to underscores.

Currently registered composers:
  lws_syndrom    -> compose_lws_narrative             (dedicated, render_maps from JSON)
  hws_syndrom    -> compose_hws_narrative             (dedicated, hardcoded maps)
  kopfschmerzen  -> compose_kopfschmerzen_narrative   (dedicated, hardcoded maps)
  migraene                   -> compose_migraene_narrative             (dedicated, hardcoded maps)
  gelenkbeschwerden_arthrose -> compose_gelenkbeschwerden_narrative    (dedicated, hardcoded maps)
  reizdarm_funktionelle_verdauungsbeschwerden -> compose_reizdarm_narrative (dedicated, hardcoded maps)
  muedigkeitssymptomatik_chronische_erschoepfung -> compose_muedigkeitssymptomatik_narrative (dedicated, hardcoded maps)
  post_covid_syndrom             -> compose_post_covid_narrative             (dedicated, hardcoded maps)
  fibromyalgie_ganzkoerperschmerzen -> compose_fibromyalgie_narrative        (dedicated, hardcoded maps)
  polyneuropathische_beschwerden_polyneuropathie -> compose_polyneuropathie_narrative (dedicated, hardcoded maps)
  ced_ibd_morbus_crohn_colitis_ulcerosa          -> compose_ced_ibd_narrative          (dedicated, hardcoded maps)
  entzuendlich_rheumatologische_gelenkbeschwerden_polyarthritis -> compose_rheuma_narrative (dedicated, hardcoded maps)
  neurodermitis_atopisches_ekzem                 -> compose_neurodermitis_narrative    (dedicated, hardcoded maps)
  tinnitus_aurium                                -> compose_tinnitus_narrative          (dedicated, hardcoded maps)

Clusters without a dedicated composer:
  Falls back to generic_narrative_composer using cluster.render_maps.
  Requires caller to pass cluster= keyword argument.
  If cluster is not provided, returns a minimal anchor-only sentence.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from core.ai_draft.lws_narrative_composer import compose_lws_narrative
from core.ai_draft.hws_narrative_composer import compose_hws_narrative
from core.ai_draft.kopfschmerzen_narrative_composer import compose_kopfschmerzen_narrative
from core.ai_draft.migraene_narrative_composer import compose_migraene_narrative
from core.ai_draft.gelenkbeschwerden_narrative_composer import compose_gelenkbeschwerden_narrative
from core.ai_draft.reizdarm_narrative_composer import compose_reizdarm_narrative
from core.ai_draft.muedigkeitssymptomatik_narrative_composer import compose_muedigkeitssymptomatik_narrative
from core.ai_draft.post_covid_narrative_composer import compose_post_covid_narrative
from core.ai_draft.fibromyalgie_narrative_composer import compose_fibromyalgie_narrative
from core.ai_draft.polyneuropathie_narrative_composer import compose_polyneuropathie_narrative
from core.ai_draft.ced_ibd_narrative_composer import compose_ced_ibd_narrative
from core.ai_draft.rheuma_narrative_composer import compose_rheuma_narrative
from core.ai_draft.neurodermitis_narrative_composer import compose_neurodermitis_narrative
from core.ai_draft.tinnitus_narrative_composer import compose_tinnitus_narrative
from core.ai_draft.generic_narrative_composer import compose_generic_narrative

if TYPE_CHECKING:
    from models.unified_cluster import UnifiedCluster


# ---------------------------------------------------------------------------
# Normalisation helper
# ---------------------------------------------------------------------------

def _normalise_cluster_id(cluster_id: str) -> str:
    """
    Convert display or internal cluster ID to the registry key form.

    Examples:
      "LWS-Syndrom"  -> "lws_syndrom"
      "lws_syndrom"  -> "lws_syndrom"
      "HWS Syndrom"  -> "hws_syndrom"
    """
    return cluster_id.lower().replace("-", "_").replace(" ", "_")


def _get_anchor(cluster: UnifiedCluster) -> str:
    """Return the anchor phrase for a cluster (preferred_phrases or name fallback).

    Priority:
      1. preferred_phrases["anchor"][0] if non-empty
      2. cluster.name if non-empty
      3. "Beschwerden" as ultimate safe fallback (prevents empty-anchor output)
    """
    anchors = cluster.preferred_phrases.get("anchor", [])
    if anchors and anchors[0].strip():
        return anchors[0].strip()
    if cluster.name.strip():
        return cluster.name.strip()
    return "Beschwerden"


# ---------------------------------------------------------------------------
# Composer registry
# ---------------------------------------------------------------------------

# Maps normalised cluster_id -> composer callable
_REGISTRY: dict[str, Callable[[dict[str, list[str]]], str]] = {
    "lws_syndrom":    compose_lws_narrative,
    "hws_syndrom":    compose_hws_narrative,
    "kopfschmerzen":  compose_kopfschmerzen_narrative,
    "migraene":                    compose_migraene_narrative,
    "gelenkbeschwerden_arthrose":                    compose_gelenkbeschwerden_narrative,
    "reizdarm_funktionelle_verdauungsbeschwerden":        compose_reizdarm_narrative,
    "muedigkeitssymptomatik_chronische_erschoepfung":     compose_muedigkeitssymptomatik_narrative,
    "post_covid_syndrom":                                 compose_post_covid_narrative,
    "fibromyalgie_ganzkoerperschmerzen":                  compose_fibromyalgie_narrative,
    "polyneuropathische_beschwerden_polyneuropathie":     compose_polyneuropathie_narrative,
    "ced_ibd_morbus_crohn_colitis_ulcerosa":              compose_ced_ibd_narrative,
    "entzuendlich_rheumatologische_gelenkbeschwerden_polyarthritis": compose_rheuma_narrative,
    "neurodermitis_atopisches_ekzem":                                compose_neurodermitis_narrative,
    "tinnitus_aurium":                                               compose_tinnitus_narrative,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compose_narrative(
    cluster_id:   str,
    shared_items: dict[str, list[str]],
    *,
    cluster: UnifiedCluster | None = None,
) -> str:
    """
    Dispatch to the appropriate narrative composer for the given cluster.

    Parameters
    ----------
    cluster_id :
        Cluster identifier, display form ("LWS-Syndrom") or internal form
        ("lws_syndrom"). Normalised internally.
    shared_items :
        Dict of selected shared pain items (alpha-sorted, selector convention).
    cluster :
        UnifiedCluster instance.  Required for the generic fallback composer.
        Ignored when a dedicated composer is registered for cluster_id.

    Returns
    -------
    str
        Rendered German clinical sentence, ending with '.'.
        Never None — falls back to generic composer or anchor-only sentence.
    """
    key = _normalise_cluster_id(cluster_id)
    composer = _REGISTRY.get(key)
    if composer is not None:
        return composer(shared_items)

    # No dedicated composer — use generic data-driven fallback.
    if cluster is not None:
        anchor = _get_anchor(cluster)
        return compose_generic_narrative(shared_items, cluster.render_maps, anchor)

    # Last resort: cluster object not provided — return safe placeholder.
    return f"Beschwerden ({cluster_id})."


def registered_clusters() -> list[str]:
    """Return list of normalised cluster IDs that have a registered composer."""
    return sorted(_REGISTRY.keys())
