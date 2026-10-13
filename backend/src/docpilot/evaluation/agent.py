"""Evaluation for Research mode: run each task through the agent graph and grade the answer.

Beyond the grader's verdict, each run is checked in code: did it find passages on every page
the answer needs, does the answer state the key figures, and what did it cost in rounds, tool
calls, tokens and time.
"""

import json
import re
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from statistics import median

from langchain_core.exceptions import ModelRateLimitError
from sqlalchemy import Engine

from docpilot.config import Settings
from docpilot.embeddings import Embedder
from docpilot.evaluation.grader import Grade
from docpilot.evaluation.report import cost_usd
from docpilot.evaluation.runner import DEMO_DIR, Grader
from docpilot.llm.base import Usage

AGENT_EVAL_SET = DEMO_DIR / "agent_eval_set.json"

_CITATION = re.compile(r"\[(\d+)\]")


@dataclass(frozen=True)
class AgentTask:
    id: str
    task: str
    reference: str
    evidence_pages: tuple[int, ...]
    key_figures: tuple[str, ...]
    category: str
    answerable: bool


def load_agent_tasks(path: Path = AGENT_EVAL_SET) -> list[AgentTask]:
    data = json.loads(path.read_text())
    return [
        AgentTask(
            id=item["id"],
            task=item["task"],
            reference=item["reference"],
            evidence_pages=tuple(item["evidence_pages"]),
            key_figures=tuple(item["key_figures"]),
            category=item["category"],
            answerable=item["answerable"],
        )
        for item in data["items"]
    ]


def _plain(text: str) -> str:
    return text.replace(",", "").replace("$", "")


def states_figure(answer: str, figure: str) -> bool:
    """Whether the answer states a figure: "98" matches "$98.00", not "1,980" or "98.50"."""
    pattern = rf"(?<![\d.]){re.escape(_plain(figure))}(?:\.0+)?(?!\d|\.\d)"
    return re.search(pattern, _plain(answer)) is not None


@dataclass
class AgentRun:
    """What a run produced, independent of how it was graded."""

    answer: str
    source_pages: list[int | None]  # page of each numbered source, in citation order
    rounds: int
    tool_calls: int
    usage: Usage


@dataclass
class AgentCase:
    task: AgentTask
    run: AgentRun | None = None
    latency_s: float | None = None
    grade: Grade | None = None
    grader_usage: Usage | None = None
    error: str | None = None
    cited: list[int] = field(default_factory=list)

    @property
    def found_evidence(self) -> bool | None:
        """Whether the run retrieved passages from every page the answer needs."""
        if self.run is None or not self.task.evidence_pages:
            return None
        return set(self.task.evidence_pages) <= set(self.run.source_pages)

    @property
    def cites_evidence(self) -> bool | None:
        """Whether the answer cites a passage from each evidence page."""
        if self.run is None or not self.task.evidence_pages:
            return None
        pages = self.run.source_pages
        cited = {pages[n - 1] for n in self.cited if 0 < n <= len(pages)}
        return set(self.task.evidence_pages) <= cited

    @property
    def missing_figures(self) -> list[str] | None:
        if self.run is None:
            return None
        return [f for f in self.task.key_figures if not states_figure(self.run.answer, f)]


RunFn = Callable[[AgentTask], AgentRun]


def oracle_run(task: AgentTask) -> AgentRun:
    """The reference answer itself, to check the grader."""
    return AgentRun(task.reference, [], 0, 0, Usage(0, 0))


def null_run(task: AgentTask) -> AgentRun:
    """Always decline: the grader should fail the answerable tasks and pass the negatives."""
    return AgentRun("The documents don't contain this information.", [], 0, 0, Usage(0, 0))


def run_and_grade(
    cases: Sequence[AgentCase],
    run: RunFn,
    grader: Grader,
    workers: int = 2,
    on_done: Callable[[AgentCase], None] | None = None,
    retries: int = 2,
    retry_wait_s: float = 60,
) -> None:
    """Fill in each case's run and grade. Failures are recorded on the case, not scored.

    A rate-limited run is retried after a pause; its time covers the successful attempt only.
    """

    def one(case: AgentCase) -> None:
        try:
            for attempt in range(retries + 1):
                started = time.perf_counter()
                try:
                    case.run = run(case.task)
                    break
                except ModelRateLimitError:  # free tiers allow a few requests a minute
                    if attempt == retries:
                        raise
                    time.sleep(retry_wait_s)
            case.latency_s = round(time.perf_counter() - started, 1)
            case.cited = [int(n) for n in _CITATION.findall(case.run.answer)]
            case.grade, case.grader_usage = grader.grade(
                question=case.task.task,
                answerable=case.task.answerable,
                reference=case.task.reference,
                answer=case.run.answer,
            )
        except Exception as exc:  # recorded per case so one failure doesn't sink the run
            case.error = f"{type(exc).__name__}: {exc}"
        if on_done:
            on_done(case)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(one, cases))


