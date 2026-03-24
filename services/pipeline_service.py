"""
pipeline_service.py
-------------------
Service layer for initialising the core NLP pipeline.

Replaces the build_pipeline() function that previously lived in ui/app.py.
UI layer imports this class and calls .build() — it has no knowledge of how
the pipeline is constructed.
"""

from __future__ import annotations

from core.template_repository import TemplateRepository
from core.embedding_index import EmbeddingIndex
from core.template_matcher import TemplateMatcher
from core.language_refiner import OpenAIRefinerClient


class PipelineService:
    """
    Constructs and returns the core pipeline components.

    Usage:
        service = PipelineService()
        matcher, llm, repo = service.build()
    """

    def build(self) -> tuple[TemplateMatcher, OpenAIRefinerClient | None, TemplateRepository]:
        repo = TemplateRepository()
        repo.load_templates()

        index = EmbeddingIndex()
        index.build_index(repo.get_all_templates())

        try:
            llm = OpenAIRefinerClient()
        except Exception:
            llm = None

        return TemplateMatcher(repo, index), llm, repo
