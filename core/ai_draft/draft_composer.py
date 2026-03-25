"""
draft_composer.py
-----------------
Deterministic draft composer for the AI-Draft pipeline.

Takes a validated list of Blocks (output of rule_engine) and assembles
a short clinical German text using the blocks' language variants.

No AI. No free generation. Only deterministic assembly rules.

Composition order (per architecture spec):
  1. CORE_SYMPTOM               — base of sentence 1
  2. MODIFIER (character, radiation, aggravating, relieving)
                                — integrated into sentence 1 or own sentences
  3. FUNCTIONAL_IMPACT          — own sentence(s)
  4. ASSOCIATED_SYMPTOM         — own sentence(s)

Follows: docs/AI_DRAFT_ARCHITECTURE_SPEC.md  (STEP 6)
"""

from __future__ import annotations

from core.ai_draft.block_model import Block, BlockType


class DraftComposer:
    """
    Assembles validated blocks into a short clinical draft string.

    Design principles:
    - Always uses variant[0] (first / most neutral formulation).
    - Sentence 1 integrates CORE + character modifier(s) + radiation.
    - Aggravating / relieving modifiers become individual follow-up sentences.
    - FUNCTIONAL_IMPACT and ASSOCIATED_SYMPTOM close the draft.
    - Output uses Verdichtungsstil: short, factual, no filler.
    """

    def compose(self, blocks: list[Block]) -> str:
        """
        Assemble a clinical draft from the given block list.

        Returns an empty string if no CORE_SYMPTOM block is present.
        """
        if not blocks:
            return ""

        # Partition blocks by role
        cores        = self._of_type(blocks, BlockType.CORE_SYMPTOM)
        chars        = self._modifiers_of(blocks, "character")
        radiations   = self._modifiers_of(blocks, "radiation")
        aggravating  = self._modifiers_of(blocks, "aggravating_factor")
        relieving    = self._modifiers_of(blocks, "relieving_factor")
        functional   = self._of_type(blocks, BlockType.FUNCTIONAL_IMPACT)
        associated   = self._of_type(blocks, BlockType.ASSOCIATED_SYMPTOM)

        if not cores:
            return ""

        sentences: list[str] = []

        # --- Sentence 1: CORE + character modifiers + radiation ---
        sentences.append(
            self._build_core_sentence(cores[0], chars, radiations)
        )

        # --- Sentence 2+: aggravating / relieving modifiers (one each) ---
        for block in aggravating:
            sentences.append(self._sentence(block))
        for block in relieving:
            sentences.append(self._sentence(block))

        # --- Sentence 3+: functional impact ---
        for block in functional:
            sentences.append(self._sentence(block))

        # --- Last: associated symptoms ---
        for block in associated:
            sentences.append(self._sentence(block))

        return " ".join(sentences)

    # ------------------------------------------------------------------
    # Sentence builders
    # ------------------------------------------------------------------

    def _build_core_sentence(
        self,
        core: Block,
        chars: list[Block],
        radiations: list[Block],
    ) -> str:
        """
        Assemble the main symptom sentence.

        Pattern (Verdichtungsstil):
          {CORE_base}[, {char1[-char2…]}][; {radiation}].

        Examples:
          "Schmerzen lumbal beidseits."
          "Schmerzen lumbal beidseits, ziehend-stechend."
          "Schmerzen lumbal beidseits, mit Ausstrahlung ins Bein."
          "Schmerzen lumbal beidseits, ziehend-stechend, mit Ausstrahlung ins Bein."
        """
        base = self._strip(self._variant(core))

        # Character modifier(s): join with "-" for compound adjective
        char_str = ""
        if chars:
            char_parts = [self._strip(self._variant(c)) for c in chars]
            char_str = "-".join(p for p in char_parts if p)

        # Radiation: append after comma (same sentence, Verdichtungsstil)
        rad_str = ""
        if radiations:
            rad_str = self._strip(self._variant(radiations[0]))

        # Assemble
        result = base
        if char_str:
            result = f"{result}, {char_str}"
        if rad_str:
            result = f"{result}, {rad_str}"

        return result + "."

    def _sentence(self, block: Block) -> str:
        """Return the block's first variant as a complete sentence (with period)."""
        v = self._variant(block).strip()
        if not v:
            return ""
        return v if v.endswith(".") else v + "."

    # ------------------------------------------------------------------
    # Helpers: block partitioning
    # ------------------------------------------------------------------

    def _of_type(self, blocks: list[Block], block_type: BlockType) -> list[Block]:
        return [b for b in blocks if b.type == block_type]

    def _modifiers_of(self, blocks: list[Block], modifier_type: str) -> list[Block]:
        return [
            b for b in blocks
            if b.type == BlockType.MODIFIER
            and b.semantic.get("modifier_type") == modifier_type
        ]

    # ------------------------------------------------------------------
    # Helpers: language variant access
    # ------------------------------------------------------------------

    def _variant(self, block: Block) -> str:
        """Return the first non-empty language variant, or empty string."""
        for v in block.language.variants:
            if v and v.strip():
                return v.strip()
        return ""

    def _strip(self, text: str) -> str:
        """Remove trailing period and whitespace."""
        return text.rstrip(". ").strip()
