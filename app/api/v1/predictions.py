from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.prediction import Prediction, PredictionStatus
from app.schemas.prediction import PredictionCreate, PredictionOut
from app.services.billing_service import charge_credits
from app.tasks.prediction_tasks import run_analysis

router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.post("/", response_model=PredictionOut, status_code=202)
def create_prediction(
    data: PredictionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if len(data.text.strip()) < 10:
        raise HTTPException(status_code=422, detail="Text too short")

    # Charge credits BEFORE creating task (atomic: if charge fails, no task created)
    cost = charge_credits(current_user, db)

    prediction = Prediction(
        user_id=current_user.id,
        text_length=len(data.text),
        credits_charged=cost,
        status=PredictionStatus.pending,
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)

    task = run_analysis.delay(prediction.id, data.text)
    prediction.task_id = task.id
    db.commit()

    return prediction


@router.get("/", response_model=List[PredictionOut])
def list_predictions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 20,
):
    return (
        db.query(Prediction)
        .filter(Prediction.user_id == current_user.id)
        .order_by(Prediction.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/{prediction_id}", response_model=PredictionOut)
def get_prediction(
    prediction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    prediction = db.query(Prediction).filter(
        Prediction.id == prediction_id,
        Prediction.user_id == current_user.id,
    ).first()
    if not prediction:
        raise HTTPException(status_code=404, detail="Not found")
    return prediction