@dataclass(frozen=True)
class AgentSummary:
    cases: int
    errors: int
    answerable_graded: int
    correct: int
    partial: int
    incorrect: int
    negatives_graded: int
    declined_correctly: int
    found_evidence_rate: float | None
    cites_evidence_rate: float | None
    figures_stated: int
    figures_expected: int
    mean_rounds: float | None
    mean_tool_calls: float | None
    usage: Usage
    grader_usage: Usage
    cost_usd: float | None
    grader_cost_usd: float | None
    median_latency_s: float | None


def _rate(flags: Sequence[bool | None]) -> float | None:
    known = [f for f in flags if f is not None]
    return sum(known) / len(known) if known else None


def summarize_agent(
    cases: Sequence[AgentCase], model: str | None = None, grader_model: str | None = None
) -> AgentSummary:
    graded = [c for c in cases if c.grade]
    answerable = [c for c in graded if c.task.answerable]
    negatives = [c for c in graded if not c.task.answerable]
    runs = [c.run for c in cases if c.run is not None and c.error is None]
    verdicts = [c.grade.verdict for c in answerable if c.grade]

    def total(usages: Sequence[Usage | None]) -> Usage:
        real = [u for u in usages if u is not None]
        return Usage(sum(u.input_tokens for u in real), sum(u.output_tokens for u in real))

    usage = total([r.usage for r in runs])
    grader_usage = total([c.grader_usage for c in cases])
    latencies = [c.latency_s for c in cases if c.latency_s is not None and c.error is None]
    figures = [c for c in cases if c.run is not None and c.task.key_figures]
    return AgentSummary(
        cases=len(cases),
        errors=sum(c.error is not None for c in cases),
        answerable_graded=len(answerable),
        correct=verdicts.count("correct"),
        partial=verdicts.count("partial"),
        incorrect=verdicts.count("incorrect"),
        negatives_graded=len(negatives),
        declined_correctly=sum(bool(c.grade and c.grade.verdict == "correct") for c in negatives),
        found_evidence_rate=_rate([c.found_evidence for c in cases]),
        cites_evidence_rate=_rate([c.cites_evidence for c in cases]),
        figures_stated=sum(len(c.task.key_figures) - len(c.missing_figures or []) for c in figures),
        figures_expected=sum(len(c.task.key_figures) for c in figures),
        mean_rounds=sum(r.rounds for r in runs) / len(runs) if runs else None,
        mean_tool_calls=sum(r.tool_calls for r in runs) / len(runs) if runs else None,
        usage=usage,
        grader_usage=grader_usage,
        cost_usd=cost_usd(model, usage) if model else None,
        grader_cost_usd=cost_usd(grader_model, grader_usage) if grader_model else None,
        median_latency_s=median(latencies) if latencies else None,
    )


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.0%}"


def _usd(value: float | None) -> str:
    return "n/a" if value is None else f"${value:.3f}"


def agent_summary_lines(s: AgentSummary) -> list[str]:
    lines = [
        f"Answers: {s.correct} correct, {s.partial} partial, {s.incorrect} incorrect "
        f"of {s.answerable_graded}",
        f"Declined correctly: {s.declined_correctly} of {s.negatives_graded} tasks the document "
        "can't answer",
        f"Evidence: found every needed page in {_pct(s.found_evidence_rate)} of runs, cited it "
        f"in {_pct(s.cites_evidence_rate)}",
        f"Key figures stated: {s.figures_stated} of {s.figures_expected}",
    ]
    if s.mean_rounds is not None and s.mean_tool_calls is not None:
        lines.append(
            f"Effort: {s.mean_rounds:.1f} rounds and {s.mean_tool_calls:.1f} tool calls per task"
        )
    lines.append(
        f"Tokens: agent {s.usage.input_tokens:,} in / {s.usage.output_tokens:,} out "
        f"({_usd(s.cost_usd)}); grader {s.grader_usage.input_tokens:,} in / "
        f"{s.grader_usage.output_tokens:,} out ({_usd(s.grader_cost_usd)})"
    )
    if s.median_latency_s is not None:
        lines.append(f"Median time per task: {s.median_latency_s:.0f}s")
    if s.errors:
        lines.append(f"Errors (not scored): {s.errors}")
    return lines


