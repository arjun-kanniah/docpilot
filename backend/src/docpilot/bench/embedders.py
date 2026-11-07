"""Embedding models compared in E4 (benchmark only; the app uses bge-small).

Each model gets its own benchmark database, because the embedding column's size is fixed by
the model (384 numbers per passage for bge-small, 768 for bge-base, ...). Hosted models are
called over the network, so their query latency includes the round trip, and every call is
counted so the log can report the real bill rather than an estimate.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from docpilot.embeddings import EMBEDDING_DIM, FastEmbedEmbedder


@dataclass(frozen=True)
class EmbedderSpec:
    model: str
    dimensions: int
    hosted: bool = False
    usd_per_million_tokens: float = 0.0  # list price, checked Nov 7 2026


EMBEDDERS = {
    "bge-small": EmbedderSpec("BAAI/bge-small-en-v1.5", EMBEDDING_DIM),
    "bge-base": EmbedderSpec("BAAI/bge-base-en-v1.5", 768),
    "openai-small": EmbedderSpec("text-embedding-3-small", 1536, True, 0.02),
    # Its full size is 3072, past pgvector's 2,000 limit for an HNSW index on `vector`, so it
    # is asked for 1536 (the API shortens it without retraining; OpenAI reports a small loss).
    "openai-large": EmbedderSpec("text-embedding-3-large", 1536, True, 0.13),
}
DEFAULT = "bge-small"


class OpenAIEmbedder:
    """OpenAI's embeddings API. Counts the tokens it is billed for."""

    BATCH = 512  # passages per request (the API allows 2,048 and 300K tokens)

    def __init__(self, spec: EmbedderSpec, api_key: str) -> None:
        from openai import OpenAI

        self.spec = spec
        self.tokens = 0
        self._client = OpenAI(api_key=api_key, max_retries=8, timeout=120)

    def _embed(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(
            model=self.spec.model, input=texts, dimensions=self.spec.dimensions
        )
        self.tokens += response.usage.total_tokens
        return [item.embedding for item in sorted(response.data, key=lambda d: d.index)]

    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.BATCH):
            vectors.extend(self._embed(list(texts[start : start + self.BATCH])))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0]

    @property
    def usd(self) -> float:
        return self.tokens / 1_000_000 * self.spec.usd_per_million_tokens


def make_embedder(
    name: str, cache_dir: str, openai_key: str, threads: int | None = None
) -> FastEmbedEmbedder | OpenAIEmbedder:
    spec = EMBEDDERS[name]
    if spec.hosted:
        if not openai_key:
            raise SystemExit(f"{name} needs OPENAI_API_KEY in .env")
        return OpenAIEmbedder(spec, openai_key)
    return FastEmbedEmbedder(spec.model, cache_dir, threads=threads)


def database_name(dataset: str, embedder: str) -> str:
    """bge-small keeps the original databases, so earlier runs' indexes stay valid."""
    suffix = "" if embedder == DEFAULT else "_" + embedder.replace("-", "_")
    return f"docpilot_bench_{dataset}{suffix}"


def size_embedding_column(session: Session, dimensions: int) -> None:
    """Make the (empty) chunks table hold vectors of this size, with its HNSW index rebuilt."""
    current = session.scalar(
        text(
            "SELECT atttypmod FROM pg_attribute "
            "WHERE attrelid = 'chunks'::regclass AND attname = 'embedding'"
        )
    )
    if current == dimensions:
        return
    session.execute(text("DROP INDEX IF EXISTS ix_chunks_embedding_hnsw"))
    session.execute(text(f"ALTER TABLE chunks ALTER COLUMN embedding TYPE vector({dimensions})"))
    session.execute(
        text(
            "CREATE INDEX ix_chunks_embedding_hnsw ON chunks "
            "USING hnsw (embedding vector_cosine_ops)"
        )
    )
    session.commit()
