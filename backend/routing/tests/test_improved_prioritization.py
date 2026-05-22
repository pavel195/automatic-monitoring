"""Тесты для улучшенной логики приоритизации."""

import pytest
from datetime import timedelta
from django.utils import timezone

from routing.tasks import classify_message
from tickets.models import ChannelMessage, Ticket, Sentiment


@pytest.mark.django_db
def test_priority_increases_with_negative_sentiment():
    """Приоритет повышается при негативной тональности."""
    message = ChannelMessage.objects.create(
        external_id="test1",
        channel=ChannelMessage.Channel.TELEGRAM,
        author="user1",
        payload="Ужасное обслуживание, все плохо",
        received_at=timezone.now(),
    )

    classify_message(str(message.id))

    ticket = Ticket.objects.get(messages=message)
    # Негативная тональность должна повысить приоритет
    assert ticket.priority >= Ticket.Priority.HIGH


@pytest.mark.django_db
def test_priority_decreases_with_positive_sentiment():
    """Приоритет снижается при позитивной тональности."""
    message = ChannelMessage.objects.create(
        external_id="test2",
        channel=ChannelMessage.Channel.TELEGRAM,
        author="user2",
        payload="Спасибо за отличную работу, все прекрасно",
        received_at=timezone.now(),
    )

    classify_message(str(message.id))

    ticket = Ticket.objects.get(messages=message)
    # Позитивная тональность должна снизить приоритет
    assert ticket.priority <= Ticket.Priority.MEDIUM


@pytest.mark.django_db
def test_critical_priority_for_critical_markers():
    """Критические маркеры устанавливают критический приоритет."""
    message = ChannelMessage.objects.create(
        external_id="test3",
        channel=ChannelMessage.Channel.TELEGRAM,
        author="user3",
        payload="Пожар в вагоне метро, нужна срочная помощь",
        received_at=timezone.now(),
    )

    classify_message(str(message.id))

    ticket = Ticket.objects.get(messages=message)
    assert ticket.priority == Ticket.Priority.CRITICAL


@pytest.mark.django_db
def test_night_time_increases_priority():
    """Ночные обращения получают повышенный приоритет."""
    # Создаем сообщение в ночное время (23:00)
    night_time = timezone.now().replace(hour=23, minute=0, second=0, microsecond=0)
    message = ChannelMessage.objects.create(
        external_id="test4",
        channel=ChannelMessage.Channel.TELEGRAM,
        author="user4",
        payload="Проблема с автобусом",
        received_at=night_time,
    )

    classify_message(str(message.id))

    ticket = Ticket.objects.get(messages=message)
    # Ночное время должно повысить приоритет
    assert ticket.priority >= Ticket.Priority.MEDIUM


@pytest.mark.django_db
def test_repeated_complaints_increase_priority():
    """Повторные жалобы от одного автора повышают приоритет."""
    author = "complainer"
    base_time = timezone.now()

    # Создаем несколько жалоб от одного автора
    for i in range(3):
        message = ChannelMessage.objects.create(
            external_id=f"test5_{i}",
            channel=ChannelMessage.Channel.TELEGRAM,
            author=author,
            payload="Жалуюсь на плохое обслуживание",
            received_at=base_time - timedelta(days=i),
            sentiment=Sentiment.NEGATIVE,
        )

    # Классифицируем последнее сообщение
    classify_message(str(message.id))

    ticket = Ticket.objects.get(messages=message)
    # Повторные жалобы должны повысить приоритет
    assert ticket.priority >= Ticket.Priority.HIGH


@pytest.mark.django_db
def test_new_message_from_same_vk_author_joins_open_ticket():
    first = ChannelMessage.objects.create(
        external_id="vk_10_1",
        channel=ChannelMessage.Channel.VK,
        author="vk-user-10",
        payload="Автобус снова задерживается",
        received_at=timezone.now(),
    )
    followup = ChannelMessage.objects.create(
        external_id="vk_10_2",
        channel=ChannelMessage.Channel.VK,
        author="vk-user-10",
        payload="Жду уже пятнадцать минут",
        received_at=timezone.now() + timedelta(minutes=1),
    )

    classify_message(str(first.id))
    classify_message(str(followup.id))

    first.refresh_from_db()
    followup.refresh_from_db()

    assert first.ticket_id == followup.ticket_id
    assert Ticket.objects.count() == 1


@pytest.mark.django_db
def test_message_from_other_channel_creates_separate_ticket():
    vk_message = ChannelMessage.objects.create(
        external_id="vk_11_1",
        channel=ChannelMessage.Channel.VK,
        author="shared-author",
        payload="Проблема в группе VK",
        received_at=timezone.now(),
    )
    telegram_message = ChannelMessage.objects.create(
        external_id="tg_11_1",
        channel=ChannelMessage.Channel.TELEGRAM,
        author="shared-author",
        payload="Проблема в Telegram",
        received_at=timezone.now() + timedelta(minutes=1),
    )

    classify_message(str(vk_message.id))
    classify_message(str(telegram_message.id))

    vk_message.refresh_from_db()
    telegram_message.refresh_from_db()

    assert vk_message.ticket_id != telegram_message.ticket_id
    assert Ticket.objects.count() == 2
