from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import ClerkUser, get_current_clerk_user
from app.db.session import get_db
from app.models.student import Student


def get_current_student(
    clerk_user: ClerkUser = Depends(get_current_clerk_user),
    db: Session = Depends(get_db),
) -> Student:
    student = db.query(Student).filter_by(clerk_user_id=clerk_user.clerk_user_id).first()
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Student profile not synced yet")
    return student
