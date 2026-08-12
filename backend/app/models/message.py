from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import MessageAuthor


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    author: Mapped[MessageAuthor] = mapped_column(Enum(MessageAuthor, native_enum=False, length=10))
    text: Mapped[str] = mapped_column(Text)
    audio_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    recast_corrections: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pronunciation_scores: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
