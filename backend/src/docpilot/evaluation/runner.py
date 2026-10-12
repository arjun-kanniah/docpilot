import json
import re
import time
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from sqlalchemy import text
from sqlalchemy.orm import Session

from docpilot.answer import stream_answer
from docpilot.config import Settings
from docpilot.dbsetup import BACKEND_DIR
from docpilot.embeddings import Embedder
from docpilot.evaluation.grader import Grade
from docpilot.ingest import SearchHit, ingest_document, search_chunks
from docpilot.llm.base import LLMError, Usage
from docpilot.llm.providers import Choice

DEMO_DIR = BACKEND_DIR.parent / "demo"
EVAL_SET = DEMO_DIR / "eval_set.json"
CORPUS = [DEMO_DIR / "aurora_knowledge_base.pdf"]

_CITATION = re.compile(r"\[(\d+)\]")


@dataclass(frozen=True)
class EvalItem:
    id: str
    question: str
    ground_truth: str
    source_page: int | None
    category: str
    difficulty: str
    answerable: bool
    also_on_pages: tuple[int, ...] = ()  # other pages stating the same evidence

    @property
    def evidence_pages(self) -> set[int]:
        """Pages whose passages count as the right evidence for this question."""
        if self.source_page is None:
            return set()
        return {self.source_page, *self.also_on_pages}


def load_eval_set(path: Path = EVAL_SET) -> list[EvalItem]:
    data = json.loads(path.read_text())
    return [
        EvalItem(
            **{f: item[f] for f in EvalItem.__dataclass_fields__ if f != "also_on_pages"},
            also_on_pages=tuple(item.get("also_on_pages", ())),
        )
        for item in data["items"]
    ]


class Grader(Protocol):
    model: str

    def grade(
        self, *, question: str, answerable: bool, reference: str, answer: str
    ) -> tuple[Grade, Usage]: ...


@dataclass
class CaseResult:
    item: EvalItem
    hits: list[SearchHit]
    answer: str | None = None
    usage: Usage | None = None
    latency_s: float | None = None
    grade: Grade | None = None
    grader_usage: Usage | None = None
    error: str | None = None
    cited: list[int] = field(default_factory=list)  # source numbers cited in the answer

    @property
    def retrieval_rank(self) -> int | None:
        """1-based rank of the first passage from an evidence page, if one was retrieved."""
        evidence = self.item.evidence_pages
        return next((i for i, hit in enumerate(self.hits, 1) if hit.page in evidence), None)

    @property
    def cites_source_page(self) -> bool | None:
        """Whether the answer cites a passage from an evidence page (answerable cases only)."""
        if self.answer is None or self.item.source_page is None or not self.item.answerable:
            return None
        pages = {self.hits[n - 1].page for n in self.cited if 0 < n <= len(self.hits)}
        return bool(pages & self.item.evidence_pages)


def index_corpus(
    session: Session, embedder: Embedder, settings: Settings, paths: Iterable[Path] = CORPUS
) -> int:
    """Replace everything in the (evaluation) database with the corpus. Returns chunk count."""
    session.execute(text("TRUNCATE documents CASCADE"))
    session.commit()
    return sum(
        ingest_document(session, embedder, settings, path.name, path.read_bytes()).chunk_count
        for path in paths
    )


def retrieve(
    session: Session, embedder: Embedder, items: Sequence[EvalItem], k: int
) -> list[CaseResult]:
    return [CaseResult(item, search_chunks(session, embedder, item.question, k)) for item in items]


AnswerFn = Callable[[CaseResult], tuple[str, Usage]]


def model_answer(choice: Choice, max_tokens: int) -> AnswerFn:
    """Answer through the same prompt and streaming path as POST /api/ask."""

    def answer(case: CaseResult) -> tuple[str, Usage]:
        parts: list[str] = []
        usage = Usage(0, 0)
        for item in stream_answer(
            choice.chat, choice.model, case.item.question, case.hits, max_tokens
        ):
            if isinstance(item, Usage):
                usage = item
            else:
                parts.append(item)
        return "".join(parts), usage

    return answer


def oracle_answer(case: CaseResult) -> tuple[str, Usage]:
    """The reference answer itself: the grader should pass nearly all of these."""
    return case.item.ground_truth, Usage(0, 0)


def null_answer(case: CaseResult) -> tuple[str, Usage]:
    """Always abstain: the grader should fail every answerable case and pass the negatives."""
    return "I don't know.", Usage(0, 0)


def answer_and_grade(
    cases: Sequence[CaseResult],
    answer: AnswerFn,
    grader: Grader,
    workers: int = 4,
    on_done: Callable[[CaseResult], None] | None = None,
) -> None:
    """Fill in each case's answer and grade. Failures are recorded on the case, not scored."""

    def run(case: CaseResult) -> None:
        started = time.perf_counter()
        try:
            case.answer, case.usage = answer(case)
            case.latency_s = round(time.perf_counter() - started, 2)
            case.cited = [int(n) for n in _CITATION.findall(case.answer)]
            case.grade, case.grader_usage = grader.grade(
                question=case.item.question,
                answerable=case.item.answerable,
                reference=case.item.ground_truth,
                answer=case.answer,
            )
        except LLMError as exc:
            case.error = str(exc)
        except Exception as exc:  # recorded per case so one failure doesn't sink the run
            case.error = f"{type(exc).__name__}: {exc}"
        if on_done:
            on_done(case)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(run, cases))
