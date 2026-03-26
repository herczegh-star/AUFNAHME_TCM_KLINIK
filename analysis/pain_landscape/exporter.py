"""
exporter.py
-----------
Export PainLandscapePack to JSON, TXT, and CSV files.

Output directory: analysis/output/pain_landscape/

Files:
  pain_landscape_pack.json     — full pack (machine-readable)
  pain_landscape_pack.txt      — human + LLM readable
  cluster_inventory.csv        — all cluster rows sorted by docs desc
  global_pain_features.csv     — all global pain features by category
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import asdict
from pathlib import Path

from analysis.pain_landscape.models import CandidateRow, PainLandscapePack

logger = logging.getLogger(__name__)


class PainLandscapeExporter:
    """
    Writes all output files for the Pain Landscape Pack.

    Usage:
        exporter = PainLandscapeExporter(output_dir)
        exporter.export(pack)
    """

    def __init__(self, output_dir: str | Path) -> None:
        self._dir = Path(output_dir)

    def export(self, pack: PainLandscapePack) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)

        self._write_json(pack)
        self._write_txt(pack)
        self._write_cluster_inventory(pack)
        self._write_global_features(pack)

        logger.info("PainLandscapeExporter: all files written to %s", self._dir)

    # ------------------------------------------------------------------
    # JSON
    # ------------------------------------------------------------------

    def _write_json(self, pack: PainLandscapePack) -> None:
        path = self._dir / "pain_landscape_pack.json"
        with path.open("w", encoding="utf-8") as fh:
            json.dump(asdict(pack), fh, ensure_ascii=False, indent=2)
        logger.debug("Wrote %s", path.name)

    # ------------------------------------------------------------------
    # TXT
    # ------------------------------------------------------------------

    def _write_txt(self, pack: PainLandscapePack) -> None:
        path = self._dir / "pain_landscape_pack.txt"
        with path.open("w", encoding="utf-8") as fh:
            fh.write("\n".join(self._render_txt(pack)) + "\n")
        logger.debug("Wrote %s", path.name)

    def _render_txt(self, pack: PainLandscapePack) -> list[str]:
        L: list[str] = []

        # ── Header ──────────────────────────────────────────────────────
        L += [
            "=" * 60,
            "  PAIN LANDSCAPE PACK",
            "=" * 60,
            "",
            f"  TOTAL DOCUMENTS        : {pack.total_documents if pack.total_documents is not None else 'n/a'}",
            f"  CLUSTER INVENTORY COUNT: {pack.cluster_inventory_count}",
            f"  Generated from         : {pack.meta.get('generated_from', '?')}",
            "",
        ]

        # ── Global sections ──────────────────────────────────────────────
        sections = [
            ("TOP CLUSTERS",        pack.top_clusters),
            ("GLOBAL TOP CHARACTERS",  pack.global_top_characters),
            ("GLOBAL TOP AGGRAVATING", pack.global_top_aggravating),
            ("GLOBAL TOP RELIEVING",   pack.global_top_relieving),
            ("GLOBAL TOP RADIATION",   pack.global_top_radiation),
            ("GLOBAL TOP ASSOCIATED",  pack.global_top_associated),
            ("GLOBAL TOP FUNCTIONAL",  pack.global_top_functional),
        ]

        for title, rows in sections:
            if not rows:
                continue
            L.append(f"── {title} ──")
            for r in rows:
                ex = " / ".join(r.examples[:3]) if r.examples else "-"
                cluster_tag = f"  [{r.cluster}]" if r.cluster else ""
                L.append(f"  {r.docs:>5}x  {r.canonical:<30}  {ex}{cluster_tag}")
            L.append("")

        # ── Cluster overviews ────────────────────────────────────────────
        L += ["=" * 60, "  CLUSTER OVERVIEWS", "=" * 60, ""]

        for ov in pack.cluster_overviews:
            L.append(f"[Cluster] {ov.cluster_name}")
            L.append(f"Documents    : {ov.document_count}")
            types_str = ", ".join(ov.types_present) if ov.types_present else "-"
            L.append(f"Types present: {types_str}")
            L.append("")

            sub_sections = [
                ("CHARACTER",  ov.top_characters),
                ("AGGRAVATING", ov.top_aggravating),
                ("RELIEVING",   ov.top_relieving),
                ("RADIATION",   ov.top_radiation),
                ("ASSOCIATED",  ov.top_associated),
                ("FUNCTIONAL",  ov.top_functional),
            ]
            for sub_title, rows in sub_sections:
                if not rows:
                    continue
                L.append(f"  {sub_title}:")
                for r in rows:
                    ex = " / ".join(r.examples[:3]) if r.examples else "-"
                    L.append(f"    {r.docs:>5}x  {r.canonical:<28}  {ex}")
                L.append("")

            L.append("-" * 60)
            L.append("")

        return L

    # ------------------------------------------------------------------
    # CSV: cluster_inventory
    # ------------------------------------------------------------------

    def _write_cluster_inventory(self, pack: PainLandscapePack) -> None:
        path = self._dir / "cluster_inventory.csv"
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["cluster_name", "docs", "example_1", "example_2", "example_3"])
            for r in pack.top_clusters:
                writer.writerow([
                    r.canonical,
                    r.docs,
                    r.examples[0] if len(r.examples) > 0 else "",
                    r.examples[1] if len(r.examples) > 1 else "",
                    r.examples[2] if len(r.examples) > 2 else "",
                ])
        logger.debug("Wrote %s", path.name)

    # ------------------------------------------------------------------
    # CSV: global_pain_features
    # ------------------------------------------------------------------

    def _write_global_features(self, pack: PainLandscapePack) -> None:
        path = self._dir / "global_pain_features.csv"

        categories: list[tuple[str, list[CandidateRow]]] = [
            ("character",  pack.global_top_characters),
            ("aggravating", pack.global_top_aggravating),
            ("relieving",   pack.global_top_relieving),
            ("radiation",   pack.global_top_radiation),
            ("associated",  pack.global_top_associated),
            ("functional",  pack.global_top_functional),
        ]

        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["category", "canonical", "docs", "examples"])
            for cat, rows in categories:
                for r in rows:
                    writer.writerow([
                        cat,
                        r.canonical,
                        r.docs,
                        " | ".join(r.examples),
                    ])
        logger.debug("Wrote %s", path.name)
