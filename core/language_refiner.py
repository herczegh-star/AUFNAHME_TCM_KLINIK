"""
language_refiner.py
-------------------
Final language refinement layer for clinical German texts.

Pipeline position:
    form → template_selection → symptom_composer → language_refiner → preview/copy

SAFETY PRINCIPLE:
    This module only corrects grammar, morphology, syntax, punctuation and
    style. It never adds, removes or changes medical content.

Architecture:
    - ClinicalLanguageRefiner     public API
    - LLMRefinerClientProtocol    abstract interface (swap backends freely)
    - AnthropicRefinerClient      concrete Claude backend
    - SemanticValidator           lightweight content-preservation checks
    - fallback_rule_based_cleanup minimal local cleanup if LLM unavailable
"""

from __future__ import annotations

import os
import re
from typing import Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """Du bist ein sprachlicher Korrektor für klinische Dokumentation.
Deine Aufgabe ist ausschließlich die sprachliche Glättung eines bereits inhaltlich \
festgelegten medizinischen Textes.

WICHTIG – STRIKTE REGELN:
- Du darfst KEINE neuen medizinischen Inhalte hinzufügen.
- Du darfst KEINE Informationen weglassen.
- Du darfst KEINE Bedeutung verändern.
- Du darfst KEINE Diagnosen ergänzen.
- Du darfst KEINE Symptome interpretieren oder ergänzen.
- Du darfst Lateralität (links/rechts/beidseits) NICHT verändern.
- Du darfst Dauer, Verlauf, Ausstrahlung, Lokalisation NICHT verändern.
- Du darfst Verneinungen (kein, keine, ohne) NICHT verändern.

Du darfst AUSSCHLIESSLICH:
- Grammatik, Morphologie, Kasus, Präpositionen, Wortstellung korrigieren.
- Satzfluss und Lesbarkeit verbessern.
- Zeichensetzung normalisieren.
- Stilistisch ungünstige Formulierungen in kompaktes klinisches Deutsch überführen.
- Rein sprachliche Redundanz entfernen wenn der Inhalt erhalten bleibt.

Ausgabe:
Gib ausschließlich den finalen überarbeiteten Text zurück.
Keine Kommentare. Keine Erklärungen. Kein Präambel."""

_USER_TEMPLATE = "Bitte sprachlich glätten:\n\n{text}"


# ---------------------------------------------------------------------------
# LLM client protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class LLMRefinerClientProtocol(Protocol):
    def refine(self, raw_text: str) -> str:
        """Send raw_text to LLM, return refined text."""
        ...


# ---------------------------------------------------------------------------
# Anthropic backend
# ---------------------------------------------------------------------------

class AnthropicRefinerClient:
    """
    Calls Claude via the Anthropic SDK.
    Requires ANTHROPIC_API_KEY environment variable.
    """

    MODEL = "claude-haiku-4-5-20251001"  # fast and cost-effective for short texts
    MAX_TOKENS = 1024

    def __init__(self) -> None:
        import anthropic
        self._client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )

    def refine(self, raw_text: str) -> str:
        message = self._client.messages.create(
            model=self.MODEL,
            max_tokens=self.MAX_TOKENS,
            system=_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": _USER_TEMPLATE.format(text=raw_text)}
            ],
        )
        return message.content[0].text.strip()


# ---------------------------------------------------------------------------
# Semantic validator
# ---------------------------------------------------------------------------

_LATERALITY   = re.compile(r"\b(links|rechts|linksbetont|rechtsbetont|beidseits|beiderseitig|einseitig)\b", re.I)
_NUMBERS      = re.compile(r"\b\d+\b")
_NEGATIONS    = re.compile(r"\b(kein|keine|keiner|keinem|keinen|ohne|nicht)\b", re.I)
_REGIONS      = re.compile(r"\b(LWS|HWS|Knie|Schulter|Hüfte|Nacken|Rücken|Wirbelsäule|Bein|Arm|Fuß|Zehen)\b", re.I)
_PROGRESSION  = re.compile(r"\b(progredient|zunehmend|intermittierend|fluktuierend|schubweise|verschlechtert)\b", re.I)


