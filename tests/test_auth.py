"""Тесты аутентификации — регистрация, логин, получение профиля."""
import pytest


def test_register_success(client):
    resp = client.post("/api/v1/auth/register", json={
        "email": "newuser@example.com",
        "full_name": "Новый Пользователь",
        "password": "securepass",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "newuser@example.com"
    # у нового пользователя должны быть начальные кредиты
    assert data["credits"] > 0


def test_register_duplicate_email(client, registered_user):
    # пытаемся зарегистрировать второй раз с тем же email
    resp = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "full_name": "Дубликат",
        "password": "pass",
    })
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"]


def test_login_success(client, registered_user):
    resp = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "password123",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password(client, registered_user):
    resp = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "неверный_пароль",
    })
    assert resp.status_code == 401


def test_login_nonexistent_user(client):
    resp = client.post("/api/v1/auth/login", json={
        "email": "nobody@example.com",
        "password": "pass",
    })
    assert resp.status_code == 401


def test_get_current_user(client, auth_headers):
    resp = client.get("/api/v1/users/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"


def test_get_user_unauthorized(client):
    # без токена должен быть 401
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 401
