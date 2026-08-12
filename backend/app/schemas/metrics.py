from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import CefrLevel


class MetricSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    recorded_at: datetime
    active_vocabulary_count: int
    grammar_errors_per_100_words: float
    words_per_minute: float | None
    avg_syntactic_complexity: float
    estimated_cefr_level: CefrLevel
