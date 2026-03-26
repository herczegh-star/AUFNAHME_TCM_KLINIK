"""
models.py
---------
Data models for the Pain Landscape Pack.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CandidateRow:
    """Single row from candidates_all.csv."""
    canonical: str
    type:      str
    cluster:   str | None   # None = not cluster-specific
    docs:      int
    examples:  list[str] = field(default_factory=list)


@dataclass
class ClusterPainOverview:
    """
    Pain feature summary for one cluster.

    All lists contain only cluster-specific candidates (cluster == cluster_name).
    Empty list means no data found — not an error.
    """
    cluster_name:    str
    document_count:  int
    types_present:   list[str]
    top_characters:  list[CandidateRow] = field(default_factory=list)
    top_aggravating: list[CandidateRow] = field(default_factory=list)
    top_relieving:   list[CandidateRow] = field(default_factory=list)
    top_radiation:   list[CandidateRow] = field(default_factory=list)
    top_associated:  list[CandidateRow] = field(default_factory=list)
    top_functional:  list[CandidateRow] = field(default_factory=list)


@dataclass
class PainLandscapePack:
    """
    Full pain landscape pack for macro-analysis.

    Global lists contain cross-cluster (cluster=None) candidates.
    Cluster overviews contain per-cluster breakdowns.
    """
    total_documents:        int | None
    cluster_inventory_count: int
    top_clusters:           list[CandidateRow]
    global_top_characters:  list[CandidateRow]
    global_top_aggravating: list[CandidateRow]
    global_top_relieving:   list[CandidateRow]
    global_top_radiation:   list[CandidateRow]
    global_top_associated:  list[CandidateRow]
    global_top_functional:  list[CandidateRow]
    cluster_overviews:      list[ClusterPainOverview]
    meta:                   dict[str, Any] = field(default_factory=dict)
