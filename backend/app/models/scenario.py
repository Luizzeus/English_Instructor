from sqlalchemy import JSON, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import CefrLevel


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    bot_persona: Mapped[str] = mapped_column(String(255))
    system_prompt: Mapped[dict] = mapped_column(JSON)
    target_cefr_level: Mapped[CefrLevel] = mapped_column(
        Enum(CefrLevel, native_enum=False, length=2)
    )
    tags: Mapped[list] = mapped_column(JSON, default=list)
