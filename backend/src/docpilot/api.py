import uuid
from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from docpilot.chunking import UnsupportedFileError
from docpilot.config import Settings, get_settings
from docpilot.db import get_session
from docpilot.embeddings import Embedder, get_embedder
from docpilot.ingest import EmptyDocumentError, ingest_document, search_chunks
from docpilot.models import Chunk, Document
from docpilot.schemas import DocumentOut, IngestOut, SearchHitOut, SearchIn

router = APIRouter(prefix="/api")

SessionDep = Annotated[Session, Depends(get_session)]
EmbedderDep = Annotated[Embedder, Depends(get_embedder)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def _document_out(document: Document, chunk_count: int) -> DocumentOut:
    return DocumentOut(
        id=document.id,
        filename=document.filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        page_count=document.page_count,
        chunk_count=chunk_count,
        created_at=document.created_at,
    )


@router.post("/documents", response_model=IngestOut, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile,
    response: Response,
    session: SessionDep,
    embedder: EmbedderDep,
    settings: SettingsDep,
) -> IngestOut:
    limit = settings.max_upload_mb * 1024 * 1024
    data = file.file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE, f"File exceeds {settings.max_upload_mb} MB"
        )
    try:
        result = ingest_document(session, embedder, settings, file.filename or "upload", data)
    except UnsupportedFileError as exc:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(exc)) from exc
    except EmptyDocumentError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc

    if result.duplicate:
        response.status_code = status.HTTP_200_OK
    return IngestOut(
        document=_document_out(result.document, result.chunk_count), duplicate=result.duplicate
    )


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(session: SessionDep) -> list[DocumentOut]:
    rows = session.execute(
        select(Document, func.count(Chunk.id))
        .outerjoin(Chunk)
        .group_by(Document.id)
        .order_by(Document.created_at.desc())
    ).all()
    return [_document_out(document, count) for document, count in rows]


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: uuid.UUID, session: SessionDep) -> None:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    session.delete(document)
    session.commit()


@router.post("/search", response_model=list[SearchHitOut])
def search(body: SearchIn, session: SessionDep, embedder: EmbedderDep) -> list[SearchHitOut]:
    hits = search_chunks(session, embedder, body.query, body.k)
    return [SearchHitOut(**asdict(hit)) for hit in hits]
