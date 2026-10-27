"""Versioned, additive SQLite migrations for the existing application.

Historical runs have unknown ownership and remain inaccessible through user APIs.
No research rows are deleted or automatically assigned to a newly registered user.
"""
import json
import uuid

from sqlalchemy import inspect, text
from app.core.security import hash_password
from app.db.database import Base, DATA_DIR, engine
from app.models.user import User, AuthSession, AuthRateLimit  # noqa: F401
from app.models import scholarly
from app.models import intelligence
from app.models import analysis  # Register additive normalized tables.
from app.models.research import ResearchRun  # noqa: F401


RUN_COLUMNS = {
    "research_id": "VARCHAR(36)",
    "user_id": "VARCHAR(36) REFERENCES users(id)",
    "report_type": "VARCHAR(32) NOT NULL DEFAULT 'academic_report'",
    "citation_style": "VARCHAR(10) NOT NULL DEFAULT 'apa'",
    "source_target": "INTEGER NOT NULL DEFAULT 10",
    "status": "VARCHAR(24) NOT NULL DEFAULT 'completed'",
    "progress": "INTEGER NOT NULL DEFAULT 100",
    "current_stage": "VARCHAR(64) NOT NULL DEFAULT 'completed'",
    "status_message": "TEXT NOT NULL DEFAULT 'Historical research record'",
    "updated_at": "DATETIME",
    "completed_at": "DATETIME",
    "error_message": "TEXT",
    "result_json": "TEXT",
    "partial": "BOOLEAN NOT NULL DEFAULT 0",
}


def migrate(database_engine=engine, users_file=None):
    Base.metadata.create_all(database_engine)
    with database_engine.begin() as connection:
        connection.execute(text("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)"))
        versions = set(connection.execute(text("SELECT version FROM schema_migrations")).scalars())
        if 1 not in versions:
            columns = {column["name"] for column in inspect(connection).get_columns("research_sessions")}
            for name, ddl in RUN_COLUMNS.items():
                if name not in columns:
                    connection.execute(text(f"ALTER TABLE research_sessions ADD COLUMN {name} {ddl}"))
            rows = connection.execute(text("SELECT id FROM research_sessions WHERE research_id IS NULL")).scalars().all()
            for row_id in rows:
                connection.execute(text("UPDATE research_sessions SET research_id=:uid, updated_at=created_at, completed_at=created_at WHERE id=:id"),
                                   {"uid": str(uuid.uuid4()), "id": row_id})
            connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_research_id ON research_sessions(research_id)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_research_owner ON research_sessions(user_id, created_at)"))
            connection.execute(text("INSERT INTO schema_migrations(version) VALUES (1)"))
        if 2 not in versions:
            path = users_file if users_file is not None else DATA_DIR / "users.json"
            if path.exists():
                records = json.loads(path.read_text(encoding="utf-8")).get("users", [])
                for record in records:
                    email = record["email"].strip().lower()
                    if connection.execute(text("SELECT id FROM users WHERE email=:email"), {"email": email}).first():
                        continue
                    # Wrap the old digest in Argon2; upgrade to direct Argon2 on login.
                    wrapped = f"legacy${record['password_salt']}${hash_password(record['password_hash'])}"
                    connection.execute(text("INSERT INTO users(id,name,email,password_hash,created_at) VALUES (:id,:name,:email,:password_hash,CURRENT_TIMESTAMP)"),
                                       {"id": record.get("id") or str(uuid.uuid4()), "name": record["name"], "email": email, "password_hash": wrapped})
            connection.execute(text("INSERT INTO schema_migrations(version) VALUES (2)"))

        if 7 not in versions:
            connection.execute(text("INSERT INTO schema_migrations(version) VALUES (7)"))

        if 6 not in versions:
            connection.execute(text("INSERT INTO schema_migrations(version) VALUES (6)"))

        if 5 not in versions:
            connection.execute(text("INSERT INTO schema_migrations(version) VALUES (5)"))

        if 4 not in versions:
            connection.execute(text("INSERT INTO schema_migrations(version) VALUES (4)"))

        if 3 not in versions:
            # create_all above adds only missing tables; original runs are retained.
            connection.execute(text("INSERT INTO schema_migrations(version) VALUES (3)"))


if __name__ == "__main__":
    migrate()
