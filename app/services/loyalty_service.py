from sqlalchemy.orm import Session
from app.models.loyalty import LoyaltyLevel, UserLoyalty
from app.models.user import User


def recalculate_loyalty(user: User, db: Session) -> None:
    """Assign loyalty level based on predictions_this_month. Called by cron."""
    loyalty = db.query(UserLoyalty).filter(UserLoyalty.user_id == user.id).first()
    if not loyalty:
        return

    levels = db.query(LoyaltyLevel).order_by(LoyaltyLevel.min_predictions.desc()).all()
    for level in levels:
        if loyalty.predictions_this_month >= level.min_predictions:
            loyalty.level_id = level.id
            break


def seed_loyalty_levels(db: Session) -> None:
    """Create default Bronze/Silver/Gold levels if they don't exist."""
    defaults = [
        {"name": "Bronze", "min_predictions": 0,  "discount_percent": 0,  "description": "Default level"},
        {"name": "Silver", "min_predictions": 20, "discount_percent": 5,  "description": "5% discount"},
        {"name": "Gold",   "min_predictions": 50, "discount_percent": 10, "description": "10% discount"},
    ]
    for item in defaults:
        exists = db.query(LoyaltyLevel).filter(LoyaltyLevel.name == item["name"]).first()
        if not exists:
            db.add(LoyaltyLevel(**item))
    db.commit()
