"""Tests for the self-hosted email/password auth: registration, login, password
hashing, and JWT-protected routes. Runs against in-memory SQLite (see conftest.py).
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.models.student import Student


def test_register_creates_student_and_returns_token(raw_client: TestClient):
    res = raw_client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "password": "supersecret123", "name": "New Student"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["student"]["email"] == "new@example.com"
    assert body["student"]["name"] == "New Student"


def test_register_rejects_duplicate_email(raw_client: TestClient):
    payload = {"email": "dup@example.com", "password": "supersecret123", "name": "First"}
    first = raw_client.post("/api/auth/register", json=payload)
    assert first.status_code == 200

    second = raw_client.post(
        "/api/auth/register",
        json={**payload, "name": "Second"},
    )
    assert second.status_code == 400


def test_register_recovers_from_concurrent_duplicate_race(raw_client: TestClient, db_session, monkeypatch):
    """Two concurrent registrations with the same email race to insert; the
    unique index catches the loser — it must get a clean 400, not a 500."""
    other_session_factory = sessionmaker(bind=db_session.get_bind())
    original_add = db_session.add
    already_raced = {"done": False}

    def add_with_race(instance):
        if not already_raced["done"] and isinstance(instance, Student):
            already_raced["done"] = True
            other = other_session_factory()
            other.add(Student(email="race@example.com", hashed_password="x", name="Race Winner"))
            other.commit()
            other.close()
        return original_add(instance)

    monkeypatch.setattr(db_session, "add", add_with_race)

    res = raw_client.post(
        "/api/auth/register",
        json={"email": "race@example.com", "password": "supersecret123", "name": "My Real Name"},
    )
    assert res.status_code == 400

    count = db_session.query(Student).filter_by(email="race@example.com").count()
    assert count == 1


def test_login_with_correct_credentials_returns_token(raw_client: TestClient):
    raw_client.post(
        "/api/auth/register",
        json={"email": "login@example.com", "password": "correct-password", "name": "Someone"},
    )

    res = raw_client.post(
        "/api/auth/login", json={"email": "login@example.com", "password": "correct-password"}
    )
    assert res.status_code == 200
    assert res.json()["access_token"]


def test_login_with_wrong_password_rejected(raw_client: TestClient):
    raw_client.post(
        "/api/auth/register",
        json={"email": "wrongpass@example.com", "password": "correct-password", "name": "Someone"},
    )

    res = raw_client.post(
        "/api/auth/login", json={"email": "wrongpass@example.com", "password": "not-the-password"}
    )
    assert res.status_code == 401


def test_login_with_unknown_email_rejected(raw_client: TestClient):
    res = raw_client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": "whatever123"}
    )
    assert res.status_code == 401


def test_password_is_hashed_not_stored_plaintext(raw_client: TestClient, db_session):
    raw_client.post(
        "/api/auth/register",
        json={"email": "hash@example.com", "password": "my-plaintext-password", "name": "Someone"},
    )

    student = db_session.query(Student).filter_by(email="hash@example.com").first()
    assert student.hashed_password != "my-plaintext-password"
    assert student.hashed_password.startswith("$2b$")


def test_protected_route_rejects_missing_token(raw_client: TestClient):
    res = raw_client.get("/api/students/me")
    assert res.status_code == 401


def test_protected_route_accepts_token_from_register(raw_client: TestClient):
    register_res = raw_client.post(
        "/api/auth/register",
        json={"email": "protected@example.com", "password": "supersecret123", "name": "Someone"},
    )
    token = register_res.json()["access_token"]

    res = raw_client.get("/api/students/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["email"] == "protected@example.com"
