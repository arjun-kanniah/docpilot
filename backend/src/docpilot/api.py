import logging
import uuid
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, status
from fastapi.sse import EventSourceResponse, ServerSentEvent
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from docpilot.agent.models import ModelFactory, get_model_factory
from docpilot.answer import NO_SOURCES_ANSWER, stream_answer
from docpilot.chunking import UnsupportedFileError
from docpilot.config import Settings, get_settings
from docpilot.db import get_session
from docpilot.embeddings import Embedder, get_embedder
from docpilot.ingest import EmptyDocumentError, SearchHit, ingest_document, search_chunks
from docpilot.llm.base import LLMError, Usage
from docpilot.llm.providers import Choice, LLMConfigError, LLMRegistry, get_llm_registry
from docpilot.models import Chunk, Document
from docpilot.ratelimit import RateLimiter, get_rate_limiter, visitor_id
from docpilot.schemas import (
    AgentIn,
    AskIn,
    DocumentOut,
    IngestOut,
    ModelChoiceOut,
    ModelsOut,
    ProviderOut,
    SearchHitOut,
    SearchIn,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

SessionDep = Annotated[Session, Depends(get_session)]
EmbedderDep = Annotated[Embedder, Depends(get_embedder)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
RegistryDep = Annotated[LLMRegistry, Depends(get_llm_registry)]
LimiterDep = Annotated[RateLimiter, Depends(get_rate_limiter)]
ModelFactoryDep = Annotated[ModelFactory, Depends(get_model_factory)]


def require_writable_library(settings: SettingsDep) -> None:
    """The public demo's document library is read-only."""
    if settings.demo_mode:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "The public demo's library is read-only. Run DocPilot locally to use your own files.",
        )


def _document_out(document: Document, chunk_count: int) -> DocumentOut:
    return DocumentOut(
        id=document.id,
        filename=document.filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        page_count=document.page_count,
        chunk_count=chunk_count,
        created_at=document.created_at,
    )


@router.post(
    "/documents",
    response_model=IngestOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_writable_library)],
)
def upload_document(
    file: UploadFile,
    response: Response,
    session: SessionDep,
    embedder: EmbedderDep,
    settings: SettingsDep,
) -> IngestOut:
    limit = settings.max_upload_mb * 1024 * 1024
    data = file.file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE, f"File exceeds {settings.max_upload_mb} MB"
        )
    try:
        result = ingest_document(session, embedder, settings, file.filename or "upload", data)
    except UnsupportedFileError as exc:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(exc)) from exc
    except EmptyDocumentError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc

    if result.duplicate:
        response.status_code = status.HTTP_200_OK
    return IngestOut(
        document=_document_out(result.document, result.chunk_count), duplicate=result.duplicate
    )


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(session: SessionDep) -> list[DocumentOut]:
    rows = session.execute(
        select(Document, func.count(Chunk.id))
        .outerjoin(Chunk)
        .group_by(Document.id)
        .order_by(Document.created_at.desc())
    ).all()
    return [_document_out(document, count) for document, count in rows]


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_writable_library)],
)
def delete_document(document_id: uuid.UUID, session: SessionDep) -> None:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    session.delete(document)
    session.commit()


@router.post("/search", response_model=list[SearchHitOut])
def search(body: SearchIn, session: SessionDep, embedder: EmbedderDep) -> list[SearchHitOut]:
    hits = search_chunks(session, embedder, body.query, body.k)
    return [SearchHitOut(**asdict(hit)) for hit in hits]


@router.get("/models", response_model=ModelsOut)
def list_models(registry: RegistryDep) -> ModelsOut:
    """Providers with a configured API key, their allowlisted models, and the default."""
    default = registry.default()
    return ModelsOut(
        providers=[
            ProviderOut(id=p.id, label=p.label, models=list(p.models)) for p in registry.available()
        ],
        default=ModelChoiceOut(provider=default[0], model=default[1]) if default else None,
    )


@dataclass(frozen=True)
class AskPlan:
    question: str
    hits: list[SearchHit]
    choice: Choice


def prepare_ask(
    body: AskIn,
    request: Request,
    session: SessionDep,
    embedder: EmbedderDep,
    settings: SettingsDep,
    registry: RegistryDep,
    limiter: LimiterDep,
) -> AskPlan:
    """Validate, rate-limit and retrieve before the stream opens, so refusals get a normal 4xx."""
    try:
        choice = registry.resolve(body.provider, body.model)
    except LLMConfigError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    k = body.k or settings.answer_top_k
    if settings.demo_mode:
        if refusal := limiter.check(visitor_id(request, settings.proxy_secret.get_secret_value())):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, refusal)
        k = min(k, settings.answer_top_k)  # bigger prompts cost more
    hits = search_chunks(session, embedder, body.question, k)
    return AskPlan(body.question, hits, choice)


