"""
test_ai_draft_pipeline.py
-------------------------
Smoke test for the deterministic AI-Draft end-to-end pipeline.

Pipeline: BlockLoader → BlockSelector → RuleEngine → DraftComposer

No AI. No pytest. Pure deterministic flow.
Run: python test_ai_draft_pipeline.py
"""

from core.ai_draft.draft_pipeline import DraftPipeline


def main() -> None:
    pipeline = DraftPipeline()

    input_data = {
        "cluster":               "LWS-Syndrom",
        "side":                  "beidseits",
        "character":             ["ziehend", "stechend"],
        "radiation":             True,
        "aggravating_factor":    "langes Sitzen",
        "relieving_factor":      "Wärme",
        "functional_limitations": ["sitting_tolerance"],
    }

    result = pipeline.run(input_data)

    print("=== DRAFT TEXT ===")
    print(result.draft_text if result.draft_text else "(kein Text – Pipeline fehlgeschlagen)")

    print()
    print("=== IS VALID ===")
    print(result.is_valid)

    print()
    print("=== BLOCKS USED ===")
    if result.blocks_used:
        for block in result.blocks_used:
            print(f"  [{block.type.value}]  {block.id}")
    else:
        print("  (keine Blöcke)")

    print()
    print("=== VIOLATIONS ===")
    if result.rule_result.violations:
        for v in result.rule_result.violations:
            print(f"  ! {v}")
    else:
        print("  (keine Violations)")


if __name__ == "__main__":
    main()
