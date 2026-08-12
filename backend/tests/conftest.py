"""Shared fixtures: in-memory SQLite DB + FastAPI TestClient with auth/LLM mocked.

Lets the test suite exercise the full API layer without a real SQL Server
instance or live Anthropic/Azure credentials — see docs/architecture.md.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import sessions as sessions_route
from app.core.security import ClerkUser, get_current_clerk_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.enums import CefrLevel
from app.models.scenario import Scenario

CLERK_USER_ID = "test-clerk-user"


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def captured_histories():
    return []


@pytest.fixture()
def client(db_session, captured_histories, monkeypatch):
    def fake_generate_reply(scenario, student, history):
        captured_histories.append(len(history))
        return f"Reply #{len(captured_histories)}: tell me more!"

    monkeypatch.setattr(sessions_route.conversation, "generate_reply", fake_generate_reply)
    # end_session computes metrics, including a grammar-error grading pass via
    # Claude — mock it here too so any test that ends a session doesn't need a
    # real ANTHROPIC_API_KEY. Tests targeting metrics specifically override this.
    monkeypatch.setattr(sessions_route.metrics, "grade_grammar_errors", lambda texts: (0.0, 0))

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_clerk_user] = lambda: ClerkUser(
        clerk_user_id=CLERK_USER_ID, session_id="sess_test"
    )

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture()
def scenario(db_session) -> Scenario:
    scenario = Scenario(
        name="Small talk profissional",
        description="Small talk before a remote meeting.",
        bot_persona="a friendly coworker named Alex",
        system_prompt={
            "role_description": "You play Alex, a colleague on a call.",
            "objective": "Keep light small talk going.",
            "opening_message": "Hey! How's your week going so far?",
        },
        target_cefr_level=CefrLevel.B1,
        tags=["trabalho remoto", "small talk"],
    )
    db_session.add(scenario)
    db_session.commit()
    db_session.refresh(scenario)
    return scenario
