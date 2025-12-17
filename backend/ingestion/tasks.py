import logging
from datetime import datetime, timezone

from celery import shared_task

from ingestion.connectors.telegram_client import TelegramConnector
from routing.tasks import classify_message
from tickets.models import ChannelMessage, Sentiment, TransportMode

logger = logging.getLogger(__name__)


@shared_task
def poll_telegram():
    """Периодический опрос Telegram и немедленная постановка сообщений в обработку."""
    connector = TelegramConnector()
    events = connector.poll()
    processed = 0
    for event in events:
        received_at = event.get("received_at") or datetime.now(timezone.utc)
        msg, created = ChannelMessage.objects.get_or_create(
            external_id=event["external_id"],
            channel=event.get("channel", ChannelMessage.Channel.TELEGRAM),
            defaults={
                "author": event.get("author", ""),
                "payload": event.get("payload", ""),
                "metadata": event.get("metadata", {}),
                "received_at": received_at,
                "is_transport": True,
                "is_comment": event.get("is_comment", False),
                "parent_external_id": event.get("parent_external_id", ""),
                "thread_url": event.get("thread_url", ""),
                "source_chat_id": event.get("source_chat_id", ""),
                "sentiment": Sentiment.NEUTRAL,
                "transport_mode": TransportMode.OTHER,
            },
        )
        if created:
            classify_message.delay(str(msg.id))
            connector.acknowledge(event["external_id"])
            processed += 1
    if processed:
        logger.info("Поставлено в обработку %s телеграм-сообщений", processed)

