import re
from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader

SUPPORTED_TYPES = {
    ".pdf": "application/pdf",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
}


class UnsupportedFileError(ValueError):
    pass


@dataclass(frozen=True)
class Page:
    number: int | None  # 1-based for PDFs; None for formats without pages
    text: str


@dataclass(frozen=True)
class TextChunk:
    page: int | None
    text: str


def content_type_for(filename: str) -> str:
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix not in SUPPORTED_TYPES:
        allowed = ", ".join(sorted(SUPPORTED_TYPES))
        raise UnsupportedFileError(f"Unsupported file type '{suffix or filename}'. Use {allowed}.")
    return SUPPORTED_TYPES[suffix]


def extract_pages(content_type: str, data: bytes) -> list[Page]:
    if content_type == "application/pdf":
        reader = PdfReader(BytesIO(data))
        return [Page(i, page.extract_text() or "") for i, page in enumerate(reader.pages, 1)]
    return [Page(None, data.decode("utf-8", errors="replace"))]


def split_text(text: str, max_chars: int, overlap: int) -> list[str]:
    """Split text into chunks of at most max_chars, preferring paragraph and sentence breaks.

    Consecutive chunks share up to `overlap` characters so that a sentence cut at a
    boundary is still retrievable from either side.
    """
    if overlap >= max_chars:
        raise ValueError("overlap must be smaller than max_chars")

    pieces = [p for p in (_normalise(p) for p in re.split(r"\n\s*\n", text)) if p]
    units: list[str] = []
    for piece in pieces:
        units.extend(_split_long(piece, max_chars))

    chunks: list[str] = []
    current = ""
    for unit in units:
        candidate = f"{current}\n\n{unit}" if current else unit
        if len(candidate) <= max_chars:
            current = candidate
            continue
        chunks.append(current)
        tail = _tail(current, overlap)
        current = f"{tail} {unit}" if tail and len(tail) + 1 + len(unit) <= max_chars else unit
    if current:
        chunks.append(current)
    return chunks


def chunk_pages(pages: list[Page], max_chars: int, overlap: int) -> list[TextChunk]:
    return [
        TextChunk(page.number, text)
        for page in pages
        for text in split_text(page.text, max_chars, overlap)
    ]


def _normalise(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()


def _split_long(text: str, max_chars: int) -> list[str]:
    """Break an over-long paragraph at sentence ends, then hard-wrap at word boundaries."""
    if len(text) <= max_chars:
        return [text]
    out: list[str] = []
    current = ""
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        while len(sentence) > max_chars:
            cut = sentence.rfind(" ", 0, max_chars)
            cut = cut if cut > 0 else max_chars
            if current:
                out.append(current)
                current = ""
            out.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()
        candidate = f"{current} {sentence}" if current else sentence
        if len(candidate) <= max_chars:
            current = candidate
        else:
            out.append(current)
            current = sentence
    if current:
        out.append(current)
    return out


def _tail(text: str, size: int) -> str:
    """Last `size` characters of text, trimmed forward to a word boundary."""
    if size <= 0 or len(text) <= size:
        return ""
    tail = text[-size:]
    space = tail.find(" ")
    return tail[space + 1 :] if space != -1 else tail
