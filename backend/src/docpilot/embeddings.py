from collections.abc import Sequence
from functools import lru_cache
from typing import Protocol

from docpilot.config import get_settings

# Dimension of BAAI/bge-small-en-v1.5. Changing the model means a new migration.
EMBEDDING_DIM = 384
PASSAGE_BATCH = 16


class Embedder(Protocol):
    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class FastEmbedEmbedder:
    """Runs a small ONNX embedding model locally on the CPU: no API key, no per-call cost."""

    def __init__(self, model_name: str, cache_dir: str, threads: int | None = None) -> None:
        from fastembed import TextEmbedding  # imported lazily: loading it is slow

        # threads=None lets ONNX Runtime use every core; the benchmarks pin it to match Cloud Run
        self._model = TextEmbedding(model_name=model_name, cache_dir=cache_dir, threads=threads)

    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]:
        # Small batches: each batch is padded to its longest text, and on CPU batches of 16
        # embedded ~65% faster than fastembed's default of 256 (10.8 vs 6.5 chunks/s)
        vectors = self._model.passage_embed(list(texts), batch_size=PASSAGE_BATCH)
        return [vector.tolist() for vector in vectors]

    def embed_query(self, text: str) -> list[float]:
        return next(iter(self._model.query_embed(text))).tolist()


@lru_cache
def get_embedder() -> Embedder:
    settings = get_settings()
    return FastEmbedEmbedder(settings.embedding_model, str(settings.model_cache_dir))
