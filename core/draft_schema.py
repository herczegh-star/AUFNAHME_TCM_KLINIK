"""
draft_schema.py
---------------
Dataclasses for the AI draft mode pipeline.

Defines input, configuration, validation and output structures.
No business logic. No side effects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SymptomDraftInput:
    cluster: str
    duration: Optional[str] = None
    localisation: Optional[str] = None
    side: Optional[str] = None
    pain_quality: list[str] = field(default_factory=list)
    radiation: Optional[str] = None
    aggravating_factors: list[str] = field(default_factory=list)
    relieving_factors: list[str] = field(default_factory=list)
    functional_limitations: list[str] = field(default_factory=list)
    additional_notes: Optional[str] = None


@dataclass
class ClusterStyleConfig:
    cluster_name: str
    meta: dict = field(default_factory=dict)
    rules: list[str] = field(default_factory=list)
    preferred_patterns: list[str] = field(default_factory=list)
    preferred_phrases: dict = field(default_factory=dict)
    examples: list[str] = field(default_factory=list)


@dataclass
class DraftValidationResult:
    is_valid: bool
    warnings: list[str] = field(default_factory=list)


@dataclass
class DraftResult:
    main_text: str
    alternative_text: Optional[str] = None
    validation: DraftValidationResult = field(
        default_factory=lambda: DraftValidationResult(is_valid=True)
    )
    used_cluster: Optional[str] = None