def _extract_guard_tokens(text: str) -> dict[str, list[str]]:
    return {
        "laterality":  _LATERALITY.findall(text.lower()),
        "numbers":     _NUMBERS.findall(text),
        "negations":   _NEGATIONS.findall(text.lower()),
        "regions":     [r.lower() for r in _REGIONS.findall(text)],
        "progression": _PROGRESSION.findall(text.lower()),
    }


def _tokens_preserved(before: dict, after: dict) -> tuple[bool, list[str]]:
    """Returns (ok, list_of_violations)."""
    violations = []
    for category, tokens_before in before.items():
        tokens_after = after[category]
        # Check that every token from before appears at least as often in after
        for token in set(tokens_before):
            if tokens_before.count(token) > tokens_after.count(token):
                violations.append(f"{category}: '{token}' lost")
    return len(violations) == 0, violations


# ---------------------------------------------------------------------------
# Rule-based fallback
# ---------------------------------------------------------------------------

def fallback_rule_based_cleanup(text: str) -> str:
    """
    Minimal local cleanup when LLM is unavailable or validation fails.
    Only fixes punctuation and whitespace.
    """
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\.\.+", ".", text)
    text = re.sub(r",([^\s])", r", \1", text)
    text = re.sub(r"\s+\.", ".", text)
    text = text.strip()
    if text and not text.endswith("."):
        text += "."
    return text


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------

class ClinicalLanguageRefiner:
    """
    Refines clinical German text with semantic-preservation guardrails.

    Usage:
        refiner = ClinicalLanguageRefiner()
        result  = refiner.refine(raw_text)

    Falls back to rule-based cleanup if:
    - no LLM client is configured
    - LLM call fails
    - semantic validation detects content change
    """

    def __init__(self, llm_client: LLMRefinerClientProtocol | None = None) -> None:
        self._llm = llm_client

    def refine(self, raw_text: str) -> str:
        """
        Main entry point.

        Args:
            raw_text: Content-complete clinical German draft.

        Returns:
            Language-refined text with identical semantic content.
        """
        if not raw_text.strip():
            return raw_text

        if self._llm is None:
            return fallback_rule_based_cleanup(raw_text)

        guard_before = _extract_guard_tokens(raw_text)

        try:
            refined = self._llm.refine(raw_text)
        except Exception as exc:
            print(f"[language_refiner] LLM call failed: {exc}. Using fallback.")
            return fallback_rule_based_cleanup(raw_text)

        guard_after = _extract_guard_tokens(refined)
        ok, violations = _tokens_preserved(guard_before, guard_after)

        if not ok:
            print(f"[language_refiner] Validation failed: {violations}. Using fallback.")
            return fallback_rule_based_cleanup(raw_text)

        return refined


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def refine_clinical_german(
    raw_text: str,
    llm_client: LLMRefinerClientProtocol | None = None,
) -> str:
    """
    Convenience wrapper around ClinicalLanguageRefiner.

    Args:
        raw_text:   Clinical German draft from symptom_composer.
        llm_client: Optional LLM backend. If None, uses rule-based fallback.

    Returns:
        Refined clinical text.
    """
    return ClinicalLanguageRefiner(llm_client=llm_client).refine(raw_text)


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------
#
# # With Anthropic backend (requires ANTHROPIC_API_KEY env variable):
# from core.language_refiner import refine_clinical_german, AnthropicRefinerClient
#
# raw = (
#     "Der Patient berichtet seit vielen Jahren über chronische Schmerzen im LWS-Bereich. "
#     "Im Verlauf habe sich die Symptomatik progredient. "
#     "Die Beschwerden werden überwiegend als ziehend, stechend beschrieben. "
#     "Teilweise besteht eine Ausstrahlung in Bein beideseits, linksbetont. "
#     "Eine Verschlechterung tritt insbesondere längere Stehen, Gehne auf. "
#     "Linderung erfolgt durch Wärme, Masage. "
#     "Begleitend besteht Kribbeln in den Zehen."
# )
#
# client = AnthropicRefinerClient()
# result = refine_clinical_german(raw, llm_client=client)
# print(result)
#
# # Without LLM (rule-based fallback only):
# result = refine_clinical_german(raw)
# print(result)
