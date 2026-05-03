from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.database import engine, SessionLocal, Base
# импортируем все модели, чтобы SQLAlchemy создал таблицы
from app.models import User, Transaction, Prediction, LoyaltyLevel, UserLoyalty, Improvement  # noqa
from app.api.v1 import auth, users, predictions, billing, improve
from app.services.loyalty_service import seed_loyalty_levels

# создаём все таблицы при старте (если не существуют)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MedDoc Analyzer",
    description="Сервис анализа и улучшения качества медицинской документации. "
                "Поддерживает загрузку текстов, автоматическое улучшение структуры и биллинг кредитов.",
    version="1.0.0",
)

# подключаем Prometheus метрики — появятся на /metrics
Instrumentator().instrument(app).expose(app)

app.include_router(auth.router,        prefix="/api/v1")
app.include_router(users.router,       prefix="/api/v1")
app.include_router(predictions.router, prefix="/api/v1")
app.include_router(billing.router,     prefix="/api/v1")
app.include_router(improve.router,     prefix="/api/v1")


@app.on_event("startup")
def startup():
    db = SessionLocal()
    try:
        # заполняем уровни лояльности по умолчанию (Bronze/Silver/Gold)
        seed_loyalty_levels(db)
    finally:
        db.close()


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok"}
