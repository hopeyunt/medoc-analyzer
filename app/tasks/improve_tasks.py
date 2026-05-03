import json
from datetime import datetime, timezone

from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.improvement import Improvement, ImprovementStatus
from app.models.loyalty import UserLoyalty
from ml.improver import improve_text


@celery_app.task(bind=True, max_retries=3)
def run_improvement(self, improvement_id: int, text: str):
    db = SessionLocal()
    try:
        item = db.query(Improvement).filter(Improvement.id == improvement_id).first()
        if not item:
            return

        item.status = ImprovementStatus.processing
        db.commit()

        result = improve_text(text)

        item.status = ImprovementStatus.completed
        item.masked_text = result["masked_text"]
        item.improved_text = result["improved_text"]
        item.missing_sections = json.dumps(result["missing_sections"], ensure_ascii=False)
        item.pii_warnings = json.dumps(result["pii_warnings"], ensure_ascii=False)
        item.method = result["method"]
        item.completed_at = datetime.now(timezone.utc)

        loyalty = db.query(UserLoyalty).filter(UserLoyalty.user_id == item.user_id).first()
        if loyalty:
            loyalty.predictions_this_month += 1

        db.commit()
    except Exception as exc:
        db.rollback()
        item = db.query(Improvement).filter(Improvement.id == improvement_id).first()
        if item:
            item.status = ImprovementStatus.failed
            db.commit()
        raise self.retry(exc=exc, countdown=5)
    finally:
        db.close()
