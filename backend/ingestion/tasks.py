import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

import requests
import redis
from celery import shared_task
from django.conf import settings

from ingestion.connectors.telegram_client import TelegramConnector
from routing.tasks import classify_message
from tickets.models import ChannelMessage, Sentiment, TransportMode

logger = logging.getLogger(__name__)


@contextmanager
def polling_lock(name: str, ttl: int = 30):
    """Защищает частый polling от наложения предыдущего запуска."""
    key = f"ingestion:poll_lock:{name}"
    token = uuid4().hex
    try:
        client = redis.Redis.from_url(settings.CELERY_BROKER_URL, decode_responses=True)
        acquired = client.set(key, token, nx=True, ex=ttl)
    except redis.RedisError as exc:
        logger.warning("Не удалось получить Redis-lock для polling %s: %s", name, exc)
        yield True
        return

    if not acquired:
        yield False
        return

    try:
        yield True
    finally:
        try:
            if client.get(key) == token:
                client.delete(key)
        except redis.RedisError as exc:
            logger.warning("Не удалось освободить Redis-lock для polling %s: %s", name, exc)


@shared_task
def poll_telegram():
    """Периодический опрос Telegram для всех активных ботов компаний."""
    from companies.models import TelegramBot

    with polling_lock(
        "telegram", ttl=getattr(settings, "POLL_LOCK_TTL_SECONDS", 30)
    ) as acquired:
        if not acquired:
            logger.debug("Предыдущий Telegram polling ещё выполняется, цикл пропущен")
            return
        _poll_telegram_bots(TelegramBot)


def _poll_telegram_bots(TelegramBot):
    active_bots = TelegramBot.objects.filter(
        status=TelegramBot.Status.ACTIVE, company__status="active"
    )
    bots_count = active_bots.count()

    logger.info("Найдено активных ботов: %s", bots_count)
    if bots_count == 0:
        logger.warning("Нет активных ботов для обработки. Проверьте статус ботов и компаний.")

    total_processed = 0
    for bot in active_bots:
        logger.info(
            "Обработка бота %s (компания: %s)",
            bot.bot_username,
            bot.company.name if bot.company else "нет",
        )
        try:
            connector = TelegramConnector(
                bot_token=bot.bot_token,
                chat_ids=bot.chat_ids or [],
                discussion_chat_ids=bot.discussion_chat_ids or [],
                allow_private=bot.allow_direct,
            )
            logger.info(
                "Запрос обновлений для бота %s (allow_private=%s, chat_ids=%s)",
                bot.bot_username,
                bot.allow_direct,
                len(bot.chat_ids or []),
            )
            events = connector.poll()
            logger.info("Получено событий от Telegram API: %s", len(events))
            processed = 0
            for event in events:
                external_id = event.get("external_id")
                logger.debug(
                    "Обработка события: external_id=%s, author=%s, payload=%s",
                    external_id,
                    event.get("author"),
                    event.get("payload", "")[:50],
                )

                # Polling может вернуть уже обработанный update, поэтому проверяем id до сохранения.
                exists = ChannelMessage.objects.filter(
                    external_id=external_id,
                    channel=event.get("channel", ChannelMessage.Channel.TELEGRAM),
                ).exists()

                if exists:
                    logger.debug("Сообщение %s уже существует в БД, пропускаем", external_id)
                    continue

                received_at = event.get("received_at") or datetime.now(timezone.utc)
                try:
                    msg, created = ChannelMessage.objects.get_or_create(
                        external_id=external_id,
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
                            "company": bot.company,
                        },
                    )
                    if created:
                        logger.info(
                            "Создано новое сообщение: ID=%s, external_id=%s, payload=%s",
                            msg.id,
                            external_id,
                            msg.payload[:50],
                        )
                        classify_message.delay(str(msg.id))
                        connector.acknowledge(external_id)
                        processed += 1
                    else:
                        logger.debug("Сообщение %s уже существует после get_or_create", external_id)
                except Exception as e:
                    logger.error("Ошибка при сохранении сообщения %s: %s", external_id, e, exc_info=True)
            if processed:
                logger.info(
                    "Обработано %s сообщений для бота компании %s",
                    processed,
                    bot.company.name,
                )
                total_processed += processed
        except requests.exceptions.HTTPError as exc:
            # Ошибка 409 Conflict - это нормально, не меняем статус
            if exc.response and exc.response.status_code == 409:
                logger.debug(
                    "Telegram API 409 Conflict для бота %s (параллельные запросы) - это нормально",
                    bot.bot_username
                )
            else:
                # Другие HTTP ошибки - логируем, но не меняем статус на ERROR сразу
                logger.warning(
                    "HTTP ошибка при обработке бота %s компании %s: %s",
                    bot.bot_username,
                    bot.company.name if bot.company else "Unknown",
                    exc,
                )
        except requests.exceptions.RequestException as exc:
            error_message = str(exc).replace(bot.bot_token, "[redacted]")
            logger.warning(
                "Сетевая ошибка при обработке бота %s компании %s: %s",
                bot.bot_username,
                bot.company.name if bot.company else "Unknown",
                error_message,
            )
            bot.last_error = error_message[:500]
            bot.save(update_fields=["last_error"])
        except Exception as exc:
            # Критические ошибки - меняем статус на ERROR
            logger.error(
                "Критическая ошибка при обработке бота %s компании %s: %s",
                bot.bot_username,
                bot.company.name if bot.company else "Unknown",
                exc,
            )
            # Обновляем статус бота при критической ошибке
            bot.status = TelegramBot.Status.ERROR
            bot.last_error = str(exc)[:500]  # Ограничиваем длину ошибки
            bot.save(update_fields=["status", "last_error"])

    if total_processed:
        logger.info("Всего обработано %s телеграм-сообщений", total_processed)


