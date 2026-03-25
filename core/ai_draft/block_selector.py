"""
block_selector.py
-----------------
Deterministic block selector for the AI-Draft pilot (LWS cluster).

Given a structured input dict, selects a coherent set of Blocks
that can be composed into a clinical draft.

Does NOT perform:
- scoring / ranking
- language composition
- AI refinement
- multi-cluster inference

Selection is entirely rule-based and traceable.

Follows: docs/AI_DRAFT_ARCHITECTURE_SPEC.md  (STEP 4)
"""

from __future__ import annotations

from typing import Any

from core.ai_draft.block_loader import BlockLoader
from core.ai_draft.block_model import Block, BlockType


class BlockSelector:
    """
    Deterministic selector for a single cluster.

    Input keys (all optional except 'cluster'):
        cluster             str       — required, e.g. "LWS-Syndrom"
        side                str       — "beidseits" | "rechts" | "links"
        character           list[str] — e.g. ["ziehend", "stechend"]
        radiation           bool|str  — truthy → include radiation modifier
        aggravating_factor  str       — trigger label, e.g. "langes Sitzen"
        relieving_factor    str       — trigger label, e.g. "Wärme"
        functional_limitations list[str] — e.g. ["Sitzen", "Gehen"]
        associated_symptoms    list[str] — e.g. ["morning_stiffness"]
    """

    def __init__(self, loader: BlockLoader) -> None:
        self._loader = loader

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def select_blocks(self, input_data: dict[str, Any]) -> list[Block]:
        """
        Return an ordered, constraint-valid list of blocks for the given input.

        Order follows composition spec:
          1. CORE_SYMPTOM
          2. MODIFIER (character → radiation → aggravating → relieving)
          3. FUNCTIONAL_IMPACT
          4. ASSOCIATED_SYMPTOM

        Blocks that violate requires or forbidden_with are silently dropped.
        """
        cluster = str(input_data.get("cluster", "")).strip()
        if not cluster:
            return []

        pool = self._loader.get_blocks_by_cluster(cluster)
        if not pool:
            return []

        selected: list[Block] = []

        # 1 — CORE
        core = self._select_core(pool, input_data)
        if core:
            selected.append(core)

        # 2 — MODIFIERs
        selected.extend(self._select_modifiers(pool, input_data, selected))

        # 3 — FUNCTIONAL_IMPACT
        selected.extend(self._select_functional(pool, input_data, selected))

        # 4 — ASSOCIATED_SYMPTOM
        selected.extend(self._select_associated(pool, input_data, selected))

        # Final constraint pass
        selected = self._enforce_requires(selected)
        selected = self._enforce_forbidden(selected)

        return selected

    # ------------------------------------------------------------------
    # Private: CORE selection
    # ------------------------------------------------------------------

    def _select_core(
        self, pool: list[Block], input_data: dict[str, Any]
    ) -> Block | None:
        """
        Select one CORE_SYMPTOM block.

        Matching strategy:
          - Match block.semantic["side"] against input_data["side"]
          - Fallback: first CORE block in pool
        """
        side = str(input_data.get("side", "")).strip().lower()

        cores = [b for b in pool if b.type == BlockType.CORE_SYMPTOM]
        if not cores:
            return None

        if side:
            for block in cores:
                block_side = str(block.semantic.get("side", "")).lower()
                if block_side == side:
                    return block

        # Fallback: first available CORE
        return cores[0]

    # ------------------------------------------------------------------
    # Private: MODIFIER selection
    # ------------------------------------------------------------------

    def _select_modifiers(
        self,
        pool: list[Block],
        input_data: dict[str, Any],
        already_selected: list[Block],
    ) -> list[Block]:
        """
        Select MODIFIER blocks in sub-type order:
          character → radiation → aggravating_factor → relieving_factor
        """
        result: list[Block] = []
        modifiers = [b for b in pool if b.type == BlockType.MODIFIER]

        # Normalise input
        raw_chars = input_data.get("character", [])
        characters: list[str] = (
            [raw_chars] if isinstance(raw_chars, str) else list(raw_chars)
        )
        characters = [c.strip().lower() for c in characters if c]

        radiation        = input_data.get("radiation")
        aggravating_raw  = str(input_data.get("aggravating_factor", "")).strip().lower()
        relieving_raw    = str(input_data.get("relieving_factor",   "")).strip().lower()

        for block in modifiers:
            mod_type = str(block.semantic.get("modifier_type", ""))

            if mod_type == "character":
                value = str(block.semantic.get("value", "")).lower()
                if value in characters:
                    result.append(block)

            elif mod_type == "radiation":
                if radiation:
                    result.append(block)

            elif mod_type == "aggravating_factor":
                if aggravating_raw:
                    trigger = str(block.semantic.get("trigger_label", "")).lower()
                    if trigger and trigger in aggravating_raw:
                        result.append(block)

            elif mod_type == "relieving_factor":
                if relieving_raw:
                    trigger = str(block.semantic.get("trigger_label", "")).lower()
                    if trigger and trigger in relieving_raw:
                        result.append(block)

        return result

    # ------------------------------------------------------------------
    # Private: FUNCTIONAL_IMPACT selection
    # ------------------------------------------------------------------

    def _select_functional(
        self,
        pool: list[Block],
        input_data: dict[str, Any],
        already_selected: list[Block],
    ) -> list[Block]:
        """
        Select FUNCTIONAL_IMPACT blocks.

        Matching: check if limitation_type keyword appears in
        functional_limitations input list.

        Keyword map:
          "sitting_tolerance" ← "sitz"
          "walking_distance"  ← "geh" | "lauf"
        """
        raw = input_data.get("functional_limitations", [])
        limitations: list[str] = (
            [raw] if isinstance(raw, str) else list(raw)
        )
        limitations = [l.strip().lower() for l in limitations if l]

        if not limitations:
            return []

        _KEYWORD_MAP: dict[str, list[str]] = {
            "sitting_tolerance": ["sitz", "sitting"],
            "walking_distance":  ["geh", "lauf", "walking"],
        }

        result: list[Block] = []
        for block in pool:
            if block.type != BlockType.FUNCTIONAL_IMPACT:
                continue
            lim_type = str(block.semantic.get("limitation_type", ""))
            # Primary: exact match against limitation_type identifier
            if lim_type.lower() in limitations:
                result.append(block)
                continue
            # Fallback: keyword substring match (for free-text inputs)
            keywords = _KEYWORD_MAP.get(lim_type, [])
            if any(
                kw in lim_str
                for kw in keywords
                for lim_str in limitations
            ):
                result.append(block)

        return result

    # ------------------------------------------------------------------
    # Private: ASSOCIATED_SYMPTOM selection
    # ------------------------------------------------------------------

    def _select_associated(
        self,
        pool: list[Block],
        input_data: dict[str, Any],
        already_selected: list[Block],
    ) -> list[Block]:
        """
        Select ASSOCIATED_SYMPTOM blocks.

        Only included when explicitly named in input_data["associated_symptoms"].
        Selective blocks (semantic["selective"] == True) follow the same rule.
        """
        raw = input_data.get("associated_symptoms", [])
        requested: list[str] = (
            [raw] if isinstance(raw, str) else list(raw)
        )
        requested = [s.strip().lower() for s in requested if s]

        if not requested:
            return []

        result: list[Block] = []
        for block in pool:
            if block.type != BlockType.ASSOCIATED_SYMPTOM:
                continue
            symptom = str(block.semantic.get("symptom", "")).lower()
            if any(req in symptom or symptom in req for req in requested):
                result.append(block)

        return result

    # ------------------------------------------------------------------
    # Private: constraint enforcement
    # ------------------------------------------------------------------

    def _enforce_requires(self, selected: list[Block]) -> list[Block]:
        """
        Drop blocks whose 'requires' list has no match in the selected set.

        Requires uses OR logic: at least ONE of the listed IDs must be present.
        Blocks with an empty requires list are always kept.
        """
        selected_ids = {b.id for b in selected}
        result: list[Block] = []
        for block in selected:
            req = block.composition.requires
            if not req or any(r in selected_ids for r in req):
                result.append(block)
            # else: drop — required block absent
        return result

    def _enforce_forbidden(self, selected: list[Block]) -> list[Block]:
        """
        Remove blocks that are forbidden given the current selection.

        Priority: blocks appearing earlier in the list (CORE first) are kept;
        later blocks are dropped if they conflict.
        """
        kept:    list[Block] = []
        kept_ids: set[str]   = set()

        for block in selected:
            conflicts = any(
                f in kept_ids for f in block.composition.forbidden_with
            ) or any(
                block.id in b.composition.forbidden_with for b in kept
            )
            if not conflicts:
                kept.append(block)
                kept_ids.add(block.id)

        return kept
