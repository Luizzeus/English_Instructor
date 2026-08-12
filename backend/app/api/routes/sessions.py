from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.api.deps import get_current_student
from app.db.session import get_db
from app.models.enums import MessageAuthor, SessionModality, SessionStatus
from app.models.message import Message
from app.models.scenario import Scenario
from app.models.session import ConversationSession
from app.models.student import Student
from app.schemas.session import (
    SendMessageRequest,
    SendMessageResponse,
    SessionCreateRequest,
    SessionOut,
)
from app.services import conversation

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _get_owned_session(db: DbSession, session_id: int, student: Student) -> ConversationSession:
    session = db.get(ConversationSession, session_id)
    if session is None or session.student_id != student.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    return session


@router.post("", response_model=SessionOut)
def start_session(
    body: SessionCreateRequest,
    student: Student = Depends(get_current_student),
    db: DbSession = Depends(get_db),
) -> ConversationSession:
    scenario = db.get(Scenario, body.scenario_id)
    if scenario is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scenario not found")

    session = ConversationSession(
        student_id=student.id,
        scenario_id=scenario.id,
        modality=SessionModality.TEXT,
    )
    db.add(session)
    db.flush()

    opening = scenario.system_prompt.get("opening_message", "Hi! Let's get started.")
    db.add(Message(session_id=session.id, author=MessageAuthor.BOT, text=opening))
    db.commit()
    db.refresh(session)
    return session


@router.get("/{session_id}", response_model=SessionOut)
def get_session(
    session_id: int,
    student: Student = Depends(get_current_student),
    db: DbSession = Depends(get_db),
) -> ConversationSession:
    return _get_owned_session(db, session_id, student)


@router.post("/{session_id}/messages", response_model=SendMessageResponse)
def send_message(
    session_id: int,
    body: SendMessageRequest,
    student: Student = Depends(get_current_student),
    db: DbSession = Depends(get_db),
) -> SendMessageResponse:
    session = _get_owned_session(db, session_id, student)
    if session.status != SessionStatus.ACTIVE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Session is not active")

    scenario = db.get(Scenario, session.scenario_id)

    student_message = Message(session_id=session.id, author=MessageAuthor.STUDENT, text=body.text)
    db.add(student_message)
    db.flush()

    history = db.query(Message).filter_by(session_id=session.id).order_by(Message.id).all()
    reply_text = conversation.generate_reply(scenario, student, history)

    bot_message = Message(session_id=session.id, author=MessageAuthor.BOT, text=reply_text)
    db.add(bot_message)
    db.commit()
    db.refresh(student_message)
    db.refresh(bot_message)

    return SendMessageResponse(student_message=student_message, bot_message=bot_message)


@router.post("/{session_id}/end", response_model=SessionOut)
def end_session(
    session_id: int,
    student: Student = Depends(get_current_student),
    db: DbSession = Depends(get_db),
) -> ConversationSession:
    session = _get_owned_session(db, session_id, student)
    session.status = SessionStatus.COMPLETED
    session.ended_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)
    return session
