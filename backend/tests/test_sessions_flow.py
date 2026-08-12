"""End-to-end test of the text conversation prototype against an in-memory SQLite DB.

Runs without a real Postgres instance or a live Ollama/Anthropic call:
`generate_reply` is monkeypatched and DB access is redirected to a throwaway
in-memory database via FastAPI dependency overrides (see conftest.py).
"""

from fastapi.testclient import TestClient

from app.api import deps
from app.core.security import hash_password
from app.main import app
from app.models.scenario import Scenario
from app.models.student import Student


def test_full_conversation_flow(client: TestClient, scenario: Scenario, captured_histories):
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


def test_rejects_token_for_nonexistent_student(client: TestClient, scenario: Scenario):
    # A token can outlive the account it points to (e.g. deleted after issuance).
    app.dependency_overrides[deps.get_current_student_id] = lambda: 999_999
    del app.dependency_overrides[deps.get_current_student]

    res = client.post("/api/sessions", json={"scenario_id": scenario.id})
    assert res.status_code == 401


def test_cannot_access_another_students_session(client: TestClient, scenario: Scenario, db_session):
    start_res = client.post("/api/sessions", json={"scenario_id": scenario.id})
    session_id = start_res.json()["id"]

    intruder = Student(
        email="intruder@example.com", hashed_password=hash_password("x"), name="Intruder"
    )
    db_session.add(intruder)
    db_session.commit()
    db_session.refresh(intruder)

    # Switch to a different authenticated user mid-test.
    app.dependency_overrides[deps.get_current_student] = lambda: intruder

    res = client.get(f"/api/sessions/{session_id}")
    assert res.status_code == 404
