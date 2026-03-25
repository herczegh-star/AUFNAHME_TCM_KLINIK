"""
block_model.py
--------------
Strict data model for the AI-Draft block system.

A Block is a structured unit of clinical meaning.
Text (language layer) is always secondary to meaning (semantic layer).

Follows: docs/AI_DRAFT_ARCHITECTURE_SPEC.md

DO NOT mix semantic and language layers.
DO NOT use this module for free AI generation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# BlockType
# ---------------------------------------------------------------------------

class BlockType(str, Enum):
    """Defines the clinical role of a block within a composed draft."""

    CORE_SYMPTOM      = "CORE_SYMPTOM"       # Main complaint. Mandatory. Max 1–3.
    MODIFIER          = "MODIFIER"            # Modifies a core block. Cannot exist alone.
    CONTEXT           = "CONTEXT"             # Defines clinical framework. Must not conflict.
    ASSOCIATED_SYMPTOM = "ASSOCIATED_SYMPTOM" # Secondary complaint.
    FUNCTIONAL_IMPACT = "FUNCTIONAL_IMPACT"   # Describes functional limitation.
    TEMPORAL          = "TEMPORAL"            # Time evolution / onset / duration.
    EXPERT            = "EXPERT"              # Advanced or specialist formulation.


# ---------------------------------------------------------------------------
# BlockComposition
# ---------------------------------------------------------------------------

@dataclass
class BlockComposition:
    """
    Rules governing how this block may be combined with others.

    All fields reference block IDs (strings).
    """

    allowed_with:  list[str] = field(default_factory=list)
    """Block IDs this block may appear together with."""

    forbidden_with: list[str] = field(default_factory=list)
    """Block IDs that must NOT appear in the same draft."""

    requires: list[str] = field(default_factory=list)
    """Block IDs that MUST be present if this block is used."""


# ---------------------------------------------------------------------------
# BlockLanguage
# ---------------------------------------------------------------------------

@dataclass
class BlockLanguage:
    """
    Textual representation of the block's meaning.

    One block must have at least one variant.
    Multiple variants represent stylistically different phrasings of
    the identical clinical meaning — never different meanings.
    """

    variants: list[str] = field(default_factory=list)
    """1–3 language variants. Same meaning, different phrasing."""

    language_code: str = "de"
    """ISO 639-1 language code. Default: German."""

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.variants:
            errors.append("BlockLanguage: at least one variant is required.")
        for i, v in enumerate(self.variants):
            if not v or not v.strip():
                errors.append(f"BlockLanguage: variant[{i}] must not be empty.")
        if len(self.variants) > 3:
            errors.append(
                f"BlockLanguage: max 3 variants allowed, got {len(self.variants)}."
            )
        return errors


# ---------------------------------------------------------------------------
# BlockQuality
# ---------------------------------------------------------------------------

@dataclass
class BlockQuality:
    """
    Quality and provenance metadata for the block.

    score:     0.0–1.0. Higher = more reliable.
    source:    Origin of the block (e.g. "manual_curation", "dataset_extraction").
    validated: Whether a clinician has confirmed the block.
    """

    score:     float = 0.0
    source:    str   = ""
    validated: bool  = False

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not (0.0 <= self.score <= 1.0):
            errors.append(
                f"BlockQuality: score must be in [0.0, 1.0], got {self.score}."
            )
        return errors


# ---------------------------------------------------------------------------
# Block  (main dataclass)
# ---------------------------------------------------------------------------

@dataclass
class Block:
    """
    A structured unit of clinical meaning.

    Layers (in order of priority):
      1. IDENTIFICATION — who is this block
      2. SEMANTIC       — what does it mean (clinical reality)
      3. COMPOSITION    — how does it combine with others
      4. LANGUAGE       — how is it expressed in text
      5. QUALITY        — how reliable is it

    Rule: semantic meaning must be defined BEFORE language variants are written.
    """

    # --- IDENTIFICATION ---
    id:      str       = ""
    cluster: str       = ""
    type:    BlockType = BlockType.CORE_SYMPTOM

    # --- SEMANTIC ---
    # dict[str, Any] allows flexible keys per block type.
    # Future: replace with typed subclasses (e.g. CoreSymptomSemantic).
    # Example keys: "localisation", "character", "radiation", "onset"
    semantic: dict[str, Any] = field(default_factory=dict)

    # --- COMPOSITION ---
    composition: BlockComposition = field(default_factory=BlockComposition)

    # --- LANGUAGE ---
    language: BlockLanguage = field(default_factory=BlockLanguage)

    # --- QUALITY ---
    quality: BlockQuality = field(default_factory=BlockQuality)

    # -----------------------------------------------------------------------
    # Validation
    # -----------------------------------------------------------------------

    def validate(self) -> list[str]:
        """
        Returns a list of validation error strings.
        Empty list means the block is valid.
        """
        errors: list[str] = []

        # Identification
        if not self.id or not self.id.strip():
            errors.append("Block: 'id' must not be empty.")
        if not self.cluster or not self.cluster.strip():
            errors.append("Block: 'cluster' must not be empty.")
        if not isinstance(self.type, BlockType):
            errors.append(
                f"Block: 'type' must be a BlockType, got {type(self.type).__name__}."
            )

        # Language
        errors.extend(self.language.validate())

        # Quality
        errors.extend(self.quality.validate())

        return errors

    def is_valid(self) -> bool:
        """Returns True if the block passes all validation checks."""
        return len(self.validate()) == 0

    # -----------------------------------------------------------------------
    # Helper methods
    # -----------------------------------------------------------------------

    def is_core(self) -> bool:
        """True if this block is a primary complaint (CORE_SYMPTOM)."""
        return self.type == BlockType.CORE_SYMPTOM

    def is_modifier(self) -> bool:
        """True if this block modifies a core block (MODIFIER)."""
        return self.type == BlockType.MODIFIER

    def to_dict(self) -> dict[str, Any]:
        """
        Serializes the block to a plain dict suitable for JSON export.
        Preserves layer separation in the output structure.
        """
        return {
            "id":      self.id,
            "cluster": self.cluster,
            "type":    self.type.value,
            "semantic": self.semantic,
            "composition": {
                "allowed_with":   self.composition.allowed_with,
                "forbidden_with": self.composition.forbidden_with,
                "requires":       self.composition.requires,
            },
            "language": {
                "variants":      self.language.variants,
                "language_code": self.language.language_code,
            },
            "quality": {
                "score":     self.quality.score,
                "source":    self.quality.source,
                "validated": self.quality.validated,
            },
        }
