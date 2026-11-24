import os
from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import BACKEND_ROOT

DATA_DIR = BACKEND_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(DATA_DIR / 'research_agent.db').as_posix()}")

POSTGRES_SCHEMA = "researchos"


def create_database_engine(database_url):
    url = make_url(database_url)
    if url.get_backend_name() in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+psycopg")
        if "sslmode" not in url.query:
            url = url.update_query_dict({"sslmode": "require"})
        return create_engine(
            url,
            pool_pre_ping=True,
            connect_args={"prepare_threshold": None},
            execution_options={"schema_translate_map": {None: POSTGRES_SCHEMA}},
        )

    if url.get_backend_name() != "sqlite":
        raise ValueError("DATABASE_URL must select SQLite or PostgreSQL.")

    sqlite_engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 30})

    @event.listens_for(sqlite_engine, "connect")
    def configure_sqlite(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")

    return sqlite_engine


engine = create_database_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
