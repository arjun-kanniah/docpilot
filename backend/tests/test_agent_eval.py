import pytest

from docpilot.evaluation.agent import (
    AgentCase,
    AgentRun,
    AgentTask,
    load_agent_set,
    matches,
    oracle_run,
    run_and_grade,
    states_figure,
    summarize_agent,
)
from docpilot.evaluation.grader import Grade
from docpilot.llm.base import Usage

CATEGORIES = {"multi-page", "multi-document", "conflict", "conditional", "calculation", "negative"}


def task(
    id_: str, evidence: tuple[str, ...] = ("kb.pdf#2", "kb.pdf#3"), figures: tuple[str, ...] = ()
) -> AgentTask:
    return AgentTask(id_, f"task {id_}", f"reference {id_}", evidence, figures, "calculation", True)


class ScriptedGrader:
    model = "claude-opus-5-5"

    def __init__(self, verdicts: dict[str, str]) -> None:
        self.verdicts = verdicts

    def grade(self, *, question: str, answerable: bool, reference: str, answer: str):
        verdict = self.verdicts[question.removeprefix("task ")]
        return Grade(reason="scripted", abstained=False, verdict=verdict), Usage(100, 20)


@pytest.mark.parametrize("name", ["single", "multi"])
def test_task_sets_are_consistent(name: str) -> None:
    tasks, corpus = load_agent_set(name)

    assert corpus and all(path.is_file() for path in corpus)
    files = {path.name for path in corpus}
    assert len({t.id for t in tasks}) == len(tasks)
    assert {t.category for t in tasks} <= CATEGORIES
    for t in tasks:
        assert bool(t.evidence) == t.answerable, t.id
        assert (t.category == "negative") == (not t.answerable), t.id
        for ref in t.evidence:  # every reference names a document the set indexes
            filename, _, page = ref.partition("#")
            assert filename in files and (not page or page.isdigit()), (t.id, ref)
        # Every key figure appears in the reference, so the reference passes its own check
        assert all(states_figure(t.reference, f) for f in t.key_figures), t.id


def test_figures_match_whole_numbers_only() -> None:
    assert states_figure("Total: $1,393.80 [3]", "1,393.80")
    assert states_figure("about 1393.80 dollars", "1,393.80")
    assert states_figure("Annually: $98.", "98")
    assert states_figure("Annually: $98.00 [2]", "98")
    assert not states_figure("$1,980 in total", "98")
    assert not states_figure("$5,480", "548")
    assert not states_figure("$548.50", "548")


def test_evidence_citation_and_figure_checks() -> None:
    case = AgentCase(task("r1", evidence=("kb.pdf#2", "notes.md"), figures=("1,393.80", "77.40")))
    sources = [("kb.pdf", 2), ("kb.pdf", 4), ("notes.md", None)]
    case.run = AgentRun("Total $1,393.80 [1][3].", sources, 1, 4, Usage(10, 5))
    case.cited = [1, 3]

    assert case.found_evidence is True
    assert case.cites_evidence is True
    assert case.missing_figures == ["77.40"]

    case.cited = [1, 2]  # kb.pdf pages 2 and 4: notes.md never cited
    assert case.cites_evidence is False
    case.run.sources = [("kb.pdf", 2), ("kb.pdf", 4)]
    assert case.found_evidence is False


def test_evidence_refs_match_by_file_and_page() -> None:
    assert matches("kb.pdf#2", ("kb.pdf", 2))
    assert not matches("kb.pdf#2", ("kb.pdf", 3))
    assert not matches("kb.pdf#2", ("guide.pdf", 2))  # page 2 of another document
    assert matches("notes.md", ("notes.md", None))
    assert matches("guide.pdf", ("guide.pdf", 4))  # no page: anywhere in the file


def test_run_grade_and_summarize() -> None:
    cases = [
        AgentCase(task("a", figures=("10",))),
        AgentCase(task("b")),
        AgentCase(AgentTask("n", "task n", "none", (), (), "negative", False)),
        AgentCase(task("boom")),
    ]
    runs = {
        "a": AgentRun(
            "It costs $10 [1][2].", [("kb.pdf", 2), ("kb.pdf", 3)], 1, 3, Usage(1000, 100)
        ),
        "b": AgentRun("Partly [1].", [("kb.pdf", 2)], 2, 7, Usage(3000, 300)),
        "n": AgentRun("The documents don't say.", [("kb.pdf", 1)], 1, 2, Usage(500, 50)),
    }

    def run(t: AgentTask) -> AgentRun:
        if t.id == "boom":
            raise RuntimeError("provider down")
        return runs[t.id]

    grader = ScriptedGrader({"a": "correct", "b": "partial", "n": "correct"})
    run_and_grade(cases, run, grader, workers=2)
    summary = summarize_agent(cases, "claude-haiku-5-5", grader.model)

    assert cases[3].error == "RuntimeError: provider down"
    assert (summary.correct, summary.partial, summary.incorrect) == (1, 1, 0)
    assert (summary.declined_correctly, summary.negatives_graded) == (1, 1)
    assert summary.found_evidence_rate == 0.5  # b found page 2 but not 3; n has no evidence
    assert (summary.figures_stated, summary.figures_expected) == (1, 1)
    assert summary.mean_rounds == 4 / 3 and summary.mean_tool_calls == 4
    assert summary.usage == Usage(4500, 450)
    assert summary.errors == 1


@pytest.mark.parametrize("name", ["single", "multi"])
def test_oracle_answers_state_every_key_figure(name: str) -> None:
    for t in load_agent_set(name)[0]:
        case = AgentCase(t, run=oracle_run(t))
        assert case.missing_figures == [], t.id


def test_rate_limited_runs_are_retried() -> None:
    from langchain_core.exceptions import ModelRateLimitError

    attempts = []

    def run(t: AgentTask) -> AgentRun:
        attempts.append(t.id)
        if len(attempts) < 2:
            raise ModelRateLimitError("429")
        return AgentRun("Done [1].", [("kb.pdf", 2), ("kb.pdf", 3)], 1, 2, Usage(1, 1))

    cases = [AgentCase(task("a"))]
    run_and_grade(cases, run, ScriptedGrader({"a": "correct"}), retry_wait_s=0)

    assert attempts == ["a", "a"]
    assert cases[0].error is None and cases[0].grade is not None
