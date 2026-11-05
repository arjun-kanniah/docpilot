"""A BM25 reference for the keyword experiment (benchmark only, never used by the app).

Postgres's ts_rank counts how often and how close the query's words appear, but not how rare
they are, so a passage repeating "the treatment" can outrank one with a rare, specific term.
BM25 weighs each word by its rarity across the library. This ranks the same chunks with BM25
(Elasticsearch's defaults, k1 = 1.2 and b = 0.75, as in BEIR's published BM25 numbers) so the
log can report what Postgres's simpler ranking gives up.
"""

import uuid
from collections.abc import Sequence

import bm25s
from py_rust_stemmers import SnowballStemmer
from sqlalchemy import select
from sqlalchemy.orm import Session

from docpilot.models import Chunk
from docpilot.retrieval import SearchHit

_stemmer = SnowballStemmer("english")


def _tokenize(texts: Sequence[str]) -> list[list[str]]:
    return bm25s.tokenize(
        list(texts),
        stopwords="en",
        stemmer=_stemmer.stem_words,
        return_ids=False,
        show_progress=False,
    )


class Bm25Chunks:
    """Every chunk in the database, indexed in memory with BM25."""

    def __init__(self, session: Session) -> None:
        rows = session.execute(
            select(Chunk.id, Chunk.document_id, Chunk.text).order_by(Chunk.id)
        ).all()
        self.chunks: list[tuple[uuid.UUID, uuid.UUID, str]] = [tuple(row) for row in rows]
        self.model = bm25s.BM25(k1=1.2, b=0.75)
        self.model.index(_tokenize([chunk_text for _, _, chunk_text in rows]), show_progress=False)

    def search(self, query: str, k: int) -> list[SearchHit]:
        """The k best chunks that share a word with the query (score: BM25, not similarity)."""
        tokens = _tokenize([query])
        if not tokens[0]:
            return []
        k = min(k, len(self.chunks))
        positions, scores = self.model.retrieve(tokens, k=k, show_progress=False, n_threads=1)
        hits = []
        for i, score in zip(positions[0], scores[0], strict=True):
            if score > 0:
                chunk_id, document_id, chunk_text = self.chunks[int(i)]
                hits.append(SearchHit(chunk_id, document_id, "", None, chunk_text, float(score)))
        return hits
