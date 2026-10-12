import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median

from docpilot.evaluation.runner import CaseResult
from docpilot.llm.base import Usage

# USD per million tokens (input, output), for the cost estimate in reports. As of October 2026.
PRICES: dict[str, tuple[float, float]] = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}


def cost_usd(model: str, usage: Usage | None) -> float | None:
    if usage is None or model not in PRICES:
        return None
    price_in, price_out = PRICES[model]
    return (usage.input_tokens * price_in + usage.output_tokens * price_out) / 1_000_000


def _ratio(part: float, whole: int) -> float | None:
    return part / whole if whole else None


@dataclass(frozen=True)
class Summary:
    cases: int
    errors: int
    retrieval_hit_rate: float | None  # expected page in the top k, answerable cases with a page
    retrieval_mrr: float | None
    answerable_graded: int
    correct: int
    partial: int
    incorrect: int
    answer_score: float | None  # correct = 1, partial = 0.5, over graded answerable cases
    false_abstentions: int  # declined although the documents had the answer
    negatives_graded: int
    abstained_correctly: int
    citation_rate: float | None  # answerable answers citing a passage from the expected page
    answer_usage: Usage
    grader_usage: Usage
    answer_cost_usd: float | None
    grader_cost_usd: float | None
    median_latency_s: float | None


def summarize(
    cases: Sequence[CaseResult], answer_model: str | None = None, grader_model: str | None = None
) -> Summary:
    with_page = [c for c in cases if c.item.answerable and c.item.source_page is not None]
    ranks = [c.retrieval_rank for c in with_page]
    graded = [c for c in cases if c.grade is not None]
    answerable = [c for c in graded if c.item.answerable]
    negatives = [c for c in graded if not c.item.answerable]
    verdicts = Counter(c.grade.verdict for c in answerable if c.grade)
    cites = [c.cites_source_page for c in answerable]

    def total(usages: Sequence[Usage | None]) -> Usage:
        real = [u for u in usages if u is not None]
        return Usage(sum(u.input_tokens for u in real), sum(u.output_tokens for u in real))

    answer_usage = total([c.usage for c in cases])
    grader_usage = total([c.grader_usage for c in cases])
    latencies = [c.latency_s for c in cases if c.latency_s is not None]
    return Summary(
        cases=len(cases),
        errors=sum(c.error is not None for c in cases),
        retrieval_hit_rate=_ratio(sum(r is not None for r in ranks), len(ranks)),
        retrieval_mrr=_ratio(sum(1 / r for r in ranks if r), len(ranks)),
        answerable_graded=len(answerable),
        correct=verdicts["correct"],
        partial=verdicts["partial"],
        incorrect=verdicts["incorrect"],
        answer_score=_ratio(verdicts["correct"] + 0.5 * verdicts["partial"], len(answerable)),
        false_abstentions=sum(bool(c.grade and c.grade.abstained) for c in answerable),
        negatives_graded=len(negatives),
        abstained_correctly=sum(bool(c.grade and c.grade.verdict == "correct") for c in negatives),
        citation_rate=_ratio(sum(bool(c) for c in cites), len(cites)),
        answer_usage=answer_usage,
        grader_usage=grader_usage,
        answer_cost_usd=cost_usd(answer_model, answer_usage) if answer_model else None,
        grader_cost_usd=cost_usd(grader_model, grader_usage) if grader_model else None,
        median_latency_s=median(latencies) if latencies else None,
    )


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.0%}"


def _usd(value: float | None) -> str:
    return "n/a" if value is None else f"${value:.3f}"


def summary_lines(s: Summary, k: int) -> list[str]:
    lines = [
        f"Retrieval: expected page in top {k} for {_pct(s.retrieval_hit_rate)} "
        f"(MRR {s.retrieval_mrr:.2f})"
        if s.retrieval_mrr is not None
        else "Retrieval: n/a",
    ]
    if s.answerable_graded or s.negatives_graded:
        lines += [
            f"Answers: {s.correct} correct, {s.partial} partial, {s.incorrect} incorrect "
            f"of {s.answerable_graded} (score {_pct(s.answer_score)}); "
            f"{s.false_abstentions} declined wrongly",
            f"Abstention: declined {s.abstained_correctly} of {s.negatives_graded} "
            "questions the document can't answer",
            f"Citations: {_pct(s.citation_rate)} of answers cite the expected page",
            f"Tokens: answers {s.answer_usage.input_tokens:,} in / "
            f"{s.answer_usage.output_tokens:,} out ({_usd(s.answer_cost_usd)}); grader "
            f"{s.grader_usage.input_tokens:,} in / {s.grader_usage.output_tokens:,} out "
            f"({_usd(s.grader_cost_usd)})",
        ]
        if s.median_latency_s is not None:
            lines.append(f"Median time to a full answer: {s.median_latency_s:.1f}s")
    if s.errors:
        lines.append(f"Errors (not scored): {s.errors}")
    return lines


def case_line(case: CaseResult) -> str:
    rank = case.retrieval_rank
    retrieval = "neg" if case.item.source_page is None else (f"#{rank}" if rank else "miss")
    if case.error:
        outcome = f"ERROR {case.error}"
    elif case.grade:
        cite = ""
        if case.cites_source_page is False:
            cite = " (cites wrong page)" if case.cited else " (no citations)"
        outcome = f"{case.grade.verdict}{cite}"
    else:
        outcome = ""
    outcome = f"{outcome:<28} " if outcome else ""
    return f"{case.item.id} [{retrieval:>4}] {outcome}{case.item.question}"


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def write_report(
    out_dir: Path,
    cases: Sequence[CaseResult],
    summary: Summary,
    *,
    title: str,
    k: int,
    settings_note: str,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "results.jsonl").open("w") as f:
        for c in cases:
            row = {
                "id": c.item.id,
                "category": c.item.category,
                "answerable": c.item.answerable,
                "source_page": c.item.source_page,
                "retrieved_pages": [h.page for h in c.hits],
                "retrieval_rank": c.retrieval_rank,
                "answer": c.answer,
                "cited": c.cited,
                "cites_source_page": c.cites_source_page,
                "grade": c.grade.model_dump() if c.grade else None,
                "usage": asdict(c.usage) if c.usage else None,
                "grader_usage": asdict(c.grader_usage) if c.grader_usage else None,
                "latency_s": c.latency_s,
                "error": c.error,
            }
            f.write(json.dumps(row) + "\n")

    rows = []
    for c in cases:
        rank = c.retrieval_rank
        retrieval = "–" if c.item.source_page is None else (f"#{rank}" if rank else "miss")
        verdict = "error" if c.error else (c.grade.verdict if c.grade else "")
        cites = {True: "yes", False: "no", None: "–"}[c.cites_source_page]
        reason = c.error or (c.grade.reason if c.grade else "")
        rows.append(
            f"| {c.item.id} | {c.item.category} | {_cell(c.item.question)} | {retrieval} | "
            f"{verdict} | {cites} | {_cell(reason)} |"
        )
    body = "\n".join(
        [
            f"# {title}",
            "",
            settings_note,
            "",
            *[f"- {line}" for line in summary_lines(summary, k)],
            "",
            "| ID | Category | Question | Retrieval | Verdict | Cites page | Grader's reason |",
            "|---|---|---|---|---|---|---|",
            *rows,
            "",
        ]
    )
    (out_dir / "report.md").write_text(body)
