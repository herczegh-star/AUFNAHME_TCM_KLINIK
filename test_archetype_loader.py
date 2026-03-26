"""
test_archetype_loader.py
------------------------
Verifies that the archetype library loads correctly and the loader API works.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.ai_draft.archetype_loader import (
    get_archetype_text,
    get_archetypes_for_cluster,
    load_archetype_library,
)


def check(label: str, result, expected) -> bool:
    if result == expected:
        print(f"  OK  {label}")
        return True
    else:
        print(f"  FAIL {label}")
        print(f"       expected: {expected!r}")
        print(f"       got:      {result!r}")
        return False


def check_nonempty_str(label: str, result) -> bool:
    ok = isinstance(result, str) and len(result) > 0
    if ok:
        print(f"  OK  {label}")
    else:
        print(f"  FAIL {label} -- not a non-empty string, got: {result!r}")
    return ok


def main() -> None:
    passed = 0
    total = 0

    def run(label, result, expected=None, nonempty_str=False):
        nonlocal passed, total
        total += 1
        if nonempty_str:
            ok = check_nonempty_str(label, result)
        else:
            ok = check(label, result, expected)
        if ok:
            passed += 1

    print("=== test_archetype_loader ===")
    print()

    # 1. Library loads
    lib = load_archetype_library()
    run("library loads (non-empty dict)", isinstance(lib, dict) and len(lib) > 0, True)

    # 2. LWS-Syndrom cluster exists
    lws = get_archetypes_for_cluster("LWS-Syndrom")
    run("LWS-Syndrom cluster exists (not None)", lws is not None, True)

    # 3. LWS1 pattern exists
    lws1 = get_archetype_text("LWS-Syndrom", "LWS1")
    run("LWS1 text is non-empty string", lws1, nonempty_str=True)

    # 4. LWS2 pattern exists
    lws2 = get_archetype_text("LWS-Syndrom", "LWS2")
    run("LWS2 text is non-empty string", lws2, nonempty_str=True)

    # 5. LWS1 text contains expected German content
    run(
        "LWS1 text mentions LWS-Bereich",
        lws1 is not None and "LWS-Bereich" in lws1,
        True,
    )
    run(
        "LWS2 text mentions Ausstrahlung",
        lws2 is not None and "Ausstrahlung" in lws2,
        True,
    )

    # 6. Unknown cluster returns None
    run("unknown cluster returns None", get_archetypes_for_cluster("HWS-Syndrom"), None)

    # 7. Unknown pattern returns None
    run("unknown pattern returns None", get_archetype_text("LWS-Syndrom", "LWS99"), None)

    # 8. Unknown cluster + pattern returns None
    run(
        "unknown cluster+pattern returns None",
        get_archetype_text("UnknownCluster", "P1"),
        None,
    )

    # 9. ICD code accessible
    if lws is not None:
        run("LWS-Syndrom icd_code is M54.86", lws.get("icd_code"), "M54.86")
    else:
        total += 1
        print("  FAIL icd_code check (cluster not loaded)")

    # 10. Type metadata accessible
    patterns = (lws or {}).get("patterns", {})
    run("LWS1 type is 'mechanical'", patterns.get("LWS1", {}).get("type"), "mechanical")
    run("LWS2 type is 'radicular'", patterns.get("LWS2", {}).get("type"), "radicular")

    print()
    print(f"Results: {passed}/{total} passed")

    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
