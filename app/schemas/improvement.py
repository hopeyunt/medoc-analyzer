from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ImprovementCreate(BaseModel):
    text: str = Field(..., min_length=10, description="Исходный текст медицинского документа")


class FeedbackRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    accepted: bool
    correction: Optional[str] = None


class ImprovementOut(BaseModel):
    id: int
    status: str
    method: Optional[str] = None
    improved_text: Optional[str] = None
    missing_sections: Optional[str] = None
    pii_warnings: Optional[str] = None
    credits_charged: float
    created_at: datetime
    completed_at: Optional[datetime] = None
    user_rating: Optional[int] = None
    user_accepted: Optional[bool] = None

    class Config:
        from_attributes = True
