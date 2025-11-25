import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from analytics.search_indexer import index_ticket
from routing.ai.transport_intent import TransportIntentModel
from routing.nlp_classifier import KeywordClassifier
from tickets.models import ChannelMessage, Ticket, TransportMode, Sentiment

logger = logging.getLogger(__name__)

ACK_SLA_MINUTES = {1: 60, 2: 30, 3: 15, 4: 5}
RESOLVE_SLA_MINUTES = {1: 1440, 2: 720, 3: 240, 4: 60}
transport_model = TransportIntentModel()


@shared_task
def classify_message(message_id: str):
    classifier = KeywordClassifier()
    message = ChannelMessage.objects.get(id=message_id)
    text_lower = message.payload.lower()
    result = classifier.predict(message.payload)
    intent = transport_model.predict(message.payload)

    if intent.sentiment == Sentiment.NEGATIVE or any(
        marker in text_lower for marker in ("задерж", "опазд", "нет поез", "нет автоб")
    ):
        result.priority = max(result.priority, Ticket.Priority.HIGH)
    if any(marker in text_lower for marker in ("пожар", "взрыв", "эвакуац", "авари")):
        result.priority = Ticket.Priority.CRITICAL

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
        sentiment=intent.sentiment,
        is_transport=intent.is_transport,
        transport_mode=intent.transport_mode or TransportMode.OTHER,
    )
    index_ticket(ticket)
    message.ticket = ticket
    message.is_transport = intent.is_transport
    message.sentiment = intent.sentiment
    message.transport_mode = intent.transport_mode or TransportMode.OTHER
    message.save(
        update_fields=["ticket", "is_transport", "sentiment", "transport_mode"]
    )
    logger.info("Создан тикет %s для сообщения %s", ticket.id, message_id)
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

