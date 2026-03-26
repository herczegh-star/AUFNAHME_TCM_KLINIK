"""
candidate_pack_builder.py
-------------------------
CLI runner: builds review packs for all default cluster seeds.

Usage:
    python analysis/candidate_pack_builder.py

Input  : analysis/output/candidate_extraction_v2/candidates_all.csv
Output : analysis/output/llm_review_packs/
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
from analysis.review_packs.candidate_csv_loader import CandidateCsvLoader
from analysis.review_packs.exporter             import ReviewPackExporter
from analysis.review_packs.pack_builder         import PackBuilder

# ── Configuration ────────────────────────────────────────────────────────────
_CSV_PATH  = _PROJECT_ROOT / "analysis" / "output" / "candidate_extraction_v2" / "candidates_all.csv"
_OUT_DIR   = _PROJECT_ROOT / "analysis" / "output" / "llm_review_packs"

_DEFAULT_SEEDS = [
    "LWS-Syndrom",
    "HWS-Syndrom",
    "Schulter-Syndrom",
    "Knie-Syndrom",
]

logging.basicConfig(
    level   = logging.INFO,
    format  = "%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt = "%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Pipeline ─────────────────────────────────────────────────────────────────

def run(seeds: list[str] = _DEFAULT_SEEDS) -> None:
    logger.info("Loading candidates from %s", _CSV_PATH)
    rows = CandidateCsvLoader(_CSV_PATH).load()
    logger.info("  → %d candidate rows loaded", len(rows))

    builder  = PackBuilder()
    exporter = ReviewPackExporter(_OUT_DIR)

    success:  list[str] = []
    missing:  list[str] = []

    for seed in seeds:
        pack = builder.build(rows, seed_cluster=seed)
        if pack is None:
            logger.warning("Seed '%s' not found in candidates CSV — skipped", seed)
            missing.append(seed)
            continue

        paths = exporter.export(pack)
        logger.info(
            "  Pack '%s': %d sections, %d items, %d questions → %s",
            seed,
            len(pack.sections),
            sum(len(s.items) for s in pack.sections),
            len(pack.curator_questions),
            paths["txt"].name,
        )
        success.append(seed)

    _print_summary(success, missing, len(rows))


def _print_summary(
    success: list[str], missing: list[str], total_rows: int
) -> None:
    print()
    print("=" * 55)
    print("  Review Pack Builder — Summary")
    print("=" * 55)
    print(f"  Candidate rows loaded : {total_rows}")
    print(f"  Packs built           : {len(success)}")
    print()
    if success:
        print("  [OK] Built:")
        for s in success:
            print(f"      {s}")
    if missing:
        print()
        print("  [--] Seed not found in candidates:")
        for m in missing:
            print(f"      {m}")
    print()
    print(f"  Output: {_OUT_DIR}")
    print("=" * 55)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run()
