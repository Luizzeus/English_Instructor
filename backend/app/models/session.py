from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import SessionModality, SessionStatus
from app.models.message import Message


class ConversationSession(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id"))
    modality: Mapped[SessionModality] = mapped_column(
        Enum(SessionModality, native_enum=False, length=10)
    )
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, native_enum=False, length=15), default=SessionStatus.ACTIVE
    )
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    messages: Mapped[list[Message]] = relationship(order_by="Message.id")
