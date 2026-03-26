"""
candidate_extractor_v2.py
-------------------------
Entry point for the deterministic mining layer.

Runs the full pipeline:
  TextExportLoader → Segmenter → RuleBasedExtractor → Aggregator → Exporter

Usage:
    python analysis/candidate_extractor_v2.py

Output: analysis/output/candidate_extraction_v2/
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup so imports resolve from project root
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
from analysis.mining.aggregator          import Aggregator
from analysis.mining.exporter            import Exporter
from analysis.mining.models              import ExtractionResult
from analysis.mining.rule_based_extractor import RuleBasedExtractor
from analysis.mining.segmenter           import Segmenter
from analysis.mining.text_export_loader  import TextExportLoader

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_JSONL_PATH   = _PROJECT_ROOT / "analysis" / "output" / "analysis_output_phase1" / "text_export.jsonl"
_OUTPUT_DIR   = _PROJECT_ROOT / "analysis" / "output" / "candidate_extraction_v2"

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt = "%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------

def run_pipeline(
    jsonl_path: Path = _JSONL_PATH,
    output_dir: Path = _OUTPUT_DIR,
) -> ExtractionResult:
    """
    Execute the full extraction pipeline.

    Returns an ExtractionResult with stats and aggregated candidates.
    """
    loader    = TextExportLoader(jsonl_path)
    segmenter = Segmenter()
    extractor = RuleBasedExtractor()
    aggregator = Aggregator()
    exporter  = Exporter(output_dir)

    result = ExtractionResult()

    # ------------------------------------------------------------------
    # Step 1 — load documents
    # ------------------------------------------------------------------
    logger.info("Loading documents from %s", jsonl_path)
    docs = loader.load()
    result.docs_processed = len(docs)
    logger.info("  → %d documents loaded", len(docs))

    # ------------------------------------------------------------------
    # Step 2 — segment
    # ------------------------------------------------------------------
    logger.info("Segmenting documents...")
    all_segments = []
    for doc in docs:
        try:
            segs = segmenter.segment(doc)
            all_segments.extend(segs)
        except Exception as exc:
            result.errors.append({"file": doc.file, "message": str(exc)})
            logger.warning("Segmenter error in %s: %s", doc.file, exc)

    result.segments_found = len(all_segments)
    logger.info("  → %d segments extracted", len(all_segments))

    # ------------------------------------------------------------------
    # Step 3 — extract
    # ------------------------------------------------------------------
    logger.info("Extracting candidates...")
    raw_matches = []
    try:
        raw_matches = extractor.extract(all_segments)
    except Exception as exc:
        result.errors.append({"file": "extractor", "message": str(exc)})
        logger.error("Extractor error: %s", exc)

    result.matches_total = len(raw_matches)
    logger.info("  → %d raw matches found", len(raw_matches))

    # ------------------------------------------------------------------
    # Step 4 — aggregate
    # ------------------------------------------------------------------
    logger.info("Aggregating candidates...")
    result.candidates = aggregator.aggregate(raw_matches)
    logger.info("  → %d aggregated candidates", len(result.candidates))

    # ------------------------------------------------------------------
    # Step 5 — export
    # ------------------------------------------------------------------
    logger.info("Writing output to %s", output_dir)
    exporter.export(result, raw_matches)

    logger.info("Pipeline complete.")
    _print_summary(result)

    return result


def _print_summary(result: ExtractionResult) -> None:
    print()
    print("=" * 55)
    print("  Mining Layer v1 — Extraction complete")
    print("=" * 55)
    print(f"  Documents   : {result.docs_processed}")
    print(f"  Segments    : {result.segments_found}")
    print(f"  Raw matches : {result.matches_total}")
    print(f"  Candidates  : {len(result.candidates)}")
    if result.errors:
        print(f"  Errors      : {len(result.errors)}")
    print()
    print("  Top 15 candidates:")
    for c in result.candidates[:15]:
        cluster = f" [{c.cluster_hint}]" if c.cluster_hint else ""
        print(f"    {c.doc_count:>4}x  {c.pattern_type:<22}  {c.canonical}{cluster}")
    print()
    print(f"  Output: {_OUTPUT_DIR}")
    print("=" * 55)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_pipeline()
