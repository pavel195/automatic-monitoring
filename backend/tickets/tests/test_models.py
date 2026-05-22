import pytest

from tickets.models import Ticket


@pytest.mark.django_db
def test_mark_acknowledged_sets_timestamp(user_factory, ticket_factory):
    ticket = ticket_factory()
    ticket.mark_acknowledged(user_factory())
    assert ticket.status == Ticket.Status.ACK
    assert ticket.acknowledged_at is not None
    assert ticket.assigned_to is not None
