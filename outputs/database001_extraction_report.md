# database001 Extraction Report

## Summary

| Metric | Count |
|--------|-------|
| Total documents processed | 2311 |
| Documents successfully parsed | 1701 |
| Missing diagnosis section | 603 |
| Missing text section | 4 |
| Needs review | 3 |
| **Total records created** | **7769** |

## Record Details

| Detail | Count |
|--------|-------|
| Type A (derzeitige_beschwerden) records | 5433 |
| Type B (spezielle_eigenanamnese) records | 2336 |
| Records with ICD code | 6943 |
| Records without ICD code | 826 |
| Records with ICD M54.86 | 368 |

## Diagnosis Header Breakdown (successfully parsed docs)

| Header used | Documents |
|-------------|-----------|
| Somatische Diagnosen / Diagnose | 1177 |
| Diagnosen | 524 |
| Diagnose (singular) | 0 |

## Output Files

- `outputs/database001_records.jsonl`
- `outputs/database001_records.csv`
- `outputs/database001_extraction_report.md`

## Extraction Rules Applied

- Diagnosis section: `Somatische Diagnosen`, `Diagnosen`, `Diagnose` (with/without colon)
- Type A text block: `Derzeitige Beschwerden (somatisch)` → medication header
- Type B text block: `Spezielle Eigenanamnese` → medication header
- End markers: `Vormedikation`, `Aktuelle Medikation`, `Medikation bei Aufnahme`, `Allgemeine Eigenanamnese`
- One record per diagnosis, all sharing the same text block
- ICD: first code extracted when multiple on one line
- Text normalization: whitespace only, German text preserved

## 5 Sample Records

### Sample 1: `Patient_001`

```json
{
  "source_case_id": "Patient_001",
  "diagnosis_label": "Chronisches Müdigkeitssyndrom",
  "icd_code": "G93.3",
  "text_block": "Die Patientin ist im Hause bekannt, voriges Jahr befand sie sich zum letzten Mal in unserer stationären Behandlung. Die ausführliche Vorgeschichte dürfen wir freundlicherweise als bekannt voraussetzen und verweisen auf die entsprechenden Berichte. Kurz gefasst berichtet die Patientin, dass sich aufg...",
  "text_source_type": "derzeitige_beschwerden",
  "source_filename": "Patient_001.docx",
  "extraction_status": "ok"
}
```

### Sample 2: `Patient_001`

```json
{
  "source_case_id": "Patient_001",
  "diagnosis_label": "Verdauungsbeschwerden",
  "icd_code": "K58.8",
  "text_block": "Die Patientin ist im Hause bekannt, voriges Jahr befand sie sich zum letzten Mal in unserer stationären Behandlung. Die ausführliche Vorgeschichte dürfen wir freundlicherweise als bekannt voraussetzen und verweisen auf die entsprechenden Berichte. Kurz gefasst berichtet die Patientin, dass sich aufg...",
  "text_source_type": "derzeitige_beschwerden",
  "source_filename": "Patient_001.docx",
  "extraction_status": "ok"
}
```

### Sample 3: `Patient_001`

```json
{
  "source_case_id": "Patient_001",
  "diagnosis_label": "Hashimoto Thyreoiditis",
  "icd_code": "E06.3",
  "text_block": "Die Patientin ist im Hause bekannt, voriges Jahr befand sie sich zum letzten Mal in unserer stationären Behandlung. Die ausführliche Vorgeschichte dürfen wir freundlicherweise als bekannt voraussetzen und verweisen auf die entsprechenden Berichte. Kurz gefasst berichtet die Patientin, dass sich aufg...",
  "text_source_type": "derzeitige_beschwerden",
  "source_filename": "Patient_001.docx",
  "extraction_status": "ok"
}
```

### Sample 4: `Patient_002`

```json
{
  "source_case_id": "Patient_002",
  "diagnosis_label": "Chronisches Müdigkeitssyndrom",
  "icd_code": "G93.3",
  "text_block": "Bei Aufnahmegespräch berichtet der Patient seit 2-3 Jahren unter Müdigkeitssymptomatik zu leiden. Er berichtet, dass er sich sehr erschöpft fühle und seine Belastbarkeitsgrenze sei schneller als vorher erreicht. Weiterhin berichtet er über Konzentrations- und Merkfähigkeitsstörungen. Er sei schnell ...",
  "text_source_type": "derzeitige_beschwerden",
  "source_filename": "Patient_002.docx",
  "extraction_status": "ok"
}
```

### Sample 5: `Patient_002`

```json
{
  "source_case_id": "Patient_002",
  "diagnosis_label": "Nichtorganische Insomnie",
  "icd_code": "F51.0",
  "text_block": "Bei Aufnahmegespräch berichtet der Patient seit 2-3 Jahren unter Müdigkeitssymptomatik zu leiden. Er berichtet, dass er sich sehr erschöpft fühle und seine Belastbarkeitsgrenze sei schneller als vorher erreicht. Weiterhin berichtet er über Konzentrations- und Merkfähigkeitsstörungen. Er sei schnell ...",
  "text_source_type": "derzeitige_beschwerden",
  "source_filename": "Patient_002.docx",
  "extraction_status": "ok"
}
```

