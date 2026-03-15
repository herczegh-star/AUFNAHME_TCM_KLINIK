from __future__ import annotations

from core.embedding_index import EmbeddingIndex
from core.template_repository import Template, TemplateRepository


class TemplateMatcher:
    def __init__(self, repository: TemplateRepository, index: EmbeddingIndex) -> None:
        self._repository = repository
        self._index = index

    def find_best_template(self, query: str) -> Template:
        results = self._index.find_best_match(query, top_k=1)
        return results[0]
