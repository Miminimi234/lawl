"""
Database configuration and helpers.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool
from typing import Generator

from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for ORM models."""


def _create_engine():
    """Create SQLAlchemy engine that works for both Postgres and SQLite."""
    url = settings.DATABASE_URL

    connect_args = {}
    engine_kwargs = {
        "pool_pre_ping": True,
    }

    if url.startswith("sqlite"):
        # SQLite requires special handling for multithreaded access
        connect_args["check_same_thread"] = False
        # SQLite doesn't like connection pooling in serverless contexts
        engine_kwargs["poolclass"] = NullPool

    return create_engine(url, connect_args=connect_args, **engine_kwargs)


engine = _create_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator:
    """FastAPI dependency that provides a transactional DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    """Create all tables if they do not exist."""
    import app.models  # noqa: F401 ensures model metadata is registered

    Base.metadata.create_all(bind=engine)
