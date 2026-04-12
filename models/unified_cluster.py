"""
unified_cluster.py
------------------
Thin wrapper around a loaded unified-cluster JSON dict.

Provides typed property accessors so the rest of the codebase never
reaches into raw dicts for cluster data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class UnifiedCluster:
    """
    Wraps the raw JSON dict loaded from data/unified_clusters/<id>.json.
    All properties are read-only views; mutation goes through the dict directly.

    IMPORTANT — two different "id" concepts:
      cluster.id          — canonical clinical id from the JSON 'id' field
                            (e.g. "lws_syndrom").  Stable across file renames.
      cluster.storage_key — filename stem used by unified_cluster_service for
                            load/save/cache (e.g. "lws_syndrom_v1_1").
                            Set by the service at load time; NOT read from JSON.
    These must be kept separate.  save_edited() and cache lookups always use
    storage_key, never cluster.id.
    """
    _data: dict[str, Any]
    # Set by unified_cluster_service after load — not part of JSON data.
    _storage_key: str = field(default="", init=False)

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def id(self) -> str:
        """Canonical clinical id from the JSON 'id' field.  Stable across file renames."""
        return self._data["id"]

    @property
    def storage_key(self) -> str:
        """
        Filename stem used by unified_cluster_service for load/save/cache.
        Matches the JSON filename without extension (e.g. 'lws_syndrom_v1_1').
        Set by unified_cluster_service.load() — never derived from cluster.id.
        """
        return self._storage_key

    @property
    def name(self) -> str:
        return self._data["name"]

    @property
    def version(self) -> str:
        return self._data.get("version", "")

    @property
    def status(self) -> str:
        return self._data.get("status", "")

    # ------------------------------------------------------------------
    # Form
    # ------------------------------------------------------------------

    @property
    def form_fields(self) -> list[dict[str, Any]]:
        return self._data.get("form", {}).get("fields", [])

    @property
    def form_title(self) -> str:
        return self._data.get("form", {}).get("title", self.name)

    # ------------------------------------------------------------------
    # Style / narrative guidance
    # ------------------------------------------------------------------

    @property
    def style(self) -> dict[str, Any]:
        return self._data.get("style", {})

    @property
    def rules(self) -> list[str]:
        return self.style.get("rules", [])

    @property
    def preferred_phrases(self) -> dict[str, list[str]]:
        return self.style.get("preferred_phrases", {})

    @property
    def sprachbausteine(self) -> dict[str, list[str]]:
        """
        Named phrase groups for use in the Pilot-Composer UI.
        Keyed by group label → list of phrases.
        Stored under style.sprachbausteine in the cluster JSON.
        Returns an empty dict if the cluster does not define any groups.
        """
        return self.style.get("sprachbausteine", {})

    @property
    def forbidden_words(self) -> list[str]:
        return self.style.get("forbidden_words", [])

    @property
    def examples(self) -> list[dict[str, str]]:
        return self.style.get("examples", [])

    # ------------------------------------------------------------------
    # Render maps
    # ------------------------------------------------------------------

    @property
    def render_maps(self) -> dict[str, dict[str, str]]:
        # TODO: render_maps are currently documentation only — lws_narrative_composer
        # uses its own internal dicts, not these values.  To make the cluster the
        # true single source of truth for rendering, refactor the composer to read
        # from cluster.render_maps instead of hardcoded module-level dicts.
        return self._data.get("render_maps", {})

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------

    @property
    def normalization_maps(self) -> dict[str, dict[str, str]]:
        return self._data.get("normalization", {})

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    @property
    def pipeline_stages(self) -> list[dict[str, Any]]:
        return self._data.get("draft_pipeline", {}).get("stages", [])

    @property
    def fallback_stage(self) -> str:
        return self._data.get("draft_pipeline", {}).get("fallback_on_llm_error", "raw")

    # ------------------------------------------------------------------
    # Archetypes
    # ------------------------------------------------------------------

    @property
    def archetypes(self) -> list[dict[str, Any]]:
        return self._data.get("archetypes", [])

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    @property
    def tests(self) -> list[dict[str, Any]]:
        return self._data.get("tests", [])

    # ------------------------------------------------------------------
    # Clinical reference texts
    # ------------------------------------------------------------------

    @property
    def reference_texts(self) -> list[str]:
        """
        Return the 3 physician-authored reference text slots as a list of 3 strings.

        Backward-compat loading order:
          1. clinical_reference.reference_texts list (new schema) — padded/trimmed to 3
          2. clinical_reference.ideal_text (legacy single field) → slot 0, rest empty
          3. All empty strings if neither key exists
        """
        cr = self._data.get("clinical_reference", {})
        if "reference_texts" in cr:
            texts = list(cr["reference_texts"])
            # Normalise to exactly 3 slots
            while len(texts) < 3:
                texts.append("")
            return texts[:3]
        legacy = cr.get("ideal_text", "")
        return [legacy, "", ""]

    # ------------------------------------------------------------------
    # Raw access (for editor / serialisation)
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return self._data
