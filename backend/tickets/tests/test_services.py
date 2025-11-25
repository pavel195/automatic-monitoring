from unittest.mock import MagicMock, patch

import pytest

from django.utils import timezone

from tickets.models import ChannelMessage, Ticket
from tickets.services import TicketResponseService


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
    service = TicketResponseService()
    fake_channel = MagicMock()
    fake_channel.send.return_value = "999"
    service.channel = fake_channel

    response = service.respond(ticket, "Ответ", author=user_factory())

    assert response.status == response.Status.SENT
    assert response.external_message_id == "999"
    fake_channel.send.assert_called_once()


