"""Тесты для улучшенной логики приоритизации."""

import pytest
from datetime import datetime, timedelta, timezone as tz
from django.utils import timezone

from routing.tasks import classify_message
from tickets.models import ChannelMessage, Ticket, Sentiment, TransportMode


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

