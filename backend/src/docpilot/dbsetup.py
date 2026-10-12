from pathlib import Path

import psycopg
from alembic import command
from alembic.config import Config
from psycopg import sql
from sqlalchemy.engine import make_url

from docpilot.config import get_settings
from docpilot.db import sqlalchemy_url

BACKEND_DIR = Path(__file__).resolve().parents[2]


def prepare_database(name: str) -> str:
    """Create a database beside the app's one if missing, migrate it, and return its URL.

    Used for the test and evaluation databases, so they never touch the dev data.
    """
    url = make_url(sqlalchemy_url(get_settings().database_url)).set(database=name)
    admin = url.set(drivername="postgresql", database="postgres")
    with psycopg.connect(admin.render_as_string(hide_password=False), autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone()
        if not exists:
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))

    rendered = url.render_as_string(hide_password=False)
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", rendered)
    command.upgrade(config, "head")
    return rendered
