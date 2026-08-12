"""Tests for the evolution metrics service: vocabulary/complexity heuristics,
LLM-graded error rate, voice fluency, and session-end persistence + history endpoint.
"""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.services import metrics


def test_compute_vocabulary_and_complexity_counts_unique_content_words():
    texts = [
        "I went to the store yesterday and bought some apples.",
        "The weather has been really nice this week, honestly.",
    ]
    count, complexity = metrics.compute_vocabulary_and_complexity(texts)
    assert count > 0
    assert complexity > 0


def test_compute_vocabulary_and_complexity_handles_empty_input():
    count, complexity = metrics.compute_vocabulary_and_complexity([])
    assert count == 0
    assert complexity == 0.0


def test_compute_fluency_wpm_weights_across_turns():
    wpm = metrics.compute_fluency_wpm(
        [
            ("hello there how are you doing today", 6.0),  # 7 words
            ("i am doing great thanks", 6.0),  # 5 words
        ]
    )
    # total words = 12, total seconds = 12 -> 60 wpm
    assert wpm == pytest.approx(60.0)


def test_compute_fluency_wpm_returns_none_without_voice_turns():
    assert metrics.compute_fluency_wpm([]) is None


def test_grade_grammar_errors_uses_llm_and_computes_rate(monkeypatch):
    fake_provider = SimpleNamespace(generate=lambda **kwargs: '{"total_errors": 2}')
    monkeypatch.setattr(metrics, "get_llm_provider", lambda: fake_provider)

    texts = ["This is five words here", "And this is five more"]  # 10 words total
    rate, total_errors = metrics.grade_grammar_errors(texts)

    assert total_errors == 2
    assert rate == pytest.approx(20.0)  # 2 errors / 10 words * 100


def test_grade_grammar_errors_skips_llm_call_when_no_words(monkeypatch):
    def fail_if_called():
        raise AssertionError("should not call the LLM provider for empty input")

    monkeypatch.setattr(metrics, "get_llm_provider", fail_if_called)
    assert metrics.grade_grammar_errors([]) == (0.0, 0)


def test_grade_grammar_errors_falls_back_to_zero_on_malformed_llm_output(monkeypatch):
    fake_provider = SimpleNamespace(generate=lambda **kwargs: "not json at all")
    monkeypatch.setattr(metrics, "get_llm_provider", lambda: fake_provider)

    assert metrics.grade_grammar_errors(["some words here"]) == (0.0, 0)


def test_end_session_persists_metric_snapshot_and_appears_in_history(client: TestClient, scenario):
    start_res = client.post("/api/sessions", json={"scenario_id": scenario.id})
    session_id = start_res.json()["id"]

    client.post(
        f"/api/sessions/{session_id}/messages",
        json={"text": "I really enjoy hiking on weekends."},
    )

    end_res = client.post(f"/api/sessions/{session_id}/end")
    assert end_res.status_code == 200

    history_res = client.get("/api/students/me/metrics")
    assert history_res.status_code == 200
    snapshots = history_res.json()
    assert len(snapshots) == 1

    snapshot = snapshots[0]
    assert snapshot["session_id"] == session_id
    assert snapshot["active_vocabulary_count"] > 0
    assert snapshot["avg_syntactic_complexity"] > 0
    assert snapshot["grammar_errors_per_100_words"] == 0.0  # mocked in conftest's client fixture
    assert snapshot["words_per_minute"] is None  # text-only session
    assert snapshot["estimated_cefr_level"] == "A2"  # Student model default
