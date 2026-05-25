from unittest.mock import MagicMock

import pytest

from django.utils import timezone
from rest_framework.test import APIClient

from companies.models import Company, UserProfile
from tickets.models import ChannelMessage, Ticket, TicketResponse
from tickets.services import TelegramChannel, TicketResponseService


@pytest.mark.django_db
def test_ticket_response_service_sends_message(user_factory, ticket_factory):
    ticket: Ticket = ticket_factory()
    ChannelMessage.objects.create(
        external_id="123",
        channel=ChannelMessage.Channel.TELEGRAM,
        author="user",
        payload="hello",
        metadata={"chat_id": 1, "raw": {"message_id": 123}},
        received_at=timezone.now(),
        ticket=ticket,
    )
    fake_channel = MagicMock()
    fake_channel.send.return_value = "999"
    service = TicketResponseService(
        channels={TicketResponse.Channel.TELEGRAM: fake_channel}
    )

    response = service.respond(ticket, "Ответ", author=user_factory())

    assert response.status == response.Status.SENT
    assert response.external_message_id == "999"
    fake_channel.send.assert_called_once()


@pytest.mark.django_db
def test_telegram_channel_uses_configured_timeouts(monkeypatch, settings, ticket_factory):
    settings.TELEGRAM_CONNECT_TIMEOUT = 0.4
    settings.TELEGRAM_READ_TIMEOUT = 0.8
    ticket: Ticket = ticket_factory()
    ChannelMessage.objects.create(
        external_id="123",
        channel=ChannelMessage.Channel.TELEGRAM,
        author="user",
        payload="hello",
        metadata={"chat_id": 1, "raw": {"message_id": 123}},
        received_at=timezone.now(),
        ticket=ticket,
    )
    sent = {}

    class FakeResponse:
        status_code = 200
        ok = True
        content = b"{}"

        def json(self):
            return {"ok": True, "result": {"message_id": 777}}

    def fake_post(url, json, timeout):
        sent["url"] = url
        sent["payload"] = json
        sent["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("tickets.services.requests.post", fake_post)

    result = TelegramChannel(token="token").send(ticket, "Ответ")

    assert result == "777"
    assert sent["timeout"] == (0.4, 0.8)
    assert sent["payload"]["reply_to_message_id"] == 123


@pytest.mark.django_db
def test_ticket_respond_api_returns_failed_response_when_delivery_fails(
    monkeypatch, user_factory
):
    company = Company.objects.create(
        name="Тестовая компания",
        contact_email="test@example.com",
        status=Company.Status.ACTIVE,
    )
    user = user_factory()
    UserProfile.objects.create(
        user=user,
        company=company,
        role=UserProfile.Role.OPERATOR,
    )
    ticket = Ticket.objects.create(
        title="Проблема с поездом",
        category=Ticket.Category.COMPLAINT,
        company=company,
    )
    ChannelMessage.objects.create(
        external_id="123",
        channel=ChannelMessage.Channel.TELEGRAM,
        author="passenger",
        payload="долго жду поезд",
        metadata={"chat_id": 1, "raw": {"message_id": 123}},
        received_at=timezone.now(),
        ticket=ticket,
        company=company,
    )

    def fail_delivery(self, ticket, body):
        raise RuntimeError("Telegram delivery failed")

    monkeypatch.setattr(TelegramChannel, "send", fail_delivery)

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        f"/api/tickets/{ticket.id}/respond/",
        {"body": "Ответ оператора"},
        format="json",
    )

    assert response.status_code == 502
    assert response.data["detail"] == "Не удалось доставить ответ во внешний канал"
    assert response.data["response"]["status"] == TicketResponse.Status.FAILED
    failed_response = TicketResponse.objects.get(ticket=ticket)
    assert failed_response.status == TicketResponse.Status.FAILED
