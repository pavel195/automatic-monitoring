import logging
import os
from typing import Iterable, Mapping, Optional

import requests
import redis
from django.conf import settings

from ingestion.connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class TelegramConnector(BaseConnector):
    """Простейший поллинг Telegram Bot API.

    Для production лучше перейти на webhook, но для MVP достаточно поллинга.
    """

    QUICK_ACTIONS = {
        "Жалоба": ("complaint", "Опишите, что произошло и где вы столкнулись с проблемой."),
        "Инцидент": (
            "incident",
            "Расскажите, какой инцидент произошёл. Укажите место, время и детали.",
        ),
        "Запрос информации": (
            "request",
            "Что именно хотите узнать? Напишите свой вопрос, мы передадим его специалистам.",
        ),
        "Благодарность": (
            "praise",
            "Пожалуйста, напишите сообщение, мы передадим благодарность сотрудникам.",
        ),
    }
    QUICK_REPLY_BUTTONS = [
        ["Жалоба", "Инцидент"],
        ["Запрос информации", "Благодарность"],
    ]

    def __init__(self, bot_token=None, chat_ids=None, discussion_chat_ids=None, allow_private=False):
        """Инициализация коннектора с параметрами бота.

        Если списки чатов не переданы явно, коннектор берет их из окружения.
        """
        self.token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        if chat_ids is None:
            monitor_ids = os.getenv("TELEGRAM_MONITOR_CHAT_ID", "")
            self.chat_ids = self._parse_chat_ids(monitor_ids)
        else:
            self.chat_ids = set(str(cid) for cid in chat_ids) if chat_ids else set()

        if discussion_chat_ids is None:
            discussion_ids = os.getenv("TELEGRAM_DISCUSSION_CHAT_IDS", "")
            self.discussion_chat_ids = self._parse_chat_ids(discussion_ids)
        else:
            self.discussion_chat_ids = set(str(cid) for cid in discussion_chat_ids) if discussion_chat_ids else set()

        self.allow_private = allow_private or os.getenv("TELEGRAM_ALLOW_DIRECT", "0") in ("1", "true")
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        bot_id = self.token[:10] if self.token else "default"
        self.offset_key = f"ingestion:telegram_offset:{bot_id}"
        self._offset = 0
        self.redis = None
        self._init_state_store()
        self._offset = self._get_stored_offset()

    def poll(self) -> Iterable[Mapping]:
        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN не задан, коннектор выключен")
            return []

        params = {"timeout": 5, "offset": self._offset}
        try:
            response = requests.get(f"{self.api_url}/getUpdates", params=params, timeout=10)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else None
            if status_code == 409:
                logger.debug("Telegram API: 409 Conflict (параллельные запросы), пропускаем этот цикл. Offset: %s", self._offset)
                return []
            response_text = e.response.text[:200] if e.response is not None else ""
            logger.error("Telegram API HTTP ошибка %s: %s", status_code, response_text)
            raise
        except requests.exceptions.RequestException as e:
            logger.warning(
                "Ошибка сети при запросе к Telegram API: %s",
                self._redact_token(str(e)),
            )
            return []
        except Exception as e:
            logger.error(
                "Неожиданная ошибка при запросе к Telegram API: %s",
                self._redact_token(str(e)),
            )
            raise

        payload = response.json()
        if not payload.get("ok"):
            logger.error("Ошибка чтения Telegram: %s", payload)
            return []

        events = []
        for update in payload.get("result", []):
            self._offset = max(self._offset, update["update_id"] + 1)
            message = (
                update.get("message")
                or update.get("channel_post")
                or update.get("edited_message")
            )
            if not message:
                continue

            chat = message.get("chat", {})
            chat_id = str(chat.get("id"))
            chat_type = chat.get("type")
            is_private = chat_type == "private"

            if not self._should_accept_chat(chat_id, is_private):
                continue

            text = (message.get("text") or message.get("caption") or "").strip()
            if is_private:
                if text.lower() in ("/start", "start"):
                    self._send_welcome_keyboard(chat_id)
                    continue
                if text in self.QUICK_ACTIONS:
                    self._remember_last_action(chat_id, text)
                    self._send_followup(chat_id, text)
                    continue

            is_comment = chat_id in self.discussion_chat_ids
            reply = message.get("reply_to_message")
            parent_external_id = ""
            thread_url = ""
            origin_username = self._extract_origin_username(message, reply)
            if is_comment and reply:
                parent_external_id = str(reply.get("message_id", ""))
                if origin_username and parent_external_id:
                    thread_url = f"https://t.me/{origin_username}/{parent_external_id}"

            author = self._extract_author(message)
            attachments = self._extract_attachments(message)

            metadata = {
                "chat_id": chat.get("id"),
                "chat_type": chat_type,
                "discussion_chat": is_comment,
                "parent_external_id": parent_external_id,
                "origin_username": origin_username,
                "attachments": attachments,
                "raw": message,
            }
            if is_private:
                last_action = self._pop_last_action(chat_id)
                if last_action:
                    metadata["suggested_category"] = self.QUICK_ACTIONS[last_action][0]

            events.append(
                {
                    "external_id": str(message.get("message_id")),
                    "channel": "telegram",
                    "author": author,
                    "payload": text,
                    "is_comment": is_comment,
                    "parent_external_id": parent_external_id,
                    "thread_url": thread_url,
                    "source_chat_id": chat_id,
                    "metadata": metadata,
                }
            )
        if events:
            self._persist_offset()
        return events

    def acknowledge(self, message_id: str) -> None:
        logger.debug("Telegram message %s отмечен как обработанный", message_id)

    def send_quick_reply(self, chat_id: str, text: str) -> Optional[str]:
        return self._post_message(
            chat_id,
            text,
            reply_markup={
                "keyboard": self.QUICK_REPLY_BUTTONS,
                "resize_keyboard": True,
                "one_time_keyboard": False,
            },
        )

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
        try:
            value = self.redis.get(self.offset_key)
        except Exception as exc:  # pragma: no cover - зависит от внешнего Redis
            logger.warning("Не удалось прочитать offset Telegram: %s", exc)
            return 0
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

    def _redact_token(self, message: str) -> str:
        if not self.token:
            return message
        return message.replace(self.token, "[redacted]")

    def _should_accept_chat(self, chat_id: str, is_private: bool) -> bool:
        if is_private:
            return self.allow_private
        if self.chat_ids and chat_id in self.chat_ids:
            return True
        if self.discussion_chat_ids and chat_id in self.discussion_chat_ids:
            return True
        return not self.chat_ids and not self.discussion_chat_ids

    def _send_welcome_keyboard(self, chat_id: str):
        text = (
            "👋 Привет! Вы можете отправить обращение в транспортную компанию. "
            "Выберите тип обращения на клавиатуре или просто опишите проблему."
        )
        self.send_quick_reply(chat_id, text)

    def _send_followup(self, chat_id: str, action: str):
        _, prompt = self.QUICK_ACTIONS.get(
            action, ("request", "Введите детали обращения.")
        )
        self._post_message(chat_id, f"✅ {action}. {prompt}")

    def _post_message(self, chat_id: str, text: str, reply_markup=None) -> Optional[str]:
        if not self.token:
            return None
        payload = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        response = requests.post(
            f"{self.api_url}/sendMessage",
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            logger.warning("Не удалось отправить сообщение клавиатуры: %s", data)
            return None
        return str(data["result"]["message_id"])

    @staticmethod
    def _parse_chat_ids(raw: str) -> set[str]:
        ids = set()
        for value in raw.split(","):
            value = value.strip()
            if value:
                ids.add(value)
        return ids

    @staticmethod
    def _extract_attachments(message: Mapping) -> list[dict[str, str]]:
        """Сохраняет только компактные ссылки на вложения из Telegram update."""
        attachments = []
        if message.get("photo"):
            photos = message["photo"]
            best = max(photos, key=lambda p: p.get("width", 0) * p.get("height", 0))
            attachments.append({"type": "photo", "file_id": best.get("file_id", "")})
        if message.get("document"):
            doc = message["document"]
            attachments.append({
                "type": "document",
                "file_id": doc.get("file_id", ""),
                "file_name": doc.get("file_name", ""),
            })
        if message.get("video"):
            video = message["video"]
            attachments.append({"type": "video", "file_id": video.get("file_id", "")})
        if message.get("voice"):
            attachments.append({"type": "voice", "file_id": message["voice"].get("file_id", "")})
        if message.get("audio"):
            audio = message["audio"]
            attachments.append({
                "type": "audio",
                "file_id": audio.get("file_id", ""),
                "file_name": audio.get("file_name", ""),
            })
        return attachments

    @staticmethod
    def _extract_author(message: Mapping) -> str:
        author = message.get("from") or {}
        return author.get("username") or author.get("first_name") or "unknown"

    @staticmethod
    def _extract_origin_username(message: Mapping, reply: Optional[Mapping]) -> str:
        sender_chat = (message.get("sender_chat") or {}).get("username")
        if sender_chat:
            return sender_chat
        if reply:
            return (
                (reply.get("sender_chat") or {}).get("username")
                or (reply.get("forward_from_chat") or {}).get("username")
                or (reply.get("chat") or {}).get("username")
                or ""
            )
        return ""

    def _remember_last_action(self, chat_id: str, action: str):
        if not self.redis:
            return
        try:
            self.redis.setex(self._private_action_key(chat_id), 600, action)
        except Exception as exc:  # pragma: no cover
            logger.warning("Не удалось сохранить выбранный тип обращения: %s", exc)

    def _pop_last_action(self, chat_id: str) -> Optional[str]:
        if not self.redis:
            return None
        key = self._private_action_key(chat_id)
        try:
            value = self.redis.get(key)
            if value:
                self.redis.delete(key)
            return value
        except Exception:  # pragma: no cover
            return None

    @staticmethod
    def _private_action_key(chat_id: str) -> str:
        return f"ingestion:telegram:last_action:{chat_id}"
