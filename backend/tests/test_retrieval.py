import uuid
from types import SimpleNamespace

import pytest
from conftest import FakeEmbedder
from sqlalchemy.orm import Session

from docpilot.config import Settings
from docpilot.ingest import ingest_document
from docpilot.retrieval import RRF_K, fuse, search_chunks

SETTINGS = Settings(_env_file=None)
LIBRARY = {
    "refunds.txt": b"Refunds are allowed within 30 days of purchase with a receipt.",
    "shipping.txt": b"Standard shipping takes five business days; express takes two.",
    "warranty.txt": b"Hardware carries a two year warranty against manufacturing defects.",
    "sku.txt": b"Part SKU-4471 replaces the older bracket in every 2024 model.",
}


@pytest.fixture
def library(db_session: Session) -> dict[str, uuid.UUID]:
    embedder = FakeEmbedder()
    return {
        name: ingest_document(db_session, embedder, SETTINGS, name, data).document.id
        for name, data in LIBRARY.items()
    }


def names(hits: list) -> list[str]:
    return [hit.filename for hit in hits]


def test_keyword_search_matches_any_word_stemmed(
    db_session: Session, library: dict[str, uuid.UUID]
) -> None:
    # "refunded" stems to "refund"; "warranties" to "warranti"; "zebra" matches nothing.
    hits = search_chunks(
        db_session, FakeEmbedder(), "refunded warranties zebra", 10, method="keyword"
    )
    assert sorted(names(hits)) == ["refunds.txt", "warranty.txt"]


def test_keyword_search_finds_codes_and_survives_punctuation(
    db_session: Session, library: dict[str, uuid.UUID]
) -> None:
    hits = search_chunks(db_session, FakeEmbedder(), "where is sku-4471?", 10, method="keyword")
    assert names(hits) == ["sku.txt"]
    # tsquery operators, quotes and backslashes in a question are words, not syntax
    for query in ["it's | !refund & (days)", "C:\\path\\refund 'x'", "a:* <-> b"]:
        search_chunks(db_session, FakeEmbedder(), query, 10, method="keyword")


def test_keyword_search_with_only_stop_words_finds_nothing_but_hybrid_still_answers(
    db_session: Session, library: dict[str, uuid.UUID]
) -> None:
    assert search_chunks(db_session, FakeEmbedder(), "the of and", 5, method="keyword") == []
    assert len(search_chunks(db_session, FakeEmbedder(), "the of and", 3, method="hybrid")) == 3


def test_hybrid_respects_k_document_filter_and_reports_cosine_similarity(
    db_session: Session, library: dict[str, uuid.UUID]
) -> None:
    only = [library["shipping.txt"], library["warranty.txt"]]
    hits = search_chunks(db_session, FakeEmbedder(), "two year warranty", 1, only, method="hybrid")
    assert names(hits) == ["warranty.txt"]
    vector = search_chunks(db_session, FakeEmbedder(), "two year warranty", 1, only)
    assert hits[0].score == vector[0].score  # the score shown is always similarity

    filtered = search_chunks(db_session, FakeEmbedder(), "refund", 10, only, method="keyword")
    assert filtered == []


def test_unknown_method_is_rejected(db_session: Session) -> None:
    with pytest.raises(ValueError, match="Unknown retrieval method"):
        search_chunks(db_session, FakeEmbedder(), "x", 3, method="magic")  # type: ignore[arg-type]


def row(chunk_id: str) -> tuple[SimpleNamespace]:
    return (SimpleNamespace(id=chunk_id),)


def test_fuse_rewards_agreement_and_breaks_ties_by_the_first_list() -> None:
    by_meaning = [row("a"), row("b"), row("c")]
    by_words = [row("c"), row("d"), row("b")]
    fused = [r[0].id for r in fuse([by_meaning, by_words])]
    # c (1/63 + 1/61) and b (1/62 + 1/63), found by both, beat a lone first place (1/61)
    assert fused == ["c", "b", "a", "d"]
    assert [r[0].id for r in fuse([[row("x")], [row("y")]])] == ["x", "y"]
    assert RRF_K == 60
