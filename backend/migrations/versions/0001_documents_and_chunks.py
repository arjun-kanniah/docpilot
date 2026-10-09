"""Documents and embedded chunks.

Revision ID: 0001
Revises:
Create Date: 2026-10-09
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

EMBEDDING_DIM = 384  # BAAI/bge-small-en-v1.5


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False, unique=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "chunks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
    )
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])
    # Approximate nearest-neighbour index for cosine similarity search.
    op.create_index(
        "ix_chunks_embedding_hnsw",
        "chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_table("chunks")
    op.drop_table("documents")
