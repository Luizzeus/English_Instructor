"""Regression test for a real race condition found while manually testing the app:
React StrictMode (and, in production, a duplicate tab or a network retry) can fire
two concurrent POST /api/students/sync for the same brand-new Clerk user. Both see
"no student yet" and race to INSERT; the loser must recover instead of 500ing.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.models.student import Student
from tests.conftest import CLERK_USER_ID


def test_sync_student_recovers_from_concurrent_insert_race(
    client: TestClient, db_session, monkeypatch
):
    other_session_factory = sessionmaker(bind=db_session.get_bind())
    original_add = db_session.add
    already_raced = {"done": False}

    def add_with_race(instance):
        # The instant our request stages its own INSERT, an independent DB
        # session wins the race and commits first for the same clerk_user_id —
        # reproducing the real unique-index conflict the fix must survive.
        if not already_raced["done"] and isinstance(instance, Student):
            already_raced["done"] = True
            other = other_session_factory()
            other.add(Student(clerk_user_id=CLERK_USER_ID, name="Race Winner"))
            other.commit()
            other.close()
        return original_add(instance)

    monkeypatch.setattr(db_session, "add", add_with_race)

    res = client.post("/api/students/sync", json={"name": "My Real Name"})

    assert res.status_code == 200
    assert res.json()["name"] == "My Real Name"

    count = db_session.query(Student).filter_by(clerk_user_id=CLERK_USER_ID).count()
    assert count == 1
