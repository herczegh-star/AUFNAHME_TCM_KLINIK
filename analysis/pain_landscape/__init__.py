"""
analysis/pain_landscape/__init__.py
------------------------------------
Deterministic Pain Landscape Pack Builder.

Aggregates pain features from candidates_all.csv into a structured pack
suitable for macro-analysis by a large LLM or human curator.

No classification. No heuristics. Pure aggregation + export.

Pipeline:
    DataLoader -> Aggregator -> Exporter

Entry point: analysis/pain_landscape_pack_builder.py
"""
