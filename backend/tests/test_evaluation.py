import csv
import uuid

from docpilot.evaluation.grader import Grade
from docpilot.evaluation.report import cost_usd, summarize
from docpilot.evaluation.runner import (
    EVAL_SET,
    CaseResult,
    EvalItem,
    answer_and_grade,
    load_eval_set,
)
from docpilot.ingest import SearchHit
from docpilot.llm.base import Usage

CATEGORIES = {
    "factual",
    "comparative",
    "numeric",
    "procedural",
    "conditional",
    "inference",
    "negative",
}


def hit(page: int) -> SearchHit:
    return SearchHit(uuid.uuid4(), uuid.uuid4(), "kb.pdf", page, "text", 0.8)


def item(id_: str, page: int | None, answerable: bool = True) -> EvalItem:
    return EvalItem(id_, f"question {id_}", f"answer {id_}", page, "factual", "easy", answerable)


class ScriptedGrader:
    """Returns canned verdicts by question id."""

    model = "claude-opus-5-5"

    def __init__(self, verdicts: dict[str, tuple[str, bool]]) -> None:
        self.verdicts = verdicts

    def grade(self, *, question: str, answerable: bool, reference: str, answer: str):
        verdict, abstained = self.verdicts[question.removeprefix("question ")]
        return Grade(reason="scripted", abstained=abstained, verdict=verdict), Usage(100, 20)


def test_eval_set_is_consistent() -> None:
    items = load_eval_set()

    assert len({i.id for i in items}) == len(items)
    assert {i.category for i in items} <= CATEGORIES
    for i in items:
        assert (i.source_page is not None) == i.answerable, i.id
        assert (i.category == "negative") == (not i.answerable), i.id
        assert i.source_page not in i.also_on_pages, i.id


def test_eval_csv_matches_json() -> None:
    with (EVAL_SET.parent / "eval_set.csv").open() as f:
        rows = list(csv.DictReader(f))

    assert [(r["id"], r["question"], r["ground_truth"]) for r in rows] == [
        (i.id, i.question, i.ground_truth) for i in load_eval_set()
    ]


def test_retrieval_rank_and_citation_checks() -> None:
    case = CaseResult(item("q1", page=3), hits=[hit(1), hit(3), hit(3)])
    case.answer, case.cited = "It is [2].", [2]

    assert case.retrieval_rank == 2
    assert case.cites_source_page is True

    case.cited = [1, 9]  # wrong page, and a number with no matching source
    assert case.cites_source_page is False


def test_evidence_on_another_page_also_counts() -> None:
    question = EvalItem("q", "question", "answer", 2, "factual", "easy", True, also_on_pages=(5,))
    case = CaseResult(question, hits=[hit(5), hit(2)])
    case.answer, case.cited = "It is [1].", [1]

    assert case.retrieval_rank == 1
    assert case.cites_source_page is True


def test_answer_and_grade_scores_and_summarizes() -> None:
    cases = [
        CaseResult(item("a", 1), [hit(1)]),
        CaseResult(item("b", 2), [hit(1), hit(2)]),
        CaseResult(item("c", 5), [hit(1)]),
        CaseResult(item("n", None, answerable=False), [hit(1)]),
    ]
    grader = ScriptedGrader(
        {
            "a": ("correct", False),
            "b": ("partial", False),
            "c": ("incorrect", True),
            "n": ("correct", True),
        }
    )

    answer_and_grade(cases, lambda case: ("Yes [1].", Usage(1000, 50)), grader, workers=2)
    summary = summarize(cases, "claude-haiku-5-5", grader.model)

    assert summary.errors == 0
    assert summary.retrieval_hit_rate == 2 / 3
    assert summary.retrieval_mrr == (1 + 1 / 2) / 3
    assert (summary.correct, summary.partial, summary.incorrect) == (1, 1, 1)
    assert summary.answer_score == 0.5
    assert summary.false_abstentions == 1
    assert (summary.abstained_correctly, summary.negatives_graded) == (1, 1)
    assert summary.citation_rate == 1 / 3  # only "a" cites a passage from its page
    assert summary.answer_usage == Usage(4000, 200)
    assert summary.grader_cost_usd == cost_usd("claude-opus-5-5", Usage(400, 80))


def test_failures_are_recorded_not_scored() -> None:
    cases = [CaseResult(item("a", 1), [hit(1)])]

    def broken(case: CaseResult) -> tuple[str, Usage]:
        raise TimeoutError("provider timed out")

    answer_and_grade(cases, broken, ScriptedGrader({}))
    summary = summarize(cases)

    assert cases[0].error == "TimeoutError: provider timed out"
    assert summary.errors == 1
    assert summary.answerable_graded == 0
