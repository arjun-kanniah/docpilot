"""Run the evaluation set against DocPilot.

    python -m docpilot.evaluation retrieval [--min-hit-rate 0.9]   # free, no API keys
    python -m docpilot.evaluation answers [--provider P] [--model M]  # paid: answers + grading
    python -m docpilot.evaluation agent [--provider P] [--model M]    # paid: Research mode tasks

Uses its own database (docpilot_eval), re-indexed from the demo corpus on every run.
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from docpilot.config import Settings, get_settings
from docpilot.dbsetup import BACKEND_DIR, prepare_database
from docpilot.embeddings import get_embedder
from docpilot.evaluation.agent import (
    AgentCase,
    RunFn,
    agent_case_line,
    agent_summary_lines,
    load_agent_tasks,
    model_run,
    null_run,
    oracle_run,
    run_and_grade,
    summarize_agent,
    write_agent_report,
)
from docpilot.evaluation.grader import DEFAULT_GRADER_MODEL, ClaudeGrader
from docpilot.evaluation.report import case_line, summarize, summary_lines, write_report
from docpilot.evaluation.runner import (
    AnswerFn,
    answer_and_grade,
    index_corpus,
    load_eval_set,
    model_answer,
    null_answer,
    oracle_answer,
    retrieve,
)
from docpilot.llm.providers import LLMConfigError, get_llm_registry

RUNS_DIR = BACKEND_DIR.parent / "eval-runs"


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m docpilot.evaluation", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    retrieval = sub.add_parser("retrieval", help="score retrieval only (free)")
    retrieval.add_argument(
        "--min-hit-rate", type=float, default=0.0, help="exit 1 below this hit rate (for CI)"
    )

    answers = sub.add_parser("answers", help="answer each question and grade it (paid)")
    answers.add_argument("--provider", help="LLM provider (default: DOCPILOT_LLM_PROVIDER)")
    answers.add_argument("--model", help="model to answer with (default: provider default)")
    answers.add_argument("--grader-model", default=DEFAULT_GRADER_MODEL)
    answers.add_argument(
        "--answers-from",
        choices=["model", "oracle", "null"],
        default="model",
        help="oracle/null feed reference answers or 'I don't know' to check the grader",
    )
    answers.add_argument("--workers", type=int, default=4, help="questions run in parallel")
    answers.add_argument("--only", help="comma-separated question ids, e.g. q01,q20")

    for p in (retrieval, answers):
        p.add_argument("--k", type=int, help="passages retrieved (default: DOCPILOT_ANSWER_TOP_K)")

    agent = sub.add_parser("agent", help="run the Research mode tasks and grade them (paid)")
    agent.add_argument("--provider", help="LLM provider (default: DOCPILOT_LLM_PROVIDER)")
    agent.add_argument("--model", help="model for every agent step (default: provider default)")
    agent.add_argument("--grader-model", default=DEFAULT_GRADER_MODEL)
    agent.add_argument(
        "--answers-from",
        choices=["model", "oracle", "null"],
        default="model",
        help="oracle/null feed reference answers or a refusal to check the grader",
    )
    agent.add_argument("--workers", type=int, default=2, help="tasks run in parallel")
    agent.add_argument("--only", help="comma-separated task ids, e.g. r02,r07")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING)
    args = parse_args(argv)
    settings = get_settings()
    if args.command == "agent":
        return run_agent_eval(args, settings)
    k = args.k or settings.answer_top_k
    items = load_eval_set()
    if getattr(args, "only", None):
        wanted = set(args.only.split(","))
        items = [item for item in items if item.id in wanted]

    engine = create_engine(prepare_database("docpilot_eval"))
    embedder = get_embedder()
    with Session(engine, expire_on_commit=False) as session:
        chunks = index_corpus(session, embedder, settings)
        cases = retrieve(session, embedder, items, k)
    engine.dispose()
    setup = (
        f"{len(items)} questions over {chunks} chunks; embeddings {settings.embedding_model}; "
        f"chunks {settings.chunk_max_chars} chars with {settings.chunk_overlap_chars} overlap; "
        f"top {k}."
    )
    print(setup)

    if args.command == "retrieval":
        for case in cases:
            print(case_line(case))
        summary = summarize(cases)
        print("\n".join(summary_lines(summary, k)))
        hit_rate = summary.retrieval_hit_rate
        if hit_rate is not None and hit_rate < args.min_hit_rate:
            print(f"FAIL: hit rate below {args.min_hit_rate:.0%}", file=sys.stderr)
            return 1
        return 0

    key = settings.anthropic_api_key.get_secret_value()
    if not key:
        print("The grader uses Claude: set ANTHROPIC_API_KEY.", file=sys.stderr)
        return 2
    grader = ClaudeGrader(key, args.grader_model)

    answer: AnswerFn
    if args.answers_from == "model":
        try:
            choice = get_llm_registry().resolve(args.provider, args.model)
        except LLMConfigError as exc:
            print(exc, file=sys.stderr)
            return 2
        answer = model_answer(choice, settings.answer_max_tokens)
        label, answer_model = f"{choice.provider}-{choice.model}", choice.model
    else:
        answer = oracle_answer if args.answers_from == "oracle" else null_answer
        label, answer_model = f"grader-check-{args.answers_from}", None

    print(f"Answering with {label}, grading with {grader.model}…")
    answer_and_grade(
        cases, answer, grader, workers=args.workers, on_done=lambda c: print(case_line(c))
    )
    cases.sort(key=lambda c: c.item.id)
    summary = summarize(cases, answer_model, grader.model)
    print()
    print("\n".join(summary_lines(summary, k)))

    out_dir: Path = RUNS_DIR / f"{datetime.now():%Y%m%d-%H%M%S}-{label}"
    write_report(
        out_dir,
        cases,
        summary,
        title=f"Evaluation: {label}",
        k=k,
        settings_note=f"{setup} Graded by {grader.model}.",
    )
    print(f"\nReport: {out_dir.relative_to(BACKEND_DIR.parent)}/report.md")
    return 1 if summary.errors else 0


def run_agent_eval(args: argparse.Namespace, settings: Settings) -> int:
    tasks = load_agent_tasks()
    if args.only:
        wanted = set(args.only.split(","))
        tasks = [t for t in tasks if t.id in wanted]

    key = settings.anthropic_api_key.get_secret_value()
    if not key:
        print("The grader uses Claude: set ANTHROPIC_API_KEY.", file=sys.stderr)
        return 2
    grader = ClaudeGrader(key, args.grader_model)

    engine = create_engine(prepare_database("docpilot_eval"))
    embedder = get_embedder()
    with Session(engine, expire_on_commit=False) as session:
        chunks = index_corpus(session, embedder, settings)

    run: RunFn
    if args.answers_from == "model":
        try:
            choice = get_llm_registry().resolve(args.provider, args.model)
        except LLMConfigError as exc:
            print(exc, file=sys.stderr)
            return 2
        run = model_run(choice.provider, choice.model, settings, engine, embedder)
        label, model = f"agent-{choice.provider}-{choice.model}", choice.model
    else:
        run = oracle_run if args.answers_from == "oracle" else null_run
        label, model = f"agent-grader-check-{args.answers_from}", None

    note = (
        f"{len(tasks)} research tasks over {chunks} chunks; up to {settings.agent_max_rounds} "
        f"rounds of {settings.agent_max_tool_calls} tool calls, {settings.agent_search_k} "
        f"passages per search. Graded by {grader.model}."
    )
    print(note)
    print(f"Running with {label}…")
    cases = [AgentCase(task) for task in tasks]
    run_and_grade(
        cases, run, grader, workers=args.workers, on_done=lambda c: print(agent_case_line(c))
    )
    engine.dispose()
    summary = summarize_agent(cases, model, grader.model)
    print()
    print("\n".join(agent_summary_lines(summary)))

    out_dir: Path = RUNS_DIR / f"{datetime.now():%Y%m%d-%H%M%S}-{label}"
    write_agent_report(
        out_dir, cases, summary, title=f"Research mode evaluation: {label}", note=note
    )
    print(f"\nReport: {out_dir.relative_to(BACKEND_DIR.parent)}/report.md")
    return 1 if summary.errors else 0


if __name__ == "__main__":
    sys.exit(main())
