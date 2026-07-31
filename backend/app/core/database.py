"""SQLAlchemy engine, session factory, and declarative base.

The engine is created lazily: importing this module must not require a running
PostgreSQL instance, so the foundation can be exercised without Docker up.
"""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """Base class every ORM model inherits from."""


@lru_cache
def get_engine() -> Engine:
    """Process-wide engine, built on first use."""
    return create_engine(
        settings.database_url,
        echo=settings.db_echo,
        pool_pre_ping=True,  # drop connections killed by the DB between requests
        future=True,
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a request-scoped session.

    Usage: ``def endpoint(db: Session = Depends(get_db)) -> ...``
    """
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
