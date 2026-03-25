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
    """
    draft_text:  str
    blocks_used: list[Block]         = field(default_factory=list)
    rule_result: RuleEngineResult    = field(
        default_factory=lambda: RuleEngineResult(is_valid=False)
    )
    is_valid:    bool                = False


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

        # Step 2 — select
        candidates = self._selector.select_blocks(input_data)

        # Step 3 — validate
        rule_result = self._engine.validate(candidates)

        # Step 4 — compose (only if valid and blocks remain)
        if not rule_result.is_valid or not rule_result.blocks:
            return DraftPipelineResult(
                draft_text  = "",
                blocks_used = rule_result.blocks,
                rule_result = rule_result,
                is_valid    = False,
            )

        draft_text = self._composer.compose(rule_result.blocks)

        return DraftPipelineResult(
            draft_text  = draft_text,
            blocks_used = rule_result.blocks,
            rule_result = rule_result,
            is_valid    = bool(draft_text),
        )
