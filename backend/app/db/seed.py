"""Idempotent seed data for local/dev environments. Run with `python -m app.db.seed`."""

from app.db.session import SessionLocal
from app.models.enums import CefrLevel
from app.models.scenario import Scenario

SCENARIOS: list[dict] = [
    {
        "name": "Small talk profissional",
        "description": (
            "Uma conversa informal antes de uma reunião remota começar — o tipo de papo rápido "
            "que acontece enquanto as pessoas entram na chamada."
        ),
        "bot_persona": "a friendly coworker named Alex joining a video call",
        "system_prompt": {
            "role_description": (
                "You play Alex, a colleague hopping onto a work video call a few minutes early. "
                "You make natural small talk while waiting for others to join — weekend plans, "
                "the weather, a recent tech news item, how the week is going."
            ),
            "objective": (
                "Keep a light, natural professional small-talk conversation going, showing "
                "genuine interest in the student's answers and asking natural follow-up questions."
            ),
            "opening_message": (
                "Hey! Good to see you — you're the first one here. How's your week going so far?"
            ),
        },
        "target_cefr_level": CefrLevel.B1,
        "tags": ["trabalho remoto", "small talk", "networking"],
    }
]


def seed() -> None:
    db = SessionLocal()
    try:
        for data in SCENARIOS:
            exists = db.query(Scenario).filter_by(name=data["name"]).first()
            if exists:
                print(f"skip (exists): {data['name']}")
                continue
            db.add(Scenario(**data))
            print(f"seeded: {data['name']}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
