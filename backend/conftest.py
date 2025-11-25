import factory
import pytest
from django.contrib.auth import get_user_model

from tickets.models import Ticket


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")


class TicketFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Ticket

    title = factory.Sequence(lambda n: f"Ticket {n}")
    category = Ticket.Category.REQUEST
    priority = Ticket.Priority.MEDIUM


@pytest.fixture
def user_factory():
    def _create(**kwargs):
        return UserFactory(**kwargs)

    return _create


@pytest.fixture
def ticket_factory():
    def _create(**kwargs):
        return TicketFactory(**kwargs)

    return _create

