"""End-to-end test of the voice message flow, with Azure Speech mocked.

No real Azure Speech key/region or Anthropic key is needed — `transcribe_and_assess`
and `synthesize_speech` are monkeypatched at the call site used by the sessions
route (app.api.routes.sessions.speech), same pattern as the text flow's
`generate_reply` mock in conftest.py.
"""

import base64

import pytest
from fastapi.testclient import TestClient

from app.api.routes import sessions as sessions_route
from app.models.scenario import Scenario
from app.services import speech

FAKE_WAV_BYTES = b"RIFF" + b"\x00" * 40 + b"fake-pcm-payload"


@pytest.fixture()
def mocked_speech(monkeypatch):
    calls = {"transcribe": 0, "synthesize": 0}

    def fake_transcribe_and_assess(wav_bytes: bytes):
        calls["transcribe"] += 1
        return "Hello there, how are you?", {
            "accuracy": 95.0,
            "fluency": 88.0,
            "completeness": 100.0,
            "pronunciation": 91.0,
        }

    def fake_synthesize_speech(text: str) -> bytes:
        calls["synthesize"] += 1
        return b"FAKE_BOT_AUDIO_BYTES"

    monkeypatch.setattr(sessions_route.speech, "transcribe_and_assess", fake_transcribe_and_assess)
    monkeypatch.setattr(sessions_route.speech, "synthesize_speech", fake_synthesize_speech)
    return calls


def _start_voice_session(client: TestClient, scenario: Scenario) -> int:
    start_res = client.post("/api/sessions", json={"scenario_id": scenario.id, "modality": "voice"})
    assert start_res.status_code == 200
    assert start_res.json()["modality"] == "voice"
    return start_res.json()["id"]


def test_voice_message_flow(client: TestClient, scenario: Scenario, mocked_speech):
    session_id = _start_voice_session(client, scenario)

    res = client.post(
        f"/api/sessions/{session_id}/voice-messages",
        files={"audio": ("recording.wav", FAKE_WAV_BYTES, "audio/wav")},
    )
    assert res.status_code == 200
    body = res.json()

    assert body["student_message"]["text"] == "Hello there, how are you?"
    assert body["student_message"]["pronunciation_scores"] == {
        "accuracy": 95.0,
        "fluency": 88.0,
        "completeness": 100.0,
        "pronunciation": 91.0,
    }
    assert body["bot_message"]["text"] == "Reply #1: tell me more!"
    assert base64.b64decode(body["bot_audio_base64"]) == b"FAKE_BOT_AUDIO_BYTES"

    assert mocked_speech["transcribe"] == 1
    assert mocked_speech["synthesize"] == 1

    get_res = client.get(f"/api/sessions/{session_id}")
    # opening + student voice message + bot reply
    assert len(get_res.json()["messages"]) == 3


def test_voice_message_rejected_when_session_not_active(
    client: TestClient, scenario: Scenario, mocked_speech
):
    session_id = _start_voice_session(client, scenario)
    client.post(f"/api/sessions/{session_id}/end")

    res = client.post(
        f"/api/sessions/{session_id}/voice-messages",
        files={"audio": ("recording.wav", FAKE_WAV_BYTES, "audio/wav")},
    )
    assert res.status_code == 400
    assert mocked_speech["transcribe"] == 0


def test_voice_message_returns_422_on_unrecognized_speech(
    client: TestClient, scenario: Scenario, monkeypatch
):
    def fake_transcribe_fails(wav_bytes: bytes):
        raise speech.TranscriptionError("Speech not recognized (reason=NoMatch)")

    monkeypatch.setattr(sessions_route.speech, "transcribe_and_assess", fake_transcribe_fails)

    session_id = _start_voice_session(client, scenario)
    res = client.post(
        f"/api/sessions/{session_id}/voice-messages",
        files={"audio": ("recording.wav", FAKE_WAV_BYTES, "audio/wav")},
    )
    assert res.status_code == 422

    get_res = client.get(f"/api/sessions/{session_id}")
    assert len(get_res.json()["messages"]) == 1  # only the opening message — nothing persisted
