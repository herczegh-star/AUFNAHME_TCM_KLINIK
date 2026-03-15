from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from core.template_repository import Template

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


class EmbeddingIndex:
    def __init__(self) -> None:
        self._model = SentenceTransformer(MODEL_NAME)
        self._templates: list[Template] = []
        self._embeddings: np.ndarray | None = None

    @staticmethod
    def _template_to_text(t: Template) -> str:
        return f"{t.section} {t.title} {t.text}"

    def build_index(self, templates: list[Template]) -> None:
        self._templates = templates
        texts = [self._template_to_text(t) for t in templates]
        self._embeddings = self._model.encode(texts, convert_to_numpy=True)

    def find_best_match(self, query: str, top_k: int = 3) -> list[Template]:
        if self._embeddings is None or not self._templates:
            raise RuntimeError("Index is empty — call build_index() first.")

        query_embedding = self._model.encode([query], convert_to_numpy=True)
        scores = cosine_similarity(query_embedding, self._embeddings)[0]
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [self._templates[i] for i in top_indices]
