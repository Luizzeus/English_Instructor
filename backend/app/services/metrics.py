"""Session-level evolution metrics: active vocabulary, grammar error rate, fluency.

All three are deliberately simple heuristics for this first pass (see
docs/architecture.md backlog item 6), not validated linguistic measures:

- active_vocabulary_count: unique non-stopword word types the student used —
  not verified to be used *correctly*, just used.
- grammar_errors_per_100_words: Claude grades the session's student messages
  as a one-off structured pass (separate from the implicit recast the bot does
  mid-conversation, which isn't machine-readable). This is a heuristic
  assessment, not a validated grammar checker — see the "qualidade da
  correção gramatical automática" risk note in docs/architecture.md.
- words_per_minute: only computed for voice turns (needs real elapsed time);
  None for text-only sessions, since typing speed isn't spoken fluency.

estimated_cefr_level here just echoes the student's current level — actual
promotion logic (backlog item 7) hasn't been built yet and must stay a
separate, auditable, rule-based step, not something inferred silently here.
"""

import json
import re

from app.core.config import get_settings
from app.models.enums import MessageAuthor
from app.models.message import Message
from app.models.student import Student
from app.services.llm_client import get_anthropic_client

_WORD_RE = re.compile(r"[A-Za-z']+")
_SENTENCE_SPLIT_RE = re.compile(r"[.!?]+")

_STOPWORDS = frozenset(
    """
    a an the and or but if then so because as of at by for with about against between into through
    during before after above below to from up down in out on off over under again further once
    here there when where why how all any both each few more most other some such no nor not only
    own same than too very s t can will just don should now i me my myself we our ours ourselves
    you your yours yourself yourselves he him his himself she her hers herself it its itself they
    them their theirs themselves what which who whom this that these those am is are was were be
    been being have has had having do does did doing would could might must shall ought im ive
    youre youve hes shes were theyre dont doesnt didnt wasnt werent isnt arent wont wouldnt couldnt
    shouldnt hasnt havent hadnt yeah um uh like well okay ok
    """.split()
)


def compute_vocabulary_and_complexity(texts: list[str]) -> tuple[int, float]:
    """Returns (active_vocabulary_count, avg_syntactic_complexity)."""
    joined = " ".join(texts)
    words = [w.lower() for w in _WORD_RE.findall(joined)]
    vocabulary = {w for w in words if w not in _STOPWORDS and len(w) > 1}

    sentences = [s for s in _SENTENCE_SPLIT_RE.split(joined) if s.strip()]
    if not sentences:
        return len(vocabulary), 0.0

    words_per_sentence = [len(_WORD_RE.findall(s)) for s in sentences]
    avg_complexity = sum(words_per_sentence) / len(words_per_sentence)

    return len(vocabulary), avg_complexity


def _count_words(texts: list[str]) -> int:
    return len(_WORD_RE.findall(" ".join(texts)))


def _parse_total_errors(raw_text: str) -> int:
    try:
        data = json.loads(raw_text.strip())
        return max(0, int(data["total_errors"]))
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return 0


def grade_grammar_errors(texts: list[str]) -> tuple[float, int]:
    """Returns (errors_per_100_words, total_errors_found)."""
    total_words = _count_words(texts)
    if total_words == 0:
        return 0.0, 0

    client = get_anthropic_client()
    settings = get_settings()

    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=100,
        system=(
            "You are a strict but fair English grammar and word-choice error counter used for "
            "internal learning analytics. Count the total number of grammar or word-choice errors "
            "across all the numbered sentences combined. Respond with ONLY a JSON object like "
            '{"total_errors": 3} — no explanation, no markdown, no other text.'
        ),
        messages=[{"role": "user", "content": numbered}],
    )

    total_errors = _parse_total_errors(response.content[0].text)
    return (total_errors / total_words) * 100, total_errors


def compute_fluency_wpm(voice_turns: list[tuple[str, float]]) -> float | None:
    """voice_turns: (text, audio_duration_seconds) pairs for the session's voice messages."""
    total_words = 0
    total_seconds = 0.0
    for text, duration in voice_turns:
        if duration <= 0:
            continue
        total_words += len(_WORD_RE.findall(text))
        total_seconds += duration

    if total_seconds == 0:
        return None

    return (total_words / total_seconds) * 60


def build_metric_snapshot_fields(student: Student, messages: list[Message]) -> dict:
    student_messages = [m for m in messages if m.author == MessageAuthor.STUDENT]
    student_texts = [m.text for m in student_messages]
    voice_turns = [
        (m.text, m.audio_duration_seconds)
        for m in student_messages
        if m.audio_duration_seconds is not None
    ]

    vocabulary_count, avg_complexity = compute_vocabulary_and_complexity(student_texts)
    errors_per_100_words, _ = grade_grammar_errors(student_texts)
    wpm = compute_fluency_wpm(voice_turns)

    return {
        "active_vocabulary_count": vocabulary_count,
        "grammar_errors_per_100_words": errors_per_100_words,
        "words_per_minute": wpm,
        "avg_syntactic_complexity": avg_complexity,
        "estimated_cefr_level": student.current_cefr_level,
    }
