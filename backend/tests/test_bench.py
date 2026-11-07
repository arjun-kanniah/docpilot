import json
import math
from pathlib import Path
from types import SimpleNamespace

import pytest
from conftest import FakeEmbedder
from sqlalchemy.orm import Session

from docpilot.bench.compare import compare
from docpilot.bench.datasets import CorpusDoc, load
from docpilot.bench.metrics import ndcg_at_k, percentile, recall_at_k, reciprocal_rank
from docpilot.bench.run import (
    check_dataset,
    document_ids,
    index_corpus,
    indexed_count,
    run_queries,
    summarize,
)

# --- Metrics ------------------------------------------------------------------------------


def test_ndcg_is_one_for_the_ideal_order_and_lower_otherwise() -> None:
    judged = {"a": 2, "b": 1}
    assert ndcg_at_k(["a", "b", "x"], judged, 10) == pytest.approx(1.0)
    # b first, a second: (1 + 2/log2(3)) / (2 + 1/log2(3))
    expected = (1 + 2 / math.log2(3)) / (2 + 1 / math.log2(3))
    assert ndcg_at_k(["b", "a"], judged, 10) == pytest.approx(expected)
    assert ndcg_at_k(["x", "y"], judged, 10) == 0.0


def test_ndcg_only_counts_the_top_k() -> None:
    assert ndcg_at_k(["x", "a"], {"a": 1}, 1) == 0.0


def test_recall_and_reciprocal_rank() -> None:
    judged = {"a": 1, "b": 1, "c": 0}  # a zero score is judged not relevant
    assert recall_at_k(["a", "x", "b"], judged, 2) == 0.5
    assert recall_at_k(["a", "x", "b"], judged, 3) == 1.0
    assert reciprocal_rank(["x", "c", "b"], judged) == pytest.approx(1 / 3)
    assert reciprocal_rank(["x"], judged) == 0.0


def test_percentile_interpolates_like_numpy() -> None:
    assert percentile([1, 2, 3, 4], 50) == 2.5
    assert percentile([10, 20, 30, 40, 50], 95) == pytest.approx(48.0)
    assert percentile([], 50) == 0.0


# --- Reading a dataset --------------------------------------------------------------------


def write_dataset(folder: Path) -> Path:
    (folder / "qrels").mkdir(parents=True)
    corpus = [
        {"_id": "d1", "title": "Refund policy", "text": "Refunds are allowed within 30 days."},
        {"_id": "d2", "title": "", "text": "Shipping takes five business days."},
        {"_id": "d3", "title": "Warranty", "text": "Hardware has a two year warranty."},
    ]
    queries = [
        {"_id": "q1", "text": "how many days for refunds"},
        {"_id": "q2", "text": "warranty length for hardware"},
        {"_id": "q9", "text": "a training query with no test judgments"},
    ]
    (folder / "corpus.jsonl").write_text("\n".join(json.dumps(d) for d in corpus) + "\n")
    (folder / "queries.jsonl").write_text("\n".join(json.dumps(q) for q in queries) + "\n")
    (folder / "qrels" / "test.tsv").write_text("query-id\tcorpus-id\tscore\nq1\td1\t1\nq2\td3\t2\n")
    return folder


def test_load_keeps_only_judged_test_queries(tmp_path: Path) -> None:
    dataset = load("tiny", write_dataset(tmp_path))
    assert dataset.queries == {
        "q1": "how many days for refunds",
        "q2": "warranty length for hardware",
    }
    assert dataset.qrels == {"q1": {"d1": 1}, "q2": {"d3": 2}}
    docs = list(dataset.corpus())
    assert [d.id for d in docs] == ["d1", "d2", "d3"]
    assert docs[0].content == "Refund policy\n\nRefunds are allowed within 30 days."
    assert docs[1].content == "Shipping takes five business days."  # no empty title line


# --- Indexing and running, through the app's own search ---------------------------------


def test_index_run_and_score_end_to_end(tmp_path: Path, db_session: Session) -> None:
    dataset = load("tiny", write_dataset(tmp_path))
    stats = index_corpus(
        db_session, FakeEmbedder(), dataset.corpus(), max_chars=1000, overlap=150, batch_size=2
    )
    assert (stats.documents, stats.chunks) == (3, 3)
    assert indexed_count(db_session) == 3

    ids = document_ids(db_session)
    assert check_dataset(dataset, ids) == []
    results = run_queries(db_session, FakeEmbedder(), dataset.queries, ids, chunk_k=10, warmup=1)
    by_query = {r.query_id: r.ranked for r in results}
    assert by_query["q1"][0] == "d1"
    assert by_query["q2"][0] == "d3"
    assert all(len(set(r.ranked)) == len(r.ranked) for r in results)  # each document once

    summary = summarize(results, dataset.qrels)
    assert summary.queries == 2
    assert summary.ndcg_at_10 == pytest.approx(1.0)
    assert summary.recall_at_20 == 1.0
    assert summary.p95_ms >= summary.p50_ms >= 0


