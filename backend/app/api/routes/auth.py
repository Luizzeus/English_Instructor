from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.student import Student
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    student = Student(
        email=body.email.lower(),
        hashed_password=hash_password(body.password),
        name=body.name,
    )
    db.add(student)
    try:
        db.commit()
    except IntegrityError as exc:
        # Two concurrent registrations for the same email race to insert —
        # the unique index catches the loser here instead of a raw 500.
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered") from exc
    db.refresh(student)

    token = create_access_token(student.id)
    return TokenResponse(access_token=token, student=student)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    student = db.query(Student).filter_by(email=body.email.lower()).first()
    if student is None or not verify_password(body.password, student.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    token = create_access_token(student.id)
    return TokenResponse(access_token=token, student=student)
