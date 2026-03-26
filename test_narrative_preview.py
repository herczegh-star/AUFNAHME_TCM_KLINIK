"""
test_narrative_preview.py
--------------------------
Verifies that narrative_preview is correctly populated by DraftPipeline
and that draft_text / blocks_used / rule_result are completely unaffected.

Read-only preview layer: no merging, no production changes.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.ai_draft.draft_pipeline import DraftPipeline

pipeline = DraftPipeline()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def check(label: str, condition: bool) -> bool:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}")
    return condition


def section(title: str) -> None:
    print()
    print(f"=== {title} ===")


# ---------------------------------------------------------------------------
# Reference run: capture baseline draft_text + blocks_used for LWS
# ---------------------------------------------------------------------------

_LWS_INPUT = {
    "cluster":              "LWS-Syndrom",
    "side":                 "beidseits",
    "character":            ["ziehend", "stechend"],
    "radiation":            True,
    "aggravating_factor":   "langes Sitzen",
    "relieving_factor":     "Waerme",
    "functional_limitations": ["sitting_tolerance"],
}

_EXPECTED_DRAFT_LWS = (
    "Schmerzen lumbal beidseits, ziehend-stechend, mit Ausstrahlung ins Bein. "
    "Verschlechterung bei längerem Sitzen. "
    "Teilweise Besserung durch Wärme. "
    "Sitztoleranz deutlich reduziert."
)

_EXPECTED_BLOCKS_LWS = 7


# ---------------------------------------------------------------------------
# Test 1: LWS-Syndrom
# ---------------------------------------------------------------------------

def test_lws() -> int:
    section("LWS-Syndrom")
    r = pipeline.run(_LWS_INPUT)
    failures = 0

    if not check("draft_text is non-empty",        bool(r.draft_text)):         failures += 1
    if not check("narrative_preview is non-empty", bool(r.narrative_preview)):  failures += 1
    if not check("draft_text unchanged",           r.draft_text == _EXPECTED_DRAFT_LWS): failures += 1
    if not check("blocks_used count == 7",         len(r.blocks_used) == _EXPECTED_BLOCKS_LWS): failures += 1
    if not check("no rule violations",             r.rule_result.violations == []): failures += 1
    if not check("draft_text != narrative_preview", r.draft_text != r.narrative_preview): failures += 1

    print(f"  [INFO] draft_text       : {r.draft_text!r}")
    print(f"  [INFO] narrative_preview: {r.narrative_preview!r}")
    return failures


# ---------------------------------------------------------------------------
# Test 2: HWS-Syndrom
# ---------------------------------------------------------------------------

_HWS_INPUT = {
    "cluster":              "HWS-Syndrom",
    "side":                 "rechts",
    "character":            ["ziehend"],
    "radiation":            False,
    "aggravating_factor":   "Bildschirmarbeit",
    "relieving_factor":     "Waerme",
    "functional_limitations": [],
}


def test_hws() -> int:
    section("HWS-Syndrom")
    r = pipeline.run(_HWS_INPUT)
    failures = 0

    if not check("draft_text is non-empty",        bool(r.draft_text)):         failures += 1
    if not check("narrative_preview is non-empty", bool(r.narrative_preview)):  failures += 1
    if not check("no rule violations",             r.rule_result.violations == []): failures += 1
    if not check("draft_text != narrative_preview", r.draft_text != r.narrative_preview): failures += 1

    print(f"  [INFO] draft_text       : {r.draft_text!r}")
    print(f"  [INFO] narrative_preview: {r.narrative_preview!r}")
    return failures


# ---------------------------------------------------------------------------
# Test 3: Unregistered cluster (Fibromyalgie)
# ---------------------------------------------------------------------------

_FIBRO_INPUT = {
    "cluster":   "Fibromyalgie",
    "side":      "beidseits",
    "character": ["dumpf"],
}


def test_unregistered() -> int:
    section("Unregistered cluster (Fibromyalgie)")
    r = pipeline.run(_FIBRO_INPUT)
    failures = 0

    # draft_text behaviour depends on whether Fibromyalgie has blocks —
    # we only assert that the field exists (may be empty if no blocks configured)
    if not check("narrative_preview is None", r.narrative_preview is None): failures += 1
    if not check("draft_text is str",         isinstance(r.draft_text, str)): failures += 1

    print(f"  [INFO] draft_text       : {r.draft_text!r}")
    print(f"  [INFO] narrative_preview: {r.narrative_preview!r}")
    return failures


# ---------------------------------------------------------------------------
# Test 4: Explicit read-only isolation
#   Run pipeline twice with identical input.
#   Mutating narrative_preview on result 1 must not affect result 2.
# ---------------------------------------------------------------------------

def test_isolation() -> int:
    section("Read-only isolation")
    r1 = pipeline.run(_LWS_INPUT)
    r2 = pipeline.run(_LWS_INPUT)
    failures = 0

    original_preview = r1.narrative_preview

    # Mutate r1's preview field
    r1.narrative_preview = "MUTATED"

    if not check("r2 narrative_preview unaffected by r1 mutation",
                 r2.narrative_preview == original_preview):
        failures += 1

    if not check("r1 draft_text unaffected by preview mutation",
                 r1.draft_text == _EXPECTED_DRAFT_LWS):
        failures += 1

    return failures


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    total = 0
    total += test_lws()
    total += test_hws()
    total += test_unregistered()
    total += test_isolation()

    print()
    if total == 0:
        print("All tests PASSED.")
    else:
        print(f"{total} test(s) FAILED.")
        sys.exit(1)