def test_check_dataset_reports_missing_judged_documents(
    tmp_path: Path, db_session: Session
) -> None:
    dataset = load("tiny", write_dataset(tmp_path))
    index_corpus(
        db_session,
        FakeEmbedder(),
        [CorpusDoc("d1", "", "Only one document")],
        max_chars=1000,
        overlap=150,
    )
    assert check_dataset(dataset, document_ids(db_session)) == [
        "1 of 2 judged documents are not indexed"
    ]


@pytest.mark.parametrize("pipeline", ["keyword", "hybrid", "bm25", "hybrid_bm25"])
def test_every_pipeline_ranks_the_right_document_first(
    pipeline: str, tmp_path: Path, db_session: Session
) -> None:
    dataset = load("tiny", write_dataset(tmp_path))
    index_corpus(db_session, FakeEmbedder(), dataset.corpus(), max_chars=1000, overlap=150)
    ids = document_ids(db_session)
    results = run_queries(
        db_session, FakeEmbedder(), dataset.queries, ids, pipeline=pipeline, warmup=0
    )
    assert {r.query_id: r.ranked[0] for r in results} == {"q1": "d1", "q2": "d3"}


def test_run_queries_rejects_unknown_pipelines(db_session: Session) -> None:
    with pytest.raises(ValueError, match="Unknown pipeline"):
        run_queries(db_session, FakeEmbedder(), {}, {}, pipeline="magic")


def test_compare_finds_a_consistent_gain_and_not_noise() -> None:
    baseline = {f"q{i}": 0.5 for i in range(100)}
    gain = {q: v + 0.1 for q, v in baseline.items()}
    c = compare(baseline, gain)
    assert c.difference == pytest.approx(0.1)
    assert c.low > 0 and c.p_value < 0.01 and (c.better, c.worse) == (100, 0)

    noise = {q: v + (0.1 if i % 2 else -0.1) for i, (q, v) in enumerate(baseline.items())}
    c = compare(baseline, noise)
    assert c.low < 0 < c.high and c.p_value > 0.5

    subset = compare(baseline, {"q0": 1.0, "q1": 0.5})  # a --limit run
    assert (subset.queries, subset.baseline, subset.difference) == (2, 0.5, 0.25)
    with pytest.raises(ValueError, match="the baseline didn't"):
        compare(baseline, {"other": 1.0})


def test_each_embedder_gets_its_own_database_and_bge_small_keeps_the_original() -> None:
    from docpilot.bench.embedders import EMBEDDERS, database_name

    assert database_name("fiqa", "bge-small") == "docpilot_bench_fiqa"
    assert database_name("fiqa", "openai-large") == "docpilot_bench_fiqa_openai_large"
    assert all(spec.dimensions <= 2000 for spec in EMBEDDERS.values())  # HNSW's limit


def test_openai_embedder_batches_keeps_order_and_counts_cost() -> None:
    from docpilot.bench.embedders import EMBEDDERS, OpenAIEmbedder

    calls: list[int] = []

    def create(model: str, input: list[str], dimensions: int) -> SimpleNamespace:
        calls.append(len(input))
        data = [SimpleNamespace(index=i, embedding=[float(len(t))]) for i, t in enumerate(input)]
        return SimpleNamespace(data=data[::-1], usage=SimpleNamespace(total_tokens=10 * len(input)))

    embedder = OpenAIEmbedder.__new__(OpenAIEmbedder)
    embedder.spec, embedder.tokens = EMBEDDERS["openai-small"], 0
    embedder._client = SimpleNamespace(embeddings=SimpleNamespace(create=create))
    texts = ["a" * (i % 7) for i in range(OpenAIEmbedder.BATCH + 3)]
    assert embedder.embed_passages(texts) == [[float(len(t))] for t in texts]
    assert calls == [OpenAIEmbedder.BATCH, 3]
    assert embedder.tokens == 10 * len(texts)
    assert embedder.usd == pytest.approx(embedder.tokens / 1e6 * 0.02)
