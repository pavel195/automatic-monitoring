"""VK Community Bot connector через Long Poll API.

Использует токен сообщества для получения сообщений через Long Poll Server
и отправки ответов от имени сообщества.
"""

import logging
import random
from datetime import datetime, timezone
from typing import Iterable, Mapping, Optional

import requests
from django.conf import settings

from ingestion.connectors.base import BaseConnector

logger = logging.getLogger(__name__)

VK_API_VERSION = "5.199"
VK_API_BASE = "https://api.vk.com/method"


class VkConnector(BaseConnector):
    """Коннектор для VK Community Bot через Long Poll Server."""

    def __init__(
        self,
        community_token: str,
        community_id: str,
        wait: int = 2,
    ):
        self.token = community_token
        self.community_id = community_id
        self.wait = wait
        self.session = requests.Session()
        self._lp_server: Optional[str] = None
        self._lp_key: Optional[str] = None
        self._lp_ts: Optional[str] = None

    def _api_call(self, method: str, **params) -> dict:
        """Вызов VK API метода."""
        params["access_token"] = self.token
        params["v"] = VK_API_VERSION
        resp = self.session.post(
            f"{VK_API_BASE}/{method}",
            data=params,
            timeout=getattr(settings, "VK_HTTP_TIMEOUT_SECONDS", 2.0),
        )
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            error = data["error"]
            raise RuntimeError(
                f"VK API error {error.get('error_code')}: {error.get('error_msg')}"
            )
        return data.get("response", {})

    def _init_long_poll(self) -> None:
        """Инициализация Long Poll сервера."""
        try:
            from django_redis import get_redis_connection
            redis = get_redis_connection("default")
        except Exception:
            import redis as redis_lib
            redis_url = getattr(settings, "CELERY_BROKER_URL", "redis://redis:6379/0")
            redis = redis_lib.from_url(redis_url)

        # Пробуем восстановить ts из Redis
        ts_key = f"ingestion:vk_ts:{self.community_id}"
        cached_ts = redis.get(ts_key)

        data = self._api_call(
            "groups.getLongPollServer",
            group_id=self.community_id,
        )
        self._lp_server = data["server"]
        self._lp_key = data["key"]
        self._lp_ts = cached_ts.decode() if cached_ts else data["ts"]

    def _save_ts(self, ts: str) -> None:
        """Сохраняет текущий ts в Redis."""
        try:
            from django_redis import get_redis_connection
            redis = get_redis_connection("default")
        except Exception:
            import redis as redis_lib
            redis_url = getattr(settings, "CELERY_BROKER_URL", "redis://redis:6379/0")
            redis = redis_lib.from_url(redis_url)

        ts_key = f"ingestion:vk_ts:{self.community_id}"
        redis.set(ts_key, ts)

    def poll(self) -> Iterable[Mapping]:
        """Получает новые сообщения через Long Poll."""
        if not self._lp_server:
            self._init_long_poll()

        try:
            resp = self.session.get(
                f"{self._lp_server}",
                params={
                    "act": "a_check",
                    "key": self._lp_key,
                    "ts": self._lp_ts,
                    "wait": self.wait,
                },
                timeout=max(
                    self.wait + 1,
                    getattr(settings, "VK_HTTP_TIMEOUT_SECONDS", 2.0),
                ),
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error("VK Long Poll ошибка: %s", e)
            return []

        # Обработка ошибок Long Poll
        failed = data.get("failed")
        if failed:
            if failed == 1:
                # Устаревшая история — обновляем ts
                self._lp_ts = data.get("ts", self._lp_ts)
            elif failed in (2, 3):
                # Ключ устарел или данные потеряны — переподключаемся
                self._init_long_poll()
            return []

        # Обновляем ts
        new_ts = data.get("ts", self._lp_ts)
        if new_ts != self._lp_ts:
            self._lp_ts = new_ts
            self._save_ts(new_ts)

        events = []
        for update in data.get("updates", []):
            if update.get("type") == "message_new":
                event = self._process_message(update)
                if event:
                    events.append(event)

        return events

    def _process_message(self, update: dict) -> Optional[dict]:
        """Обрабатывает новое сообщение из VK."""
        obj = update.get("object", {})
        message = obj.get("message", {})

        text = message.get("text", "")
        if not text.strip():
            return None

        from_id = message.get("from_id", 0)
        peer_id = message.get("peer_id", 0)
        msg_id = message.get("id", 0)
        conversation_message_id = message.get("conversation_message_id", 0)
        date = message.get("date", 0)

        # Пропускаем сообщения от самого сообщества
        if from_id < 0 and str(abs(from_id)) == str(self.community_id):
            return None

        # Собираем вложения
        attachments = []
        for att in message.get("attachments", []):
            att_type = att.get("type", "")
            if att_type == "photo":
                photo = att.get("photo", {})
                sizes = photo.get("sizes", [])
                if sizes:
                    best = max(sizes, key=lambda s: s.get("width", 0) * s.get("height", 0))
                    attachments.append({"type": "photo", "url": best.get("url", "")})
            elif att_type == "doc":
                doc = att.get("doc", {})
                attachments.append({
                    "type": "document",
                    "title": doc.get("title", ""),
                    "url": doc.get("url", ""),
                })

        received_at = datetime.fromtimestamp(date, tz=timezone.utc) if date else datetime.now(timezone.utc)

        return {
            "external_id": f"vk_{peer_id}_{msg_id}",
            "channel": "vk",
            "author": str(from_id),
            "payload": text,
            "metadata": {
                "peer_id": peer_id,
                "from_id": from_id,
                "message_id": msg_id,
                "conversation_message_id": conversation_message_id,
                "attachments": attachments,
                "raw": message,
            },
            "received_at": received_at,
            "source_chat_id": str(peer_id),
        }

    def send_message(self, peer_id: int, text: str, reply_to: Optional[int] = None) -> int:
        """Отправляет сообщение в VK."""
        params = {
            "peer_id": peer_id,
            "message": text,
            "random_id": random.randint(1, 2**31),
        }
        if reply_to:
            params["reply_to"] = reply_to

        result = self._api_call("messages.send", **params)
        return result

    def acknowledge(self, message_id: str) -> None:
        """No-op — VK не требует подтверждения."""
        pass