@shared_task
def poll_vk():
    """Периодический опрос VK для всех активных ботов сообществ."""
    from companies.models import VkBot
    from ingestion.connectors.vk_client import VkConnector

    with polling_lock("vk", ttl=getattr(settings, "POLL_LOCK_TTL_SECONDS", 30)) as acquired:
        if not acquired:
            logger.debug("Предыдущий VK polling ещё выполняется, цикл пропущен")
            return
        _poll_vk_bots(VkBot, VkConnector)


def _poll_vk_bots(VkBot, VkConnector):
    active_bots = VkBot.objects.filter(
        status=VkBot.Status.ACTIVE, company__status="active"
    )

    logger.info("VK: найдено активных ботов: %s", active_bots.count())

    total_processed = 0
    for bot in active_bots:
        logger.info("VK: обработка бота %s (сообщество: %s)", bot.community_name, bot.company.name)
        try:
            connector = VkConnector(
                community_token=bot.community_token,
                community_id=bot.community_id,
                wait=getattr(settings, "VK_LONG_POLL_WAIT_SECONDS", 1),
            )
            events = connector.poll()
            logger.info("VK: получено событий: %s", len(events))
            processed = 0
            for event in events:
                external_id = event.get("external_id")

                exists = ChannelMessage.objects.filter(
                    external_id=external_id,
                    channel=ChannelMessage.Channel.VK,
                ).exists()
                if exists:
                    continue

                received_at = event.get("received_at") or datetime.now(timezone.utc)
                try:
                    msg, created = ChannelMessage.objects.get_or_create(
                        external_id=external_id,
                        channel=ChannelMessage.Channel.VK,
                        defaults={
                            "author": event.get("author", ""),
                            "payload": event.get("payload", ""),
                            "metadata": event.get("metadata", {}),
                            "received_at": received_at,
                            "is_transport": True,
                            "sentiment": Sentiment.NEUTRAL,
                            "transport_mode": TransportMode.OTHER,
                            "company": bot.company,
                            "source_chat_id": event.get("source_chat_id", ""),
                        },
                    )
                    if created:
                        logger.info("VK: создано сообщение ID=%s", msg.id)
                        classify_message.delay(str(msg.id))
                        connector.acknowledge(external_id)
                        processed += 1
                except Exception as e:
                    logger.error("VK: ошибка сохранения сообщения %s: %s", external_id, e, exc_info=True)

            if processed:
                logger.info("VK: обработано %s сообщений для %s", processed, bot.company.name)
                total_processed += processed
        except Exception as exc:
            logger.error("VK: ошибка при обработке бота %s: %s", bot.community_name, exc)
            bot.status = VkBot.Status.ERROR
            bot.last_error = str(exc)[:500]
            bot.save(update_fields=["status", "last_error"])

    if total_processed:
        logger.info("VK: всего обработано %s сообщений", total_processed)
