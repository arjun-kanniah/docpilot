"""The filter problem (E5): vector search limited to a few documents in a large library.

    python -m docpilot.bench.filters --dataset fiqa [--fractions 0.001 0.01 0.1] [--k 6]

A chat limited to some documents (and, later, a user allowed to read only some) searches with
a `document_id IN (...)` filter. pgvector's HNSW index finds the nearest chunks first and the
filter is applied afterwards, so when the allowed documents are a small share of the library,
the nearest `hnsw.ef_search` chunks (40 by default) may hold few or none of them. This runs
each test query against a fixed random subset of the library ("what this user may read") and
compares the app's own search under three settings with the exact answer:

- app: whatever the database defaults to, which is how the app runs (iterative since 0003)
- default: pgvector's own defaults (ef_search 40, no iterative scan), the app before 0003
- iterative: pgvector 0.8's iterative index scan, which keeps scanning until it has k rows
- exact: no index, every allowed chunk compared (the ground truth)

Postgres may also skip the HNSW index on its own for a narrow filter, so the plan used is
recorded too.
"""

import argparse
import json
import random
import sys
import time
import uuid
from datetime import datetime

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from docpilot.bench import datasets
from docpilot.bench.__main__ import RUNS_DIR, cpu_name, pin_to_cores
from docpilot.bench.metrics import percentile
from docpilot.config import get_settings
from docpilot.dbsetup import BACKEND_DIR, prepare_database
from docpilot.embeddings import FastEmbedEmbedder
from docpilot.models import Document
from docpilot.retrieval import _base, _vector_rows

SEED = 2026
MODES = {
    "app": [],  # the database's own defaults, as the app runs (migration 0003)
    "default": ["SET hnsw.ef_search = 40", "SET hnsw.iterative_scan = off"],
    "iterative": ["SET hnsw.ef_search = 40", "SET hnsw.iterative_scan = strict_order"],
    "exact": ["SET enable_indexscan = off"],
}


def configure(session: Session, mode: str) -> None:
    session.execute(text("RESET ALL"))
    for statement in MODES[mode]:
        session.execute(text(statement))


def uses_hnsw(session: Session, vector: list[float], k: int, ids: list[uuid.UUID] | None) -> bool:
    statement, distance = _base(vector, ids)
    compiled = (
        statement.order_by(distance)
        .limit(k)
        .compile(session.bind, compile_kwargs={"literal_binds": True})
    )
    plan = session.execute(text(f"EXPLAIN {compiled}")).scalars().all()
    return any("ix_chunks_embedding_hnsw" in line for line in plan)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m docpilot.bench.filters", description=__doc__)
    parser.add_argument("--dataset", choices=list(datasets.DATASETS), required=True)
    parser.add_argument("--fractions", type=float, nargs="+", default=[1.0, 0.1, 0.01, 0.001])
    parser.add_argument("--k", type=int, default=6, help="passages per question (the app: 6)")
    parser.add_argument("--limit", type=int, help="run only the first N test queries")
    args = parser.parse_args(argv)

    settings = get_settings()
    dataset = datasets.load(args.dataset)
    queries = list(dataset.queries.values())[: args.limit]
    engine = create_engine(prepare_database(f"docpilot_bench_{args.dataset}"))
    cores = pin_to_cores(1)
    embedder = FastEmbedEmbedder(settings.embedding_model, str(settings.model_cache_dir), 1)
    vectors = [embedder.embed_query(q) for q in queries]

    rows = []
    with Session(engine) as session:
        all_ids = sorted(session.scalars(select(Document.id)).all())
        for fraction in args.fractions:
            allowed = (
                None
                if fraction >= 1
                else random.Random(SEED).sample(all_ids, max(1, round(len(all_ids) * fraction)))
            )
            found: dict[str, list[list[uuid.UUID]]] = {}
            for mode in MODES:
                configure(session, mode)
                for vector in vectors[:5]:  # warm the caches
                    _vector_rows(session, vector, args.k, allowed)
                results, seconds = [], []
                for vector in vectors:
                    started = time.perf_counter()
                    hits = _vector_rows(session, vector, args.k, allowed)
                    seconds.append((time.perf_counter() - started) * 1000)
                    results.append([row[0].id for row in hits])
                found[mode] = results
                rows.append(
                    {
                        "fraction": fraction,
                        "documents_allowed": len(allowed) if allowed else len(all_ids),
                        "mode": mode,
                        "uses_hnsw": uses_hnsw(session, vectors[0], args.k, allowed),
                        "mean_returned": sum(map(len, results)) / len(results),
                        "short_queries": sum(len(r) < args.k for r in results) / len(results),
                        "empty_queries": sum(not r for r in results) / len(results),
                        "p50_ms": percentile(seconds, 50),
                        "p95_ms": percentile(seconds, 95),
                    }
                )
                session.rollback()
            exact = found["exact"]
            for row in rows[-len(MODES) :]:
                got = found[row["mode"]]
                overlaps = [
                    len(set(g) & set(e)) / len(e) for g, e in zip(got, exact, strict=True) if e
                ]
                row["recall_vs_exact"] = sum(overlaps) / len(overlaps) if overlaps else 1.0

    print(f"E5 filters on {args.dataset}, k = {args.k}, {len(queries)} queries, 1 core")
    print("allowed docs | mode      | HNSW | returned | short | empty | recall | p50 / p95 ms")
    for r in rows:
        hnsw = "yes" if r["uses_hnsw"] else "no"
        print(
            f"{r['documents_allowed']:>12} | {r['mode']:<9} | {hnsw:<4} "
            f"| {r['mean_returned']:>8.2f} | {r['short_queries']:>5.0%} "
            f"| {r['empty_queries']:>5.0%} | {r['recall_vs_exact']:>6.3f} "
            f"| {r['p50_ms']:.1f} / {r['p95_ms']:.1f}"
        )

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = RUNS_DIR / f"{stamp}-E5-filters-{args.dataset}.json"
    record = {
        "experiment": "E5",
        "pipeline": "filters",
        "dataset": args.dataset,
        "run_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "config": {"k": args.k, "seed": SEED, "modes": MODES, "query_cores": len(cores) or None},
        "machine": {"cpu": cpu_name(), "python": sys.version.split()[0]},
        "rows": rows,
    }
    out.write_text(json.dumps(record, indent=2))
    print(f"Saved {out.relative_to(BACKEND_DIR.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
