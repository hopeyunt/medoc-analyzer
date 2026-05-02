from pydantic import BaseModel
from datetime import datetime
from app.models.transaction import TransactionType


class DepositRequest(BaseModel):
    amount: float


class TransactionOut(BaseModel):
    id: int
    amount: float
    type: TransactionType
    description: Optional[str]
    balance_after: float
    created_at: datetime

    model_config = {"from_attributes": True}


class BalanceOut(BaseModel):
    credits: float
    loyalty_level: str
    discount_percent: float


from typing import Optional
