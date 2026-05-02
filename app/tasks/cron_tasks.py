from celery.schedules import crontab
from app.tasks.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.user import User
from app.models.loyalty import UserLoyalty
from app.services.loyalty_service import recalculate_loyalty

# Run every 1st day of month at 00:00
celery_app.conf.beat_schedule = {
    "monthly-loyalty-recalc": {
        "task": "app.tasks.cron_tasks.recalculate_all_loyalty",
        "schedule": crontab(day_of_month=1, hour=0, minute=0),
    }
}


@celery_app.task
def recalculate_all_loyalty():
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.is_active == True).all()
        for user in users:
            recalculate_loyalty(user, db)

        # Reset monthly counter
        db.query(UserLoyalty).update({"predictions_this_month": 0})
        db.commit()
    finally:
        db.close()
