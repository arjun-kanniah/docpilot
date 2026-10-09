from collections.abc import Sequence
from functools import lru_cache
from typing import Protocol

from docpilot.config import get_settings

# Dimension of BAAI/bge-small-en-v1.5. Changing the model means a new migration.
EMBEDDING_DIM = 384


class Embedder(Protocol):
    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class FastEmbedEmbedder:
    """Runs a small ONNX embedding model locally on the CPU: no API key, no per-call cost."""

    def __init__(self, model_name: str, cache_dir: str) -> None:
        from fastembed import TextEmbedding  # imported lazily: loading it is slow

        self._model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)

    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self._model.passage_embed(list(texts))]

    def embed_query(self, text: str) -> list[float]:
        return next(iter(self._model.query_embed(text))).tolist()


@lru_cache
def get_embedder() -> Embedder:
    settings = get_settings()
    return FastEmbedEmbedder(settings.embedding_model, str(settings.model_cache_dir))