def agent_case_line(case: AgentCase) -> str:
    if case.error:
        outcome = f"ERROR {case.error}"
    elif case.grade and case.run:
        notes = []
        if case.found_evidence is False:
            notes.append("missed evidence")
        if case.missing_figures:
            notes.append(f"missing {', '.join(case.missing_figures)}")
        effort = f"{case.run.rounds}r/{case.run.tool_calls}t"
        outcome = f"{case.grade.verdict} {effort}" + (f" ({'; '.join(notes)})" if notes else "")
    else:
        outcome = ""
    return f"{case.task.id} {outcome:<40} {case.task.task[:70]}"


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def write_agent_report(
    out_dir: Path, cases: Sequence[AgentCase], summary: AgentSummary, *, title: str, note: str
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "results.jsonl").open("w") as f:
        for c in cases:
            row = {
                "id": c.task.id,
                "category": c.task.category,
                "answerable": c.task.answerable,
                "answer": c.run.answer if c.run else None,
                "source_pages": c.run.source_pages if c.run else None,
                "rounds": c.run.rounds if c.run else None,
                "tool_calls": c.run.tool_calls if c.run else None,
                "usage": asdict(c.run.usage) if c.run else None,
                "found_evidence": c.found_evidence,
                "cites_evidence": c.cites_evidence,
                "missing_figures": c.missing_figures,
                "grade": c.grade.model_dump() if c.grade else None,
                "grader_usage": asdict(c.grader_usage) if c.grader_usage else None,
                "latency_s": c.latency_s,
                "error": c.error,
            }
            f.write(json.dumps(row) + "\n")

    flag = {True: "yes", False: "no", None: "–"}
    rows = []
    for c in cases:
        verdict = "error" if c.error else (c.grade.verdict if c.grade else "")
        effort = f"{c.run.rounds} / {c.run.tool_calls}" if c.run else "–"
        figures = (
            "–"
            if not c.task.key_figures or c.missing_figures is None
            else ("all" if not c.missing_figures else f"missing {', '.join(c.missing_figures)}")
        )
        reason = c.error or (c.grade.reason if c.grade else "")
        rows.append(
            f"| {c.task.id} | {c.task.category} | {_cell(c.task.task)} | {verdict} | "
            f"{flag[c.found_evidence]} | {figures} | {effort} | {_cell(reason)} |"
        )
    body = "\n".join(
        [
            f"# {title}",
            "",
            note,
            "",
            *[f"- {line}" for line in agent_summary_lines(summary)],
            "",
            "| ID | Category | Task | Verdict | Found evidence | Key figures | Rounds / tools | "
            "Grader's reason |",
            "|---|---|---|---|---|---|---|---|",
            *rows,
            "",
        ]
    )
    (out_dir / "report.md").write_text(body)


def model_run(
    provider: str, model: str, settings: Settings, engine: Engine, embedder: Embedder
) -> RunFn:
    """Run a task through the same graph, tools and limits as POST /api/agent."""
    from sqlalchemy.orm import Session

    from docpilot.agent.graph import Limits, build_graph, run_agent
    from docpilot.agent.models import make_model_factory
    from docpilot.agent.tools import SourceBook, make_tools

    build_model = make_model_factory(settings)
    limits = Limits(
        max_rounds=settings.agent_max_rounds, max_tool_calls=settings.agent_max_tool_calls
    )

    def run(task: AgentTask) -> AgentRun:
        with Session(engine, expire_on_commit=False) as session:  # one per task: runs overlap
            book = SourceBook()
            graph = build_graph(
                build_model(provider, model, limits.step_max_tokens),
                build_model(provider, model, settings.answer_max_tokens),
                make_tools(session, embedder, book, settings.agent_search_k),
                book,
                limits,
            )
            parts: list[str] = []
            done: dict = {}
            for event, data in run_agent(graph, task.task):
                if event == "delta":
                    parts.append(data["text"])
                elif event == "done":
                    done = data
            return AgentRun(
                answer="".join(parts),
                source_pages=[hit.page for hit in book.hits],
                rounds=done.get("rounds", 0),
                tool_calls=done.get("tool_calls", 0),
                usage=Usage(done.get("input_tokens", 0), done.get("output_tokens", 0)),
            )

    return run
