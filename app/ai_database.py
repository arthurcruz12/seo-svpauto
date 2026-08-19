from __future__ import annotations

import os
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

AIBase = declarative_base()


class AIStorageUnavailable(RuntimeError):
    """Raised when the isolated AI/SAF-T database is not configured."""


def _resolve_ai_database_url() -> str | None:
    explicit = os.getenv("AI_DATABASE_URL")
    if explicit:
        return explicit

    # Vercel Neon Marketplace exposes POSTGRES_URL for the pooled application
    # connection. Keep DATABASE_URL untouched so the operational database is
    # never silently replaced.
    neon = os.getenv("POSTGRES_URL")
    if neon:
        return neon

    if os.getenv("ENVIRONMENT", "development") in {"development", "test"}:
        return os.getenv("AI_SQLITE_URL", "sqlite:///./seo_ai.db")

    return None


def ai_database_configured() -> bool:
    return _resolve_ai_database_url() is not None


@lru_cache(maxsize=1)
def get_ai_engine() -> Engine:
    url = _resolve_ai_database_url()
    if not url:
        raise AIStorageUnavailable(
            "AI_DATABASE_URL/POSTGRES_URL is not configured for the AI storage layer"
        )

    kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # Neon pooled connections are appropriate for application traffic.
        # Alembic/administrative work should use POSTGRES_URL_NON_POOLING.
        kwargs["pool_size"] = int(os.getenv("AI_DB_POOL_SIZE", "5"))
        kwargs["max_overflow"] = int(os.getenv("AI_DB_MAX_OVERFLOW", "10"))

    return create_engine(url, **kwargs)


@lru_cache(maxsize=1)
def _session_factory():
    return sessionmaker(autocommit=False, autoflush=False, bind=get_ai_engine())


def get_ai_db():
    factory = _session_factory()
    db: Session = factory()
    try:
        yield db
    finally:
        db.close()


def initialize_ai_schema() -> None:
    """Create additive AI tables in the isolated database only."""

    AIBase.metadata.create_all(bind=get_ai_engine())


def maybe_initialize_ai_schema() -> None:
    environment = os.getenv("ENVIRONMENT", "development")
    default = "true" if environment in {"development", "test"} else "false"
    if os.getenv("AI_AUTO_CREATE_SCHEMA", default).lower() == "true":
        initialize_ai_schema()


def reset_ai_database_caches() -> None:
    """Testing helper for environment-specific engine reconfiguration."""

    _session_factory.cache_clear()
    get_ai_engine.cache_clear()
