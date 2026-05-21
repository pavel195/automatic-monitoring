import logging
import time
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
        token = self._get_bot_token(ticket)
        if not token:
            raise RuntimeError("Telegram token is not configured for this ticket's company")

        context = self._extract_context(ticket)
        payload = {
            "chat_id": context.chat_id,
            "text": body,
            "disable_web_page_preview": True,
        }

        if context.reply_to:
            try:
                reply_id = int(context.reply_to)
                payload["reply_to_message_id"] = reply_id
            except (ValueError, TypeError):
                logger.warning("Некорректный reply_to_message_id: %s", context.reply_to)

        url = self.api_template.format(token=token, method="sendMessage")
        logger.info("Отправка ответа в Telegram: chat_id=%s", context.chat_id)

        # Retry logic (3 attempts, exponential backoff)
        last_exc = None
        for attempt in range(3):
            try:
                response = requests.post(url, json=payload, timeout=10)
                if response.status_code in (502, 503, 504):
                    raise requests.exceptions.HTTPError(response=response)
                if not response.ok:
                    error_data = response.json() if response.content else {}
                    logger.error("Ошибка Telegram API: status=%s, response=%s", response.status_code, error_data)
                    response.raise_for_status()

                data = response.json()
                if not data.get("ok"):
                    raise RuntimeError(f"Telegram API error: {data.get('description', 'Unknown')}")
                return str(data["result"]["message_id"])
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
                last_exc = exc
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise
            except requests.exceptions.HTTPError as exc:
                if exc.response is not None and exc.response.status_code in (502, 503, 504):
                    last_exc = exc
                    if attempt < 2:
                        time.sleep(2 ** attempt)
                        continue
                raise

        raise last_exc or RuntimeError("Failed to send Telegram message")

    def _get_bot_token(self, ticket: Ticket) -> Optional[str]:
        if not ticket.company:
            return self.token
        try:
            from companies.models import TelegramBot
            bot = TelegramBot.objects.filter(
                company=ticket.company,
                status=TelegramBot.Status.ACTIVE
            ).first()
            if bot:
                return bot.bot_token
            return self.token
        except Exception as e:
            logger.error("Ошибка при получении токена бота: %s", e)
            return self.token

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

        reply_to = None
        raw_data = metadata.get("raw", {})
        if raw_data:
            reply_to = raw_data.get("message_id")
        if not reply_to:
            reply_to = message.external_id

        return TelegramContext(chat_id=str(chat_id), reply_to=str(reply_to) if reply_to else None)


class VkChannel(OutboundChannel):
    """Отправка ответов через VK Community Bot."""

    def send(self, ticket: Ticket, body: str) -> str:
        message = ticket.messages.order_by("received_at").first()
        if not message:
            raise RuntimeError("Ticket doesn't have source message")

        metadata = message.metadata or {}
        peer_id = metadata.get("peer_id")
        if not peer_id:
            raise RuntimeError("VK peer_id missing in metadata")

        token = self._get_community_token(ticket)
        if not token:
            raise RuntimeError("VK community token not configured")

        reply_to = metadata.get("conversation_message_id")

        from ingestion.connectors.vk_client import VkConnector
        connector = VkConnector(
            community_token=token,
            community_id=self._get_community_id(ticket),
        )
        result = connector.send_message(
            peer_id=int(peer_id),
            text=body,
            reply_to=int(reply_to) if reply_to else None,
        )
        return str(result)

    def _get_community_token(self, ticket: Ticket) -> Optional[str]:
        if not ticket.company:
            return None
        try:
            from companies.models import VkBot
            bot = VkBot.objects.filter(
                company=ticket.company,
                status=VkBot.Status.ACTIVE
            ).first()
            return bot.community_token if bot else None
        except Exception:
            return None

    def _get_community_id(self, ticket: Ticket) -> str:
        if not ticket.company:
            return ""
        try:
            from companies.models import VkBot
            bot = VkBot.objects.filter(
                company=ticket.company,
                status=VkBot.Status.ACTIVE
            ).first()
            return bot.community_id if bot else ""
        except Exception:
            return ""


class TicketResponseService:
    """Высокоуровневый сервис публикации ответов (SOLID: SRP).

    Автоматически определяет канал ответа по исходному сообщению.
    """

    def __init__(self, channels: Optional[dict[str, OutboundChannel]] = None):
        self.channels = channels or {}

    def respond(self, ticket: Ticket, body: str, author=None) -> TicketResponse:
        channel_type, outbound = self._resolve_channel(ticket)

        response = TicketResponse.objects.create(
            ticket=ticket,
            channel_message=ticket.messages.first(),
            author=author,
            body=body,
            channel=channel_type,
        )
        try:
            external_id = outbound.send(ticket, body)
            response.mark_sent(external_id)
            logger.info("Ответ отправлен через %s для тикета %s", channel_type, ticket.id)
        except Exception as exc:
            logger.error("Не удалось отправить ответ: %s", exc)
            response.status = TicketResponse.Status.FAILED
            response.sent_at = timezone.now()
            response.save(update_fields=["status", "sent_at"])
            raise
        return response

    def _resolve_channel(self, ticket: Ticket) -> tuple:
        """Определяет канал ответа по исходному сообщению."""
        first_message = ticket.messages.order_by("received_at").first()
        if first_message and first_message.channel == "vk":
            channel_type = TicketResponse.Channel.VK
            return channel_type, self.channels.get(channel_type) or VkChannel()
        channel_type = TicketResponse.Channel.TELEGRAM
        return channel_type, self.channels.get(channel_type) or TelegramChannel()
