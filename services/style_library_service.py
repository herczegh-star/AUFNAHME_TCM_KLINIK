"""
style_library_service.py
------------------------
Loads and exposes style rules from data/style_library.json.

Provides cluster names and per-cluster ClusterStyleConfig instances.
No LLM. No UI. No side effects beyond file I/O.
"""

from __future__ import annotations

import json
from pathlib import Path

from core.draft_schema import ClusterStyleConfig


class StyleLibraryService:

    _LIBRARY_PATH = Path(__file__).parent.parent / "data" / "style_library.json"

    def __init__(self) -> None:
        self._library_data: dict | None = None

    def load_library(self) -> None:
        if not self._LIBRARY_PATH.exists():
            raise FileNotFoundError(
                f"style_library.json nicht gefunden: {self._LIBRARY_PATH}"
            )
        with self._LIBRARY_PATH.open(encoding="utf-8") as f:
            self._library_data = json.load(f)

    def reload_library(self) -> None:
        self._library_data = None
        self.load_library()

    def _ensure_loaded(self) -> dict:
        if self._library_data is None:
            self.load_library()
        return self._library_data  # type: ignore[return-value]

    def get_cluster_names(self) -> list[str]:
        data = self._ensure_loaded()
        return list(data.get("clusters", {}).keys())

    def get_cluster_config(self, cluster_name: str) -> ClusterStyleConfig:
        data = self._ensure_loaded()
        clusters = data.get("clusters", {})
        if cluster_name not in clusters:
            raise KeyError(
                f"Cluster '{cluster_name}' nicht in style_library gefunden. "
                f"Verfügbare Cluster: {list(clusters.keys())}"
            )
        c = clusters[cluster_name]
        return ClusterStyleConfig(
            cluster_name=cluster_name,
            meta=c.get("meta", {}),
            rules=c.get("rules", []),
            preferred_patterns=c.get("preferred_patterns", []),
            preferred_phrases=c.get("preferred_phrases", {}),
            examples=c.get("examples", []),
        )
