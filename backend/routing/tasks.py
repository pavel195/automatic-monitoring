import json
import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from kafka import KafkaProducer

from analytics.search_indexer import index_ticket
from routing.nlp_classifier import KeywordClassifier
from tickets.models import ChannelMessage, Ticket

logger = logging.getLogger(__name__)

ACK_SLA_MINUTES = {1: 60, 2: 30, 3: 15, 4: 5}
RESOLVE_SLA_MINUTES = {1: 1440, 2: 720, 3: 240, 4: 60}


def _get_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=settings.KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )


@shared_task
def classify_message(message_id: str):
    classifier = KeywordClassifier()
    message = ChannelMessage.objects.get(id=message_id)
    result = classifier.predict(message.payload)

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
    )
    index_ticket(ticket)
    message.ticket = ticket
    message.save(update_fields=["ticket"])
    logger.info("Создан тикет %s для сообщения %s", ticket.id, message_id)
    _emit_alert(
        {
            "type": "ticket_created",
            "ticket_id": ticket.id,
            "priority": ticket.priority,
        }
    )
    return str(ticket.id)


@shared_task
def sla_watchdog():
    now = timezone.now()
    breached = Ticket.objects.filter(
        ack_deadline__lt=now,
        status=Ticket.Status.NEW,
    )
    try:
        producer = _get_producer()
    except Exception as exc:  # pragma: no cover
        logger.error("Kafka недоступен для SLA watchdog: %s", exc)
        return
    for ticket in breached:
        payload = {
            "type": "sla_ack_breach",
            "ticket_id": ticket.id,
            "priority": ticket.priority,
            "deadline": ticket.ack_deadline.isoformat()
            if ticket.ack_deadline
            else None,
        }
        producer.send(settings.KAFKA_ALERTS_TOPIC, payload)
        logger.warning("SLA ACK нарушен для тикета %s", ticket.id)
    producer.flush()


def _emit_alert(payload):
    try:
        producer = _get_producer()
        producer.send(settings.KAFKA_ALERTS_TOPIC, payload)
        producer.flush()
    except Exception as exc:  # pragma: no cover
        logger.error("Не удалось отправить оповещение: %s", exc)

