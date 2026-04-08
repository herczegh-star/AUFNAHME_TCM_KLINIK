"""
unified_cluster_service.py
--------------------------
Loads and caches UnifiedCluster objects from data/unified_clusters/.

Saves edited clusters as <id>.edited.json next to the originals so
the originals are never overwritten by the author tool.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models.unified_cluster import UnifiedCluster

_CLUSTER_DIR = Path(__file__).parent.parent / "data" / "unified_clusters"
_cache: dict[str, UnifiedCluster] = {}


def load(storage_key: str, *, bust_cache: bool = False) -> UnifiedCluster:
    """
    Load a cluster by storage_key (= filename stem, e.g. 'lws_syndrom_v1_1').

    NOTE: storage_key is the filename stem, NOT the JSON 'id' field.
    They are intentionally different:
      - JSON 'id'   = canonical clinical id, e.g. "lws_syndrom"
      - storage_key = filename stem,          e.g. "lws_syndrom_v1_1"
    All cache lookups and save/load operations use storage_key exclusively.

    Prefers <storage_key>.edited.json over <storage_key>.json.
    Results are cached; pass bust_cache=True to reload from disk.
    """
    if storage_key in _cache and not bust_cache:
        return _cache[storage_key]

    edited   = _CLUSTER_DIR / f"{storage_key}.edited.json"
    original = _CLUSTER_DIR / f"{storage_key}.json"

    path = edited if edited.exists() else original
    if not path.exists():
        raise FileNotFoundError(
            f"No cluster file found for storage_key={storage_key!r} in {_CLUSTER_DIR}"
        )

    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    cluster = UnifiedCluster(_data=data)
    cluster._storage_key = storage_key  # bind storage_key — distinct from cluster.id
    _cache[storage_key] = cluster
    return cluster


def load_lws() -> UnifiedCluster:
    """Convenience shortcut for the LWS pilot cluster."""
    return load("lws_syndrom_v1_1")


def save_edited(cluster: UnifiedCluster) -> Path:
    """
    Persist an edited cluster to <storage_key>.edited.json.
    Uses cluster.storage_key (filename stem), NOT cluster.id (clinical id).
    Returns the path written.
    """
    if not cluster.storage_key:
        raise ValueError(
            "cluster.storage_key is not set — cluster was not loaded via unified_cluster_service.load()"
        )
    path = _CLUSTER_DIR / f"{cluster.storage_key}.edited.json"
    path.write_text(
        json.dumps(cluster.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    # Invalidate cache using storage_key so next load() re-reads from disk
    _cache.pop(cluster.storage_key, None)
    return path


def list_available() -> list[str]:
    """Return storage_keys of all cluster files found in the cluster directory."""
    ids: list[str] = []
    for p in sorted(_CLUSTER_DIR.glob("*.json")):
        if p.stem.endswith(".edited"):
            continue  # skip edited copies from the list
        ids.append(p.stem)
    return ids


def create_cluster(cluster_id: str, display_name: str) -> UnifiedCluster:
    """
    Create a new cluster scaffold and save as data/unified_clusters/<cluster_id>_v1_0.json.

    The scaffold is a minimal valid cluster structure compatible with:
      - P1: form.fields with shared_items_key
      - P2: render_maps + preferred_phrases.anchor for generic composer
      - Builder: all keys expected by load/save/tabs are present

    Parameters
    ----------
    cluster_id :
        Canonical clinical id, lowercase letters, digits, underscores.
        e.g. "schulter_syndrom"
    display_name :
        Human-readable name, e.g. "Schulter-Syndrom"

    Returns
    -------
    UnifiedCluster
        Loaded cluster with storage_key set.

    Raises
    ------
    ValueError
        If cluster_id is invalid or the target file already exists.
    """
    if not cluster_id:
        raise ValueError("cluster_id darf nicht leer sein.")
    if not all(c.isalnum() or c == "_" for c in cluster_id) or not cluster_id[0].isalpha():
        raise ValueError(
            f"Ungueltige cluster_id {cluster_id!r}. "
            "Nur Kleinbuchstaben, Ziffern und Unterstriche erlaubt; muss mit Buchstabe beginnen."
        )
    if not display_name:
        raise ValueError("display_name darf nicht leer sein.")

    storage_key = f"{cluster_id}_v1_0"
    target = _CLUSTER_DIR / f"{storage_key}.json"
    if target.exists():
        raise ValueError(
            f"Cluster-Datei existiert bereits: {target.name}"
        )

    scaffold: dict = {
        "id": cluster_id,
        "name": display_name,
        "aliases": [],
        "status": "draft",
        "version": "1.0",
        "category": "",
        "family": "",
        "tags": [],
        "meta": {
            "icd10": "",
            "icd10_label": "",
            "anatomical_region": "",
            "typical_age_range": "",
            "tcm_pattern_hints": []
        },
        "form": {
            "title": f"{display_name} \u2013 Anamnese",
            "fields": []
        },
        "normalization": {},
        "style": {
            "rules": [],
            "preferred_phrases": {
                "anchor": [f"Beschwerden im {display_name}-Bereich"]
            },
            "forbidden_words": [],
            "examples": []
        },
        "render_maps": {},
        "archetypes": [],
        "tests": [],
        "draft_pipeline": {
            "stages": [],
            "fallback_on_llm_error": "raw"
        }
    }

    target.write_text(
        json.dumps(scaffold, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return load(storage_key, bust_cache=True)
