"""
shared_pain_loader.py
---------------------
Loader for the shared pain layer (data/ai_draft/shared_pain_layer_v2.json).

Provides family-aware access to shared pain modules for any cluster.

API:
  load_shared_pain_layer()              -> dict          (full raw JSON)
  get_family_allowed_modules(cluster_id)-> set[str]      (union of primary + overlay modules)
  get_module_items(module_name)         -> list[dict]    (items of a block_group module)
  get_module_definition(module_name)    -> dict | None   (full module definition)
  get_cluster_family_info(cluster_id)   -> dict | None   (primary_family + overlays)

JSON is loaded once and cached for the process lifetime.
Call _invalidate_cache() in tests to force reload.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_LAYER_PATH = (
    Path(__file__).parent.parent.parent
    / "data" / "ai_draft" / "shared_pain_layer_v2.json"
)

# Module-level cache — loaded on first access, shared across all callers
_cache: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------

def load_shared_pain_layer() -> dict[str, Any]:
    """
    Return the full shared pain layer as a raw dict.
    Loads from disk on first call; returns cached dict on subsequent calls.
    """
    global _cache
    if _cache is None:
        if not _LAYER_PATH.exists():
            raise FileNotFoundError(
                f"shared_pain_layer_v2.json not found: {_LAYER_PATH}"
            )
        with _LAYER_PATH.open(encoding="utf-8") as fh:
            _cache = json.load(fh)
    return _cache


def _invalidate_cache() -> None:
    """Force reload on next access. Intended for tests only."""
    global _cache
    _cache = None


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def get_cluster_family_info(cluster_id: str) -> dict[str, Any] | None:
    """
    Return {"primary_family": str, "overlays": list[str]} for cluster_id.
    Returns None if cluster_id is not in the map.
    """
    layer = load_shared_pain_layer()
    key = cluster_id.strip().lower()
    for entry in layer.get("cluster_family_map", []):
        if entry.get("cluster_id", "").lower() == key:
            return {
                "primary_family": entry.get("primary_family", "none"),
                "overlays":       list(entry.get("overlays", [])),
            }
    return None


def get_family_allowed_modules(cluster_id: str) -> set[str]:
    """
    Return the union of allowed_modules for primary_family + all overlays.

    Example:
        hws_syndrom → mechanical ∪ neurogenic ∪ cephalgic
        → {"pain_character", "pain_laterality", ..., "cephalgic_features", ...}

    Returns empty set if cluster_id is not in the map.
    """
    family_info = get_cluster_family_info(cluster_id)
    if family_info is None:
        return set()

    layer    = load_shared_pain_layer()
    families = layer.get("pain_families", {})

    families_to_merge = [family_info["primary_family"]] + family_info["overlays"]

    allowed: set[str] = set()
    for family_name in families_to_merge:
        family_def = families.get(family_name, {})
        allowed.update(family_def.get("allowed_modules", []))

    return allowed


def get_module_definition(module_name: str) -> dict[str, Any] | None:
    """
    Return the full definition dict for a module, or None if not found.
    """
    layer = load_shared_pain_layer()
    return layer.get("modules", {}).get(module_name)


def get_module_items(module_name: str) -> list[dict[str, Any]]:
    """
    Return the items list for a block_group module.
    Returns [] for slot_group / template_group / unknown modules.
    """
    defn = get_module_definition(module_name)
    if defn is None:
        return []
    return list(defn.get("items", []))


def get_allowed_modules_with_definitions(cluster_id: str) -> dict[str, dict[str, Any]]:
    """
    Return a dict of {module_name: module_definition} for all modules
    allowed for the given cluster.

    Convenience helper for block_selector and draft_pipeline.
    """
    allowed = get_family_allowed_modules(cluster_id)
    layer   = load_shared_pain_layer()
    modules = layer.get("modules", {})
    return {name: modules[name] for name in allowed if name in modules}
