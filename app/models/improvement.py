from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Float, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class ImprovementStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Improvement(Base):
    __tablename__ = "improvements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(String, index=True)
    status = Column(Enum(ImprovementStatus), default=ImprovementStatus.pending)

    # We store masked text only — never raw original
    masked_text = Column(Text)
    improved_text = Column(Text)
    missing_sections = Column(Text)   # JSON list stored as string
    pii_warnings = Column(Text)       # JSON list stored as string
    method = Column(String)           # 'llm' or 'rules'

    credits_charged = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    # User feedback for continuous learning
    user_rating = Column(Integer)          # 1-5 stars
    user_accepted = Column(Boolean)        # did user use the result?
    user_correction = Column(Text)         # what user actually wrote (anonymized)

    user = relationship("User", backref="improvements")
