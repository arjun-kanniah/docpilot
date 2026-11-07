"""Filtered vector search returns k passages: pgvector's iterative index scan, on by default.

pgvector's HNSW index finds the nearest chunks first and applies a filter (a chat limited to
some documents) afterwards, from at most hnsw.ef_search (40) candidates. When the allowed
documents are a small share of the library, few or none of those 40 pass: on FiQA with 1% of
57,638 documents allowed, 69% of questions got no passages at all
(docs/retrieval-experiments.md, E5). An iterative scan keeps searching the index until it has
enough rows; strict_order keeps them in exact distance order. It needs pgvector 0.8.0 or later,
so a database without it fails this migration rather than the app's searches.

Set as the database's default, so every connection gets it at no per-query cost.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-07
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def _set_default(value: str) -> None:
    # ALTER DATABASE needs the database's name; a DO block reads it from the connection.
    op.execute(
        "DO $$ BEGIN EXECUTE format('ALTER DATABASE %I SET hnsw.iterative_scan = "
        f"{value}', current_database()); END $$"
    )


def upgrade() -> None:
    op.execute("SET hnsw.iterative_scan = strict_order")  # fails early on pgvector < 0.8
    _set_default("strict_order")


def downgrade() -> None:
    op.execute(
        "DO $$ BEGIN EXECUTE format('ALTER DATABASE %I RESET hnsw.iterative_scan', "
        "current_database()); END $$"
    )
