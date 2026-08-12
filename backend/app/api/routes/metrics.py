from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_student
from app.db.session import get_db
from app.models.metric import MetricSnapshot
from app.models.student import Student
from app.schemas.metrics import MetricSnapshotOut

router = APIRouter(prefix="/students/me/metrics", tags=["metrics"])


@router.get("", response_model=list[MetricSnapshotOut])
def list_my_metrics(
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> list[MetricSnapshot]:
    return (
        db.query(MetricSnapshot)
        .filter_by(student_id=student.id)
        .order_by(MetricSnapshot.recorded_at)
        .all()
    )
