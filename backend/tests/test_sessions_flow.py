"""End-to-end test of the text conversation prototype against an in-memory SQLite DB.

Runs without a real SQL Server instance or Anthropic API key: `generate_reply` is
monkeypatched and DB access is redirected to a throwaway in-memory database via
FastAPI dependency overrides. Production still targets SQL Server (see
docs/architecture.md) — this is a test-only substitution, not an architecture change.
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


def test_full_conversation_flow(client: TestClient, scenario: Scenario, captured_histories):
    sync_res = client.post("/api/students/sync", json={"name": "Test Student"})
    assert sync_res.status_code == 200
    assert sync_res.json()["name"] == "Test Student"

    start_res = client.post("/api/sessions", json={"scenario_id": scenario.id})
    assert start_res.status_code == 200
    session_data = start_res.json()
    assert session_data["status"] == "active"
    assert len(session_data["messages"]) == 1
    assert session_data["messages"][0]["author"] == "bot"
    assert session_data["messages"][0]["text"] == scenario.system_prompt["opening_message"]
    session_id = session_data["id"]

    turns = [
        "Pretty good, just finishing up a project!",
        "It's been busy but in a good way.",
        "I'm looking forward to the weekend, honestly.",
    ]
    for i, text in enumerate(turns, start=1):
        res = client.post(f"/api/sessions/{session_id}/messages", json={"text": text})
        assert res.status_code == 200
        body = res.json()
        assert body["student_message"]["text"] == text
        assert body["bot_message"]["text"] == f"Reply #{i}: tell me more!"

    # Full history (opening + all prior turns, including the just-sent message)
    # must reach the conversation service every time — this is what "doesn't
    # lose context" means in practice: 1 opening + N-th student turn each time.
    assert captured_histories == [2, 4, 6]

    get_res = client.get(f"/api/sessions/{session_id}")
    assert get_res.status_code == 200
    assert len(get_res.json()["messages"]) == 1 + 2 * len(turns)

    end_res = client.post(f"/api/sessions/{session_id}/end")
    assert end_res.status_code == 200
    assert end_res.json()["status"] == "completed"
    assert end_res.json()["ended_at"] is not None

    # Sending another message after the session ended must be rejected.
    closed_res = client.post(f"/api/sessions/{session_id}/messages", json={"text": "still there?"})
    assert closed_res.status_code == 400


def test_requires_synced_profile_before_starting_session(client: TestClient, scenario: Scenario):
    res = client.post("/api/sessions", json={"scenario_id": scenario.id})
    assert res.status_code == 404


def test_cannot_access_another_students_session(client: TestClient, scenario: Scenario, db_session):
    client.post("/api/students/sync", json={"name": "Owner"})
    start_res = client.post("/api/sessions", json={"scenario_id": scenario.id})
    session_id = start_res.json()["id"]

    # Switch to a different authenticated user mid-test.
    app.dependency_overrides[get_current_clerk_user] = lambda: ClerkUser(
        clerk_user_id="another-clerk-user", session_id="sess_other"
    )
    client.post("/api/students/sync", json={"name": "Intruder"})

    res = client.get(f"/api/sessions/{session_id}")
    assert res.status_code == 404
