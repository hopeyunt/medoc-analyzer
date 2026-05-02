from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class LoyaltyLevel(Base):
    """Rules stored in DB so admin can change them without redeploying."""
    __tablename__ = "loyalty_levels"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)   # Bronze, Silver, Gold
    min_predictions = Column(Integer, nullable=False)     # min predictions/month
    discount_percent = Column(Float, nullable=False)      # 0, 5, 10, 20
    description = Column(String)

    user_loyalties = relationship("UserLoyalty", back_populates="level")


class UserLoyalty(Base):
    __tablename__ = "user_loyalty"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    level_id = Column(Integer, ForeignKey("loyalty_levels.id"), nullable=False)
    predictions_this_month = Column(Integer, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="loyalty")
    level = relationship("LoyaltyLevel", back_populates="user_loyalties")
