"""
pack_builder.py
---------------
Build a ReviewPack for a single cluster seed from CandidateRow data.

Algorithm:
  1. Locate seed row (type=cluster, canonical=seed_cluster)
  2. Collect cluster-linked candidates (cluster == seed_cluster)
  3. Collect global top candidates (cluster is None) per type — top N each
  4. Build sections: cluster-linked first, then global fills gaps
  5. Deduplicate by canonical within each section
  6. Generate deterministic curator questions
  7. Assemble ReviewPack with meta

No AI. No scoring. Fully reproducible.
"""

from __future__ import annotations

from collections import defaultdict

from analysis.review_packs.models import (
    CandidateRow,
    PackSection,
    ReviewPack,
)

# Types included in sections (cluster type is seed metadata, not a section)
_SECTION_TYPES = ("side", "character", "aggravating", "relieving", "radiation",
                  "functional", "associated")

# Max global (non-cluster-specific) candidates per type to include
_MAX_GLOBAL_PER_TYPE = 10

# Curator question templates per type
_QUESTION_TEMPLATES: dict[str, str] = {
    "relieving":   "Má být {canonical} pro cluster {cluster} samostatný relieving block?",
    "aggravating": "Má být {canonical} pro cluster {cluster} aggravating modifier?",
    "radiation":   "Má být {canonical} u clusteru {cluster} řešena jako slotovaný block?",
    "side":        "Mají být side hodnoty ({examples}) řešeny samostatnou laterality vrstvou?",
    "character":   "Má být charakter '{canonical}' pro cluster {cluster} zahrnut jako MODIFIER block?",
    "functional":  "Má být funkční omezení '{canonical}' pro cluster {cluster} přidáno do FUNCTIONAL_IMPACT bloku?",
    "associated":  "Má být přidružený symptom '{canonical}' pro cluster {cluster} přidán jako ASSOCIATED_SYMPTOM?",
}

_MAX_CURATOR_QUESTIONS = 8


class PackBuilder:
    """
    Builds a ReviewPack for one seed cluster.

    Usage:
        builder = PackBuilder()
        pack    = builder.build(rows, seed_cluster="LWS-Syndrom")
        # returns None if seed not found in rows
    """

    def build(
        self,
        rows:         list[CandidateRow],
        seed_cluster: str,
    ) -> ReviewPack | None:
        """
        Build and return a ReviewPack, or None if seed_cluster not found.
        """
        # 1 — locate seed
        seed = self._find_seed(rows, seed_cluster)
        if seed is None:
            return None

        # 2 — cluster-linked candidates (excluding the seed itself)
        cluster_linked = [
            r for r in rows
            if r.cluster == seed_cluster and r.type != "cluster"
        ]

        # 3 — global candidates (cluster is None), top N per type
        global_candidates = self._top_global(rows)

        # 4 — build sections
        sections = self._build_sections(cluster_linked, global_candidates)

        # 5 — curator questions
        questions = self._build_questions(sections, seed_cluster)

        # 6 — meta
        total_global_used = sum(
            1 for r in global_candidates
            if any(r.canonical in [i.canonical for i in s.items] for s in sections)
        )

        meta = {
            "seed_cluster":        seed_cluster,
            "total_cluster_linked": len(cluster_linked),
            "total_global_used":   total_global_used,
            "generated_from":      "candidates_all.csv",
        }

        return ReviewPack(
            seed_cluster              = seed_cluster,
            seed_docs                 = seed.docs,
            seed_examples             = seed.examples,
            sections                  = sections,
            global_candidates         = global_candidates,
            cluster_linked_candidates = cluster_linked,
            curator_questions         = questions,
            meta                      = meta,
        )

    # ------------------------------------------------------------------
    # Private: seed
    # ------------------------------------------------------------------

    def _find_seed(
        self, rows: list[CandidateRow], seed_cluster: str
    ) -> CandidateRow | None:
        for r in rows:
            if r.type == "cluster" and r.canonical == seed_cluster:
                return r
        return None

    # ------------------------------------------------------------------
    # Private: global candidates
    # ------------------------------------------------------------------

    def _top_global(self, rows: list[CandidateRow]) -> list[CandidateRow]:
        """
        Select top _MAX_GLOBAL_PER_TYPE rows per type where cluster is None.
        Returns flat list sorted by docs desc within each type.
        """
        by_type: dict[str, list[CandidateRow]] = defaultdict(list)
        for r in rows:
            if r.cluster is None and r.type in _SECTION_TYPES:
                by_type[r.type].append(r)

        result: list[CandidateRow] = []
        for t in _SECTION_TYPES:
            top = sorted(by_type[t], key=lambda r: r.docs, reverse=True)
            result.extend(top[:_MAX_GLOBAL_PER_TYPE])

        return result

    # ------------------------------------------------------------------
    # Private: sections
    # ------------------------------------------------------------------

    def _build_sections(
        self,
        cluster_linked:   list[CandidateRow],
        global_candidates: list[CandidateRow],
    ) -> list[PackSection]:
        """
        For each section type:
          1. cluster-linked items first
          2. global items appended if canonical not already present
        """
        sections: list[PackSection] = []

        for stype in _SECTION_TYPES:
            linked  = [r for r in cluster_linked   if r.type == stype]
            globals_ = [r for r in global_candidates if r.type == stype]

            seen:  set[str]       = {r.canonical for r in linked}
            items: list[CandidateRow] = list(linked)

            for r in globals_:
                if r.canonical not in seen:
                    seen.add(r.canonical)
                    items.append(r)

            if items:
                sections.append(PackSection(type=stype, items=items))

        return sections

    # ------------------------------------------------------------------
    # Private: curator questions
    # ------------------------------------------------------------------

    def _build_questions(
        self, sections: list[PackSection], seed_cluster: str
    ) -> list[str]:
        questions: list[str] = []
        types_seen: set[str] = set()

        for section in sections:
            if len(questions) >= _MAX_CURATOR_QUESTIONS:
                break

            stype = section.type
            template = _QUESTION_TEMPLATES.get(stype)
            if not template:
                continue

            if stype == "side":
                # One question for the whole side section
                if "side" not in types_seen and section.items:
                    examples_str = " / ".join(r.canonical for r in section.items[:3])
                    questions.append(template.format(
                        cluster=seed_cluster, examples=examples_str, canonical="side"
                    ))
                    types_seen.add("side")
            else:
                # One question per item (up to limit)
                for item in section.items:
                    if len(questions) >= _MAX_CURATOR_QUESTIONS:
                        break
                    questions.append(template.format(
                        canonical=item.canonical,
                        cluster=seed_cluster,
                        examples=" / ".join(item.examples[:3]),
                    ))

        return questions
