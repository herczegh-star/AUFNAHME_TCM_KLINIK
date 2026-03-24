"""
ai_draft_service.py
-------------------
Orchestrates the AI draft mode pipeline.

Composes prompts, calls the LLM (placeholder), splits output,
and validates the resulting clinical text.

No UI. No export. No side effects beyond the LLM call.
"""

from __future__ import annotations

import re

from core.draft_schema import (
    ClusterStyleConfig,
    DraftResult,
    DraftValidationResult,
    SymptomDraftInput,
)
from core.prompt_builder import PromptBuilder
from services.style_library_service import StyleLibraryService


_FORBIDDEN_WORDS = [
    "wahrscheinlich",
    "vermutlich",
    "empfohlen",
    "sollte",
]

_SENTENCE_PATTERN = re.compile(r"[.!?]")


class AIDraftService:

    def __init__(
        self,
        style_library_service: StyleLibraryService,
        prompt_builder: PromptBuilder,
    ) -> None:
        self._style_library = style_library_service
        self._prompt_builder = prompt_builder

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_draft(self, draft_input: SymptomDraftInput) -> DraftResult:
        style_config: ClusterStyleConfig = self._style_library.get_cluster_config(
            draft_input.cluster
        )

        system_prompt: str = self._prompt_builder.build_system_prompt()
        user_prompt: str = self._prompt_builder.build_user_prompt(
            draft_input, style_config
        )

        raw_output: str = self._call_llm(system_prompt, user_prompt)

        main_text, alternative_text = self._split_output(raw_output)

        validation: DraftValidationResult = self.validate_draft(
            main_text, draft_input, style_config
        )

        return DraftResult(
            main_text=main_text,
            alternative_text=alternative_text,
            validation=validation,
            used_cluster=draft_input.cluster,
        )

    def validate_draft(
        self,
        text: str,
        draft_input: SymptomDraftInput,
        style_config: ClusterStyleConfig,
    ) -> DraftValidationResult:
        warnings: list[str] = []

        text_lower = text.lower()

        # --- Forbidden words ---
        for word in _FORBIDDEN_WORDS:
            if word in text_lower:
                warnings.append(
                    f"Unzulässiges Wort gefunden: '{word}' – "
                    "kein diagnostisches Urteil, keine Empfehlung."
                )

        # --- Sentence count ---
        sentence_count = self._count_sentences(text)
        if sentence_count < 3:
            warnings.append(
                f"Text zu kurz: {sentence_count} Satz/Sätze gefunden (Ziel: 3–4)."
            )
        elif sentence_count > 4:
            warnings.append(
                f"Text zu lang: {sentence_count} Sätze gefunden (Ziel: 3–4)."
            )

        # --- Coverage checks ---
        if draft_input.functional_limitations:
            tokens = self._significant_tokens(
                " ".join(draft_input.functional_limitations)
            )
            if tokens and not any(t in text_lower for t in tokens):
                warnings.append(
                    "Funktionelle Einschränkungen sind angegeben, "
                    "aber im Entwurf möglicherweise nicht enthalten."
                )

        if draft_input.additional_notes:
            tokens = self._significant_tokens(draft_input.additional_notes)
            if tokens and not any(t in text_lower for t in tokens):
                warnings.append(
                    "Zusatzhinweise sind angegeben, "
                    "aber im Entwurf möglicherweise nicht enthalten."
                )

        if draft_input.radiation:
            tokens = self._significant_tokens(draft_input.radiation)
            if tokens and not any(t in text_lower for t in tokens):
                warnings.append(
                    "Ausstrahlung ist angegeben, aber im Entwurf "
                    "möglicherweise zu stark vereinfacht oder nicht enthalten."
                )

        return DraftValidationResult(
            is_valid=len(warnings) == 0,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _significant_tokens(self, value: str) -> list[str]:
        """Return lowercase tokens from value that are long enough to be meaningful."""
        return [
            t.lower() for t in re.split(r"[\s,/\-]+", value)
            if len(t) >= 4
        ]

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        # Placeholder – no API call.
        # Replace with real LLM integration in a later step.
        return (
            "Der Patient berichtet seit mehreren Jahren über persistierende "
            "Beschwerden im Bereich der LWS. "
            "Die Schmerzen werden als ziehend und teilweise stechend beschrieben, "
            "mit gelegentlicher Ausstrahlung ins linke Bein. "
            "Eine Verstärkung tritt insbesondere bei längerem Sitzen, Kälte und "
            "unter Stress auf. "
            "Linderung erfolgt durch Wärme, manuelle Therapie und Krankengymnastik."
        )

    def _split_output(self, raw_output: str) -> tuple[str, str | None]:
        return raw_output.strip(), None

    def _count_sentences(self, text: str) -> int:
        return len(_SENTENCE_PATTERN.findall(text))
