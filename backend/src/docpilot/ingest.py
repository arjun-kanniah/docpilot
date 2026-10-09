import hashlib
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from docpilot.chunking import chunk_pages, content_type_for, extract_pages
from docpilot.config import Settings
from docpilot.embeddings import Embedder
from docpilot.models import Chunk, Document


class EmptyDocumentError(ValueError):
    pass


@dataclass(frozen=True)
class IngestResult:
    document: Document
    chunk_count: int
    duplicate: bool


@dataclass(frozen=True)
class SearchHit:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    page: int | None
    text: str
    score: float


def ingest_document(
    session: Session, embedder: Embedder, settings: Settings, filename: str, data: bytes
) -> IngestResult:
    """Extract, chunk, embed and store a document. Re-uploading identical bytes is a no-op."""
    content_type = content_type_for(filename)
    sha256 = hashlib.sha256(data).hexdigest()

    existing = session.scalar(select(Document).where(Document.sha256 == sha256))
    if existing is not None:
        return IngestResult(existing, _chunk_count(session, existing.id), duplicate=True)

    pages = extract_pages(content_type, data)
    chunks = chunk_pages(pages, settings.chunk_max_chars, settings.chunk_overlap_chars)
    if not chunks:
        raise EmptyDocumentError(
            "No text could be extracted. Scanned PDFs need OCR, which isn't supported yet."
        )

    vectors = embedder.embed_passages([c.text for c in chunks])
    document = Document(
        filename=filename,
        content_type=content_type,
        sha256=sha256,
        size_bytes=len(data),
        page_count=len(pages) if content_type == "application/pdf" else None,
    )
    document.chunks = [
        Chunk(ordinal=i, page=c.page, text=c.text, embedding=v)
        for i, (c, v) in enumerate(zip(chunks, vectors, strict=True))
    ]
    session.add(document)
    session.commit()
    return IngestResult(document, len(chunks), duplicate=False)


def search_chunks(session: Session, embedder: Embedder, query: str, k: int) -> list[SearchHit]:
    """Nearest chunks by cosine similarity (1.0 = identical direction)."""
    distance = Chunk.embedding.cosine_distance(embedder.embed_query(query))
    rows = session.execute(
        select(Chunk, Document.filename, distance.label("distance"))
        .join(Document)
        .order_by(distance)
        .limit(k)
    ).all()
    return [
        SearchHit(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            filename=filename,
            page=chunk.page,
            text=chunk.text,
            score=round(1 - dist, 4),
        )
        for chunk, filename, dist in rows
    ]


def _chunk_count(session: Session, document_id: uuid.UUID) -> int:
    query = select(func.count()).select_from(Chunk).where(Chunk.document_id == document_id)
    return session.scalar(query) or 0
