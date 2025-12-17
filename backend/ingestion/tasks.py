import logging
from datetime import datetime, timezone

from celery import shared_task

from ingestion.connectors.telegram_client import TelegramConnector
from routing.tasks import classify_message
from tickets.models import ChannelMessage, Sentiment, TransportMode

logger = logging.getLogger(__name__)


@shared_task
def poll_telegram():
    """Периодический опрос Telegram для всех активных ботов компаний."""
    from companies.models import TelegramBot

    # Получаем все активные боты
    active_bots = TelegramBot.objects.filter(
        status=TelegramBot.Status.ACTIVE, company__status="active"
    )
    
    logger.info(f"Найдено активных ботов: {active_bots.count()}")
    if active_bots.count() == 0:
        logger.warning("Нет активных ботов для обработки. Проверьте статус ботов и компаний.")

    total_processed = 0
    for bot in active_bots:
        logger.info(f"Обработка бота {bot.bot_username} (компания: {bot.company.name if bot.company else 'нет'})")
        try:
            connector = TelegramConnector(
                bot_token=bot.bot_token,
                chat_ids=bot.chat_ids or [],
                discussion_chat_ids=bot.discussion_chat_ids or [],
                allow_private=bot.allow_direct,
            )
            logger.info(f"Запрос обновлений для бота {bot.bot_username} (allow_private={bot.allow_direct}, chat_ids={len(bot.chat_ids or [])})")
            events = connector.poll()
            logger.info(f"Получено событий от Telegram API: {len(events)}")
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
                        "company": bot.company,  # Устанавливаем компанию из бота
                    },
                )
                if created:
                    classify_message.delay(str(msg.id))
                    connector.acknowledge(event["external_id"])
                    processed += 1
            if processed:
                logger.info(
                    "Обработано %s сообщений для бота компании %s",
                    processed,
                    bot.company.name,
                )
                total_processed += processed
        except Exception as exc:
            logger.error(
                "Ошибка при обработке бота %s компании %s: %s",
                bot.bot_username,
                bot.company.name if bot.company else "Unknown",
                exc,
            )
            # Обновляем статус бота при ошибке
            bot.status = TelegramBot.Status.ERROR
            bot.last_error = str(exc)
            bot.save(update_fields=["status", "last_error"])

    if total_processed:
        logger.info("Всего обработано %s телеграм-сообщений", total_processed)

