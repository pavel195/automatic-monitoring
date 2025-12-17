from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class Sentiment(models.TextChoices):
    NEGATIVE = "negative", "Негатив"
    NEUTRAL = "neutral", "Нейтрально"
    POSITIVE = "positive", "Позитив"


class TransportMode(models.TextChoices):
    METRO = "metro", "Метро"
    BUS = "bus", "Автобус"
    TRAM = "tram", "Трамвай"
    TRAIN = "train", "Поезд"
    AIRPLANE = "airplane", "Самолёт"
    WATER = "water", "Водный транспорт"
    TAXI = "taxi", "Такси"
    OTHER = "other", "Другое"


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
    is_transport = models.BooleanField(default=True)
    is_comment = models.BooleanField(default=False)
    transport_mode = models.CharField(
        max_length=16,
        choices=TransportMode.choices,
        default=TransportMode.OTHER,
    )
    source_chat_id = models.CharField(max_length=64, blank=True)
    parent_external_id = models.CharField(max_length=255, blank=True)
    thread_url = models.URLField(blank=True)
    sentiment = models.CharField(
        max_length=16, choices=Sentiment.choices, default=Sentiment.NEUTRAL
    )
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

    class Meta:
        unique_together = ("external_id", "channel")

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
    sentiment = models.CharField(
        max_length=16, choices=Sentiment.choices, default=Sentiment.NEUTRAL
    )
    is_transport = models.BooleanField(default=True)
    transport_mode = models.CharField(
        max_length=16,
        choices=TransportMode.choices,
        default=TransportMode.OTHER,
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


class TicketResponse(models.Model):
    class Channel(models.TextChoices):
        TELEGRAM = "telegram", "Telegram"
        INTERNAL = "internal", "Внутренняя"

    class Status(models.TextChoices):
        PENDING = "pending", "В ожидании"
        SENT = "sent", "Отправлено"
        FAILED = "failed", "Ошибка"

    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="responses"
    )
    channel_message = models.ForeignKey(
        ChannelMessage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Связанное входящее сообщение",
    )
    author = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    channel = models.CharField(
        max_length=32, choices=Channel.choices, default=Channel.TELEGRAM
    )
    body = models.TextField()
    status = models.CharField(
        max_length=32, choices=Status.choices, default=Status.PENDING
    )
    external_message_id = models.CharField(max_length=255, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def mark_sent(self, external_id: str):
        self.status = self.Status.SENT
        self.external_message_id = external_id
        self.sent_at = timezone.now()
        self.save(update_fields=["status", "external_message_id", "sent_at"])

    def mark_failed(self):  # pragma: no cover - простая ветка
        self.status = self.Status.FAILED
        self.save(update_fields=["status"])

