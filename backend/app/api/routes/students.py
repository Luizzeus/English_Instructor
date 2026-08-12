from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_student
from app.core.security import ClerkUser, get_current_clerk_user
from app.db.session import get_db
from app.models.student import Student
from app.schemas.student import StudentOut, StudentSyncRequest

router = APIRouter(prefix="/students", tags=["students"])


@router.post("/sync", response_model=StudentOut)
def sync_student(
    body: StudentSyncRequest,
    clerk_user: ClerkUser = Depends(get_current_clerk_user),
    db: Session = Depends(get_db),
) -> Student:
    """Upsert the Student row for the authenticated Clerk user.

    Called by the frontend right after sign-in — Clerk session tokens don't
    carry profile fields like name, so the client supplies them once here.
    """
    student = db.query(Student).filter_by(clerk_user_id=clerk_user.clerk_user_id).first()
    if student is None:
        student = Student(clerk_user_id=clerk_user.clerk_user_id, name=body.name)
        db.add(student)
    else:
        student.name = body.name
    db.commit()
    db.refresh(student)
    return student


@router.get("/me", response_model=StudentOut)
def read_current_student(student: Student = Depends(get_current_student)) -> Student:
    return student
