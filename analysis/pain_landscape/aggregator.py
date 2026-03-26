"""
aggregator.py
-------------
Deterministic aggregation of CandidateRow data into a PainLandscapePack.

No scoring. No heuristics. No classification.
Purely: filter → sort by docs desc → slice top N → assemble.
"""

from __future__ import annotations

from collections import defaultdict

from analysis.pain_landscape.models import (
    CandidateRow,
    ClusterPainOverview,
    PainLandscapePack,
)

# Limits
_TOP_CLUSTERS         = 20
_TOP_GLOBAL_PER_TYPE  = 15
_TOP_CLUSTER_PER_TYPE = 10

# Types included in sections (cluster rows are seed metadata)
_PAIN_TYPES = ("character", "aggravating", "relieving", "radiation",
               "associated", "functional")


def build_pain_landscape_pack(
    rows:            list[CandidateRow],
    total_documents: int | None,
) -> PainLandscapePack:
    """
    Build a PainLandscapePack from candidate rows.

    Steps:
      1. Global overview (all clusters + global pain features)
      2. Cluster overviews (per-cluster pain features for top N clusters)
      3. Meta
    """
    # ── 1a. Top clusters ────────────────────────────────────────────────
    cluster_rows = [r for r in rows if r.type == "cluster"]
    top_clusters = _top(cluster_rows, _TOP_CLUSTERS)

    # ── 1b. Global pain features (cluster is None) ──────────────────────
    global_by_type = _global_by_type(rows)

    # ── 2. Cluster overviews ─────────────────────────────────────────────
    cluster_overviews = _build_cluster_overviews(rows, top_clusters)

    # ── 3. Meta ──────────────────────────────────────────────────────────
    meta = {
        "generated_from":  "candidates_all.csv",
        "builder":         "pain_landscape_pack_builder",
        "cluster_limit":   _TOP_CLUSTERS,
        "global_limit":    _TOP_GLOBAL_PER_TYPE,
        "cluster_type_limit": _TOP_CLUSTER_PER_TYPE,
    }

    return PainLandscapePack(
        total_documents         = total_documents,
        cluster_inventory_count = len(cluster_rows),
        top_clusters            = top_clusters,
        global_top_characters   = global_by_type.get("character",   []),
        global_top_aggravating  = global_by_type.get("aggravating", []),
        global_top_relieving    = global_by_type.get("relieving",   []),
        global_top_radiation    = global_by_type.get("radiation",   []),
        global_top_associated   = global_by_type.get("associated",  []),
        global_top_functional   = global_by_type.get("functional",  []),
        cluster_overviews       = cluster_overviews,
        meta                    = meta,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _top(rows: list[CandidateRow], n: int) -> list[CandidateRow]:
    """Sort by docs desc, return top n."""
    return sorted(rows, key=lambda r: r.docs, reverse=True)[:n]


def _global_by_type(rows: list[CandidateRow]) -> dict[str, list[CandidateRow]]:
    """
    For each pain type, collect rows where cluster is None, sorted docs desc.
    """
    by_type: dict[str, list[CandidateRow]] = defaultdict(list)
    for r in rows:
        if r.cluster is None and r.type in _PAIN_TYPES:
            by_type[r.type].append(r)

    return {
        t: _top(by_type[t], _TOP_GLOBAL_PER_TYPE)
        for t in _PAIN_TYPES
        if by_type[t]
    }


def _build_cluster_overviews(
    rows:         list[CandidateRow],
    top_clusters: list[CandidateRow],
) -> list[ClusterPainOverview]:
    """Build a ClusterPainOverview for each cluster in top_clusters."""
    overviews: list[ClusterPainOverview] = []

    for cluster_row in top_clusters:
        name = cluster_row.canonical

        # All rows linked to this cluster
        linked = [r for r in rows if r.cluster == name]

        types_present = sorted({r.type for r in linked} - {"cluster"})

        def _linked_top(ptype: str) -> list[CandidateRow]:
            return _top([r for r in linked if r.type == ptype], _TOP_CLUSTER_PER_TYPE)

        overviews.append(ClusterPainOverview(
            cluster_name    = name,
            document_count  = cluster_row.docs,
            types_present   = types_present,
            top_characters  = _linked_top("character"),
            top_aggravating = _linked_top("aggravating"),
            top_relieving   = _linked_top("relieving"),
            top_radiation   = _linked_top("radiation"),
            top_associated  = _linked_top("associated"),
            top_functional  = _linked_top("functional"),
        ))

    return overviews
