"""
test_ai_draft.py
----------------
Local smoke test for the AI draft pipeline.

No UI. No export. No API calls.
Run: python test_ai_draft.py
"""

from core.draft_schema import SymptomDraftInput
from core.prompt_builder import PromptBuilder
from services.style_library_service import StyleLibraryService
from services.ai_draft_service import AIDraftService


def main() -> None:
    style_library_service = StyleLibraryService()
    prompt_builder = PromptBuilder()
    ai_draft_service = AIDraftService(style_library_service, prompt_builder)

    draft_input = SymptomDraftInput(
        cluster="LWS-Syndrom",
        duration="5 Jahre",
        localisation="lumbal beidseits",
        side="links betont",
        pain_quality=["ziehend", "teilweise stechend"],
        radiation="links ins Bein",
        aggravating_factors=["langes Sitzen", "Kälte", "Stress"],
        relieving_factors=["Wärme", "manuelle Therapie", "Krankengymnastik"],
        functional_limitations=["Sitztoleranz ca. 30 Minuten"],
        additional_notes=None,
    )

    result = ai_draft_service.generate_draft(draft_input)

    print("=== MAIN TEXT ===")
    print(result.main_text)

    if result.alternative_text:
        print()
        print("=== ALTERNATIVE TEXT ===")
        print(result.alternative_text)

    print()
    print("=== VALIDATION ===")
    print(f"is_valid : {result.validation.is_valid}")
    if result.validation.warnings:
        print("warnings :")
        for w in result.validation.warnings:
            print(f"  - {w}")
    else:
        print("warnings : (none)")

    print()
    print(f"used_cluster : {result.used_cluster}")


if __name__ == "__main__":
    main()
