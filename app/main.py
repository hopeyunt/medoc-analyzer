from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.database import engine, SessionLocal, Base
from app.models import User, Transaction, Prediction, LoyaltyLevel, UserLoyalty  # noqa: ensure tables created
from app.api.v1 import auth, users, predictions, billing
from app.services.loyalty_service import seed_loyalty_levels

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MedDoc Analyzer",
    description="ML-сервис анализа качества медицинской документации",
    version="1.0.0",
)

Instrumentator().instrument(app).expose(app)

app.include_router(auth.router,        prefix="/api/v1")
app.include_router(users.router,       prefix="/api/v1")
app.include_router(predictions.router, prefix="/api/v1")
app.include_router(billing.router,     prefix="/api/v1")


@app.on_event("startup")
def startup():
    db = SessionLocal()
    try:
        seed_loyalty_levels(db)
    finally:
        db.close()


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok"}
