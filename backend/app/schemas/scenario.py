from pydantic import BaseModel, ConfigDict

from app.models.enums import CefrLevel


class ScenarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    bot_persona: str
    target_cefr_level: CefrLevel
    tags: list[str]
