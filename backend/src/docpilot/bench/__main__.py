"""Benchmark DocPilot's retrieval on a public BEIR dataset (free: local models, local Postgres).

    python -m docpilot.bench --dataset nfcorpus [--pipeline vector] [--experiment E0]

The first run downloads the dataset and indexes it into its own database
(docpilot_bench_<dataset>); later runs reuse the index while the embedding model and chunking
are unchanged. Queries run on one CPU core, like the 1-vCPU Cloud Run instance, so latencies
are comparable with the demo's (which adds the network hop to its database).
"""

import argparse
import json
import os
import platform
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from docpilot import __version__
from docpilot.bench import datasets
from docpilot.bench.run import (
    PIPELINES,
    check_dataset,
    document_ids,
    index_corpus,
    indexed_count,
    run_queries,
    summarize,
)
from docpilot.config import get_settings
from docpilot.dbsetup import BACKEND_DIR, prepare_database
from docpilot.embeddings import FastEmbedEmbedder

RUNS_DIR = BACKEND_DIR.parent / "eval-runs" / "bench"


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m docpilot.bench", description=__doc__)
    parser.add_argument("--dataset", choices=list(datasets.DATASETS), required=True)
    parser.add_argument("--pipeline", choices=PIPELINES, default="vector")
    parser.add_argument("--experiment", default="adhoc", help="label for the log, e.g. E0")
    parser.add_argument("--limit", type=int, help="run only the first N test queries")
    parser.add_argument("--chunk-k", type=int, default=150, help="passages retrieved per query")
    parser.add_argument("--ef-search", type=int, default=200, help="pgvector hnsw.ef_search")
    parser.add_argument("--threads", type=int, default=1, help="CPU cores for the query phase")
    parser.add_argument("--reindex", action="store_true", help="rebuild the index first")
    return parser.parse_args(argv)


def cpu_name() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or platform.machine()


def pin_to_cores(count: int) -> list[int]:
    """Limit this process to `count` cores (Linux), so timings match a small instance."""
    if not hasattr(os, "sched_setaffinity"):
        return []
    cores = sorted(os.sched_getaffinity(0))[:count]
    os.sched_setaffinity(0, cores)
    return cores


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    settings = get_settings()
    dataset = datasets.load(args.dataset)
    queries = dict(list(dataset.queries.items())[: args.limit])
    print(f"{args.dataset}: {len(dataset.queries)} test queries ({len(queries)} to run)")

    index_config = {
        "embedding_model": settings.embedding_model,
        "chunk_max_chars": settings.chunk_max_chars,
        "chunk_overlap_chars": settings.chunk_overlap_chars,
    }
    marker = dataset.path / "index.json"
    engine = create_engine(prepare_database(f"docpilot_bench_{args.dataset}"))
    with Session(engine, expire_on_commit=False) as session:
        current = json.loads(marker.read_text()) if marker.exists() else None
        count = indexed_count(session)
        if args.reindex or current != {**index_config, "documents": count} or count == 0:
            session.execute(text("TRUNCATE documents CASCADE"))
            session.commit()
            print("Indexing (all cores)...", flush=True)
            embedder = FastEmbedEmbedder(settings.embedding_model, str(settings.model_cache_dir))
            stats = index_corpus(
                session,
                embedder,
                dataset.corpus(),
                max_chars=settings.chunk_max_chars,
                overlap=settings.chunk_overlap_chars,
                progress=lambda done: print(f"  {done} documents", end="\r", flush=True),
            )
            print(
                f"Indexed {stats.documents} documents as {stats.chunks} chunks "
                f"in {stats.seconds:.0f} s"
            )
            marker.write_text(json.dumps({**index_config, "documents": stats.documents}))
            del embedder

        ids = document_ids(session)
        for warning in check_dataset(dataset, ids):
            print(f"Warning: {warning}")
        chunk_count = session.scalar(text("SELECT count(*) FROM chunks"))
        index_mb = session.scalar(text("SELECT pg_total_relation_size('chunks') / 1048576.0"))

        cores = pin_to_cores(args.threads)
        embedder = FastEmbedEmbedder(
            settings.embedding_model, str(settings.model_cache_dir), threads=args.threads
        )
        print(f"Running {len(queries)} queries on {len(cores) or 'all'} core(s)...", flush=True)
        results = run_queries(
            session,
            embedder,
            queries,
            ids,
            pipeline=args.pipeline,
            chunk_k=args.chunk_k,
            ef_search=args.ef_search,
        )
    summary = summarize(results, dataset.qrels)

    print(
        f"{args.experiment} {args.pipeline} on {args.dataset}: "
        f"nDCG@10 {summary.ndcg_at_10:.3f} | R@20 {summary.recall_at_20:.3f} | "
        f"R@50 {summary.recall_at_50:.3f} | R@100 {summary.recall_at_100:.3f} | "
        f"MRR@10 {summary.mrr_at_10:.3f} | p50 {summary.p50_ms:.0f} ms | "
        f"p95 {summary.p95_ms:.0f} ms"
    )

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = RUNS_DIR / f"{stamp}-{args.experiment}-{args.pipeline}-{args.dataset}.json"
    record = {
        "experiment": args.experiment,
        "pipeline": args.pipeline,
        "dataset": args.dataset,
        "run_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "docpilot_version": __version__,
        "config": {
            **index_config,
            "chunk_k": args.chunk_k,
            "ef_search": args.ef_search,
            "query_cores": len(cores) or None,
        },
        "index": {"documents": len(ids), "chunks": chunk_count, "chunks_table_mb": float(index_mb)},
        "machine": {"cpu": cpu_name(), "python": sys.version.split()[0]},
        "summary": {k: v for k, v in asdict(summary).items() if k != "per_query"},
        "per_query_ndcg_at_10": summary.per_query,
    }
    out.write_text(json.dumps(record, indent=2))
    print(f"Saved {out.relative_to(BACKEND_DIR.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
