"""
aggregator.py
-------------
Aggregate raw CandidateMatch objects into frequency-ranked AggregatedCandidate objects.

Aggregation key: (canonical, pattern_type, cluster_hint)
  - Counts unique documents (not raw match count)
  - Collects up to MAX_EXAMPLES distinct surface-form examples

Output is sorted by frequency descending, then canonical alphabetically.
"""

from __future__ import annotations

from collections import defaultdict

from analysis.mining.models import AggregatedCandidate, CandidateMatch

_MAX_EXAMPLES    = 5   # max surface form examples per candidate
_MIN_DOC_COUNT   = 1   # minimum docs to include in output (filter noise)


class Aggregator:
    """
    Groups CandidateMatch objects into AggregatedCandidate objects.

    Usage:
        agg = Aggregator()
        candidates = agg.aggregate(matches)
    """

    def aggregate(self, matches: list[CandidateMatch]) -> list[AggregatedCandidate]:
        """
        Aggregate matches by (canonical, pattern_type, cluster_hint).

        Returns sorted list of AggregatedCandidate objects.
        """
        # key → set of doc_files seen
        doc_sets:  dict[tuple[str, str, str], set[str]] = defaultdict(set)
        # key → list of (matched_text, doc_file) for examples
        examples:  dict[tuple[str, str, str], list[tuple[str, str]]] = defaultdict(list)

        for m in matches:
            key = (m.canonical, m.pattern_type, m.cluster_hint)
            doc_sets[key].add(m.doc_file)
            examples[key].append((m.matched_text, m.doc_file))

        results: list[AggregatedCandidate] = []

        for key, docs in doc_sets.items():
            canonical, ptype, cluster_hint = key
            freq = len(docs)

            if freq < _MIN_DOC_COUNT:
                continue

            # Deduplicate examples by surface form, preserve insertion order
            seen_texts: set[str] = set()
            ex_texts:   list[str] = []
            ex_docs:    list[str] = []

            for text, doc in examples[key]:
                text_lower = text.lower()
                if text_lower not in seen_texts and len(ex_texts) < _MAX_EXAMPLES:
                    seen_texts.add(text_lower)
                    ex_texts.append(text)
                    ex_docs.append(doc)

            results.append(AggregatedCandidate(
                canonical     = canonical,
                pattern_type  = ptype,
                cluster_hint  = cluster_hint,
                frequency     = freq,
                doc_count     = freq,
                example_texts = ex_texts,
                example_docs  = ex_docs,
            ))

        # Sort: frequency desc, then canonical asc
        results.sort(key=lambda c: (-c.frequency, c.canonical))
        return results
