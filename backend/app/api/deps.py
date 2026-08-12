from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_student_id
from app.db.session import get_db
from app.models.student import Student


def get_current_student(
    student_id: int = Depends(get_current_student_id),
    db: Session = Depends(get_db),
) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Student not found")
    return student
