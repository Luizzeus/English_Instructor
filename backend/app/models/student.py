from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import CefrLevel


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    current_cefr_level: Mapped[CefrLevel] = mapped_column(
        Enum(CefrLevel, native_enum=False, length=2), default=CefrLevel.A2
    )
    bot_tone_preference: Mapped[str] = mapped_column(String(50), default="casual")
    default_session_minutes: Mapped[int] = mapped_column(default=10)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
