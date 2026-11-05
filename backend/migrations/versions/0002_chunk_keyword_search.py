"""Keyword search over chunks: a generated tsvector column and its GIN index.

The column is computed by Postgres from the chunk's text, so existing rows are filled in by the
migration itself (nothing is re-embedded) and the app never writes it.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-05
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE chunks ADD COLUMN text_search tsvector "
        "GENERATED ALWAYS AS (to_tsvector('english', text)) STORED"
    )
    op.create_index("ix_chunks_text_search", "chunks", ["text_search"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_index("ix_chunks_text_search", table_name="chunks")
    op.drop_column("chunks", "text_search")
