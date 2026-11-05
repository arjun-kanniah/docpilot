"""Finding the passages for a question: by meaning (embeddings), by words (Postgres full-text
search), or both merged with Reciprocal Rank Fusion; then, optionally, reordered by a
reranker. docs/retrieval-experiments.md has the measurements behind each choice."""

import uuid
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import Select, func, literal_column, select
from sqlalchemy.dialects.postgresql import TSQUERY
from sqlalchemy.orm import Session

from docpilot.config import get_settings
from docpilot.embeddings import Embedder
from docpilot.models import Chunk, Document
from docpilot.reranking import Reranker, get_reranker

Method = Literal["vector", "keyword", "hybrid"]
METHODS: tuple[Method, ...] = ("vector", "keyword", "hybrid")

# Reciprocal Rank Fusion: a passage scores 1 / (RRF_K + rank) in each list it appears in.
# 60 is the constant from the original paper (Cormack et al., 2009) and the common default.
RRF_K = 60
# Passages taken from each list before merging. Ranks past ~40 add under 0.01 to a score, and
# 40 is pgvector's default hnsw.ef_search, the most one HNSW scan returns.
HYBRID_CANDIDATES = 40


@dataclass(frozen=True)
class SearchHit:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    page: int | None
    text: str
    score: float  # cosine similarity to the question (1.0 = same direction), for every method


def search_chunks(
    session: Session,
    embedder: Embedder,
    query: str,
    k: int,
    document_ids: Collection[uuid.UUID] | None = None,
    *,
    method: Method = "vector",
    candidates: int = HYBRID_CANDIDATES,
) -> list[SearchHit]:
    """The k best passages for a query, optionally only from the given documents.

    `candidates` is how many passages hybrid search takes from each list before merging.
    """
    if method not in METHODS:
        raise ValueError(f"Unknown retrieval method {method!r}; choose from {', '.join(METHODS)}")
    vector = embedder.embed_query(query)
    if method == "vector":
        return _hits(_vector_rows(session, vector, k, document_ids))
    if method == "keyword":
        return _hits(_keyword_rows(session, query, vector, k, document_ids))

    depth = max(k, candidates)
    by_meaning = _vector_rows(session, vector, depth, document_ids)
    by_words = _keyword_rows(session, query, vector, depth, document_ids)
    return _hits(fuse([by_meaning, by_words])[:k])


def rerank(reranker: Reranker, query: str, hits: Sequence[SearchHit], top: int) -> list[SearchHit]:
    """The first `top` hits reordered by the reranker's scores, then the rest unchanged."""
    head, tail = list(hits[:top]), list(hits[top:])
    scores = reranker.scores(query, [hit.text for hit in head])
    order = sorted(range(len(head)), key=lambda i: -scores[i])  # stable: ties keep order
    return [head[i] for i in order] + tail


@dataclass(frozen=True)
class Retrieval:
    """How the app finds passages: a method, and optionally a reranker over the top candidates."""

    method: Method = "vector"
    reranker: Reranker | None = None
    rerank_candidates: int = 20  # passages the reranker reads; each costs a model pass

    def search(
        self,
        session: Session,
        embedder: Embedder,
        query: str,
        k: int,
        document_ids: Collection[uuid.UUID] | None = None,
    ) -> list[SearchHit]:
        if self.reranker is None:
            return search_chunks(session, embedder, query, k, document_ids, method=self.method)
        depth = max(k, self.rerank_candidates)
        pool = search_chunks(session, embedder, query, depth, document_ids, method=self.method)
        return rerank(self.reranker, query, pool, depth)[:k]


def get_retrieval() -> Retrieval:
    settings = get_settings()
    return Retrieval(settings.retrieval, get_reranker(), settings.rerank_candidates)


def fuse(ranked_lists: Sequence[Sequence[Any]]) -> list[Any]:
    """Merge ranked lists of (Chunk, ...) rows with Reciprocal Rank Fusion, best first.

    Ties keep the order of first appearance, so the first list wins them.
    """
    scores: dict[uuid.UUID, float] = {}
    rows: dict[uuid.UUID, Any] = {}
    for ranked in ranked_lists:
        for rank, row in enumerate(ranked, start=1):
            chunk_id = row[0].id
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1 / (RRF_K + rank)
            rows.setdefault(chunk_id, row)
    order = sorted(scores, key=lambda chunk_id: -scores[chunk_id])  # stable: ties keep order
    return [rows[chunk_id] for chunk_id in order]


def _base(vector: list[float], document_ids: Collection[uuid.UUID] | None) -> tuple[Select, Any]:
    distance = Chunk.embedding.cosine_distance(vector)
    statement = select(Chunk, Document.filename, distance.label("distance")).join(Document)
    if document_ids is not None:
        statement = statement.where(Chunk.document_id.in_(document_ids))
    return statement, distance


def _vector_rows(
    session: Session, vector: list[float], k: int, document_ids: Collection[uuid.UUID] | None
) -> Sequence[Any]:
    statement, distance = _base(vector, document_ids)
    return session.execute(statement.order_by(distance).limit(k)).all()


def any_word_query(query: str) -> Any:
    """A tsquery matching passages with any of the query's words, stemmed, minus stop words.

    Postgres's own parsers (plainto_tsquery, websearch_to_tsquery) require every word, which
    misses most passages for a question in plain language. Each lexeme is quoted, so
    punctuation in it can't be read as a tsquery operator. NULL when no words are left.
    """
    words = func.unnest(func.to_tsvector("english", query)).table_valued("lexeme")
    quoted = literal_column("'''' || replace(replace(lexeme, '\\', '\\\\'), '''', '''''') || ''''")
    return select(func.string_agg(quoted, " | ").cast(TSQUERY)).select_from(words).scalar_subquery()


def _keyword_rows(
    session: Session,
    query: str,
    vector: list[float],
    k: int,
    document_ids: Collection[uuid.UUID] | None,
) -> Sequence[Any]:
    statement, _ = _base(vector, document_ids)
    tsquery = any_word_query(query)
    rank = func.ts_rank(Chunk.text_search, tsquery)
    statement = statement.where(Chunk.text_search.op("@@")(tsquery))
    return session.execute(statement.order_by(rank.desc(), Chunk.id).limit(k)).all()


def _hits(rows: Sequence[Any]) -> list[SearchHit]:
    return [
        SearchHit(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            filename=filename,
            page=chunk.page,
            text=chunk.text,
            score=round(1 - distance, 4),
        )
        for chunk, filename, distance in rows
    ]
