"""
exporter.py
-----------
Export mining results to CSV and JSONL files.

Outputs:
  - candidates_all.csv        : all aggregated candidates
  - candidates_by_type/       : one CSV per pattern_type
  - raw_matches.jsonl         : all raw CandidateMatch objects (for debugging)
  - summary.txt               : human-readable pipeline run summary
"""

from __future__ import annotations

import csv
import json
import logging
from collections import defaultdict
from pathlib import Path

from analysis.mining.models import AggregatedCandidate, CandidateMatch, ExtractionResult

logger = logging.getLogger(__name__)


class Exporter:
    """
    Writes mining outputs to disk.

    Usage:
        exporter = Exporter(output_dir)
        exporter.export(result, raw_matches)
    """

    def __init__(self, output_dir: str | Path) -> None:
        self._output_dir = Path(output_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def export(
        self,
        result:      ExtractionResult,
        raw_matches: list[CandidateMatch],
    ) -> None:
        """
        Write all output files to the output directory.
        Creates the directory if it does not exist.
        """
        self._output_dir.mkdir(parents=True, exist_ok=True)

        self._write_candidates_all(result.candidates)
        self._write_candidates_by_type(result.candidates)
        self._write_raw_matches(raw_matches)
        self._write_summary(result, raw_matches)

        logger.info(
            "Exporter: wrote %d candidates, %d raw matches to %s",
            len(result.candidates), len(raw_matches), self._output_dir,
        )

    # ------------------------------------------------------------------
    # Private: writers
    # ------------------------------------------------------------------

    def _write_candidates_all(self, candidates: list[AggregatedCandidate]) -> None:
        path = self._output_dir / "candidates_all.csv"
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow([
                "canonical", "pattern_type", "cluster_hint",
                "doc_count", "example_1", "example_2", "example_3",
                "example_docs",
            ])
            for c in candidates:
                writer.writerow([
                    c.canonical,
                    c.pattern_type,
                    c.cluster_hint,
                    c.doc_count,
                    c.example_texts[0] if len(c.example_texts) > 0 else "",
                    c.example_texts[1] if len(c.example_texts) > 1 else "",
                    c.example_texts[2] if len(c.example_texts) > 2 else "",
                    "; ".join(c.example_docs[:3]),
                ])
        logger.debug("Wrote %s", path)

    def _write_candidates_by_type(
        self, candidates: list[AggregatedCandidate]
    ) -> None:
        by_type: dict[str, list[AggregatedCandidate]] = defaultdict(list)
        for c in candidates:
            by_type[c.pattern_type].append(c)

        subdir = self._output_dir / "candidates_by_type"
        subdir.mkdir(exist_ok=True)

        for ptype, group in by_type.items():
            path = subdir / f"{ptype}.csv"
            with path.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow([
                    "canonical", "cluster_hint", "doc_count",
                    "examples", "example_docs",
                ])
                for c in group:
                    writer.writerow([
                        c.canonical,
                        c.cluster_hint,
                        c.doc_count,
                        " | ".join(c.example_texts),
                        " | ".join(c.example_docs),
                    ])
            logger.debug("Wrote %s", path)

    def _write_raw_matches(self, matches: list[CandidateMatch]) -> None:
        path = self._output_dir / "raw_matches.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            for m in matches:
                fh.write(json.dumps({
                    "doc_file":       m.doc_file,
                    "section":        m.section,
                    "pattern_id":     m.pattern_id,
                    "pattern_type":   m.pattern_type,
                    "matched_text":   m.matched_text,
                    "canonical":      m.canonical,
                    "cluster_hint":   m.cluster_hint,
                    "context_window": m.context_window,
                }, ensure_ascii=False) + "\n")
        logger.debug("Wrote %s (%d matches)", path, len(matches))

    def _write_summary(
        self,
        result:      ExtractionResult,
        raw_matches: list[CandidateMatch],
    ) -> None:
        path = self._output_dir / "summary.txt"

        # Count by type
        type_counts: dict[str, int] = defaultdict(int)
        for c in result.candidates:
            type_counts[c.pattern_type] += 1

        lines = [
            "=== Mining Layer v1 — Extraction Summary ===",
            f"Documents processed : {result.docs_processed}",
            f"Segments found      : {result.segments_found}",
            f"Raw matches         : {result.matches_total}",
            f"Aggregated candidates: {len(result.candidates)}",
            "",
            "--- Candidates by type ---",
        ]
        for ptype, count in sorted(type_counts.items()):
            lines.append(f"  {ptype:<25} {count:>4}")

        if result.errors:
            lines.append("")
            lines.append(f"--- Errors ({len(result.errors)}) ---")
            for err in result.errors[:20]:
                lines.append(f"  {err.get('file', '?')}: {err.get('message', '?')}")

        lines.append("")
        lines.append("--- Top 20 candidates by frequency ---")
        for c in result.candidates[:20]:
            cluster = f" [{c.cluster_hint}]" if c.cluster_hint else ""
            lines.append(
                f"  {c.doc_count:>4}x  {c.pattern_type:<20}  "
                f"{c.canonical}{cluster}"
            )

        with path.open("w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")

        logger.debug("Wrote %s", path)
