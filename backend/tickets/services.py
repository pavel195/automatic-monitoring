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
        # Получаем токен бота из компании тикета
        token = self._get_bot_token(ticket)
        if not token:
            raise RuntimeError("Telegram token is not configured for this ticket's company")
        
        context = self._extract_context(ticket)
        payload = {
            "chat_id": context.chat_id,
            "text": body,
            "disable_web_page_preview": True,
        }
        
        # Добавляем reply_to только если он есть и валидный
        if context.reply_to:
            try:
                # Проверяем, что reply_to - это число
                reply_id = int(context.reply_to)
                payload["reply_to_message_id"] = reply_id
            except (ValueError, TypeError):
                logger.warning("Некорректный reply_to_message_id: %s", context.reply_to)
        
        url = self.api_template.format(token=token, method="sendMessage")
        logger.info("Отправка ответа в Telegram: chat_id=%s, reply_to=%s", context.chat_id, context.reply_to)
        response = requests.post(url, json=payload, timeout=10)
        
        # Логируем детали ошибки, если есть
        if not response.ok:
            error_data = response.json() if response.content else {}
            logger.error("Ошибка Telegram API: status=%s, response=%s", response.status_code, error_data)
            response.raise_for_status()
        
        data = response.json()
        if not data.get("ok"):
            error_desc = data.get("description", "Unknown error")
            raise RuntimeError(f"Telegram API error: {error_desc}")
        return str(data["result"]["message_id"])

    def _get_bot_token(self, ticket: Ticket) -> Optional[str]:
        """Получает токен бота из компании тикета."""
        if not ticket.company:
            logger.warning("У тикета %s нет компании", ticket.id)
            return self.token  # Fallback на токен из настроек
        
        try:
            from companies.models import TelegramBot
            # Получаем активный бот компании
            bot = TelegramBot.objects.filter(
                company=ticket.company,
                status=TelegramBot.Status.ACTIVE
            ).first()
            
            if bot:
                logger.info("Используется токен бота %s для компании %s", bot.bot_username, ticket.company.name)
                return bot.bot_token
            else:
                logger.warning("Не найден активный бот для компании %s", ticket.company.name)
                return self.token  # Fallback на токен из настроек
        except Exception as e:
            logger.error("Ошибка при получении токена бота: %s", e)
            return self.token  # Fallback на токен из настроек

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
        
        # Получаем message_id из raw данных или external_id
        reply_to = None
        raw_data = metadata.get("raw", {})
        if raw_data:
            reply_to = raw_data.get("message_id")
        if not reply_to:
            reply_to = message.external_id
        
        return TelegramContext(chat_id=str(chat_id), reply_to=str(reply_to) if reply_to else None)


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


