"""Index files into the configured database, skipping any that are already there.

    python -m docpilot.seed demo/aurora_knowledge_base.pdf

The deploy job runs this after migrations to load the public demo's documents.
"""

import sys
from pathlib import Path

from sqlalchemy.orm import Session

from docpilot.config import get_settings
from docpilot.db import get_engine
from docpilot.embeddings import get_embedder
from docpilot.ingest import ingest_document


def main(argv: list[str] | None = None) -> int:
    paths = [Path(p) for p in (argv if argv is not None else sys.argv[1:])]
    if not paths:
        print(__doc__, file=sys.stderr)
        return 2
    settings, embedder = get_settings(), get_embedder()
    with Session(get_engine(), expire_on_commit=False) as session:
        for path in paths:
            result = ingest_document(session, embedder, settings, path.name, path.read_bytes())
            state = "already indexed" if result.duplicate else f"{result.chunk_count} chunks"
            print(f"{path.name}: {state}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
