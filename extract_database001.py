"""
extract_database001.py
-----------------------
CLI runner: deterministic extraction of diagnoses + text blocks
from all .docx files in dataset/aufnahmeberichte_2312_/

Outputs:
  outputs/database001_records.jsonl
  outputs/database001_records.csv
  outputs/database001_extraction_report.md

No AI. No clustering. No semantic interpretation.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from analysis.database001.extractor import extract_all
from analysis.database001.exporter import write_csv, write_jsonl, write_report

_DATASET_DIR = Path("dataset/aufnahmeberichte_2312_")
_OUT_JSONL   = Path("outputs/database001_records.jsonl")
_OUT_CSV     = Path("outputs/database001_records.csv")
_OUT_REPORT  = Path("outputs/database001_extraction_report.md")


def main() -> None:
    print(f"database001 extractor")
    print(f"  dataset : {_DATASET_DIR}")
    print(f"  files   : {len(list(_DATASET_DIR.glob('*.docx')))}")
    print()

    print("Extracting...")
    results = extract_all(_DATASET_DIR)

    # Flatten all ok records
    all_records = [rec for res in results for rec in res.records]

    # Stats
    ok_docs       = sum(1 for r in results if r.status == "ok")
    missing_diag  = sum(1 for r in results if r.status == "missing_diagnosis_section")
    missing_text  = sum(1 for r in results if r.status == "missing_text_section")
    needs_review  = sum(1 for r in results if r.status == "needs_review")

    print(f"  total docs     : {len(results)}")
    print(f"  ok             : {ok_docs}")
    print(f"  missing diag   : {missing_diag}")
    print(f"  missing text   : {missing_text}")
    print(f"  needs_review   : {needs_review}")
    print(f"  records created: {len(all_records)}")
    print()

    print("Writing outputs...")
    write_jsonl(all_records, _OUT_JSONL)
    print(f"  [OK] {_OUT_JSONL}")

    write_csv(all_records, _OUT_CSV)
    print(f"  [OK] {_OUT_CSV}")

    write_report(results, all_records, _OUT_REPORT)
    print(f"  [OK] {_OUT_REPORT}")

    print()
    print("Done.")


if __name__ == "__main__":
    main()
