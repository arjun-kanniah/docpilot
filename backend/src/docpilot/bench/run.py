"""Index a BEIR dataset with DocPilot's own chunking and embeddings, run its test queries
through the app's retrieval code, and score the ranked documents."""

import hashlib
import time
import uuid
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from itertools import islice
from types import SimpleNamespace
from typing import cast

from sqlalchemy import func, insert, select, text
from sqlalchemy.orm import Session

from docpilot.bench.bm25 import Bm25Chunks
from docpilot.bench.datasets import CorpusDoc, Dataset
from docpilot.bench.metrics import ndcg_at_k, percentile, recall_at_k, reciprocal_rank
from docpilot.chunking import split_text
from docpilot.embeddings import Embedder
from docpilot.models import Chunk, Document
from docpilot.reranking import Reranker
from docpilot.retrieval import Method, SearchHit, fuse, rerank, search_chunks

# vector, keyword and hybrid are the app's own retrieval methods. bm25 is a reference ranking
# for the keyword experiment (bench/bm25.py), and hybrid_bm25 merges it with vector search the
# same way hybrid does, to show what a BM25 ranking inside Postgres would be worth.
PIPELINES = ("vector", "keyword", "hybrid", "bm25", "hybrid_bm25")


@dataclass(frozen=True)
class IndexStats:
    documents: int
    chunks: int
    seconds: float


@dataclass(frozen=True)
class QueryResult:
    query_id: str
    ranked: list[str]  # document ids, best first, no repeats
    seconds: float


@dataclass
class Summary:
    queries: int
    ndcg_at_10: float
    recall_at_20: float
    recall_at_50: float
    recall_at_100: float
    mrr_at_10: float
    p50_ms: float
    p95_ms: float
    per_query: dict[str, float] = field(default_factory=dict)  # nDCG@10, to compare runs


def _batches[T](items: Iterable[T], size: int) -> Iterator[list[T]]:
    iterator = iter(items)
    while batch := list(islice(iterator, size)):
        yield batch


def indexed_count(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Document)) or 0


def index_corpus(
    session: Session,
    embedder: Embedder,
    docs: Iterable[CorpusDoc],
    *,
    max_chars: int,
    overlap: int,
    batch_size: int = 256,
    progress: Callable[[int], None] = lambda done: None,
) -> IndexStats:
    """Store every document and its chunks, embedded in batches. Expects an empty database."""
    started = time.perf_counter()
    documents = chunks = 0
    for batch in _batches(docs, batch_size):
        doc_rows, chunk_rows, texts = [], [], []
        for doc in batch:
            doc_uuid = uuid.uuid4()
            content = doc.content
            doc_rows.append(
                {
                    "id": doc_uuid,
                    "filename": doc.id[:255],
                    "content_type": "text/plain",
                    "sha256": hashlib.sha256(doc.id.encode()).hexdigest(),
                    "size_bytes": len(content.encode()),
                    "page_count": None,
                }
            )
            for ordinal, piece in enumerate(split_text(content, max_chars, overlap)):
                chunk_rows.append(
                    {"id": uuid.uuid4(), "document_id": doc_uuid, "ordinal": ordinal, "page": None}
                )
                texts.append(piece)
        for row, piece, vector in zip(
            chunk_rows, texts, embedder.embed_passages(texts), strict=True
        ):
            row["text"] = piece
            row["embedding"] = vector
        session.execute(insert(Document), doc_rows)
        if chunk_rows:
            session.execute(insert(Chunk), chunk_rows)
        session.commit()
        documents += len(doc_rows)
        chunks += len(chunk_rows)
        progress(documents)
    return IndexStats(documents, chunks, time.perf_counter() - started)


def document_ids(session: Session) -> dict[uuid.UUID, str]:
    """Database id -> the dataset's own document id."""
    rows = session.execute(select(Document.id, Document.filename))
    return {doc_id: name for doc_id, name in rows}


