from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import CefrLevel


class MetricSnapshot(Base):
    """Per-session metric readout. Feeds CefrPromotionLog but never decides promotion by itself."""

    __tablename__ = "metric_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    recorded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    active_vocabulary_count: Mapped[int] = mapped_column(Integer)
    grammar_errors_per_100_words: Mapped[float] = mapped_column(Float)
    words_per_minute: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_syntactic_complexity: Mapped[float] = mapped_column(Float)
    estimated_cefr_level: Mapped[CefrLevel] = mapped_column(
        Enum(CefrLevel, native_enum=False, length=2)
    )


class CefrPromotionLog(Base):
    """Explicit, auditable record of level changes — the rule applied must always be traceable here."""

    __tablename__ = "cefr_promotion_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    previous_level: Mapped[CefrLevel] = mapped_column(Enum(CefrLevel, native_enum=False, length=2))
    new_level: Mapped[CefrLevel] = mapped_column(Enum(CefrLevel, native_enum=False, length=2))
    metrics_used: Mapped[dict] = mapped_column(JSON)
    rule_applied: Mapped[str] = mapped_column(String(255))
