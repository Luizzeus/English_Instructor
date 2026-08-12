from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import MessageAuthor, SessionModality, SessionStatus


class SessionCreateRequest(BaseModel):
    scenario_id: int
    modality: SessionModality = SessionModality.TEXT


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    author: MessageAuthor
    text: str
    created_at: datetime
    pronunciation_scores: dict[str, float] | None = None


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scenario_id: int
    modality: SessionModality
    status: SessionStatus
    started_at: datetime
    ended_at: datetime | None
    messages: list[MessageOut] = []


class SendMessageRequest(BaseModel):
    text: str


class SendMessageResponse(BaseModel):
    student_message: MessageOut
    bot_message: MessageOut


class SendVoiceMessageResponse(BaseModel):
    student_message: MessageOut
    bot_message: MessageOut
    bot_audio_base64: str
