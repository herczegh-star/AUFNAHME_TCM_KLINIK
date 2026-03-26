"""
archetype_loader.py
-------------------
Loads and serves clinically validated ready-made archetype patterns from
data/template_library_archetypes.json.

This is NOT AI generation. This is a simple selectable text library.

Public API:
  load_archetype_library()                        -> dict
  get_archetypes_for_cluster(cluster_id)          -> dict | None
  get_archetype_text(cluster_id, pattern_id)      -> str | None
"""
from __future__ import annotations

import json
from pathlib import Path

_LIBRARY_PATH = Path(__file__).parent.parent.parent / "data" / "template_library_archetypes.json"

_cache: dict | None = None


def load_archetype_library() -> dict:
    """
    Load the archetype library from disk (cached after first call).
    Returns the full library dict. Returns {} on any read/parse error.
    """
    global _cache
    if _cache is not None:
        return _cache
    try:
        _cache = json.loads(_LIBRARY_PATH.read_text(encoding="utf-8"))
    except Exception:
        _cache = {}
    return _cache


def get_archetypes_for_cluster(cluster_id: str) -> dict | None:
    """
    Return the entry for cluster_id (e.g. "LWS-Syndrom"), or None if not found.
    """
    library = load_archetype_library()
    return library.get(cluster_id)


def get_archetype_text(cluster_id: str, pattern_id: str) -> str | None:
    """
    Return the ready-made text for cluster_id + pattern_id (e.g. "LWS-Syndrom", "LWS1"),
    or None if either the cluster or the pattern does not exist.
    """
    entry = get_archetypes_for_cluster(cluster_id)
    if entry is None:
        return None
    pattern = entry.get("patterns", {}).get(pattern_id)
    if pattern is None:
        return None
    return pattern.get("text") or None