@router.post("/ask", response_class=EventSourceResponse)
def ask(
    plan: Annotated[AskPlan, Depends(prepare_ask)], settings: SettingsDep
) -> Iterator[ServerSentEvent]:
    """Stream an answer as Server-Sent Events.

    Events: `sources` (the numbered passages citations refer to), then `delta` (answer
    text) repeatedly, then `done` (model and token usage) or `error`.
    """
    choice = plan.choice
    yield ServerSentEvent(event="sources", data=[SearchHitOut(**asdict(hit)) for hit in plan.hits])
    usage = Usage(0, 0)
    try:
        for item in stream_answer(
            choice.chat, choice.model, plan.question, plan.hits, settings.answer_max_tokens
        ):
            if isinstance(item, Usage):
                usage = item
            else:
                yield ServerSentEvent(event="delta", data={"text": item})
    except LLMError as exc:
        log.warning("ask failed (%s/%s): %s", choice.provider, choice.model, exc)
        yield ServerSentEvent(event="error", data={"message": str(exc)})
        return
    except Exception:
        log.exception("ask failed (%s/%s)", choice.provider, choice.model)
        yield ServerSentEvent(event="error", data={"message": "Something went wrong."})
        return
    log.info(
        "ask %s/%s: %d in, %d out tokens",
        choice.provider,
        choice.model,
        usage.input_tokens,
        usage.output_tokens,
    )
    yield ServerSentEvent(
        event="done",
        data={"provider": choice.provider, "model": choice.model, **asdict(usage)},
    )


def prepare_agent(
    body: AgentIn,
    request: Request,
    settings: SettingsDep,
    registry: RegistryDep,
    limiter: LimiterDep,
) -> tuple[AgentIn, Choice]:
    """Validate and rate-limit before the stream opens, so refusals get a normal 4xx."""
    try:
        choice = registry.resolve(body.provider, body.model)
    except LLMConfigError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    if settings.demo_mode:
        visitor = visitor_id(request, settings.proxy_secret.get_secret_value())
        if refusal := limiter.check(visitor, cost=settings.agent_question_cost):
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                f"{refusal} An agent run counts as {settings.agent_question_cost} questions.",
            )
    return body, choice


@router.post("/agent", response_class=EventSourceResponse)
def agent(
    prepared: Annotated[tuple[AgentIn, Choice], Depends(prepare_agent)],
    session: SessionDep,
    embedder: EmbedderDep,
    settings: SettingsDep,
    build_model: ModelFactoryDep,
) -> Iterator[ServerSentEvent]:
    """Run a task through the researcher, analyst and writer, streaming the run as it happens.

    Events: `step` (a node starts), `tool` (a tool call and a summary of its result),
    `sources` (every passage found so far, numbered for citations), `notes` (the researcher's
    findings), `review` (the analyst's verdict), `delta` (answer text), then `done` (model,
    rounds, tool calls and token usage) or `error`.
    """
    from docpilot.agent.errors import friendly_error  # LangGraph loads on the first agent run
    from docpilot.agent.graph import Limits, build_graph, run_agent
    from docpilot.agent.tools import SourceBook, make_tools

    body, choice = prepared
    if session.scalar(select(func.count()).select_from(Document)) == 0:
        yield ServerSentEvent(event="delta", data={"text": NO_SOURCES_ANSWER})
        yield ServerSentEvent(
            event="done", data={"provider": choice.provider, "model": choice.model}
        )
        return

    limits = Limits(
        max_rounds=settings.agent_max_rounds, max_tool_calls=settings.agent_max_tool_calls
    )
    book = SourceBook()
    graph = build_graph(
        build_model(choice.provider, choice.model, limits.step_max_tokens),
        build_model(choice.provider, choice.model, settings.answer_max_tokens),
        make_tools(session, embedder, book, settings.agent_search_k),
        book,
        limits,
    )
    try:
        for event, data in run_agent(graph, body.task):
            if event == "sources":
                data = [SearchHitOut(**asdict(hit)) for hit in data]
            elif event == "done":
                log.info("agent %s/%s: %s", choice.provider, choice.model, data)
                data = {"provider": choice.provider, "model": choice.model, **data}
            yield ServerSentEvent(event=event, data=data)
    except Exception as exc:
        message = friendly_error(exc)
        if message:
            log.warning("agent failed (%s/%s): %s", choice.provider, choice.model, exc)
        else:
            log.exception("agent failed (%s/%s)", choice.provider, choice.model)
        yield ServerSentEvent(event="error", data={"message": message or "Something went wrong."})
