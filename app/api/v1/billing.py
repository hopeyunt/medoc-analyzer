from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.transaction import Transaction
from app.models.loyalty import UserLoyalty, LoyaltyLevel
from app.schemas.billing import DepositRequest, TransactionOut, BalanceOut
from app.services.billing_service import deposit_credits

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get("/balance", response_model=BalanceOut)
def get_balance(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    loyalty = db.query(UserLoyalty).filter(UserLoyalty.user_id == current_user.id).first()
    level = db.query(LoyaltyLevel).filter(LoyaltyLevel.id == loyalty.level_id).first() if loyalty else None
    return BalanceOut(
        credits=current_user.credits,
        loyalty_level=level.name if level else "Bronze",
        discount_percent=level.discount_percent if level else 0.0,
    )


@router.post("/deposit")
def deposit(data: DepositRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    deposit_credits(current_user, data.amount, db)
    db.commit()
    db.refresh(current_user)
    return {"credits": current_user.credits, "message": f"Added {data.amount} credits"}


@router.get("/transactions", response_model=List[TransactionOut])
def get_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 20,
):
    return (
        db.query(Transaction)
        .filter(Transaction.user_id == current_user.id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
        .all()
    )
