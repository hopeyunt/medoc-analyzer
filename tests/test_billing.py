"""Тесты биллинга — пополнение баланса, списание кредитов, история транзакций."""
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.billing_service import charge_credits, deposit_credits


def test_get_balance(client, auth_headers):
    resp = client.get("/api/v1/billing/balance", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "credits" in data
    assert "loyalty_level" in data
    assert data["loyalty_level"] == "Bronze"  # новый пользователь всегда Bronze


def test_deposit_credits(client, auth_headers):
    # узнаём текущий баланс
    before = client.get("/api/v1/billing/balance", headers=auth_headers).json()["credits"]

    resp = client.post("/api/v1/billing/deposit", json={"amount": 50.0}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["credits"] == pytest.approx(before + 50.0, abs=0.01)


def test_deposit_invalid_amount(client, auth_headers):
    resp = client.post("/api/v1/billing/deposit", json={"amount": -10}, headers=auth_headers)
    assert resp.status_code == 400


def test_get_transactions(client, auth_headers):
    # пополняем баланс, потом смотрим транзакции
    client.post("/api/v1/billing/deposit", json={"amount": 20.0}, headers=auth_headers)
    resp = client.get("/api/v1/billing/transactions", headers=auth_headers)
    assert resp.status_code == 200
    transactions = resp.json()
    assert len(transactions) >= 1
    assert transactions[0]["type"] == "deposit"


def test_charge_credits_service(db):
    """Тест сервисной функции charge_credits напрямую."""
    user = User(
        email="billing_test@example.com",
        full_name="Биллинг Тест",
        hashed_password="hash",
        credits=100.0,
    )
    db.add(user)
    db.commit()

    cost = charge_credits(user, db)
    assert cost > 0
    assert user.credits == pytest.approx(100.0 - cost, abs=0.01)


def test_charge_insufficient_credits(db):
    """Если кредитов недостаточно — должна быть ошибка 402."""
    user = User(
        email="broke@example.com",
        full_name="Без Денег",
        hashed_password="hash",
        credits=0.0,
    )
    db.add(user)
    db.commit()

    with pytest.raises(HTTPException) as exc:
        charge_credits(user, db)
    assert exc.value.status_code == 402


def test_deposit_service(db):
    """Тест функции deposit_credits напрямую."""
    user = User(
        email="deposit_test@example.com",
        full_name="Депозит Тест",
        hashed_password="hash",
        credits=5.0,
    )
    db.add(user)
    db.commit()

    deposit_credits(user, 30.0, db)
    db.commit()
    assert user.credits == pytest.approx(35.0, abs=0.01)
