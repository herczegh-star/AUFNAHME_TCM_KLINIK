"""
block_loader.py
---------------
Loads and validates the AI-Draft block library from JSON.

Responsibilities:
- Read data/ai_draft/ai_draft_library.json
- Deserialize each entry into a typed Block instance
- Validate every block via Block.validate()
- Provide indexed access by cluster and by id

Does NOT perform:
- block selection
- composition / ordering
- scoring
- AI refinement

Follows: docs/AI_DRAFT_ARCHITECTURE_SPEC.md  (STEP 3)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.ai_draft.block_model import (
    Block,
    BlockComposition,
    BlockLanguage,
    BlockQuality,
    BlockType,
)


class BlockLoaderError(Exception):
    """Raised when the library cannot be loaded or a block fails validation."""


class BlockLoader:

    _LIBRARY_PATH = (
        Path(__file__).parent.parent.parent / "data" / "ai_draft" / "ai_draft_library.json"
    )

    def __init__(self) -> None:
        self._blocks: list[Block] | None = None
        self._by_id:  dict[str, Block]   = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_blocks(self) -> list[Block]:
        """
        Load, parse and validate all blocks from the library.
        Results are cached — subsequent calls return the same list.
        Call reload_blocks() to force a fresh load.
        """
        if self._blocks is None:
            self._blocks = self._load()
            self._by_id  = {b.id: b for b in self._blocks}
        return self._blocks

    def reload_blocks(self) -> list[Block]:
        """Invalidate cache and reload from disk."""
        self._blocks = None
        self._by_id  = {}
        return self.load_blocks()

    def get_blocks_by_cluster(self, cluster: str) -> list[Block]:
        """Return all blocks that belong to the given cluster."""
        return [b for b in self.load_blocks() if b.cluster == cluster]

    def get_block_by_id(self, block_id: str) -> Block | None:
        """Return the block with the given id, or None if not found."""
        self.load_blocks()
        return self._by_id.get(block_id)

    # ------------------------------------------------------------------
    # Private: load pipeline
    # ------------------------------------------------------------------

    def _load(self) -> list[Block]:
        raw_library = self._read_json()
        self._check_structure(raw_library)
        return self._parse_all(raw_library["library"])

    def _read_json(self) -> dict[str, Any]:
        if not self._LIBRARY_PATH.exists():
            raise BlockLoaderError(
                f"ai_draft_library.json nicht gefunden: {self._LIBRARY_PATH}"
            )
        try:
            with self._LIBRARY_PATH.open(encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise BlockLoaderError(
                f"ai_draft_library.json enthält ungültiges JSON: {exc}"
            ) from exc
        if not isinstance(data, dict):
            raise BlockLoaderError(
                "ai_draft_library.json: Root-Element muss ein JSON-Objekt sein."
            )
        return data

    def _check_structure(self, data: dict[str, Any]) -> None:
        if "library" not in data:
            raise BlockLoaderError(
                "ai_draft_library.json: Pflichtfeld 'library' fehlt."
            )
        if not isinstance(data["library"], list):
            raise BlockLoaderError(
                "ai_draft_library.json: 'library' muss ein JSON-Array sein."
            )

    def _parse_all(self, entries: list[Any]) -> list[Block]:
        blocks:     list[Block]  = []
        seen_ids:   set[str]     = set()

        for i, raw in enumerate(entries):
            if not isinstance(raw, dict):
                raise BlockLoaderError(
                    f"library[{i}]: Eintrag muss ein JSON-Objekt sein."
                )

            block_id = raw.get("id", f"<unbekannt, Index {i}>")

            # Duplicate id check
            if block_id in seen_ids:
                raise BlockLoaderError(
                    f"Doppelte Block-ID gefunden: '{block_id}' (Index {i})."
                )
            seen_ids.add(block_id)

            # Parse
            block = self._parse_block(raw, block_id)

            # Validate
            errors = block.validate()
            if errors:
                detail = "; ".join(errors)
                raise BlockLoaderError(
                    f"Block '{block_id}' ist ungültig: {detail}"
                )

            blocks.append(block)

        return blocks

    # ------------------------------------------------------------------
    # Private: single block deserialization
    # ------------------------------------------------------------------

    def _parse_block(self, raw: dict[str, Any], block_id: str) -> Block:
        # --- type ---
        raw_type = raw.get("type", "")
        try:
            block_type = BlockType(raw_type)
        except ValueError:
            valid = [t.value for t in BlockType]
            raise BlockLoaderError(
                f"Block '{block_id}': unbekannter Typ '{raw_type}'. "
                f"Erlaubte Werte: {valid}"
            ) from None

        # --- composition ---
        raw_comp = raw.get("composition", {})
        composition = BlockComposition(
            allowed_with   = list(raw_comp.get("allowed_with",   [])),
            forbidden_with = list(raw_comp.get("forbidden_with", [])),
            requires       = list(raw_comp.get("requires",       [])),
        )

        # --- language ---
        raw_lang = raw.get("language", {})
        language = BlockLanguage(
            variants      = list(raw_lang.get("variants", [])),
            language_code = str(raw_lang.get("language_code", "de")),
        )

        # --- quality ---
        raw_qual = raw.get("quality", {})
        quality = BlockQuality(
            score     = float(raw_qual.get("score",     0.0)),
            source    = str(raw_qual.get("source",    "")),
            validated = bool(raw_qual.get("validated", False)),
        )

        return Block(
            id          = str(raw.get("id",      "")),
            cluster     = str(raw.get("cluster", "")),
            type        = block_type,
            semantic    = dict(raw.get("semantic", {})),
            composition = composition,
            language    = language,
            quality     = quality,
        )
