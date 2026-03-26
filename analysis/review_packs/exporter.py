"""
exporter.py
-----------
Export ReviewPack to JSON and human-readable TXT.

Output files:
  pack_<safe_seed>.json  — machine-readable, full structure
  pack_<safe_seed>.txt   — readable for humans and LLM prompts

safe_seed: lowercase, spaces and "/" replaced with "_"
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path

from analysis.review_packs.models import ReviewPack

logger = logging.getLogger(__name__)


def _safe_seed(seed_cluster: str) -> str:
    return seed_cluster.lower().replace(" ", "_").replace("/", "_")


class ReviewPackExporter:
    """
    Writes a ReviewPack to disk.

    Usage:
        exporter = ReviewPackExporter(output_dir)
        exporter.export(pack)
    """

    def __init__(self, output_dir: str | Path) -> None:
        self._output_dir = Path(output_dir)

    def export(self, pack: ReviewPack) -> dict[str, Path]:
        """
        Write JSON and TXT files. Returns dict with paths.
        """
        self._output_dir.mkdir(parents=True, exist_ok=True)
        safe = _safe_seed(pack.seed_cluster)

        json_path = self._write_json(pack, safe)
        txt_path  = self._write_txt(pack, safe)

        logger.info("Exported pack '%s': %s, %s", pack.seed_cluster, json_path.name, txt_path.name)
        return {"json": json_path, "txt": txt_path}

    # ------------------------------------------------------------------
    # JSON
    # ------------------------------------------------------------------

    def _write_json(self, pack: ReviewPack, safe: str) -> Path:
        path = self._output_dir / f"pack_{safe}.json"
        data = asdict(pack)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        return path

    # ------------------------------------------------------------------
    # TXT
    # ------------------------------------------------------------------

    def _write_txt(self, pack: ReviewPack, safe: str) -> Path:
        path = self._output_dir / f"pack_{safe}.txt"
        lines = self._render_txt(pack)
        with path.open("w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        return path

    def _render_txt(self, pack: ReviewPack) -> list[str]:
        L: list[str] = []

        # ── Header ──────────────────────────────────────────────────────
        L.append("=" * 60)
        L.append(f"  REVIEW PACK — {pack.seed_cluster}")
        L.append("=" * 60)
        L.append(f"  Seed cluster : {pack.seed_cluster}")
        L.append(f"  Documents    : {pack.seed_docs}")
        L.append(f"  Examples     : {', '.join(pack.seed_examples)}")
        L.append(f"  Generated from: {pack.meta.get('generated_from', '?')}")
        L.append(f"  Cluster-linked candidates : {pack.meta.get('total_cluster_linked', '?')}")
        L.append(f"  Global candidates used    : {pack.meta.get('total_global_used', '?')}")
        L.append("")

        # ── Sections ────────────────────────────────────────────────────
        for section in pack.sections:
            L.append(f"── {section.type.upper()} ──")
            for item in section.items:
                cluster_tag = f" [cluster-linked]" if item.cluster else ""
                ex = " / ".join(item.examples[:3]) if item.examples else "—"
                L.append(f"  {item.docs:>5}x  {item.canonical:<30}  ex: {ex}{cluster_tag}")
            L.append("")

        # ── Curator questions ────────────────────────────────────────────
        if pack.curator_questions:
            L.append("── CURATOR QUESTIONS ──")
            for i, q in enumerate(pack.curator_questions, start=1):
                L.append(f"  Q{i:02d}. {q}")
            L.append("")

        L.append("=" * 60)
        return L
