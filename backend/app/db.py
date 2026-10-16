import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str):
    kwargs = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # fail fast instead of hanging a readiness probe when the DB is unreachable
        kwargs["connect_args"] = {"connect_timeout": 3}
        # 5 + 10 connections per replica: 6 replicas stay under Postgres' default
        # max_connections of 100. Waiting longer than 5 s for one means the pod is
        # saturated; the API then answers 503 so the client (or HPA) can react.
        kwargs["pool_size"] = int(os.getenv("DB_POOL_SIZE", "5"))
        kwargs["max_overflow"] = int(os.getenv("DB_POOL_OVERFLOW", "10"))
        kwargs["pool_timeout"] = int(os.getenv("DB_POOL_TIMEOUT", "5"))
    return create_engine(url, **kwargs)


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def db_is_up() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
