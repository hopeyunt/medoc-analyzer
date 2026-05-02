from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.user import User
from app.models.transaction import Transaction, TransactionType
from app.models.loyalty import UserLoyalty, LoyaltyLevel
from app.core.config import settings


def get_user_discount(user: User, db: Session) -> float:
    """Returns discount fraction (e.g. 0.10 for 10% off)."""
    loyalty = db.query(UserLoyalty).filter(UserLoyalty.user_id == user.id).first()
    if not loyalty:
        return 0.0
    level = db.query(LoyaltyLevel).filter(LoyaltyLevel.id == loyalty.level_id).first()
    return (level.discount_percent / 100) if level else 0.0


def charge_credits(user: User, db: Session) -> float:
    """
    Deducts credits for one prediction atomically.
    Returns actual amount charged.
    Raises HTTPException if balance is insufficient.
    """
    discount = get_user_discount(user, db)
    cost = round(settings.COST_PER_PREDICTION * (1 - discount), 4)

    if user.credits < cost:
        raise HTTPException(status_code=402, detail="Insufficient credits")

    user.credits = round(user.credits - cost, 4)

    tx = Transaction(
        user_id=user.id,
        amount=-cost,
        type=TransactionType.charge,
        description=f"Prediction analysis (discount {discount*100:.0f}%)",
        balance_after=user.credits,
    )
    db.add(tx)
    # Caller must commit
    return cost


def deposit_credits(user: User, amount: float, db: Session) -> None:
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    user.credits = round(user.credits + amount, 4)
    tx = Transaction(
        user_id=user.id,
        amount=amount,
        type=TransactionType.deposit,
        description="Manual deposit",
        balance_after=user.credits,
    )
    db.add(tx)
