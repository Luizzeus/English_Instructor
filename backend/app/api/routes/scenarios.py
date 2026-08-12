from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_clerk_user
from app.db.session import get_db
from app.models.scenario import Scenario
from app.schemas.scenario import ScenarioOut

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("", response_model=list[ScenarioOut], dependencies=[Depends(get_current_clerk_user)])
def list_scenarios(db: Session = Depends(get_db)) -> list[Scenario]:
    return db.query(Scenario).all()
