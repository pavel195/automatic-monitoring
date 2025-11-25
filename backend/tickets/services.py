import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import requests
from django.conf import settings
from django.utils import timezone

from tickets.models import ChannelMessage, Ticket, TicketResponse

logger = logging.getLogger(__name__)


class OutboundChannel(ABC):
    """Базовый интерфейс отправки ответов (SOLID: ISP + DIP)."""

    @abstractmethod
    def send(self, ticket: Ticket, body: str) -> str:
        """Возвращает внешний идентификатор отправленного сообщения."""


@dataclass
class TelegramContext:
    chat_id: str
    reply_to: Optional[str]


class TelegramChannel(OutboundChannel):
    api_template = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.TELEGRAM_BOT_TOKEN

    def send(self, ticket: Ticket, body: str) -> str:
        if not self.token:
            raise RuntimeError("Telegram token is not configured")
        context = self._extract_context(ticket)
        payload = {
            "chat_id": context.chat_id,
            "text": body,
            "reply_to_message_id": context.reply_to,
            "disable_web_page_preview": True,
        }
        url = self.api_template.format(token=self.token, method="sendMessage")
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram error: {data}")
        return str(data["result"]["message_id"])

    def _extract_context(self, ticket: Ticket) -> TelegramContext:
        message: Optional[ChannelMessage] = (
            ticket.messages.order_by("received_at").first()
        )
        if not message:
            raise RuntimeError("Ticket doesn't have source message")
        metadata = message.metadata or {}
        chat_id = metadata.get("chat_id")
        if not chat_id:
            raise RuntimeError("Telegram chat_id missing in metadata")
        reply_to = metadata.get("raw", {}).get("message_id", message.external_id)
        return TelegramContext(chat_id=str(chat_id), reply_to=str(reply_to))


class TicketResponseService:
    """Высокоуровневый сервис публикации ответов (SOLID: SRP)."""

    def __init__(self, channel: Optional[OutboundChannel] = None):
        self.channel = channel or TelegramChannel()

    def respond(self, ticket: Ticket, body: str, author=None) -> TicketResponse:
        response = TicketResponse.objects.create(
            ticket=ticket,
            channel_message=ticket.messages.first(),
            author=author,
            body=body,
            channel=TicketResponse.Channel.TELEGRAM,
        )
        try:
            external_id = self.channel.send(ticket, body)
            response.mark_sent(external_id)
            logger.info("Ответ отправлен в Telegram для тикета %s", ticket.id)
        except Exception as exc:  # pragma: no cover - логирование
            logger.error("Не удалось отправить ответ: %s", exc)
            response.status = TicketResponse.Status.FAILED
            response.sent_at = timezone.now()
            response.save(update_fields=["status", "sent_at"])
            raise
        return response


