import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    page_count: int | None
    chunk_count: int
    created_at: datetime


class IngestOut(BaseModel):
    document: DocumentOut
    duplicate: bool


class SearchIn(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    k: int = Field(default=5, ge=1, le=20)


class SearchHitOut(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    filename: str
    page: int | None
    text: str
    score: float
