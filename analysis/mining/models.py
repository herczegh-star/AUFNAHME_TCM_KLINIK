"""
models.py
---------
Data models for the deterministic mining layer.

All models are pure dataclasses — no business logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

@dataclass
class TextDocument:
    """
    Single patient document loaded from text_export.jsonl.

    file:  original filename, e.g. "Patient_042.docx"
    text:  full extracted text of the document
    """
    file: str
    text: str


# ---------------------------------------------------------------------------
# Segmentation
# ---------------------------------------------------------------------------

@dataclass
class TextSegment:
    """
    A contiguous block of text attributed to a clinical section.

    doc_file:     source document filename
    section:      detected section label, e.g. "Derzeitige Beschwerden"
    text:         raw segment text
    char_offset:  character offset of segment start in original text
    """
    doc_file:    str
    section:     str
    text:        str
    char_offset: int = 0


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

@dataclass
class CandidateMatch:
    """
    A single pattern match within a segment.

    doc_file:      source document filename
    section:       section this match was found in
    pattern_id:    ID of the rule pattern that fired, e.g. "side_beidseits"
    pattern_type:  semantic category, e.g. "side", "character", "aggravating"
    matched_text:  the exact substring that was matched
    canonical:     normalized canonical value, e.g. "beidseits"
    cluster_hint:  optional cluster this match is associated with
    context_window: ±N chars around the match for human review
    """
    doc_file:       str
    section:        str
    pattern_id:     str
    pattern_type:   str
    matched_text:   str
    canonical:      str
    cluster_hint:   str           = ""
    context_window: str           = ""


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

@dataclass
class AggregatedCandidate:
    """
    A deduplicated, frequency-ranked candidate block.

    canonical:      canonical value, e.g. "langes Sitzen"
    pattern_type:   semantic category
    cluster_hint:   cluster association (may be empty = cross-cluster)
    frequency:      number of documents this candidate appeared in
    doc_count:      alias for frequency (same value, for readability)
    example_texts:  up to 5 raw matched_text examples from real documents
    example_docs:   corresponding doc_file names for the examples
    """
    canonical:     str
    pattern_type:  str
    cluster_hint:  str
    frequency:     int
    doc_count:     int
    example_texts: list[str] = field(default_factory=list)
    example_docs:  list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pipeline result
# ---------------------------------------------------------------------------

@dataclass
class ExtractionResult:
    """
    Full output of one pipeline run.

    docs_processed:    number of documents read
    segments_found:    total segments extracted
    matches_total:     total CandidateMatch objects produced
    candidates:        aggregated and ranked candidates
    errors:            non-fatal errors encountered (file, message)
    """
    docs_processed: int                        = 0
    segments_found: int                        = 0
    matches_total:  int                        = 0
    candidates:     list[AggregatedCandidate]  = field(default_factory=list)
    errors:         list[dict[str, str]]       = field(default_factory=list)
