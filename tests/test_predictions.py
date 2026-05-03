"""Тесты эндпоинта предсказаний."""
import pytest
from unittest.mock import patch, MagicMock


def test_create_prediction_no_credits(client, auth_headers, db):
    """Если кредитов нет — должен вернуть 402."""
    from app.models.user import User
    # обнуляем кредиты у нашего пользователя
    user = db.query(User).filter(User.email == "test@example.com").first()
    user.credits = 0.0
    db.commit()

    resp = client.post("/api/v1/predictions/", json={"text": "Жалобы: боль. Диагноз: ОРВИ."}, headers=auth_headers)
    assert resp.status_code == 402


def test_create_prediction_too_short(client, auth_headers):
    """Текст меньше 10 символов — должен быть 422."""
    resp = client.post("/api/v1/predictions/", json={"text": "короткий"}, headers=auth_headers)
    assert resp.status_code == 422


def test_list_predictions_empty(client, auth_headers):
    resp = client.get("/api/v1/predictions/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_nonexistent_prediction(client, auth_headers):
    resp = client.get("/api/v1/predictions/99999", headers=auth_headers)
    assert resp.status_code == 404


def test_create_prediction_accepted(client, auth_headers):
    """Задача создаётся — возвращает 202 и id."""
    # мокаем celery, чтобы не нужен был реальный воркер
    with patch("app.api.v1.predictions.run_analysis") as mock_task:
        mock_task.delay.return_value = MagicMock(id="fake-task-id-123")
        resp = client.post(
            "/api/v1/predictions/",
            json={"text": "Жалобы: температура 38. Анамнез: заболел вчера. Диагноз: ОРВИ. Назначен парацетамол."},
            headers=auth_headers,
        )
    assert resp.status_code == 202
    data = resp.json()
    assert "id" in data
    assert data["status"] == "pending"
    assert data["credits_charged"] > 0


def test_prediction_deducts_credits(client, auth_headers, db):
    """После создания задачи кредиты должны уменьшиться."""
    from app.models.user import User
    user = db.query(User).filter(User.email == "test@example.com").first()
    credits_before = user.credits

    with patch("app.api.v1.predictions.run_analysis") as mock_task:
        mock_task.delay.return_value = MagicMock(id="task-456")
        client.post(
            "/api/v1/predictions/",
            json={"text": "Жалобы: кашель. Анамнез: болеет неделю. Диагноз: бронхит. Лечение: азитромицин."},
            headers=auth_headers,
        )

    db.refresh(user)
    assert user.credits < credits_before
