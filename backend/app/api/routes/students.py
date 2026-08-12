from fastapi import APIRouter, Depends

from app.api.deps import get_current_student
from app.models.student import Student
from app.schemas.student import StudentOut

router = APIRouter(prefix="/students", tags=["students"])


@router.get("/me", response_model=StudentOut)
def read_current_student(student: Student = Depends(get_current_student)) -> Student:
    return student
