"""
cluster_validator.py
--------------------
Save-time validation for cluster schema dicts.

Works purely on the assembled dict produced by ScreenClusterBuilder._on_save
before it is passed to save_edited().  Does not import Flet, UnifiedCluster,
or narrative_dispatcher.  Does not mutate the input dict.

Validation invariants implemented:

  ERROR (blocks save)
    INV-01  No empty field.id
    INV-02  No duplicate field.id
    INV-03  select / multi_select fields must have ≥1 option
    INV-05  cluster.name must not be empty

  WARNING (allows save)
    INV-04  field.normalization_map must reference an existing normalization section
    INV-08  field.label should not be empty

  INFO (allows save)
    INV-06  normalization sections not referenced by any field are orphaned
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------

@dataclass
class ValidationIssue:
    severity: str        # "ERROR" | "WARNING" | "INFO"
    code: str            # machine-readable identifier, e.g. "duplicate_field_id"
    message: str         # human-readable German message for the UI
    field_id: str | None = field(default=None)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_cluster_dict(d: dict) -> list[ValidationIssue]:
    """
    Validate an assembled cluster dict.  Returns a list of ValidationIssue
    objects.  An empty list means the dict is clean.

    Caller responsibilities:
    - Pass the fully assembled dict, not the on-disk version.
    - Check severity of returned issues; ERROR means save must be aborted.
    - Does not raise; malformed/missing sections produce issues, not exceptions.
    """
    issues: list[ValidationIssue] = []
    _check_name(d, issues)
    _check_fields(d, issues)
    _check_normalization_orphans(d, issues)
    return issues


# ---------------------------------------------------------------------------
# Internal checks
# ---------------------------------------------------------------------------

def _check_name(d: dict, issues: list[ValidationIssue]) -> None:
    """INV-05: cluster.name must not be blank."""
    name = str(d.get("name", "") or "").strip()
    if not name:
        issues.append(ValidationIssue(
            severity="ERROR",
            code="empty_cluster_name",
            message="Cluster-Name darf nicht leer sein.",
        ))


def _check_fields(d: dict, issues: list[ValidationIssue]) -> None:
    """INV-01, INV-02, INV-03, INV-04, INV-08."""
    fields: list[dict] = []
    try:
        fields = list(d.get("form", {}).get("fields", []))
    except (AttributeError, TypeError):
        return  # malformed form section — not our concern here

    normalization: dict = {}
    try:
        normalization = dict(d.get("normalization", {}) or {})
    except (AttributeError, TypeError):
        pass

    seen_ids: set[str] = set()

    for f in fields:
        if not isinstance(f, dict):
            continue

        raw_id = str(f.get("id", "") or "").strip()

        # INV-01: empty id
        if not raw_id:
            issues.append(ValidationIssue(
                severity="ERROR",
                code="empty_field_id",
                message="Ein Formularfeld hat keine ID. Alle Felder benötigen eine eindeutige ID.",
            ))
            continue  # remaining checks require a non-empty id

        # INV-02: duplicate id
        if raw_id in seen_ids:
            issues.append(ValidationIssue(
                severity="ERROR",
                code="duplicate_field_id",
                message=f"Feld-ID mehrfach verwendet: '{raw_id}'",
                field_id=raw_id,
            ))
        seen_ids.add(raw_id)

        ftype = str(f.get("type", "") or "").strip()

        # INV-03: select / multi_select without options
        if ftype in ("select", "multi_select"):
            options = f.get("options")
            if not options or not isinstance(options, list) or len(options) == 0:
                issues.append(ValidationIssue(
                    severity="ERROR",
                    code="select_without_options",
                    message=f"Feld '{raw_id}' ist vom Typ '{ftype}', hat aber keine Optionen.",
                    field_id=raw_id,
                ))

        # INV-04: dangling normalization_map reference
        norm_map = str(f.get("normalization_map") or "").strip()
        if norm_map and norm_map not in normalization:
            issues.append(ValidationIssue(
                severity="WARNING",
                code="missing_normalization_section",
                message=(
                    f"Feld '{raw_id}' verweist auf normalization_map '{norm_map}', "
                    f"die in 'normalization' nicht existiert."
                ),
                field_id=raw_id,
            ))

        # INV-08: empty label
        label = str(f.get("label", "") or "").strip()
        if not label:
            issues.append(ValidationIssue(
                severity="WARNING",
                code="empty_field_label",
                message=f"Feld '{raw_id}' hat kein Label.",
                field_id=raw_id,
            ))


def _check_normalization_orphans(d: dict, issues: list[ValidationIssue]) -> None:
    """INV-06: normalization sections not referenced by any field."""
    normalization: dict = {}
    try:
        normalization = dict(d.get("normalization", {}) or {})
    except (AttributeError, TypeError):
        return

    if not normalization:
        return

    referenced: set[str] = set()
    try:
        for f in d.get("form", {}).get("fields", []):
            if not isinstance(f, dict):
                continue
            nm = str(f.get("normalization_map") or "").strip()
            if nm:
                referenced.add(nm)
    except (AttributeError, TypeError):
        pass

    for section_key in normalization:
        if section_key not in referenced:
            issues.append(ValidationIssue(
                severity="INFO",
                code="orphan_normalization_section",
                message=(
                    f"Normalization-Sektion '{section_key}' wird von keinem Feld "
                    f"referenziert (normalization_map)."
                ),
            ))
