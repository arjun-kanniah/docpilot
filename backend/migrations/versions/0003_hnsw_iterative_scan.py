"""Require pgvector 0.8 or later, for iterative index scans in filtered vector search.

retrieval._vector_rows turns on hnsw.iterative_scan for searches limited to some documents
(docs/retrieval-experiments.md, E5). It is set per transaction because a managed database's
role may not be allowed to make it a database default (Neon refuses ALTER DATABASE ... SET
for it). This migration only checks that the setting exists, so a database with an older
pgvector fails here, before a deploy, rather than in the app's searches.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-07
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET LOCAL hnsw.iterative_scan = strict_order")


def downgrade() -> None:
    pass
