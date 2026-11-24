import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier
from uuid import uuid4

from fastapi.testclient import TestClient
from psycopg import sql
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.agents.research_orchestrator import ResearchOrchestrator
from app.agents.search_agent import SearchAgent
from app.api.background import get_executor
from app.core.security import token_digest, verify_password
from app.db.database import POSTGRES_SCHEMA, create_database_engine, get_db
from app.db.migrations import migrate
from app.main import app
from app.models.user import AuthSession, User
from app.schemas.research import ResearchRequest
from app.services.execution import execute_research
from app.services.research_runs import TooManyRunsError, create_run
from app.services.user_store import create_user
from test_foundation import DeferredExecutor, PASSWORD, RecordedProvider


class DatabaseConfigurationTests(unittest.TestCase):
    def test_postgres_uri_variants_and_schema_isolation(self):
        for scheme in ("postgres", "postgresql", "postgresql+psycopg"):
            with self.subTest(scheme=scheme):
                engine = create_database_engine(f"{scheme}://localhost/postgres")
                self.addCleanup(engine.dispose)
                self.assertEqual(engine.url.drivername, "postgresql+psycopg")
                self.assertEqual(engine.url.query["sslmode"], "require")
                self.assertEqual(engine.get_execution_options()["schema_translate_map"], {None: POSTGRES_SCHEMA})

        engine = create_database_engine("postgresql://localhost/postgres?sslmode=verify-full")
        self.addCleanup(engine.dispose)
        self.assertEqual(engine.url.query["sslmode"], "verify-full")

    def test_sqlite_foreign_keys_remain_enabled(self):
        with TemporaryDirectory() as directory:
            engine = create_database_engine(f"sqlite:///{Path(directory) / 'research.db'}")
            try:
                with engine.connect() as connection:
                    self.assertEqual(connection.scalar(text("PRAGMA foreign_keys")), 1)
            finally:
                engine.dispose()


@unittest.skipUnless(os.environ.get("RESEARCHOS_TEST_POSTGRES_URL"), "requires a disposable local PostgreSQL server")
class PostgreSQLIntegrationTests(unittest.TestCase):
    def setUp(self):
        url = make_url(os.environ["RESEARCHOS_TEST_POSTGRES_URL"])
        if url.host not in {"localhost", "127.0.0.1", "::1"} or {"host", "hostaddr"} & url.query.keys():
            self.fail("RESEARCHOS_TEST_POSTGRES_URL must point to a disposable loopback PostgreSQL server")
        admin_engine = create_database_engine(url)
        self.addCleanup(admin_engine.dispose)
        self.admin = admin_engine.raw_connection()
        self.addCleanup(self.admin.close)
        connection = self.admin.driver_connection
        connection.autocommit = True
        name = f"researchos_test_{uuid4().hex}"
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        self.addCleanup(connection.execute, sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))
        self.engine = create_database_engine(url.set(database=name))
        self.addCleanup(self.engine.dispose)

    def test_existing_schemas_are_protected(self):
        with self.engine.begin() as connection:
            connection.execute(text("CREATE TABLE public.users (id INTEGER PRIMARY KEY)"))
            connection.execute(text("INSERT INTO public.users VALUES (42)"))
            connection.execute(text("CREATE SCHEMA researchos"))
            connection.execute(text("CREATE TABLE researchos.users (id INTEGER PRIMARY KEY)"))
            connection.execute(text("INSERT INTO researchos.users VALUES (43)"))
        with self.assertRaisesRegex(RuntimeError, "already exists"):
            migrate(self.engine)
        with self.engine.connect() as connection:
            self.assertEqual(connection.scalar(text("SELECT id FROM public.users")), 42)
            self.assertEqual(connection.scalar(text("SELECT id FROM researchos.users")), 43)
            self.assertEqual(inspect(connection).get_table_names(schema="researchos"), ["users"])

    def test_refuses_a_changed_researchos_schema(self):
        migrate(self.engine)
        with self.engine.begin() as connection:
            connection.execute(text("DROP INDEX researchos.ix_users_email"))
        with self.assertRaisesRegex(RuntimeError, "Table: users"):
            migrate(self.engine)

    def test_concurrent_requests_respect_active_run_limit(self):
        migrate(self.engine)
        sessions = sessionmaker(bind=self.engine)
        with sessions() as db:
            user_id = create_user(db, "Alice", "alice@example.test", PASSWORD).id
        start = Barrier(2, timeout=5)

        def submit():
            with sessions() as db:
                start.wait()
                try:
                    create_run(db, user_id, ResearchRequest(topic="Deep learning"), max_active=1)
                except TooManyRunsError:
                    return False
                return True

        with ThreadPoolExecutor(max_workers=2) as workers:
            results = [workers.submit(submit) for _ in range(2)]
            self.assertCountEqual([result.result(timeout=10) for result in results], [True, False])

    def test_account_session_and_completed_research_persist(self):
        with self.engine.begin() as connection:
            connection.execute(text("CREATE TABLE public.users (id INTEGER PRIMARY KEY)"))

        migrate(self.engine)
        migrate(self.engine)
        sessions = sessionmaker(bind=self.engine)

        def test_db():
            with sessions() as session:
                yield session

        self.addCleanup(app.dependency_overrides.clear)
        app.dependency_overrides[get_db] = test_db
        executor = DeferredExecutor()
        app.dependency_overrides[get_executor] = lambda: executor
        client = TestClient(app, headers={"X-ResearchOS-Client": "web", "Origin": "http://localhost:5173"})
        self.addCleanup(client.close)
        account = {"email": "alice@example.test", "password": PASSWORD}
        signup = client.post("/api/auth/signup", json={"name": "Alice", **account})
        self.assertEqual(signup.status_code, 201, signup.text)
        self.assertIn("HttpOnly", signup.headers["set-cookie"])
        with sessions() as db:
            user = db.get(User, signup.json()["id"])
            self.assertTrue(verify_password(PASSWORD, user.password_hash))
            token = client.cookies["researchos_session"]
            self.assertIsNotNone(db.get(AuthSession, token_digest(token)))
            self.assertIsNone(db.get(AuthSession, token))

        self.assertEqual(client.post("/api/auth/signup", json={"name": "Alice", **account}).status_code, 409)
        client.headers["X-CSRF-Token"] = signup.json()["csrf_token"]
        create = client.post("/api/research", json={"topic": "Deep learning", "source_target": 5})
        self.assertEqual(create.status_code, 202, create.text)
        run_id = create.json()["research_id"]
        self.assertEqual(executor.jobs, [run_id])
        execute_research(run_id, sessions, lambda: ResearchOrchestrator(searcher=SearchAgent(provider=RecordedProvider())))

        self.engine.dispose()
        migrate(self.engine)
        self.assertEqual(client.get("/api/auth/me").status_code, 200)
        history = client.get("/api/research/history")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()[0]["research_id"], run_id)
        self.assertEqual(history.json()[0]["status"], "completed")
        self.assertEqual(client.get(f"/api/research/{run_id}").status_code, 200)
        self.assertEqual(client.post("/api/auth/signout").status_code, 204)
        self.assertEqual(client.get("/api/research/history").status_code, 401)
        self.assertEqual(client.post("/api/auth/signin", json=account).status_code, 200)
        self.assertEqual(client.get("/api/research/history").json()[0]["research_id"], run_id)
        with self.engine.connect() as connection:
            self.assertEqual(connection.scalar(text("SELECT count(*) FROM public.users")), 0)
