import pytest

from docpilot.chunking import (
    Page,
    UnsupportedFileError,
    chunk_pages,
    content_type_for,
    split_text,
)


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("guide.pdf", "application/pdf"),
        ("README.MD", "text/markdown"),
        ("notes.txt", "text/plain"),
    ],
)
def test_content_type_for_supported_files(filename: str, expected: str) -> None:
    assert content_type_for(filename) == expected


@pytest.mark.parametrize("filename", ["report.docx", "noextension"])
def test_content_type_for_rejects_unsupported_files(filename: str) -> None:
    with pytest.raises(UnsupportedFileError):
        content_type_for(filename)


def test_short_text_is_a_single_chunk() -> None:
    assert split_text("One short paragraph.", max_chars=100, overlap=10) == ["One short paragraph."]


def test_blank_text_gives_no_chunks() -> None:
    assert split_text(" \n\n \t ", max_chars=100, overlap=10) == []


def test_chunks_respect_max_chars_and_keep_all_words() -> None:
    paragraphs = [f"Paragraph {i} " + "word " * 40 for i in range(10)]
    text = "\n\n".join(paragraphs)

    chunks = split_text(text, max_chars=300, overlap=50)

    assert len(chunks) > 1
    assert all(len(c) <= 300 for c in chunks)
    for i in range(10):
        assert any(f"Paragraph {i}" in c for c in chunks)


def test_consecutive_chunks_overlap() -> None:
    sentences = " ".join(f"Sentence number {i} ends here." for i in range(60))

    chunks = split_text(sentences, max_chars=200, overlap=60)

    assert len(chunks) > 2
    for previous, current in zip(chunks, chunks[1:], strict=False):
        assert previous[-20:].split()[-1] in current


def test_unbroken_text_is_hard_wrapped() -> None:
    chunks = split_text("x" * 450, max_chars=200, overlap=0)

    assert [len(c) for c in chunks] == [200, 200, 50]


def test_overlap_must_be_smaller_than_chunk() -> None:
    with pytest.raises(ValueError):
        split_text("text", max_chars=100, overlap=100)


def test_chunk_pages_keeps_page_numbers() -> None:
    pages = [Page(1, "First page text."), Page(2, "Second page text.")]

    chunks = chunk_pages(pages, max_chars=100, overlap=10)

    assert [(c.page, c.text) for c in chunks] == [
        (1, "First page text."),
        (2, "Second page text."),
    ]
