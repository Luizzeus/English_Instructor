from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import CefrLevel


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    current_cefr_level: CefrLevel
    bot_tone_preference: str
    default_session_minutes: int
    created_at: datetime
