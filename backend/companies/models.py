from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class Company(models.Model):
    """Модель компании - клиента платформы."""

    class Status(models.TextChoices):
        PENDING = "pending", "На модерации"
        ACTIVE = "active", "Активна"
        INACTIVE = "inactive", "Неактивна"
        SUSPENDED = "suspended", "Приостановлена"

    name = models.CharField(max_length=255, verbose_name="Название компании")
    description = models.TextField(blank=True, verbose_name="Описание")
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Статус",
    )
    contact_email = models.EmailField(verbose_name="Контактный email")
    contact_phone = models.CharField(
        max_length=32, blank=True, verbose_name="Контактный телефон"
    )
    # Настройки SLA по умолчанию (в минутах)
    default_ack_sla_minutes = models.IntegerField(
        default=30, verbose_name="SLA подтверждения (минуты)"
    )
    default_resolve_sla_minutes = models.IntegerField(
        default=720, verbose_name="SLA решения (минуты)"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_companies",
        verbose_name="Одобрено пользователем",
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата одобрения")

    def approve(self, user):
        """Одобрить компанию."""
        self.status = self.Status.ACTIVE
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save(update_fields=["status", "approved_by", "approved_at"])

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    class Meta:
        verbose_name = "Компания"
        verbose_name_plural = "Компании"
        ordering = ["-created_at"]


class UserProfile(models.Model):
    """Расширенный профиль пользователя с ролью и привязкой к компании."""

    class Role(models.TextChoices):
        OPERATOR = "operator", "Оператор"
        COMPANY_ADMIN = "company_admin", "Администратор компании"
        SUPERADMIN = "superadmin", "Супер-администратор"

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile", verbose_name="Пользователь"
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True,
        verbose_name="Компания",
    )
    role = models.CharField(
        max_length=32, choices=Role.choices, default=Role.OPERATOR, verbose_name="Роль"
    )
    phone = models.CharField(max_length=32, blank=True, verbose_name="Телефон")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    def is_superadmin(self):
        """Проверка, является ли пользователь супер-администратором."""
        return self.role == self.Role.SUPERADMIN

    def is_company_admin(self):
        """Проверка, является ли пользователь администратором компании."""
        return self.role == self.Role.COMPANY_ADMIN

    def can_manage_company(self, company):
        """Проверка, может ли пользователь управлять компанией."""
        if self.is_superadmin():
            return True
        return self.is_company_admin() and self.company == company

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"


class TelegramBot(models.Model):
    """Модель для хранения информации о Telegram ботах компаний."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Активен"
        INACTIVE = "inactive", "Неактивен"
        ERROR = "error", "Ошибка"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="bots", verbose_name="Компания"
    )
    bot_token = models.CharField(max_length=255, unique=True, verbose_name="Токен бота")
    bot_username = models.CharField(max_length=128, blank=True, verbose_name="Username бота")
    chat_ids = models.JSONField(
        default=list, blank=True, verbose_name="ID чатов для мониторинга"
    )
    discussion_chat_ids = models.JSONField(
        default=list, blank=True, verbose_name="ID чатов для обсуждений"
    )
    allow_direct = models.BooleanField(
        default=False, verbose_name="Разрешить личные сообщения"
    )
    status = models.CharField(
        max_length=32, choices=Status.choices, default=Status.INACTIVE, verbose_name="Статус"
    )
    last_error = models.TextField(blank=True, verbose_name="Последняя ошибка")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    def __str__(self):
        return f"{self.company.name} - {self.bot_username or 'Бот'}"

    class Meta:
        verbose_name = "Telegram бот"
        verbose_name_plural = "Telegram боты"
        ordering = ["-created_at"]


class VkBot(models.Model):
    """Модель для хранения информации о VK ботах сообществ."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Активен"
        INACTIVE = "inactive", "Неактивен"
        ERROR = "error", "Ошибка"

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="vk_bots", verbose_name="Компания"
    )
    community_token = models.CharField(max_length=255, unique=True, verbose_name="Токен сообщества")
    community_id = models.CharField(max_length=64, blank=True, verbose_name="ID сообщества")
    community_name = models.CharField(max_length=255, blank=True, verbose_name="Название сообщества")
    status = models.CharField(
        max_length=32, choices=Status.choices, default=Status.INACTIVE, verbose_name="Статус"
    )
    last_error = models.TextField(blank=True, verbose_name="Последняя ошибка")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    def __str__(self):
        return f"{self.company.name} - {self.community_name or 'VK бот'}"

    class Meta:
        verbose_name = "VK бот"
        verbose_name_plural = "VK боты"
        ordering = ["-created_at"]

