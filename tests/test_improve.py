"""Тесты эндпоинта улучшения текста."""
import pytest
from unittest.mock import patch, MagicMock


def test_improve_requires_auth(client):
    resp = client.post("/api/v1/improve/", json={"text": "Жалобы: температура."})
    assert resp.status_code == 401


def test_improve_too_short(client, auth_headers):
    resp = client.post("/api/v1/improve/", json={"text": "кор"}, headers=auth_headers)
    assert resp.status_code == 422


def test_improve_no_credits(client, auth_headers, db):
    from app.models.user import User
    user = db.query(User).filter(User.email == "test@example.com").first()
    user.credits = 0.0
    db.commit()

    resp = client.post("/api/v1/improve/", json={"text": "Жалобы: боль в горле."}, headers=auth_headers)
    assert resp.status_code == 402


def test_improve_accepted(client, auth_headers):
    """Задача создаётся — 202, статус pending."""
    with patch("app.api.v1.improve.run_improvement") as mock_task:
        mock_task.delay.return_value = MagicMock(id="improve-task-001")
        resp = client.post(
            "/api/v1/improve/",
            json={"text": "Жалобы: боль в груди при нагрузке. Анамнез: гипертония 5 лет."},
            headers=auth_headers,
        )
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "pending"
    assert data["credits_charged"] > 0


def test_improve_list_empty(client, auth_headers):
    resp = client.get("/api/v1/improve/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_improve_get_not_found(client, auth_headers):
    resp = client.get("/api/v1/improve/99999", headers=auth_headers)
    assert resp.status_code == 404


def test_improve_feedback_not_found(client, auth_headers):
    resp = client.post(
        "/api/v1/improve/99999/feedback",
        json={"rating": 5, "accepted": True},
        headers=auth_headers,
    )
    assert resp.status_code == 404
