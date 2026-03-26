"""
analysis/mining/__init__.py
---------------------------
Deterministic mining layer for candidate block extraction.

Extracts symptom block candidates from text_export.jsonl using
rule-based pattern matching — no AI, no scoring, fully auditable.

Pipeline:
    TextExportLoader → Segmenter → RuleBasedExtractor → Aggregator → Exporter

Entry point: analysis/candidate_extractor_v2.py
"""
