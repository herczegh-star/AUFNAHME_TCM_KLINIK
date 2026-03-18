from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from core.template_repository import Cluster

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


class EmbeddingIndex:
    def __init__(self) -> None:
        self._model = SentenceTransformer(MODEL_NAME)
        self._clusters: list[Cluster] = []
        self._embeddings: np.ndarray | None = None

    @staticmethod
    def _cluster_to_text(c: Cluster) -> str:
        """
        Build a rich text representation for embedding.

        structured → name + slot names + representative option values
        template   → name + first template text
        variant    → name + variant names
        """
        parts: list[str] = [c.name]

        if c.mode == "structured":
            # Only slot names — not option values, to avoid cross-cluster
            # contamination (e.g. WS-Syndrom.lokalisation contains "LWS")
            parts.extend(c.struktur)

        elif c.mode == "template" and c.templates:
            parts.append(c.templates[0][:300])

        elif c.mode == "variant":
            for v in c.varianty:
                parts.append(v.get("name", ""))

        return " ".join(parts)

    def build_index(self, clusters: list[Cluster]) -> None:
        # Only index symptom_cluster entries (all entries from v2 already are)
        self._clusters = [c for c in clusters if c.type == "symptom_cluster"]
        texts = [self._cluster_to_text(c) for c in self._clusters]
        self._embeddings = self._model.encode(texts, convert_to_numpy=True)

    def find_best_match(self, query: str, top_k: int = 3) -> list[Cluster]:
        if self._embeddings is None or not self._clusters:
            raise RuntimeError("Index is empty — call build_index() first.")

        query_embedding = self._model.encode([query], convert_to_numpy=True)
        scores = cosine_similarity(query_embedding, self._embeddings)[0]
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [self._clusters[i] for i in top_indices]
