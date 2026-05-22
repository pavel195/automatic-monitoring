"""Тесты для работы с Telegram ботами."""

import pytest
import requests
from unittest.mock import patch, Mock

from companies.models import Company, TelegramBot, UserProfile
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def company():
    """Фикстура для создания компании."""
    return Company.objects.create(
        name="Тестовая компания",
        contact_email="test@example.com",
        status=Company.Status.ACTIVE,
    )


@pytest.fixture
def company_admin(company):
    """Фикстура для создания администратора компании."""
    user = User.objects.create_user(
        username="admin", email="admin@test.com", password="test123"
    )
    UserProfile.objects.create(
        user=user, company=company, role=UserProfile.Role.COMPANY_ADMIN
    )
    return user


@pytest.fixture
def operator(company):
    """Фикстура для создания оператора компании."""
    user = User.objects.create_user(
        username="operator", email="operator@test.com", password="test123"
    )
    UserProfile.objects.create(
        user=user, company=company, role=UserProfile.Role.OPERATOR
    )
    return user


@pytest.mark.django_db
@patch("companies.serializers.requests.get")
def test_telegram_bot_token_validation(mock_get, company_admin, company):
    """Тест валидации токена Telegram бота."""
    from rest_framework.test import APIClient

    # Мокаем успешный ответ от Telegram API
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "ok": True,
        "result": {"id": 123456, "is_bot": True, "username": "test_bot"},
    }
    mock_get.return_value = mock_response

    client = APIClient()
    client.force_authenticate(user=company_admin)

    response = client.post(
        "/api/companies/bots/",
        {
            "company": company.id,
            "bot_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            "chat_ids": ["-1001234567890"],
            "allow_direct": True,
        },
    )

    assert response.status_code == 201
    bot = TelegramBot.objects.get(company=company)
    assert bot.bot_username == "test_bot"
    assert bot.status == TelegramBot.Status.ACTIVE


@pytest.mark.django_db
@patch("companies.serializers.requests.get")
def test_telegram_bot_invalid_token(mock_get, company_admin, company):
    """Тест отклонения неверного токена."""
    from rest_framework.test import APIClient

    # Мокаем неуспешный ответ от Telegram API
    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.json.return_value = {"ok": False, "description": "Unauthorized"}
    mock_get.return_value = mock_response

    client = APIClient()
    client.force_authenticate(user=company_admin)

    response = client.post(
        "/api/companies/bots/",
        {
            "company": company.id,
            "bot_token": "invalid_token",
            "chat_ids": [],
        },
    )

    assert response.status_code == 400
    assert "токен" in response.data["bot_token"][0].lower()


@pytest.mark.django_db
def test_telegram_bot_belongs_to_company(company):
    """Тест привязки бота к компании."""
    bot = TelegramBot.objects.create(
        company=company,
        bot_token="123456:ABC-DEF",
        bot_username="test_bot",
        status=TelegramBot.Status.ACTIVE,
    )

    assert bot.company == company
    assert company.bots.count() == 1
    assert company.bots.first() == bot


@pytest.mark.django_db
def test_operator_cannot_create_telegram_bot(operator):
    """Оператор не должен управлять интеграциями компании."""
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(user=operator)

    response = client.post(
        "/api/companies/bots/",
        {
            "bot_token": "123456:ABC-DEF",
            "chat_ids": ["-1001234567890"],
            "allow_direct": True,
        },
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_operator_cannot_create_vk_bot(operator):
    """Оператор не должен подключать VK-сообщества."""
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(user=operator)

    response = client.post(
        "/api/companies/vk-bots/",
        {
            "community_token": "vk-token",
            "community_id": "123",
            "community_name": "Test VK",
        },
    )

    assert response.status_code == 403


@pytest.mark.django_db
@patch("companies.serializers.requests.get")
def test_telegram_bot_create_logs_do_not_include_token(mock_get, company_admin, caplog):
    """Токен Telegram не должен попадать в логи при создании интеграции."""
    from rest_framework.test import APIClient

    token = "123456:SECRET-TOKEN"
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "ok": True,
        "result": {"id": 123456, "is_bot": True, "username": "safe_bot"},
    }
    mock_get.return_value = mock_response

    client = APIClient()
    client.force_authenticate(user=company_admin)

    with caplog.at_level("INFO", logger="companies.views"):
        response = client.post(
            "/api/companies/bots/",
            {
                "bot_token": token,
                "chat_ids": ["-1001234567890"],
                "allow_direct": True,
            },
        )

    assert response.status_code == 201
    assert token not in caplog.text


@pytest.mark.django_db
@patch("companies.serializers.requests.get")
def test_telegram_token_request_error_does_not_return_token(mock_get, company_admin):
    """Ошибки проверки Telegram не должны возвращать токен в ответе API."""
    from rest_framework.test import APIClient

    token = "123456:SECRET-TOKEN"
    mock_get.side_effect = requests.RequestException(
        f"GET https://api.telegram.org/bot{token}/getMe failed"
    )

    client = APIClient()
    client.force_authenticate(user=company_admin)

    response = client.post(
        "/api/companies/bots/",
        {
            "bot_token": token,
            "chat_ids": [],
            "allow_direct": True,
        },
    )

    assert response.status_code == 400
    assert token not in str(response.data)
