import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from analytics.search_indexer import index_ticket
from routing.llm_classifier import HybridClassifier
from tickets.models import ChannelMessage, Ticket, TransportMode, Sentiment

logger = logging.getLogger(__name__)

ACK_SLA_MINUTES = {1: 60, 2: 30, 3: 15, 4: 5}
RESOLVE_SLA_MINUTES = {1: 1440, 2: 720, 3: 240, 4: 60}
hybrid_classifier = HybridClassifier()


@shared_task
def classify_message(message_id: str):
    """Классификация с гибридным подходом: LLM (Ollama) + keyword fallback."""
    message = ChannelMessage.objects.get(id=message_id)
    text_lower = message.payload.lower()

    result, sentiment, is_transport, transport_mode, source = hybrid_classifier.classify(message.payload)

    # Корректировки приоритета на основе тональности
    if sentiment == Sentiment.NEGATIVE:
        result.priority = max(result.priority, Ticket.Priority.HIGH)
    elif sentiment == Sentiment.POSITIVE:
        result.priority = min(result.priority, Ticket.Priority.MEDIUM)

    # Критические маркеры (всегда проверяем — safety net)
    critical_markers = ("пожар", "взрыв", "эвакуац", "авари", "травм", "ранен", "кров", "смерт")
    if any(marker in text_lower for marker in critical_markers):
        result.priority = Ticket.Priority.CRITICAL

    # Высокий приоритет для задержек и сбоев
    high_priority_markers = ("задерж", "опазд", "нет поез", "нет автоб", "не работает", "слом", "поломк")
    if any(marker in text_lower for marker in high_priority_markers):
        result.priority = max(result.priority, Ticket.Priority.HIGH)

    # Учет времени суток (ночные обращения выше приоритет)
    received_hour = message.received_at.hour if message.received_at else timezone.now().hour
    if 22 <= received_hour or received_hour < 6:
        if result.priority < Ticket.Priority.HIGH:
            result.priority = min(result.priority + 1, Ticket.Priority.HIGH)

    # История обращений от автора
    if message.author:
        recent_complaints = ChannelMessage.objects.filter(
            author=message.author,
            sentiment=Sentiment.NEGATIVE,
            received_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        if recent_complaints >= 3:
            result.priority = max(result.priority, Ticket.Priority.HIGH)

    ack_deadline = timezone.now() + timedelta(
        minutes=ACK_SLA_MINUTES[result.priority]
    )
    resolve_deadline = timezone.now() + timedelta(
        minutes=RESOLVE_SLA_MINUTES[result.priority]
    )

    ticket = Ticket.objects.create(
        title=result.title,
        category=result.category,
        priority=result.priority,
        assigned_group=result.group,
        ack_deadline=ack_deadline,
        resolve_deadline=resolve_deadline,
        sentiment=sentiment,
        is_transport=is_transport,
        transport_mode=transport_mode or TransportMode.OTHER,
        company=message.company,
    )
    index_ticket(ticket)
    message.ticket = ticket
    message.is_transport = is_transport
    message.sentiment = sentiment
    message.transport_mode = transport_mode or TransportMode.OTHER
    message.save(
        update_fields=["ticket", "is_transport", "sentiment", "transport_mode"]
    )
    logger.info("Создан тикет %s для сообщения %s (classifier: %s)", ticket.id, message_id, source)
    return str(ticket.id)


@shared_task
def sla_watchdog():
    now = timezone.now()
    breached = Ticket.objects.filter(
        ack_deadline__lt=now,
        status=Ticket.Status.NEW,
    )
    for ticket in breached:
        logger.warning(
            "SLA ACK нарушен для тикета %s (deadline %s)",
            ticket.id,
            ticket.ack_deadline,
        )
