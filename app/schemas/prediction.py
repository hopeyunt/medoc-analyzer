from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any
from app.models.prediction import PredictionStatus


class PredictionCreate(BaseModel):
    text: str


class PredictionOut(BaseModel):
    id: int
    task_id: Optional[str]
    status: PredictionStatus
    quality_score: Optional[float]
    document_type: Optional[str]
    result: Optional[Dict[str, Any]]
    credits_charged: float
    created_at: datetime

    model_config = {"from_attributes": True}
