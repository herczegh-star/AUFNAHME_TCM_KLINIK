"""
extractor.py
------------
Deterministic extraction of diagnoses and text blocks from .docx files.

No AI. No clustering. No semantic interpretation.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

import docx

from analysis.database001.models import DiagnosisLine, DocumentResult, ExtractionRecord


# ---------------------------------------------------------------------------
# Section header patterns
# ---------------------------------------------------------------------------

# Hard stops — always end the diagnosis section
_DIAG_HARD_STOP_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r'Allgemeine Eigenanamnese', re.IGNORECASE),
    re.compile(r'TCM-Diagnose', re.IGNORECASE),
    re.compile(r'Familienanamnese', re.IGNORECASE),
    re.compile(r'Vormedikation', re.IGNORECASE),
    re.compile(r'Aktuelle Medikation', re.IGNORECASE),
    re.compile(r'Medikament', re.IGNORECASE),
    re.compile(r'Vegetative Anamnese', re.IGNORECASE),
    re.compile(r'K.rperlicher', re.IGNORECASE),
]

# Soft skips — these can appear as column headers *inside* the diagnosis table
# in some documents.  Skip the line, do NOT stop.
# Examples:
#   Patient_055: "Derzeitige Beschwerden (somatisch):" before the diagnosis lines
#   Patient_335/373: "Aufnahme somatisch/chinesisch:" before the diagnosis lines
_DIAG_SOFT_SKIP_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r'Derzeitige Beschwerden', re.IGNORECASE),
    re.compile(r'Spezielle Eigenanamnese', re.IGNORECASE),
    re.compile(r'Aufnahme somatisch', re.IGNORECASE),
]

# Headers that terminate the text block (both Type A and Type B)
_TEXT_STOP_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r'^Vormedikation\s*:', re.IGNORECASE),
    re.compile(r'^Aktuelle Medikation\s*:', re.IGNORECASE),
    re.compile(r'^Aktuelle Medikamente\s*:', re.IGNORECASE),
    re.compile(r'^Medikation bei Aufnahme\s*:', re.IGNORECASE),
    re.compile(r'^Bedarfsmedikation\s*:', re.IGNORECASE),
    re.compile(r'^Dauermedikation\s*:', re.IGNORECASE),
    re.compile(r'^Allgemeine Eigenanamnese\s*:', re.IGNORECASE),
    re.compile(r'^Allgem\. Eigenanamnese\s*:', re.IGNORECASE),
]

# ICD-10 code pattern: one letter + 2 digits + optional .digit(s)
_ICD_RE = re.compile(r'\b([A-Z]\d{2}(?:\.\d+)?)\b')

# Diagnosis section start — all observed real variants (with or without colon)
#   "Somatische Diagnosen:"  /  "Somatische Diagnose:"
#   "Diagnosen:"             /  "Diagnose:"
_DIAG_SECTION_RE = re.compile(
    r'^(Somatische\s+Diagnos[ae]n?|Diagnos[ae]n?)\s*:?\s*$',
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Diagnosis parsing
# ---------------------------------------------------------------------------

def _parse_diagnosis_line(raw: str) -> Optional[DiagnosisLine]:
    """
    Parse one line from the diagnosis section.

    Expected format (tab-separated):
      <diagnosis_label>    <icd_code>

    Returns None if the line appears to be a continuation / artifact (no text
    content on the left side and no ICD code detectable).
    """
    text = raw.strip()

    # Remove leading bullet/dash artifacts
    text = re.sub(r'^[-\u2013\u2014\*]+\s*', '', text)
    # Remove paragraph marks and dot leaders
    text = re.sub(r'[¶…]+', '', text)
    text = text.strip()

    if not text:
        return None

    # Split on tab(s)
    parts = re.split(r'\t+', text)

    if len(parts) >= 2:
        label = parts[0].strip()
        # ICD is the last non-empty part — take only the FIRST code if multiple
        raw_icd = parts[-1].strip()
        # Multiple ICD codes on one line (e.g. "L40.5, M07.00") → first only
        icd_match = _ICD_RE.search(raw_icd)
        icd = icd_match.group(1) if icd_match else ""
    else:
        # No tab — try to find ICD code at end of line
        icd_match = _ICD_RE.search(text)
        if icd_match:
            icd = icd_match.group(1)
            # Label is everything before the ICD code, trimmed
            label = text[:icd_match.start()].strip().rstrip(',').strip()
        else:
            # No ICD found — still emit record with empty icd_code
            label = text
            icd = ""

    if not label:
        return None

    return DiagnosisLine(raw_text=raw, diagnosis_label=label, icd_code=icd)


def _extract_diagnoses(paragraphs: list[str]) -> tuple[list[DiagnosisLine], str]:
    """
    Extract diagnosis lines from the diagnosis section.

    Recognised section headers (with or without trailing colon):
      "Somatische Diagnosen"  /  "Somatische Diagnose"
      "Diagnosen"             /  "Diagnose"

    Returns (list_of_diagnosis_lines, exact_header_text_matched).

    Two-tier stop logic:
    - Hard stop: headers that unambiguously end the diagnosis block.
    - Soft skip: headers that can appear as column labels *inside* the
      diagnosis table in some documents.  Skip the line, keep collecting.
    - Prose guard: a line > 120 chars without a tab is clinical prose → stop.
    """
    results: list[DiagnosisLine] = []
    in_section = False
    header_used = ""

    for text in paragraphs:
        stripped = text.strip()

        if not in_section:
            if _DIAG_SECTION_RE.match(stripped):
                in_section = True
                header_used = stripped
            continue

        # Hard stop
        if stripped and any(p.search(stripped) for p in _DIAG_HARD_STOP_PATTERNS):
            break

        # Prose guard — long line without a tab is clinical text, not a diagnosis
        if stripped and len(stripped) > 120 and '\t' not in stripped:
            break

        # Soft skip — column label within diagnosis table
        if stripped and any(p.search(stripped) for p in _DIAG_SOFT_SKIP_PATTERNS):
            continue

        if not stripped:
            continue

        dl = _parse_diagnosis_line(stripped)
        if dl:
            results.append(dl)

    return results, header_used


# ---------------------------------------------------------------------------
# Text block extraction
# ---------------------------------------------------------------------------

def _is_text_stop(line: str) -> bool:
    return any(p.match(line.strip()) for p in _TEXT_STOP_PATTERNS)


def _extract_text_block(paragraphs: list[str]) -> tuple[str, str]:
    """
    Try Type A then Type B.

    Returns (text_block, text_source_type).
    text_block is "" if not found.
    text_source_type is "" if not found.
    """
    # --- Type A: Derzeitige Beschwerden (somatisch): → medication header ---
    result, src = _try_extract(
        paragraphs,
        start_pattern=re.compile(r'Derzeitige Beschwerden\s*\(somatisch\)\s*:', re.IGNORECASE),
        source_type="derzeitige_beschwerden",
    )
    if result:
        return result, src

    # --- Type B: Spezielle Eigenanamnese: → medication header ---
    result, src = _try_extract(
        paragraphs,
        start_pattern=re.compile(r'Spezielle Eigenanamnese\s*:', re.IGNORECASE),
        source_type="spezielle_eigenanamnese",
    )
    if result:
        return result, src

    return "", ""


def _try_extract(
    paragraphs: list[str],
    start_pattern: re.Pattern[str],
    source_type: str,
) -> tuple[str, str]:
    """
    Scan paragraphs for start_pattern, collect lines until a stop header,
    normalize and return as a single text block.
    """
    collecting = False
    lines: list[str] = []

    for text in paragraphs:
        stripped = text.strip()

        if not collecting:
            if start_pattern.search(stripped):
                collecting = True
            continue

        # Stop at medication / next-section headers
        if stripped and _is_text_stop(stripped):
            break

        if stripped:
            lines.append(stripped)

    if not lines:
        return "", ""

    # Normalize: join with single space between paragraphs
    text_block = " ".join(lines)
    # Collapse multiple whitespace
    text_block = re.sub(r'\s+', ' ', text_block).strip()

    return text_block, source_type


# ---------------------------------------------------------------------------
# Document processor
# ---------------------------------------------------------------------------

def process_document(filepath: str | Path) -> DocumentResult:
    """
    Extract diagnoses and text block from one .docx file.

    Returns DocumentResult with zero or more ExtractionRecord entries.
    """
    filepath = Path(filepath)
    filename = filepath.name
    source_case_id = filepath.stem  # filename without extension

    try:
        doc = docx.Document(str(filepath))
    except Exception as exc:
        return DocumentResult(
            source_filename=filename,
            status="needs_review",
            notes=f"Could not open file: {exc}",
        )

    paragraphs = [p.text for p in doc.paragraphs]

    has_diag_section = any(
        _DIAG_SECTION_RE.match(p.strip()) for p in paragraphs if p.strip()
    )
    has_text_section = bool(
        any(re.match(r'Derzeitige Beschwerden\s*\(somatisch\)\s*:?', p.strip(), re.IGNORECASE)
            for p in paragraphs) or
        any(re.match(r'Spezielle Eigenanamnese\s*:?', p.strip(), re.IGNORECASE)
            for p in paragraphs)
    )

    # Determine status
    if not has_diag_section:
        return DocumentResult(
            source_filename=filename,
            status="missing_diagnosis_section",
        )

    if not has_text_section:
        return DocumentResult(
            source_filename=filename,
            status="missing_text_section",
        )

    # Extract
    diagnoses, header_used = _extract_diagnoses(paragraphs)
    text_block, text_source_type = _extract_text_block(paragraphs)

    if not diagnoses:
        return DocumentResult(
            source_filename=filename,
            status="needs_review",
            notes="Diagnosis section present but no lines parsed",
            diag_header_used=header_used,
        )

    if not text_block:
        return DocumentResult(
            source_filename=filename,
            status="missing_text_section",
            diag_header_used=header_used,
        )

    # One record per diagnosis, all sharing the same text_block
    records: list[ExtractionRecord] = []
    for dl in diagnoses:
        records.append(ExtractionRecord(
            source_case_id    = source_case_id,
            diagnosis_label   = dl.diagnosis_label,
            icd_code          = dl.icd_code,
            text_block        = text_block,
            text_source_type  = text_source_type,
            source_filename   = filename,
            extraction_status = "ok",
        ))

    return DocumentResult(
        source_filename=filename,
        status="ok",
        records=records,
        diag_header_used=header_used,
    )


# ---------------------------------------------------------------------------
# Batch runner
# ---------------------------------------------------------------------------

def extract_all(dataset_dir: str | Path) -> list[DocumentResult]:
    """
    Process all .docx files in dataset_dir, sorted by filename.
    """
    dataset_dir = Path(dataset_dir)
    files = sorted(dataset_dir.glob("*.docx"))
    return [process_document(f) for f in files]
