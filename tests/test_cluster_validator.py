"""
test_cluster_validator.py
--------------------------
Focused tests for services/cluster_validator.py.
No pytest — run from project root: python tests/test_cluster_validator.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.cluster_validator import validate_cluster_dict, ValidationIssue


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _issues_by_code(issues: list[ValidationIssue], code: str) -> list[ValidationIssue]:
    return [i for i in issues if i.code == code]


def _severities(issues: list[ValidationIssue]) -> list[str]:
    return [i.severity for i in issues]


def _minimal_valid() -> dict:
    """Smallest dict that passes all ERROR checks."""
    return {
        "name": "Test-Cluster",
        "form": {
            "fields": [
                {
                    "id": "duration",
                    "label": "Dauer",
                    "type": "text",
                    "required": False,
                    "normalization_map": None,
                    "shared_items_key": None,
                }
            ]
        },
        "normalization": {},
        "render_maps": {},
        "style": {},
    }


# ---------------------------------------------------------------------------
# INV-05: cluster name
# ---------------------------------------------------------------------------

def test_empty_name_is_error():
    d = _minimal_valid()
    d["name"] = ""
    issues = validate_cluster_dict(d)
    assert any(i.code == "empty_cluster_name" and i.severity == "ERROR" for i in issues), issues

def test_whitespace_name_is_error():
    d = _minimal_valid()
    d["name"] = "   "
    issues = validate_cluster_dict(d)
    assert any(i.code == "empty_cluster_name" and i.severity == "ERROR" for i in issues), issues

def test_valid_name_no_error():
    d = _minimal_valid()
    issues = validate_cluster_dict(d)
    assert not _issues_by_code(issues, "empty_cluster_name"), issues


# ---------------------------------------------------------------------------
# INV-01: empty field.id
# ---------------------------------------------------------------------------

def test_empty_field_id_is_error():
    d = _minimal_valid()
    d["form"]["fields"][0]["id"] = ""
    issues = validate_cluster_dict(d)
    assert any(i.code == "empty_field_id" and i.severity == "ERROR" for i in issues), issues

def test_whitespace_field_id_is_error():
    d = _minimal_valid()
    d["form"]["fields"][0]["id"] = "   "
    issues = validate_cluster_dict(d)
    assert any(i.code == "empty_field_id" and i.severity == "ERROR" for i in issues), issues


# ---------------------------------------------------------------------------
# INV-02: duplicate field.id
# ---------------------------------------------------------------------------

def test_duplicate_field_id_is_error():
    d = _minimal_valid()
    d["form"]["fields"].append({
        "id": "duration",
        "label": "Dauer 2",
        "type": "text",
        "required": False,
        "normalization_map": None,
        "shared_items_key": None,
    })
    issues = validate_cluster_dict(d)
    dupes = _issues_by_code(issues, "duplicate_field_id")
    assert len(dupes) == 1, issues
    assert dupes[0].severity == "ERROR"
    assert dupes[0].field_id == "duration"

def test_distinct_field_ids_no_duplicate_error():
    d = _minimal_valid()
    d["form"]["fields"].append({
        "id": "character",
        "label": "Charakter",
        "type": "text",
        "required": False,
        "normalization_map": None,
        "shared_items_key": None,
    })
    issues = validate_cluster_dict(d)
    assert not _issues_by_code(issues, "duplicate_field_id"), issues

def test_trimmed_duplicate_field_id_is_error():
    # " pain_character " and "pain_character" must be detected as duplicates
    d = _minimal_valid()
    d["form"]["fields"] = [
        {
            "id": "pain_character",
            "label": "Charakter",
            "type": "text",
            "required": False,
            "normalization_map": None,
            "shared_items_key": None,
        },
        {
            "id": " pain_character ",
            "label": "Charakter 2",
            "type": "text",
            "required": False,
            "normalization_map": None,
            "shared_items_key": None,
        },
    ]
    issues = validate_cluster_dict(d)
    dupes = _issues_by_code(issues, "duplicate_field_id")
    assert len(dupes) == 1, issues
    assert dupes[0].severity == "ERROR"
    assert dupes[0].field_id == "pain_character"


# ---------------------------------------------------------------------------
# INV-03: select / multi_select without options
# ---------------------------------------------------------------------------

def test_select_without_options_is_error():
    d = _minimal_valid()
    d["form"]["fields"].append({
        "id": "character",
        "label": "Charakter",
        "type": "select",
        "options": [],
        "required": False,
        "normalization_map": None,
        "shared_items_key": None,
    })
    issues = validate_cluster_dict(d)
    errs = _issues_by_code(issues, "select_without_options")
    assert len(errs) == 1 and errs[0].severity == "ERROR", issues

def test_multi_select_without_options_is_error():
    d = _minimal_valid()
    d["form"]["fields"].append({
        "id": "character",
        "label": "Charakter",
        "type": "multi_select",
        "required": False,
        "normalization_map": None,
        "shared_items_key": None,
    })
    issues = validate_cluster_dict(d)
    errs = _issues_by_code(issues, "select_without_options")
    assert len(errs) == 1 and errs[0].severity == "ERROR", issues

def test_select_with_options_no_error():
    d = _minimal_valid()
    d["form"]["fields"].append({
        "id": "character",
        "label": "Charakter",
        "type": "select",
        "options": ["ziehend", "stechend"],
        "required": False,
        "normalization_map": None,
        "shared_items_key": None,
    })
    issues = validate_cluster_dict(d)
    assert not _issues_by_code(issues, "select_without_options"), issues

def test_text_field_without_options_no_error():
    # text fields are not required to have options
    d = _minimal_valid()
    issues = validate_cluster_dict(d)
    assert not _issues_by_code(issues, "select_without_options"), issues


# ---------------------------------------------------------------------------
# INV-04: dangling normalization_map reference
# ---------------------------------------------------------------------------

def test_missing_normalization_section_is_warning():
    d = _minimal_valid()
    d["form"]["fields"][0]["normalization_map"] = "nonexistent_section"
    issues = validate_cluster_dict(d)
    warns = _issues_by_code(issues, "missing_normalization_section")
    assert len(warns) == 1 and warns[0].severity == "WARNING", issues
    assert warns[0].field_id == "duration"

def test_existing_normalization_section_no_warning():
    d = _minimal_valid()
    d["form"]["fields"][0]["normalization_map"] = "character"
    d["normalization"] = {"character": {"ziehend": "ziehend"}}
    issues = validate_cluster_dict(d)
    assert not _issues_by_code(issues, "missing_normalization_section"), issues

def test_null_normalization_map_no_warning():
    d = _minimal_valid()
    d["form"]["fields"][0]["normalization_map"] = None
    issues = validate_cluster_dict(d)
    assert not _issues_by_code(issues, "missing_normalization_section"), issues


# ---------------------------------------------------------------------------
# INV-08: empty label
# ---------------------------------------------------------------------------

def test_empty_label_is_warning():
    d = _minimal_valid()
    d["form"]["fields"][0]["label"] = ""
    issues = validate_cluster_dict(d)
    warns = _issues_by_code(issues, "empty_field_label")
    assert len(warns) == 1 and warns[0].severity == "WARNING", issues

def test_nonempty_label_no_warning():
    d = _minimal_valid()
    issues = validate_cluster_dict(d)
    assert not _issues_by_code(issues, "empty_field_label"), issues


# ---------------------------------------------------------------------------
# INV-06: orphaned normalization sections
# ---------------------------------------------------------------------------

def test_orphan_normalization_section_is_info():
    d = _minimal_valid()
    d["normalization"] = {"side": {"links": "links", "rechts": "rechts"}}
    # no field references "side"
    issues = validate_cluster_dict(d)
    infos = _issues_by_code(issues, "orphan_normalization_section")
    assert len(infos) == 1 and infos[0].severity == "INFO", issues

def test_referenced_normalization_section_not_orphaned():
    d = _minimal_valid()
    d["form"]["fields"][0]["normalization_map"] = "character"
    d["normalization"] = {"character": {"ziehend": "ziehend"}}
    issues = validate_cluster_dict(d)
    assert not _issues_by_code(issues, "orphan_normalization_section"), issues

def test_empty_normalization_no_orphan_info():
    d = _minimal_valid()
    d["normalization"] = {}
    issues = validate_cluster_dict(d)
    assert not _issues_by_code(issues, "orphan_normalization_section"), issues


# ---------------------------------------------------------------------------
# Multiple simultaneous errors
# ---------------------------------------------------------------------------

def test_multiple_errors_all_reported():
    # empty name + blank field id + select without options — all three must appear
    d = {
        "name": "",
        "form": {
            "fields": [
                {
                    "id": "",
                    "label": "Kein Name",
                    "type": "text",
                    "required": False,
                    "normalization_map": None,
                    "shared_items_key": None,
                },
                {
                    "id": "character",
                    "label": "Charakter",
                    "type": "select",
                    "options": [],
                    "required": False,
                    "normalization_map": None,
                    "shared_items_key": None,
                },
            ]
        },
        "normalization": {},
        "render_maps": {},
        "style": {},
    }
    issues = validate_cluster_dict(d)
    codes = {i.code for i in issues}
    assert "empty_cluster_name" in codes, issues
    assert "empty_field_id"     in codes, issues
    assert "select_without_options" in codes, issues
    errors = [i for i in issues if i.severity == "ERROR"]
    assert len(errors) >= 3, issues


# ---------------------------------------------------------------------------
# Clean dict produces no issues
# ---------------------------------------------------------------------------

def test_minimal_valid_dict_is_clean():
    d = _minimal_valid()
    issues = validate_cluster_dict(d)
    assert issues == [], issues

def test_no_fields_is_clean():
    d = _minimal_valid()
    d["form"]["fields"] = []
    issues = validate_cluster_dict(d)
    assert issues == [], issues


# ---------------------------------------------------------------------------
# Robustness: malformed input should not raise
# ---------------------------------------------------------------------------

def test_missing_form_section_no_crash():
    d = {"name": "X"}
    issues = validate_cluster_dict(d)
    assert isinstance(issues, list)

def test_missing_name_key_no_crash():
    d = {"form": {"fields": []}}
    issues = validate_cluster_dict(d)
    assert any(i.code == "empty_cluster_name" for i in issues)

def test_none_normalization_no_crash():
    d = _minimal_valid()
    d["normalization"] = None
    issues = validate_cluster_dict(d)
    assert isinstance(issues, list)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main() -> None:
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed}/{passed + failed} Tests bestanden.")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
