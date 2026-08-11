from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import ExerciseType


class ExerciseAttempt(Base):
    __tablename__ = "exercise_attempts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    exercise_type: Mapped[ExerciseType] = mapped_column(
        Enum(ExerciseType, native_enum=False, length=30)
    )
    target_item: Mapped[str] = mapped_column(String(255))
    was_correct: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SpacedRepetitionCard(Base):
    __tablename__ = "spaced_repetition_cards"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    item: Mapped[str] = mapped_column(String(255))
    next_review_at: Mapped[datetime] = mapped_column(DateTime)
    current_interval_days: Mapped[int] = mapped_column(Integer, default=1)
    correct_streak: Mapped[int] = mapped_column(Integer, default=0)
