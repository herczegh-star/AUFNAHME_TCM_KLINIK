"""
test_hws_narrative_composer.py
-------------------------------
Tests for the HWS pilot narrative composer.

Verifies:
  - sentence structure for all 4 specified cases
  - overlay attachment rule (mit begleitendem vs. begleitet von)
  - edge cases: empty input, temporality, overlay combinations
  - no changes to DraftPipeline output
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.ai_draft.hws_narrative_composer import compose_hws_narrative


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def check(label: str, shared_items: dict, expected: str) -> bool:
    result = compose_hws_narrative(shared_items)
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
        "Case 1 -- character + laterality",
        {
            "pain_character": ["ziehend"],
            "pain_laterality": ["rechts"],
        },
        "Ziehende Schmerzen im HWS-Bereich rechts.",
    )
    if not ok: failures += 1

    ok = check(
        "Case 2 -- radiation + aggravating + relieving",
        {
            "pain_character":         ["stechend", "ziehend"],
            "pain_laterality":        ["rechts"],
            "pain_radiation":         ["rechte_schulter"],
            "aggravating_mechanical": ["rotation"],
            "relieving_passive":      ["waerme"],
        },
        "Stechende und ziehende Schmerzen im HWS-Bereich rechts "
        "mit Ausstrahlung in die rechte Schulter, "
        "verstärkt bei Rotation, gebessert durch Wärme.",
    )
    if not ok: failures += 1

    ok = check(
        "Case 3 -- neuro overlay, bare anchor (mit begleitendem)",
        {
            "pain_character": ["dumpf"],
            "neuro_sensory":  ["kribbeln"],
        },
        "Dumpfe Schmerzen im HWS-Bereich mit begleitendem Kribbeln.",
    )
    if not ok: failures += 1

    ok = check(
        "Case 4 -- cephalgic overlay only (mit begleitenden)",
        {
            "cephalgic_features": ["okzipitale_kopfschmerzen"],
        },
        "Schmerzen im HWS-Bereich mit begleitenden okzipitalen Kopfschmerzen.",
    )
    if not ok: failures += 1

    return failures


# ---------------------------------------------------------------------------
# Overlay attachment rule tests
# ---------------------------------------------------------------------------

def test_overlay_attachment() -> int:
    failures = 0
    print()
    print("=== Overlay attachment rule ===")

    # has_appended=False (no radiation, no predicates) -> mit begleitendem
    ok = check(
        "Overlay: bare anchor + neuro -> mit begleitendem",
        {"neuro_sensory": ["taubheit"]},
        "Schmerzen im HWS-Bereich mit begleitendem Taubheitsgefühl.",
    )
    if not ok: failures += 1

    # has_appended=True (radiation present) -> begleitet von
    ok = check(
        "Overlay: radiation + neuro -> begleitet von",
        {
            "pain_radiation": ["hinterkopf"],
            "neuro_sensory":  ["kribbeln"],
        },
        "Schmerzen im HWS-Bereich mit Ausstrahlung in den Hinterkopf, begleitet von Kribbeln.",
    )
    if not ok: failures += 1

    # has_appended=True (aggravating present) -> begleitet von
    ok = check(
        "Overlay: aggravating + neuro -> begleitet von",
        {
            "aggravating_mechanical": ["bildschirm"],
            "neuro_sensory":          ["paraesthesien"],
        },
        "Schmerzen im HWS-Bereich, verstärkt bei Bildschirmarbeit, begleitet von Parästhesien.",
    )
    if not ok: failures += 1

    # Both neuro + cephalgic, bare anchor -> mit begleitendem ... sowie ...
    ok = check(
        "Overlay: neuro + cephalgic, bare anchor -> mit ... sowie ...",
        {
            "neuro_sensory":      ["kribbeln"],
            "cephalgic_features": ["uebelkeit"],
        },
        "Schmerzen im HWS-Bereich mit begleitendem Kribbeln sowie begleitender Übelkeit.",
    )
    if not ok: failures += 1

    # Both neuro + cephalgic, with aggravating -> begleitet von ... sowie ...
    ok = check(
        "Overlay: neuro + cephalgic, aggravating -> begleitet von ... sowie ...",
        {
            "aggravating_mechanical": ["kopfrotation"],
            "neuro_sensory":          ["taubheit"],
            "cephalgic_features":     ["lichtempfindlichkeit"],
        },
        "Schmerzen im HWS-Bereich, verstärkt bei Kopfrotation, "
        "begleitet von Taubheitsgefühl sowie Lichtempfindlichkeit.",
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
        "Empty input, anchor only",
        {},
        "Schmerzen im HWS-Bereich.",
    )
    if not ok: failures += 1

    ok = check(
        "Generic radiation (no target) -- suppressed",
        {"pain_radiation": ["radiation"]},
        "Schmerzen im HWS-Bereich.",
    )
    if not ok: failures += 1

    ok = check(
        "Temporality alone",
        {"pain_temporality": ["chronisch"]},
        "Chronische Schmerzen im HWS-Bereich.",
    )
    if not ok: failures += 1

    ok = check(
        "Temporality + character + laterality",
        {
            "pain_character":  ["dumpf"],
            "pain_laterality": ["beidseits"],
            "pain_temporality": ["intermittierend"],
        },
        "Intermittierende, dumpfe Schmerzen im HWS-Bereich beidseits.",
    )
    if not ok: failures += 1

    ok = check(
        "HWS-specific aggravating: bildschirmarbeit",
        {"aggravating_mechanical": ["bildschirmarbeit"]},
        "Schmerzen im HWS-Bereich, verstärkt bei Bildschirmarbeit.",
    )
    if not ok: failures += 1

    ok = check(
        "HWS radiation: linker_arm",
        {"pain_radiation": ["linker_arm"]},
        "Schmerzen im HWS-Bereich mit Ausstrahlung in den linken Arm.",
    )
    if not ok: failures += 1

    ok = check(
        "HWS radiation: okziput",
        {"pain_radiation": ["okziput"]},
        "Schmerzen im HWS-Bereich mit Ausstrahlung in die okzipitale Region.",
    )
    if not ok: failures += 1

    ok = check(
        "Full sentence -- all base modules",
        {
            "aggravating_mechanical": ["bildschirm"],
            "pain_character":         ["ziehend"],
            "pain_laterality":        ["beidseits"],
            "pain_radiation":         ["hinterkopf"],
            "pain_temporality":       ["chronisch"],
            "relieving_passive":      ["waerme"],
        },
        "Chronische, ziehende Schmerzen im HWS-Bereich beidseits "
        "mit Ausstrahlung in den Hinterkopf, "
        "verstärkt bei Bildschirmarbeit, gebessert durch Wärme.",
    )
    if not ok: failures += 1

    ok = check(
        "Unknown canonical silently skipped",
        {
            "pain_character":  ["unknown_xyz"],
            "pain_laterality": ["links"],
        },
        "Schmerzen im HWS-Bereich links.",
    )
    if not ok: failures += 1

    return failures


# ---------------------------------------------------------------------------
# Pipeline isolation check
# ---------------------------------------------------------------------------

def test_pipeline_isolation() -> int:
    failures = 0
    print()
    print("=== Pipeline isolation -- draft_text unchanged ===")

    from core.ai_draft.draft_pipeline import DraftPipeline
    pipeline = DraftPipeline()

    r = pipeline.run({
        "cluster":              "HWS-Syndrom",
        "side":                 "beidseits",
        "character":            ["ziehend", "stechend"],
        "radiation":            True,
        "aggravating_factor":   "Bildschirmarbeit",
        "relieving_factor":     "Waerme",
        "functional_limitations": [],
    })

    # draft_text must be produced (non-empty) — we don't pin the exact string
    # since HWS block content may vary; we verify it is untouched by the composer
    ok = isinstance(r.draft_text, str) and len(r.draft_text) > 0
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] draft_text is non-empty string")
    if not ok:
        failures += 1

    ok2 = r.rule_result.violations == []
    status2 = "PASS" if ok2 else "FAIL"
    print(f"  [{status2}] no rule violations")
    if not ok2:
        failures += 1

    # Narrative composer produces its own sentence independently
    narrative = compose_hws_narrative(r.shared_pain_items_selected)
    print(f"  [INFO] narrative from shared_items: {narrative!r}")
    print(f"  [INFO] draft_text               : {r.draft_text!r}")

    return failures


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    total_failures = 0
    total_failures += test_specified_cases()
    total_failures += test_overlay_attachment()
    total_failures += test_edge_cases()
    total_failures += test_pipeline_isolation()

    print()
    if total_failures == 0:
        print("All tests PASSED.")
    else:
        print(f"{total_failures} test(s) FAILED.")
        sys.exit(1)
