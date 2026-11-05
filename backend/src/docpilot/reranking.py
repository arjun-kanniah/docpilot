"""Rerankers: a cross-encoder reads the question and each candidate passage together and scores
how well the passage answers it. That is more accurate than comparing two separately made
embeddings, and much slower (one model pass per passage), so it only reorders the top few
candidates. docs/retrieval-experiments.md (E3) measures which models are worth it."""

from collections.abc import Sequence
from functools import lru_cache
from typing import Protocol

from docpilot.config import get_settings

RERANK_BATCH = 16  # each batch is padded to its longest passage, as with embeddings


class Reranker(Protocol):
    def scores(self, query: str, texts: Sequence[str]) -> list[float]: ...


class FastEmbedReranker:
    """Runs a cross-encoder locally on the CPU with ONNX Runtime."""

    def __init__(self, model_name: str, cache_dir: str, threads: int | None = None) -> None:
        from fastembed.rerank.cross_encoder import TextCrossEncoder  # slow import

        self.model_name = model_name
        self._model = TextCrossEncoder(model_name=model_name, cache_dir=cache_dir, threads=threads)

    def scores(self, query: str, texts: Sequence[str]) -> list[float]:
        if not texts:
            return []
        return [float(s) for s in self._model.rerank(query, list(texts), batch_size=RERANK_BATCH)]


@lru_cache
def get_reranker() -> Reranker | None:
    """The configured reranker, or None when DOCPILOT_RERANKER is unset (the default)."""
    settings = get_settings()
    if not settings.reranker:
        return None
    return FastEmbedReranker(settings.reranker, str(settings.model_cache_dir))
