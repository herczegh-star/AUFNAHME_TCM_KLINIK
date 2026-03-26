"""
test_lws_narrative_composer.py
-------------------------------
Tests for the LWS pilot narrative composer.

Verifies:
  - sentence structure for all 4 specified cases
  - clinical narrative order is applied (not alpha order)
  - edge cases: empty input, temporality, extended radiation targets
  - no changes to DraftPipeline output
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.ai_draft.lws_narrative_composer import compose_lws_narrative


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def check(label: str, shared_items: dict, expected: str) -> bool:
    result = compose_lws_narrative(shared_items)
    ok = result == expected
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {label}")
    if not ok:
        print(f"         got     : {result!r}")
        print(f"         expected: {expected!r}")
    return ok


# ---------------------------------------------------------------------------
# Specified test cases
# ---------------------------------------------------------------------------

def test_specified_cases() -> int:
    failures = 0
    print("=== Specified test cases ===")

    ok = check(
        "Case 1 — character + laterality",
        {
            "pain_character": ["ziehend"],
            "pain_laterality": ["links"],
        },
        "Ziehende Schmerzen im LWS-Bereich links.",
    )
    if not ok: failures += 1

    ok = check(
        "Case 2 — two characters + laterality + aggravating + relieving",
        {
            "pain_character":        ["stechend", "ziehend"],
            "pain_laterality":       ["links"],
            "aggravating_mechanical": ["langes_sitzen"],
            "relieving_passive":     ["waerme"],
        },
        "Stechende und ziehende Schmerzen im LWS-Bereich links, "
        "verstärkt bei langem Sitzen, gebessert durch Wärme.",
    )
    if not ok: failures += 1

    ok = check(
        "Case 3 — radiation only (extended target)",
        {
            "pain_radiation": ["linkes_bein_bis_ferse"],
        },
        "Schmerzen im LWS-Bereich mit Ausstrahlung ins linke Bein bis zur Ferse.",
    )
    if not ok: failures += 1

    ok = check(
        "Case 4 — empty input, anchor only",
        {},
        "Schmerzen im LWS-Bereich.",
    )
    if not ok: failures += 1

    return failures


# ---------------------------------------------------------------------------
# Additional edge case tests
# ---------------------------------------------------------------------------

def test_edge_cases() -> int:
    failures = 0
    print()
    print("=== Edge cases ===")

    ok = check(
        "Beidseits no character",
        {"pain_laterality": ["beidseits"]},
        "Schmerzen im LWS-Bereich beidseits.",
    )
    if not ok: failures += 1

    ok = check(
        "Temporality alone",
        {"pain_temporality": ["chronisch"]},
        "Chronische Schmerzen im LWS-Bereich.",
    )
    if not ok: failures += 1

    ok = check(
        "Temporality + character",
        {
            "pain_character":  ["ziehend"],
            "pain_temporality": ["intermittierend"],
        },
        "Intermittierende, ziehende Schmerzen im LWS-Bereich.",
    )
    if not ok: failures += 1

    ok = check(
        "Temporality + character + laterality",
        {
            "pain_character":  ["dumpf"],
            "pain_laterality": ["rechts"],
            "pain_temporality": ["belastungsabhaengig"],
        },
        "Belastungsabhängige, dumpfe Schmerzen im LWS-Bereich rechts.",
    )
    if not ok: failures += 1

    ok = check(
        "Generic radiation (radiation=True, no target) -- suppressed",
        {"pain_radiation": ["radiation"]},
        "Schmerzen im LWS-Bereich.",
    )
    if not ok: failures += 1

    ok = check(
        "Standard radiation target — Gesäß",
        {
            "pain_character":  ["stechend"],
            "pain_laterality": ["rechts"],
            "pain_radiation":  ["Gesäß"],
        },
        "Stechende Schmerzen im LWS-Bereich rechts mit Ausstrahlung ins Gesäß.",
    )
    if not ok: failures += 1

    ok = check(
        "Aggravating only (no character)",
        {
            "aggravating_mechanical": ["buecken"],
        },
        "Schmerzen im LWS-Bereich, verstärkt bei Bücken.",
    )
    if not ok: failures += 1

    ok = check(
        "Full sentence — all supported modules",
        {
            "aggravating_mechanical": ["langes_sitzen"],
            "pain_character":         ["ziehend"],
            "pain_laterality":        ["beidseits"],
            "pain_radiation":         ["Bein"],
            "pain_temporality":       ["chronisch"],
            "relieving_passive":      ["waerme"],
        },
        "Chronische, ziehende Schmerzen im LWS-Bereich beidseits "
        "mit Ausstrahlung ins Bein, verstärkt bei langem Sitzen, gebessert durch Wärme.",
    )
    if not ok: failures += 1

    ok = check(
        "Unknown canonical is silently skipped",
        {
            "pain_character": ["unknown_xyz"],
            "pain_laterality": ["links"],
        },
        "Schmerzen im LWS-Bereich links.",
    )
    if not ok: failures += 1

    return failures


# ---------------------------------------------------------------------------
# Pipeline isolation check
# ---------------------------------------------------------------------------

def test_pipeline_isolation() -> int:
    failures = 0
    print()
    print("=== Pipeline isolation — draft_text unchanged ===")

    from core.ai_draft.draft_pipeline import DraftPipeline
    pipeline = DraftPipeline()

    r = pipeline.run({
        "cluster":              "LWS-Syndrom",
        "side":                 "beidseits",
        "character":            ["ziehend", "stechend"],
        "radiation":            True,
        "aggravating_factor":   "langes Sitzen",
        "relieving_factor":     "Waerme",
        "functional_limitations": ["sitting_tolerance"],
    })

    expected_draft = (
        "Schmerzen lumbal beidseits, ziehend-stechend, mit Ausstrahlung ins Bein. "
        "Verschlechterung bei längerem Sitzen. "
        "Teilweise Besserung durch Wärme. "
        "Sitztoleranz deutlich reduziert."
    )

    ok = r.draft_text == expected_draft
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] draft_text unchanged")
    if not ok:
        print(f"         got     : {r.draft_text!r}")
        print(f"         expected: {expected_draft!r}")
        failures += 1

    ok2 = len(r.blocks_used) == 7
    status2 = "PASS" if ok2 else "FAIL"
    print(f"  [{status2}] blocks_used count == 7 (got {len(r.blocks_used)})")
    if not ok2:
        failures += 1

    ok3 = r.rule_result.violations == []
    status3 = "PASS" if ok3 else "FAIL"
    print(f"  [{status3}] no rule violations")
    if not ok3:
        failures += 1

    # Narrative composer produces its own sentence independently
    narrative = compose_lws_narrative(r.shared_pain_items_selected)
    print(f"  [INFO] narrative from shared_items: {narrative!r}")

    return failures


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    total_failures = 0
    total_failures += test_specified_cases()
    total_failures += test_edge_cases()
    total_failures += test_pipeline_isolation()

    print()
    if total_failures == 0:
        print("All tests PASSED.")
    else:
        print(f"{total_failures} test(s) FAILED.")
        sys.exit(1)
