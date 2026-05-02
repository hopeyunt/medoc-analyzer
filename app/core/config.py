from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://medoc_user:medoc_password@localhost:5432/medoc_db"
    SECRET_KEY: str = "change-me-in-production-at-least-32-characters-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    COST_PER_PREDICTION: float = 1.0
    INITIAL_CREDITS: float = 10.0

    APP_ENV: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
