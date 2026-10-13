from dataclasses import dataclass, field

from langchain_core.tools import BaseTool, tool
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from docpilot.embeddings import Embedder
from docpilot.ingest import SearchHit, search_chunks
from docpilot.models import Chunk, Document


@dataclass
class SourceBook:
    """Every passage the researcher has seen, numbered once for citations across the run."""

    hits: list[SearchHit] = field(default_factory=list)

    def number(self, hit: SearchHit) -> int:
        for i, seen in enumerate(self.hits, 1):
            if seen.chunk_id == hit.chunk_id:
                return i
        self.hits.append(hit)
        return len(self.hits)


def format_source(number: int, hit: SearchHit) -> str:
    page = f' page="{hit.page}"' if hit.page else ""
    return f'<source id="{number}" file="{hit.filename}"{page}>\n{hit.text}\n</source>'


def make_tools(
    session: Session,
    embedder: Embedder,
    book: SourceBook,
    k: int,
) -> list[BaseTool]:
    @tool
    def list_documents() -> str:
        """List the documents in the library with their page counts."""
        rows = session.execute(
            select(Document.filename, Document.page_count, func.count(Chunk.id))
            .outerjoin(Chunk)
            .group_by(Document.id)
            .order_by(Document.filename)
        ).all()
        if not rows:
            return "The library is empty."
        return "\n".join(
            f"- {name} ({pages} pages, {chunks} passages)"
            if pages
            else f"- {name} ({chunks} passages)"
            for name, pages, chunks in rows
        )

    @tool(parse_docstring=True)
    def search_library(query: str) -> str:
        """Find the passages most relevant to a query.

        Args:
            query: A short phrase about one topic, like "education discount". Long queries
                listing several topics return general passages and miss specific ones.
        """
        hits = search_chunks(session, embedder, query, k)
        if not hits:
            return "No passages found."
        return "\n\n".join(format_source(book.number(hit), hit) for hit in hits)

    return [list_documents, search_library]
