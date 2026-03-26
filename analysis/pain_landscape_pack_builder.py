"""
pain_landscape_pack_builder.py
-------------------------------
Main runner for the Pain Landscape Pack Builder.

Input:
  analysis/output/candidate_extraction_v2/candidates_all.csv
  analysis/output/analysis_output_phase1/text_export.jsonl  (optional)

Output:
  analysis/output/pain_landscape/

Usage:
  python analysis/pain_landscape_pack_builder.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# ── Path setup ──────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ── Imports ─────────────────────────────────────────────────────────────────
from analysis.pain_landscape.aggregator  import build_pain_landscape_pack
from analysis.pain_landscape.data_loader import load_candidates, load_total_documents
from analysis.pain_landscape.exporter    import PainLandscapeExporter

# ── Configuration ────────────────────────────────────────────────────────────
_CSV_PATH   = _PROJECT_ROOT / "analysis" / "output" / "candidate_extraction_v2" / "candidates_all.csv"
_JSONL_PATH = _PROJECT_ROOT / "analysis" / "output" / "analysis_output_phase1" / "text_export.jsonl"
_OUT_DIR    = _PROJECT_ROOT / "analysis" / "output" / "pain_landscape"

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt = "%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Runner ───────────────────────────────────────────────────────────────────

def run() -> None:
    # 1 — load candidates
    logger.info("Loading candidates: %s", _CSV_PATH)
    rows = load_candidates(_CSV_PATH)
    logger.info("  %d candidate rows loaded", len(rows))

    # 2 — total documents (optional)
    logger.info("Loading document count: %s", _JSONL_PATH)
    total_docs = load_total_documents(_JSONL_PATH)
    if total_docs is not None:
        logger.info("  %d total documents", total_docs)
    else:
        logger.info("  text_export.jsonl not found — total_documents = None")

    # 3 — build pack
    logger.info("Building Pain Landscape Pack...")
    pack = build_pain_landscape_pack(rows, total_documents=total_docs)
    logger.info(
        "  clusters: %d  |  overviews: %d",
        pack.cluster_inventory_count,
        len(pack.cluster_overviews),
    )

    # 4 — export
    logger.info("Exporting to %s", _OUT_DIR)
    PainLandscapeExporter(_OUT_DIR).export(pack)

    # 5 — console summary
    _print_summary(pack)


def _print_summary(pack) -> None:
    top_cluster   = pack.top_clusters[0]   if pack.top_clusters           else None
    top_character = pack.global_top_characters[0]  if pack.global_top_characters  else None
    top_aggravating = pack.global_top_aggravating[0] if pack.global_top_aggravating else None
    top_relieving   = pack.global_top_relieving[0]   if pack.global_top_relieving   else None

    print()
    print("=" * 55)
    print("  Pain Landscape Pack Builder -- Summary")
    print("=" * 55)
    print(f"  Total documents        : {pack.total_documents if pack.total_documents is not None else 'n/a'}")
    print(f"  Cluster inventory count: {pack.cluster_inventory_count}")
    print(f"  Cluster overviews built: {len(pack.cluster_overviews)}")

    if top_cluster:
        print(f"  Top cluster            : {top_cluster.canonical} ({top_cluster.docs} docs)")
    if top_character:
        print(f"  Global top character   : {top_character.canonical} ({top_character.docs} docs)")
    if top_aggravating:
        print(f"  Global top aggravating : {top_aggravating.canonical} ({top_aggravating.docs} docs)")
    if top_relieving:
        print(f"  Global top relieving   : {top_relieving.canonical} ({top_relieving.docs} docs)")

    print()
    print(f"  Output written to: {_OUT_DIR}")
    print("=" * 55)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run()