def run_queries(
    session: Session,
    embedder: Embedder,
    queries: dict[str, str],
    ids: dict[uuid.UUID, str],
    *,
    pipeline: str = "vector",
    chunk_k: int = 150,
    ef_search: int = 200,
    reranker: Reranker | None = None,
    rerank_k: int = 50,
    exact: bool = False,
    warmup: int = 5,
) -> list[QueryResult]:
    """Run each query through the app's search and rank documents by their best chunk.

    pgvector's HNSW scan returns at most `hnsw.ef_search` rows (40 by default), so it is raised
    above `chunk_k` here; the app asks for only 6 passages, well inside the default. Hybrid
    takes `chunk_k` passages from each list before merging (the app takes 40). A reranker
    reorders the top `rerank_k` chunks and leaves the rest after them, as the app does.
    """
    if pipeline not in PIPELINES:
        raise ValueError(f"Unknown pipeline {pipeline!r}; choose from {', '.join(PIPELINES)}")
    session.execute(text(f"SET hnsw.ef_search = {int(ef_search)}"))
    if exact:  # compare every chunk instead of using the HNSW index: slower, never misses
        session.execute(text("SET enable_indexscan = off"))

    chunk_hits: Callable[[str], list[SearchHit]]
    if pipeline in ("bm25", "hybrid_bm25"):
        bm25 = Bm25Chunks(session)

    if pipeline == "bm25":

        def chunk_hits(query: str) -> list[SearchHit]:
            return bm25.search(query, chunk_k)
    elif pipeline == "hybrid_bm25":

        def chunk_hits(query: str) -> list[SearchHit]:
            lists = [search_chunks(session, embedder, query, chunk_k), bm25.search(query, chunk_k)]
            wrapped = [[(SimpleNamespace(id=h.chunk_id), h) for h in hits] for hits in lists]
            return [hit for _, hit in fuse(wrapped)[:chunk_k]]
    else:
        method = cast(Method, pipeline)

        def chunk_hits(query: str) -> list[SearchHit]:
            return search_chunks(
                session, embedder, query, chunk_k, method=method, candidates=chunk_k
            )

    def search(query: str) -> list[str]:
        hits = chunk_hits(query)
        if reranker is not None:
            hits = rerank(reranker, query, hits, rerank_k)
        ranked: list[str] = []
        for hit in hits:
            doc = ids[hit.document_id]
            if doc not in ranked:
                ranked.append(doc)
        return ranked

    for query in islice(queries.values(), warmup):  # load the model and warm the caches
        search(query)

    results = []
    for query_id, query in queries.items():
        started = time.perf_counter()
        ranked = search(query)
        results.append(QueryResult(query_id, ranked, time.perf_counter() - started))
    return results


def summarize(results: Sequence[QueryResult], qrels: dict[str, dict[str, int]]) -> Summary:
    def mean(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    ndcg = {r.query_id: ndcg_at_k(r.ranked, qrels[r.query_id], 10) for r in results}
    latencies = [r.seconds * 1000 for r in results]
    return Summary(
        queries=len(results),
        ndcg_at_10=mean(list(ndcg.values())),
        recall_at_20=mean([recall_at_k(r.ranked, qrels[r.query_id], 20) for r in results]),
        recall_at_50=mean([recall_at_k(r.ranked, qrels[r.query_id], 50) for r in results]),
        recall_at_100=mean([recall_at_k(r.ranked, qrels[r.query_id], 100) for r in results]),
        mrr_at_10=mean([reciprocal_rank(r.ranked, qrels[r.query_id], 10) for r in results]),
        p50_ms=percentile(latencies, 50),
        p95_ms=percentile(latencies, 95),
        per_query=ndcg,
    )


def check_dataset(dataset: Dataset, ids: dict[uuid.UUID, str]) -> list[str]:
    """Warnings for judged documents missing from the index (a broken load would show here)."""
    indexed = set(ids.values())
    judged = {doc for docs in dataset.qrels.values() for doc in docs}
    missing = judged - indexed
    return [f"{len(missing)} of {len(judged)} judged documents are not indexed"] if missing else []
