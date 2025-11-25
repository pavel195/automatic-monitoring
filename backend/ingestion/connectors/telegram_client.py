import logging
import os
from typing import Iterable, Mapping

import requests
import redis
from django.conf import settings

from ingestion.connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class TelegramConnector(BaseConnector):
    """Простейший поллинг Telegram Bot API.

    Для production лучше перейти на webhook, но для MVP достаточно поллинга.
    """

    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_MONITOR_CHAT_ID", "")
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        self.offset_key = "ingestion:telegram_offset"
        self._offset = 0
        self.redis = None
        self._init_state_store()
        self._offset = self._get_stored_offset()

    def poll(self) -> Iterable[Mapping]:
        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN не задан, коннектор выключен")
            return []

        params = {"timeout": 5, "offset": self._offset}
        response = requests.get(f"{self.api_url}/getUpdates", params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            logger.error("Ошибка чтения Telegram: %s", payload)
            return []

        events = []
        for update in payload.get("result", []):
            self._offset = max(self._offset, update["update_id"] + 1)
            message = update.get("message") or update.get("channel_post")
            if not message:
                continue
            if self.chat_id and str(message["chat"]["id"]) != str(self.chat_id):
                continue
            events.append(
                {
                    "external_id": str(message["message_id"]),
                    "channel": "telegram",
                    "author": message.get("from", {}).get("username", "unknown"),
                    "payload": message.get("text", ""),
                    "metadata": {
                        "chat_id": message["chat"]["id"],
                        "raw": message,
                    },
                }
            )
        if events:
            self._persist_offset()
        return events

    def acknowledge(self, message_id: str) -> None:
        logger.debug("Telegram message %s отмечен как обработанный", message_id)

    # --- внутренние служебные методы ---
    def _init_state_store(self):
        try:
            self.redis = redis.Redis.from_url(
                getattr(settings, "REDIS_URL", "redis://redis:6379/0"),
                decode_responses=True,
            )
        except Exception as exc:  # pragma: no cover - логирование
            logger.warning("Не удалось подключиться к Redis для offset: %s", exc)
            self.redis = None

    def _get_stored_offset(self) -> int:
        if not self.redis:
            return 0
        value = self.redis.get(self.offset_key)
        try:
            return int(value) if value is not None else 0
        except ValueError:  # pragma: no cover
            logger.warning("Некорректное значение offset %s, сбрасываем", value)
            return 0

    def _persist_offset(self) -> None:
        if not self.redis or self._offset is None:
            return
        try:
            self.redis.set(self.offset_key, self._offset)
        except Exception as exc:  # pragma: no cover
            logger.warning("Не удалось сохранить offset Telegram: %s", exc)

