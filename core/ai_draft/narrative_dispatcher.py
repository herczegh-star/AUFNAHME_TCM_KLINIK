"""
narrative_dispatcher.py
-----------------------
Cluster-aware dispatcher for narrative composers.

Provides a single entry point:

    compose_narrative(cluster_id, shared_items) -> str | None

Dispatches to the appropriate pilot composer based on cluster_id.
Returns None for clusters without a composer yet — callers can decide
whether to log, skip, or fall back to draft_text.

IMPORTANT: Not yet integrated into DraftPipeline. This module is a
design stub. Integration will be done in a separate step after all
pilot composers are validated.

Cluster ID normalisation:
  Accepts both display form ("LWS-Syndrom") and internal form ("lws_syndrom").
  Normalisation: lowercased, spaces and hyphens collapsed to underscores.

Currently registered composers:
  lws_syndrom   -> compose_lws_narrative
  hws_syndrom   -> compose_hws_narrative

Clusters without a composer (returns None):
  All other cluster_ids.
"""

from __future__ import annotations

from typing import Callable

from core.ai_draft.lws_narrative_composer import compose_lws_narrative
from core.ai_draft.hws_narrative_composer import compose_hws_narrative


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


# ---------------------------------------------------------------------------
# Composer registry
# ---------------------------------------------------------------------------

# Maps normalised cluster_id -> composer callable
_REGISTRY: dict[str, Callable[[dict[str, list[str]]], str]] = {
    "lws_syndrom": compose_lws_narrative,
    "hws_syndrom": compose_hws_narrative,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compose_narrative(
    cluster_id:   str,
    shared_items: dict[str, list[str]],
) -> str | None:
    """
    Dispatch to the appropriate narrative composer for the given cluster.

    Parameters
    ----------
    cluster_id :
        Cluster identifier, display form ("LWS-Syndrom") or internal form
        ("lws_syndrom"). Normalised internally.
    shared_items :
        Dict of selected shared pain items (alpha-sorted, selector convention).
        Same structure as DraftPipelineResult.shared_pain_items_selected.

    Returns
    -------
    str
        Rendered German clinical sentence, ending with '.'.
    None
        If no composer is registered for this cluster.
    """
    key = _normalise_cluster_id(cluster_id)
    composer = _REGISTRY.get(key)
    if composer is None:
        return None
    return composer(shared_items)


def registered_clusters() -> list[str]:
    """Return list of normalised cluster IDs that have a registered composer."""
    return sorted(_REGISTRY.keys())
