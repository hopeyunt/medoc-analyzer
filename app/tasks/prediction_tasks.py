from datetime import datetime, timezone

from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.prediction import Prediction, PredictionStatus
from app.models.loyalty import UserLoyalty
from ml.analyzer import analyze_document


@celery_app.task(bind=True, max_retries=3)
def run_analysis(self, prediction_id: int, text: str):
    db = SessionLocal()
    try:
        prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
        if not prediction:
            return

        prediction.status = PredictionStatus.processing
        db.commit()

        result = analyze_document(text)

        prediction.status = PredictionStatus.completed
        prediction.result = result
        prediction.quality_score = result["quality_score"]
        prediction.document_type = result["document_type"]
        prediction.completed_at = datetime.now(timezone.utc)

        loyalty = db.query(UserLoyalty).filter(UserLoyalty.user_id == prediction.user_id).first()
        if loyalty:
            loyalty.predictions_this_month += 1

        db.commit()
    except Exception as exc:
        db.rollback()
        prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
        if prediction:
            prediction.status = PredictionStatus.failed
            db.commit()
        raise self.retry(exc=exc, countdown=5)
    finally:
        db.close()
