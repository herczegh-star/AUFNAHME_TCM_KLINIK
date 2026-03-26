"""
rule_based_extractor.py
-----------------------
Apply rule patterns to TextSegments and produce CandidateMatch objects.

Strategy:
  - For each segment, try all relevant patterns
  - CLUSTER patterns applied to all sections (especially "Diagnosen")
  - All other patterns applied to "Derzeitige Beschwerden" primarily
  - Context window: ±60 chars around the match
  - Multi-match patterns: all non-overlapping matches collected
  - Single-match patterns: first match per sentence only

No heuristic scoring. No ML. Fully deterministic.
"""

from __future__ import annotations

import re

from analysis.mining.models import CandidateMatch, TextSegment
from analysis.mining.rule_patterns import (
    ALL_PATTERNS,
    CLUSTER_PATTERNS,
    RulePattern,
)

# Sections to mine for symptom patterns
_SYMPTOM_SECTIONS = frozenset({
    "Derzeitige Beschwerden",
    "Anamnese",
    "Unbekannt",  # include unclassified text too
})

_CONTEXT_WINDOW = 60   # chars on each side


class RuleBasedExtractor:
    """
    Applies all rule patterns to a list of TextSegments.

    Usage:
        extractor = RuleBasedExtractor()
        matches   = extractor.extract(segments)
    """

    def extract(self, segments: list[TextSegment]) -> list[CandidateMatch]:
        """
        Return all CandidateMatch objects found in the given segments.
        """
        results: list[CandidateMatch] = []

        for segment in segments:
            results.extend(self._extract_segment(segment))

        return results

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _extract_segment(self, segment: TextSegment) -> list[CandidateMatch]:
        matches: list[CandidateMatch] = []

        is_symptom = segment.section in _SYMPTOM_SECTIONS

        for pattern in ALL_PATTERNS:
            # CLUSTER patterns: apply everywhere
            # Other patterns: only in symptom sections
            if pattern.pattern_type != "cluster" and not is_symptom:
                continue

            found = self._apply_pattern(pattern, segment)
            matches.extend(found)

        return matches

    def _apply_pattern(
        self, pattern: RulePattern, segment: TextSegment
    ) -> list[CandidateMatch]:
        text = segment.text
        results: list[CandidateMatch] = []

        if pattern.multi:
            for m in pattern.regex.finditer(text):
                results.append(self._make_match(pattern, segment, m, text))
        else:
            m = pattern.regex.search(text)
            if m:
                results.append(self._make_match(pattern, segment, m, text))

        return results

    def _make_match(
        self,
        pattern: RulePattern,
        segment: TextSegment,
        m: re.Match[str],
        text: str,
    ) -> CandidateMatch:
        start = m.start()
        end   = m.end()

        ctx_start = max(0, start - _CONTEXT_WINDOW)
        ctx_end   = min(len(text), end + _CONTEXT_WINDOW)
        context   = text[ctx_start:ctx_end].replace("\n", " ").strip()

        return CandidateMatch(
            doc_file       = segment.doc_file,
            section        = segment.section,
            pattern_id     = pattern.id,
            pattern_type   = pattern.pattern_type,
            matched_text   = m.group(0),
            canonical      = pattern.canonical,
            cluster_hint   = pattern.cluster_hint,
            context_window = context,
        )
