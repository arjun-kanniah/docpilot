import hashlib
import math
import re
from collections.abc import Iterator, Sequence
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from docpilot.config import get_settings
from docpilot.db import get_session, sqlalchemy_url
from docpilot.embeddings import EMBEDDING_DIM, get_embedder
from docpilot.llm.base import Usage
from docpilot.llm.providers import LLMRegistry, get_llm_registry
from docpilot.main import app

BACKEND_DIR = Path(__file__).resolve().parents[1]


class FakeEmbedder:
    """Deterministic bag-of-words vectors: texts sharing words score as similar.

    Good enough to test retrieval wiring without downloading a real model.
    """

    def _vector(self, text_: str) -> list[float]:
        vector = [0.0] * EMBEDDING_DIM
        for word in re.findall(r"[a-z0-9]+", text_.lower()):
            bucket = int(hashlib.md5(word.encode()).hexdigest(), 16) % EMBEDDING_DIM
            vector[bucket] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text_: str) -> list[float]:
        return self._vector(text_)


class FakeChat:
    """Records each request and streams a canned answer that cites source 1."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def stream(
        self, *, model: str, system: str, prompt: str, max_tokens: int
    ) -> Iterator[str | Usage]:
        self.calls.append({"model": model, "system": system, "prompt": prompt})
        yield "Refunds are allowed "
        yield "within 30 days [1]."
        yield Usage(input_tokens=120, output_tokens=9)


@pytest.fixture(scope="session")
def test_db_url() -> str:
    """A separate database next to the dev one, migrated to the latest schema."""
    url = make_url(sqlalchemy_url(get_settings().database_url)).set(database="docpilot_test")
    admin = url.set(drivername="postgresql", database="postgres")
    with psycopg.connect(admin.render_as_string(hide_password=False), autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = 'docpilot_test'"
        ).fetchone()
        if not exists:
            conn.execute("CREATE DATABASE docpilot_test")

    rendered = url.render_as_string(hide_password=False)
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", rendered)
    command.upgrade(config, "head")
    return rendered


@pytest.fixture
def db_session(test_db_url: str) -> Iterator[Session]:
    engine = create_engine(test_db_url)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    yield session
    session.close()
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE documents CASCADE"))
    engine.dispose()


@pytest.fixture
def fake_chat() -> FakeChat:
    return FakeChat()


@pytest.fixture
def client(db_session: Session, fake_chat: FakeChat) -> Iterator[TestClient]:
    registry = LLMRegistry({"anthropic": fake_chat}, default_provider="anthropic")
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_embedder] = FakeEmbedder
    app.dependency_overrides[get_llm_registry] = lambda: registry
    yield TestClient(app)
    app.dependency_overrides.clear()
