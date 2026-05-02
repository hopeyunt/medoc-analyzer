from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class PredictionStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(String, index=True)
    status = Column(Enum(PredictionStatus), default=PredictionStatus.pending)
    # We store only hash of text, not raw text (privacy)
    text_hash = Column(String)
    text_length = Column(Integer)
    result = Column(JSON)
    quality_score = Column(Float)
    document_type = Column(String)
    credits_charged = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="predictions")
