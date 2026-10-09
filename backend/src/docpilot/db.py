from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from docpilot.config import get_settings


class Base(DeclarativeBase):
    pass


def sqlalchemy_url(url: str) -> str:
    """Accept plain postgresql:// URLs and point SQLAlchemy at the psycopg 3 driver."""
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


@lru_cache
def get_engine() -> Engine:
    return create_engine(sqlalchemy_url(get_settings().database_url), pool_pre_ping=True)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request."""
    session = sessionmaker(bind=get_engine(), expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
