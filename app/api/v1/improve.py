from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.improvement import Improvement, ImprovementStatus
from app.schemas.improvement import ImprovementCreate, ImprovementOut, FeedbackRequest
from app.services.billing_service import charge_credits
from app.tasks.improve_tasks import run_improvement

router = APIRouter(prefix="/improve", tags=["Improvement"])


@router.post("/", response_model=ImprovementOut, status_code=202)
def create_improvement(
    data: ImprovementCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cost = charge_credits(current_user, db)

    item = Improvement(
        user_id=current_user.id,
        credits_charged=cost,
        status=ImprovementStatus.pending,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    task = run_improvement.delay(item.id, data.text)
    item.task_id = task.id
    db.commit()

    return item


@router.get("/", response_model=List[ImprovementOut])
def list_improvements(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 20,
):
    return (
        db.query(Improvement)
        .filter(Improvement.user_id == current_user.id)
        .order_by(Improvement.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/{improvement_id}", response_model=ImprovementOut)
def get_improvement(
    improvement_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(Improvement).filter(
        Improvement.id == improvement_id,
        Improvement.user_id == current_user.id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return item


@router.post("/{improvement_id}/feedback", status_code=200)
def submit_feedback(
    improvement_id: int,
    feedback: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.query(Improvement).filter(
        Improvement.id == improvement_id,
        Improvement.user_id == current_user.id,
        Improvement.status == ImprovementStatus.completed,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found or not completed")

    item.user_rating = feedback.rating
    item.user_accepted = feedback.accepted
    if feedback.correction:
        # Mask PII in user correction before storing
        from ml.improver import mask_pii
        masked_correction, _ = mask_pii(feedback.correction)
        item.user_correction = masked_correction

    db.commit()
    return {"message": "Feedback saved. Thank you!"}
