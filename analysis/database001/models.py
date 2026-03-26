"""
models.py — data structures for database001 extraction
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class DiagnosisLine:
    """One parsed diagnosis line from 'Somatische Diagnosen:' section."""
    raw_text:        str
    diagnosis_label: str
    icd_code:        str   # empty string if not found


@dataclass
class ExtractionRecord:
    """One output record (one diagnosis × one text block)."""
    source_case_id:   str
    diagnosis_label:  str
    icd_code:         str
    text_block:       str
    text_source_type: str   # "derzeitige_beschwerden" | "spezielle_eigenanamnese" | ""
    source_filename:  str
    extraction_status: str  # "ok" | "missing_diagnosis_section" | "missing_text_section" | "needs_review"


@dataclass
class DocumentResult:
    """Extraction outcome for a single document."""
    source_filename: str
    status:          str
    records:         list[ExtractionRecord] = field(default_factory=list)
    notes:           str = ""
    diag_header_used: str = ""   # exact header text matched, e.g. "Somatische Diagnosen:" or "Diagnosen:"
