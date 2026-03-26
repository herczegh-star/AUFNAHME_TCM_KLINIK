"""
segmenter.py
------------
Split a TextDocument into labelled TextSegments by clinical section.

Sections are detected by header patterns — fixed list, no ML.
The relevant section for block mining is "Derzeitige Beschwerden".
All other sections are also extracted so the extractor can be
cluster-aware (e.g. diagnoses appear in "Diagnosen" section).

Strategy:
  - Scan for section headers line by line
  - Assign each line to the most recently seen header
  - Return one TextSegment per (doc, section) pair
"""

from __future__ import annotations

import re

from analysis.mining.models import TextDocument, TextSegment


# ---------------------------------------------------------------------------
# Section header patterns
# (ordered: first match wins if multiple patterns could match)
# ---------------------------------------------------------------------------

_SECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Derzeitige Beschwerden",    re.compile(r"derzeitige\s+beschwerden", re.IGNORECASE)),
    ("Diagnosen",                 re.compile(r"\bdiagnos[ei]", re.IGNORECASE)),
    ("Anamnese",                  re.compile(r"\banamnese\b", re.IGNORECASE)),
    ("Vormedikation",             re.compile(r"vormedikation", re.IGNORECASE)),
    ("Körperliche Untersuchung",  re.compile(r"k.rperliche\s+untersuchung", re.IGNORECASE)),
    ("Therapie",                  re.compile(r"\btherapie\b", re.IGNORECASE)),
    ("Empfehlung",                re.compile(r"\bempfehlung\b", re.IGNORECASE)),
    ("Sonstiges",                 re.compile(r"\bsonstiges\b", re.IGNORECASE)),
]

_DEFAULT_SECTION = "Unbekannt"

# Minimum characters for a segment to be kept
_MIN_SEGMENT_CHARS = 10


# ---------------------------------------------------------------------------
# Public class
# ---------------------------------------------------------------------------

class Segmenter:
    """
    Splits a TextDocument into TextSegments.

    Usage:
        seg = Segmenter()
        segments = seg.segment(doc)
    """

    def segment(self, doc: TextDocument) -> list[TextSegment]:
        """
        Return one TextSegment per detected section in doc.

        Sections with fewer than _MIN_SEGMENT_CHARS are dropped.
        """
        lines = doc.text.splitlines()

        current_section = _DEFAULT_SECTION
        current_lines:  list[str] = []
        current_offset: int       = 0
        char_cursor:    int       = 0

        results: list[TextSegment] = []

        for line in lines:
            detected = self._detect_section(line)

            if detected is not None:
                # Flush current buffer
                self._flush(doc.file, current_section, current_lines,
                            current_offset, results)
                current_section = detected
                current_lines   = []
                current_offset  = char_cursor
            else:
                current_lines.append(line)

            char_cursor += len(line) + 1  # +1 for newline

        # Flush last segment
        self._flush(doc.file, current_section, current_lines,
                    current_offset, results)

        return results

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _detect_section(self, line: str) -> str | None:
        """Return section label if line is a section header, else None."""
        stripped = line.strip()
        if not stripped:
            return None
        for label, pattern in _SECTION_PATTERNS:
            if pattern.search(stripped):
                return label
        return None

    def _flush(
        self,
        doc_file:    str,
        section:     str,
        lines:       list[str],
        offset:      int,
        results:     list[TextSegment],
    ) -> None:
        text = "\n".join(lines).strip()
        if len(text) < _MIN_SEGMENT_CHARS:
            return
        results.append(TextSegment(
            doc_file    = doc_file,
            section     = section,
            text        = text,
            char_offset = offset,
        ))
