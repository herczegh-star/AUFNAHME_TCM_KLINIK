"""
data_loader.py
--------------
Load input data for the Pain Landscape Pack Builder.

Sources:
  - candidates_all.csv  → list[CandidateRow]
  - text_export.jsonl   → int | None  (total document count)
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

from analysis.pain_landscape.models import CandidateRow

logger = logging.getLogger(__name__)

# Values treated as "no cluster"
_NULL_CLUSTER = frozenset({"", "—", "none", "null", "n/a", "-"})


def load_candidates(csv_path: str | Path) -> list[CandidateRow]:
    """
    Load candidates_all.csv into CandidateRow objects.

    Tolerates missing/extra columns and malformed rows.
    Raises FileNotFoundError if the file does not exist.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"candidates CSV not found: {path}")

    rows: list[CandidateRow] = []
    skipped = 0

    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for lineno, raw in enumerate(reader, start=2):
            row = _parse_row(raw, lineno)
            if row is not None:
                rows.append(row)
            else:
                skipped += 1

    logger.info(
        "load_candidates: %d rows loaded, %d skipped from %s",
        len(rows), skipped, path.name,
    )
    return rows


def load_total_documents(jsonl_path: str | Path) -> int | None:
    """
    Count valid lines in text_export.jsonl.

    Returns None if the file does not exist (not an error — optional input).
    """
    path = Path(jsonl_path)
    if not path.exists():
        logger.info("load_total_documents: %s not found — returning None", path.name)
        return None

    count = 0
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                json.loads(line)
                count += 1
            except json.JSONDecodeError:
                pass

    logger.info("load_total_documents: %d valid documents in %s", count, path.name)
    return count


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _parse_row(raw: dict[str, str], lineno: int) -> CandidateRow | None:
    canonical = raw.get("canonical", "").strip()
    if not canonical:
        logger.warning("Line %d: empty canonical — skipped", lineno)
        return None

    # Accept both column name variants
    type_val = raw.get("pattern_type", raw.get("type", "")).strip()

    cluster_raw = raw.get("cluster_hint", raw.get("cluster", "")).strip()
    cluster = None if cluster_raw.lower() in _NULL_CLUSTER else cluster_raw

    try:
        docs = int(raw.get("doc_count", raw.get("docs", "0")).strip())
    except ValueError:
        docs = 0

    examples = _parse_examples(raw)

    return CandidateRow(
        canonical=canonical,
        type=type_val,
        cluster=cluster,
        docs=docs,
        examples=examples,
    )


def _parse_examples(raw: dict[str, str]) -> list[str]:
    """Collect examples from example_1/2/3 columns or a single column."""
    parts: list[str] = []

    for key in ("example_1", "example_2", "example_3"):
        val = raw.get(key, "").strip()
        if val:
            parts.append(val)

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
