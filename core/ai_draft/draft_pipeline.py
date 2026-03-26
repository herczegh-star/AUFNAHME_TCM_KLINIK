"""
draft_pipeline.py
-----------------
Orchestration layer for the deterministic AI-Draft pilot.

Connects: BlockLoader → BlockSelector → RuleEngine → DraftComposer

No AI. No language refinement. End-to-end deterministic.

Follows: docs/AI_DRAFT_ARCHITECTURE_SPEC.md  (STEP 7)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.ai_draft.block_loader import BlockLoader
from core.ai_draft.block_model import Block
from core.ai_draft.block_selector import BlockSelector
from core.ai_draft.draft_composer import DraftComposer
from core.ai_draft.input_normalizer import InputNormalizer
from core.ai_draft.rule_engine import RuleEngine, RuleEngineResult
from core.ai_draft.narrative_dispatcher import compose_narrative
from core.ai_draft.shared_pain_loader import (
    get_cluster_family_info,
    get_family_allowed_modules,
)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class DraftPipelineResult:
    """
    Full output of one pipeline run.

    draft_text:   Final assembled clinical text. Empty string if pipeline failed.
    blocks_used:  Blocks after rule engine — the exact blocks reflected in draft_text.
    rule_result:  Full rule engine output (violations, is_valid, cleaned block list).
    is_valid:     False if rule engine found critical violations or no blocks remain.

    -- Shared pain layer (architectural pilot, not yet used in draft composition) --
    cluster_family_info:          {"primary_family": ..., "overlays": [...]} or None
    shared_pain_modules_available: sorted list of shared module names for this cluster

    -- Narrative preview (read-only experimental layer) --
    narrative_preview: German clinical sentence from narrative_dispatcher, or None
                       if no composer is registered for this cluster.
                       Never merged into draft_text. Never affects blocks_used or rule_result.
    """
    draft_text:   str
    blocks_used:  list[Block]         = field(default_factory=list)
    rule_result:  RuleEngineResult    = field(
        default_factory=lambda: RuleEngineResult(is_valid=False)
    )
    is_valid:     bool                = False
    # Shared pain layer info — populated on every run, regardless of draft validity
    cluster_family_info:           dict | None        = None
    shared_pain_modules_available: list[str]          = field(default_factory=list)
    # Concrete shared pain items matched from normalized_input (selection only, not yet composed)
    shared_pain_items_selected:    dict[str, list[str]] = field(default_factory=dict)
    # Narrative preview — experimental, read-only, never affects production draft
    narrative_preview:             str | None           = None


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class DraftPipeline:
    """
    Deterministic pilot pipeline for a single cluster.

    Usage:
        pipeline = DraftPipeline()
        result   = pipeline.run({"cluster": "LWS-Syndrom", "side": "beidseits", ...})
    """

    def __init__(self) -> None:
        loader            = BlockLoader()
        self._normalizer  = InputNormalizer()
        self._selector    = BlockSelector(loader)
        self._engine      = RuleEngine()
        self._composer    = DraftComposer()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, input_data: dict[str, Any]) -> DraftPipelineResult:
        """
        Execute the full pipeline for the given input.

        Steps:
          1. BlockSelector  — select candidate blocks
          2. RuleEngine     — validate and clean the selection
          3. DraftComposer  — assemble the draft (only if valid)

        Returns DraftPipelineResult with draft_text="" and is_valid=False
        if the rule engine finds critical violations or no blocks remain.
        """
        # Step 1 — normalize
        input_data = self._normalizer.normalize_input(input_data)

        # Step 2 — resolve shared pain layer (family info + concrete item selection)
        cluster_id    = str(input_data.get("cluster", "")).strip()
        cid_key       = self._to_cluster_id(cluster_id)
        family_info   = get_cluster_family_info(cid_key)
        shared_mods   = sorted(get_family_allowed_modules(cid_key))
        shared_items  = self._selector.select_shared_pain_items(cid_key, input_data)

        # Step 2b — narrative preview (read-only, no effect on downstream steps)
        narrative_preview = compose_narrative(cid_key, shared_items)

        # Step 3 — select cluster blocks (unchanged)
        candidates = self._selector.select_blocks(input_data)

        # Step 4 — validate
        rule_result = self._engine.validate(candidates)

        # Step 5 — compose (only if valid and blocks remain)
        if not rule_result.is_valid or not rule_result.blocks:
            return DraftPipelineResult(
                draft_text                    = "",
                blocks_used                   = rule_result.blocks,
                rule_result                   = rule_result,
                is_valid                      = False,
                cluster_family_info           = family_info,
                shared_pain_modules_available = shared_mods,
                shared_pain_items_selected    = shared_items,
                narrative_preview             = narrative_preview,
            )

        draft_text = self._composer.compose(rule_result.blocks)

        return DraftPipelineResult(
            draft_text                    = draft_text,
            blocks_used                   = rule_result.blocks,
            rule_result                   = rule_result,
            is_valid                      = bool(draft_text),
            cluster_family_info           = family_info,
            shared_pain_modules_available = shared_mods,
            shared_pain_items_selected    = shared_items,
            narrative_preview             = narrative_preview,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_cluster_id(cluster_name: str) -> str:
        """
        Convert display cluster name to cluster_family_map id format.
        e.g. "LWS-Syndrom" → "lws_syndrom"
        """
        return cluster_name.lower().replace("-", "_").replace(" ", "_")
