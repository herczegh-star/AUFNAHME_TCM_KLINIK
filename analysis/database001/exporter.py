"""
exporter.py
-----------
Writes database001 output files.

All files UTF-8, no BOM.
Field names English, no diacritics in filenames.
German text content preserved as-is.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from analysis.database001.models import DocumentResult, ExtractionRecord


# ---------------------------------------------------------------------------
# JSONL
# ---------------------------------------------------------------------------

def write_jsonl(records: list[ExtractionRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as fh:
        for rec in records:
            line = {
                "source_case_id":   rec.source_case_id,
                "diagnosis_label":  rec.diagnosis_label,
                "icd_code":         rec.icd_code,
                "text_block":       rec.text_block,
                "text_source_type": rec.text_source_type,
                "source_filename":  rec.source_filename,
                "extraction_status": rec.extraction_status,
            }
            fh.write(json.dumps(line, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

_CSV_FIELDS = [
    "source_case_id",
    "diagnosis_label",
    "icd_code",
    "text_source_type",
    "extraction_status",
    "source_filename",
    "text_block",
]


def write_csv(records: list[ExtractionRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_CSV_FIELDS, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for rec in records:
            writer.writerow({
                "source_case_id":    rec.source_case_id,
                "diagnosis_label":   rec.diagnosis_label,
                "icd_code":          rec.icd_code,
                "text_source_type":  rec.text_source_type,
                "extraction_status": rec.extraction_status,
                "source_filename":   rec.source_filename,
                "text_block":        rec.text_block,
            })


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def write_report(
    results: list[DocumentResult],
    records: list[ExtractionRecord],
    output_path: Path,
) -> None:
    import re as _re
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Tally statuses
    total = len(results)
    ok_docs = sum(1 for r in results if r.status == "ok")
    missing_diag = sum(1 for r in results if r.status == "missing_diagnosis_section")
    missing_text = sum(1 for r in results if r.status == "missing_text_section")
    needs_review = sum(1 for r in results if r.status == "needs_review")
    total_records = len(records)

    # Source type breakdown
    type_a = sum(1 for r in records if r.text_source_type == "derzeitige_beschwerden")
    type_b = sum(1 for r in records if r.text_source_type == "spezielle_eigenanamnese")

    # ICD coverage
    with_icd = sum(1 for r in records if r.icd_code)
    without_icd = total_records - with_icd

    # M54.86 count
    m5486_count = sum(1 for r in records if r.icd_code == "M54.86")

    # Header type breakdown across ok docs
    header_somatische = sum(
        1 for r in results
        if r.status == "ok" and _re.match(r'Somatische', r.diag_header_used, _re.IGNORECASE)
    )
    header_diagnosen = sum(
        1 for r in results
        if r.status == "ok" and _re.match(r'Diagnosen', r.diag_header_used, _re.IGNORECASE)
    )
    header_diagnose = sum(
        1 for r in results
        if r.status == "ok" and _re.fullmatch(r'Diagnose:?', r.diag_header_used, _re.IGNORECASE)
    )

    # 5 sample records
    samples = records[:5]

    lines: list[str] = [
        "# database001 Extraction Report",
        "",
        "## Summary",
        "",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Total documents processed | {total} |",
        f"| Documents successfully parsed | {ok_docs} |",
        f"| Missing diagnosis section | {missing_diag} |",
        f"| Missing text section | {missing_text} |",
        f"| Needs review | {needs_review} |",
        f"| **Total records created** | **{total_records}** |",
        "",
        "## Record Details",
        "",
        f"| Detail | Count |",
        f"|--------|-------|",
        f"| Type A (derzeitige_beschwerden) records | {type_a} |",
        f"| Type B (spezielle_eigenanamnese) records | {type_b} |",
        f"| Records with ICD code | {with_icd} |",
        f"| Records without ICD code | {without_icd} |",
        f"| Records with ICD M54.86 | {m5486_count} |",
        "",
        "## Diagnosis Header Breakdown (successfully parsed docs)",
        "",
        f"| Header used | Documents |",
        f"|-------------|-----------|",
        f"| Somatische Diagnosen / Diagnose | {header_somatische} |",
        f"| Diagnosen | {header_diagnosen} |",
        f"| Diagnose (singular) | {header_diagnose} |",
        "",
        "## Output Files",
        "",
        "- `outputs/database001_records.jsonl`",
        "- `outputs/database001_records.csv`",
        "- `outputs/database001_extraction_report.md`",
        "",
        "## Extraction Rules Applied",
        "",
        "- Diagnosis section: `Somatische Diagnosen`, `Diagnosen`, `Diagnose` (with/without colon)",
        "- Type A text block: `Derzeitige Beschwerden (somatisch)` → medication header",
        "- Type B text block: `Spezielle Eigenanamnese` → medication header",
        "- End markers: `Vormedikation`, `Aktuelle Medikation`, `Medikation bei Aufnahme`, `Allgemeine Eigenanamnese`",
        "- One record per diagnosis, all sharing the same text block",
        "- ICD: first code extracted when multiple on one line",
        "- Text normalization: whitespace only, German text preserved",
        "",
        "## 5 Sample Records",
        "",
    ]

    for i, rec in enumerate(samples, 1):
        lines.append(f"### Sample {i}: `{rec.source_case_id}`")
        lines.append("")
        lines.append("```json")
        sample_dict = {
            "source_case_id":    rec.source_case_id,
            "diagnosis_label":   rec.diagnosis_label,
            "icd_code":          rec.icd_code,
            "text_block":        rec.text_block[:300] + ("..." if len(rec.text_block) > 300 else ""),
            "text_source_type":  rec.text_source_type,
            "source_filename":   rec.source_filename,
            "extraction_status": rec.extraction_status,
        }
        lines.append(json.dumps(sample_dict, ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
