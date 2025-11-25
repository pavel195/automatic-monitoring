import logging
from datetime import datetime, timezone

from celery import shared_task

from ingestion.connectors.telegram_client import TelegramConnector
from ingestion.consumers import RawMessageProducer

logger = logging.getLogger(__name__)


@shared_task
def poll_telegram():
    """Периодический опрос Telegram и публикация в Kafka."""
    connector = TelegramConnector()
    producer = RawMessageProducer()
    events = connector.poll()
    enriched = []
    for event in events:
        event["received_at"] = event.get("received_at") or datetime.now(timezone.utc)
        enriched.append(event)
        connector.acknowledge(event["external_id"])
    if enriched:
        logger.info("Отправляем %s событий из Telegram", len(enriched))
        try:
            producer.send_events(enriched)
        except Exception as exc:
            logger.error("Kafka недоступен: %s", exc)

