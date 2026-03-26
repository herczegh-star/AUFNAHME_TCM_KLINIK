"""
models.py
---------
Data models for review pack generation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CandidateRow:
    """Single row from candidates_all.csv."""
    canonical: str
    type:      str
    cluster:   str | None   # None when not cluster-specific
    docs:      int
    examples:  list[str] = field(default_factory=list)


@dataclass
class PackSection:
    """Candidates grouped by semantic type within a review pack."""
    type:  str
    items: list[CandidateRow] = field(default_factory=list)


@dataclass
class ReviewPack:
    """
    Full review pack for a single cluster seed.

    Consumed by:
      - LLM analytical review (paste pack_<seed>.txt into prompt)
      - Human curation (browse pack_<seed>.json in spreadsheet or editor)
    """
    seed_cluster:              str
    seed_docs:                 int
    seed_examples:             list[str]
    sections:                  list[PackSection]
    global_candidates:         list[CandidateRow]
    cluster_linked_candidates: list[CandidateRow]
    curator_questions:         list[str]
    meta:                      dict[str, Any] = field(default_factory=dict)
