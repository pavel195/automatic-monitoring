import json
import logging
from datetime import datetime, timezone
from typing import Iterable, Mapping

from django.conf import settings
from django.utils.dateparse import parse_datetime
from kafka import KafkaConsumer, KafkaProducer

from routing.tasks import classify_message
from tickets.models import ChannelMessage

logger = logging.getLogger(__name__)


class RawMessageProducer:
    """Отправляет события в Kafka для дальнейшей обработки."""

    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_BROKER,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

    def send_events(self, events: Iterable[Mapping]) -> None:
        for event in events:
            logger.debug("Публикуем событие %s", event)
            self.producer.send(settings.KAFKA_RAW_TOPIC, value=event)
        self.producer.flush()


class RawMessageConsumer:
    """Консюмит Kafka topic и создаёт ChannelMessage + Celery задачу."""

    def __init__(self):
        self.consumer = KafkaConsumer(
            settings.KAFKA_RAW_TOPIC,
            bootstrap_servers=settings.KAFKA_BROKER,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="latest",
            enable_auto_commit=True,
            group_id="ingestion",
        )

    def run_forever(self):
        for message in self.consumer:
            try:
                self._handle(message.value)
            except Exception as exc:  # pragma: no cover - логируем
                logger.exception("Не удалось обработать сообщение: %s", exc)

    def _handle(self, payload: Mapping) -> None:
        received_at = payload.get("received_at")
        if isinstance(received_at, str):
            parsed = parse_datetime(received_at)
            received_at = parsed if parsed else datetime.now(timezone.utc)
        if not received_at:
            received_at = datetime.now(timezone.utc)

        msg = ChannelMessage.objects.create(
            external_id=payload["external_id"],
            channel=payload.get("channel", ChannelMessage.Channel.OTHER),
            author=payload.get("author", ""),
            payload=payload.get("payload", ""),
            metadata=payload.get("metadata", {}),
            received_at=received_at,
        )
        classify_message.delay(str(msg.id))

