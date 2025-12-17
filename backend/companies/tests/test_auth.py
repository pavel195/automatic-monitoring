"""Тесты для системы авторизации и разрешений."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from companies.models import Company, UserProfile

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
def superadmin_user():
    """Фикстура для создания супер-администратора."""
    user = User.objects.create_user(
        username="superadmin",
        email="superadmin@example.com",
        password="testpass123",
    )
    UserProfile.objects.create(user=user, role=UserProfile.Role.SUPERADMIN)
    return user


@pytest.fixture
def company_admin_user(company):
    """Фикстура для создания администратора компании."""
    user = User.objects.create_user(
        username="company_admin",
        email="admin@company.com",
        password="testpass123",
    )
    UserProfile.objects.create(
        user=user, company=company, role=UserProfile.Role.COMPANY_ADMIN
    )
    return user


@pytest.fixture
def operator_user(company):
    """Фикстура для создания оператора."""
    user = User.objects.create_user(
        username="operator",
        email="operator@company.com",
        password="testpass123",
    )
    UserProfile.objects.create(
        user=user, company=company, role=UserProfile.Role.OPERATOR
    )
    return user


@pytest.mark.django_db
def test_superadmin_can_access_all_companies(superadmin_user):
    """Супер-администратор может видеть все компании."""
    Company.objects.create(
        name="Компания 1", contact_email="c1@example.com", status=Company.Status.ACTIVE
    )
    Company.objects.create(
        name="Компания 2", contact_email="c2@example.com", status=Company.Status.ACTIVE
    )

    client = APIClient()
    client.force_authenticate(user=superadmin_user)

    response = client.get("/api/companies/companies/")
    assert response.status_code == 200
    # ViewSet возвращает список, а не словарь с results
    data = response.data if isinstance(response.data, list) else response.data.get("results", [])
    assert len(data) >= 2


@pytest.mark.django_db
def test_company_admin_sees_only_own_company(company_admin_user, company):
    """Администратор компании видит только свою компанию."""
    # Создаем другую компанию
    Company.objects.create(
        name="Другая компания",
        contact_email="other@example.com",
        status=Company.Status.ACTIVE,
    )

    client = APIClient()
    client.force_authenticate(user=company_admin_user)

    response = client.get("/api/companies/companies/")
    assert response.status_code == 200
    data = response.data if isinstance(response.data, list) else response.data.get("results", [])
    assert len(data) == 1
    assert data[0]["name"] == company.name


@pytest.mark.django_db
def test_operator_sees_only_own_company(operator_user, company):
    """Оператор видит только свою компанию."""
    Company.objects.create(
        name="Другая компания",
        contact_email="other@example.com",
        status=Company.Status.ACTIVE,
    )

    client = APIClient()
    client.force_authenticate(user=operator_user)

    response = client.get("/api/companies/companies/")
    assert response.status_code == 200
    data = response.data if isinstance(response.data, list) else response.data.get("results", [])
    assert len(data) == 1
    assert data[0]["name"] == company.name


@pytest.mark.django_db
def test_unauthenticated_cannot_access_companies():
    """Неаутентифицированный пользователь не может получить доступ."""
    client = APIClient()
    response = client.get("/api/companies/companies/")
    # DRF возвращает 403 для неаутентифицированных пользователей с IsAuthenticated
    assert response.status_code in [401, 403]


@pytest.mark.django_db
def test_company_registration():
    """Тест регистрации компании."""
    client = APIClient()
    response = client.post(
        "/api/companies/companies/register/",
        {
            "name": "Новая компания",
            "description": "Описание",
            "contact_email": "new@example.com",
            "contact_phone": "+79991234567",
            "admin_email": "admin@newcompany.com",
            "admin_password": "securepass123",
            "admin_first_name": "Иван",
            "admin_last_name": "Иванов",
        },
    )
    assert response.status_code == 201
    assert Company.objects.filter(name="Новая компания").exists()
    # Проверяем, что создан администратор
    admin_user = User.objects.get(email="admin@newcompany.com")
    assert admin_user.profile.role == UserProfile.Role.COMPANY_ADMIN
    assert admin_user.profile.company.name == "Новая компания"
    # Компания должна быть на модерации
    company = Company.objects.get(name="Новая компания")
    assert company.status == Company.Status.PENDING


@pytest.mark.django_db
def test_superadmin_can_approve_company(superadmin_user):
    """Супер-администратор может одобрить компанию."""
    company = Company.objects.create(
        name="На модерации",
        contact_email="pending@example.com",
        status=Company.Status.PENDING,
    )

    client = APIClient()
    client.force_authenticate(user=superadmin_user)

    response = client.post(f"/api/companies/companies/{company.id}/approve/")
    assert response.status_code == 200
    company.refresh_from_db()
    assert company.status == Company.Status.ACTIVE
    assert company.approved_by == superadmin_user
    assert company.approved_at is not None

