from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class ChannelMessage(models.Model):
    class Channel(models.TextChoices):
        TELEGRAM = "telegram", "Telegram"
        EMAIL = "email", "Email"
        VK = "vk", "VKontakte"
        OTHER = "other", "Другое"

    external_id = models.CharField(max_length=255, db_index=True)
    channel = models.CharField(max_length=32, choices=Channel.choices)
    author = models.CharField(max_length=255, blank=True)
    payload = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    received_at = models.DateTimeField()
    ticket = models.ForeignKey(
        "tickets.Ticket",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="messages",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover - удобное представление
        return f"{self.channel}:{self.external_id}"


class Ticket(models.Model):
    class Category(models.TextChoices):
        COMPLAINT = "complaint", "Жалоба"
        PRAISE = "praise", "Благодарность"
        REQUEST = "request", "Запрос информации"
        INCIDENT = "incident", "Инцидент"

    class Priority(models.IntegerChoices):
        LOW = 1, "Низкий"
        MEDIUM = 2, "Средний"
        HIGH = 3, "Высокий"
        CRITICAL = 4, "Критический"

    class Status(models.TextChoices):
        NEW = "new", "Новое"
        ACK = "acknowledged", "Подтверждено"
        IN_PROGRESS = "in_progress", "В работе"
        RESOLVED = "resolved", "Решено"
        CLOSED = "closed", "Закрыто"

    title = models.CharField(max_length=255)
    category = models.CharField(
        max_length=32, choices=Category.choices, default=Category.REQUEST
    )
    priority = models.IntegerField(
        choices=Priority.choices, default=Priority.MEDIUM
    )
    status = models.CharField(
        max_length=32, choices=Status.choices, default=Status.NEW
    )
    assigned_group = models.CharField(
        max_length=128, blank=True, help_text="Ответственный департамент"
    )
    assigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    ack_deadline = models.DateTimeField(null=True, blank=True)
    resolve_deadline = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def mark_acknowledged(self, user=None):
        self.status = self.Status.ACK
        if not self.acknowledged_at:
            self.acknowledged_at = timezone.now()
        self.assigned_to = user or self.assigned_to
        self.save(update_fields=["status", "acknowledged_at", "assigned_to"])

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.title} ({self.get_status_display()})"


class Assignment(models.Model):
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="assignments"
    )
    assignee = models.CharField(max_length=255)
    channel = models.CharField(max_length=64, default="internal")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.assignee} -> {self.ticket_id}"

