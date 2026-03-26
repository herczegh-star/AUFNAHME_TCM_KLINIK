"""
candidate_csv_loader.py
-----------------------
Load candidates_all.csv into CandidateRow objects.

Handles:
  - examples column: pipe-separated string → list[str]
  - cluster column: "—", "", "None", "null" → None
  - docs column: str → int (0 on parse error)
  - missing/extra columns: tolerant
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from analysis.review_packs.models import CandidateRow

logger = logging.getLogger(__name__)

# Values that mean "no cluster"
_NULL_CLUSTER = frozenset({"", "—", "none", "null", "n/a", "-"})


class CandidateCsvLoader:
    """
    Loads analysis/output/candidate_extraction_v2/candidates_all.csv.

    Usage:
        loader = CandidateCsvLoader(path)
        rows   = loader.load()
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def load(self) -> list[CandidateRow]:
        if not self._path.exists():
            raise FileNotFoundError(f"candidates CSV not found: {self._path}")

        rows: list[CandidateRow] = []
        skipped = 0

        with self._path.open(encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for lineno, raw in enumerate(reader, start=2):   # 2 = data starts after header
                row = self._parse_row(raw, lineno)
                if row is not None:
                    rows.append(row)
                else:
                    skipped += 1

        logger.info(
            "CandidateCsvLoader: loaded %d rows, skipped %d from %s",
            len(rows), skipped, self._path.name,
        )
        return rows

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _parse_row(self, raw: dict[str, str], lineno: int) -> CandidateRow | None:
        canonical = raw.get("canonical", "").strip()
        if not canonical:
            logger.warning("Line %d: empty canonical — skipped", lineno)
            return None

        type_val = raw.get("pattern_type", raw.get("type", "")).strip()

        cluster_raw = raw.get("cluster_hint", raw.get("cluster", "")).strip()
        cluster = None if cluster_raw.lower() in _NULL_CLUSTER else cluster_raw

        try:
            docs = int(raw.get("doc_count", raw.get("docs", "0")).strip())
        except ValueError:
            docs = 0

        # Examples: stored as comma or pipe separated in 3 columns or single column
        examples = self._parse_examples(raw)

        return CandidateRow(
            canonical = canonical,
            type      = type_val,
            cluster   = cluster,
            docs      = docs,
            examples  = examples,
        )

    def _parse_examples(self, raw: dict[str, str]) -> list[str]:
        """
        Collect examples from example_1/2/3 columns or a single 'examples' column.
        Returns deduped, non-empty list.
        """
        parts: list[str] = []

        # Named columns from our CSV format
        for key in ("example_1", "example_2", "example_3"):
            val = raw.get(key, "").strip()
            if val:
                parts.append(val)

        # Fallback: single 'examples' column (pipe or comma separated)
        if not parts:
            combined = raw.get("examples", "").strip()
            if combined:
                for sep in ("|", ";", ","):
                    if sep in combined:
                        parts = [p.strip() for p in combined.split(sep) if p.strip()]
                        break
                else:
                    parts = [combined]

        # Deduplicate preserving order
        seen: set[str] = set()
        result: list[str] = []
        for p in parts:
            if p.lower() not in seen:
                seen.add(p.lower())
                result.append(p)

        return result
