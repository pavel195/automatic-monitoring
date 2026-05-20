import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from companies.models import Company, TelegramBot, UserProfile, VkBot
from tickets.models import ChannelMessage, Ticket, TicketResponse

User = get_user_model()


@pytest.mark.django_db
def test_seed_demo_data_creates_realistic_workspace():
    call_command(
        "seed_demo_data",
        companies=2,
        tickets=12,
        password="DemoPass123!",
        skip_index=True,
    )

    assert Company.objects.filter(contact_email__endswith="@demo.transport.local").count() == 2
    assert User.objects.filter(username__startswith="demo_").count() == 9
    assert UserProfile.objects.filter(user__username__startswith="demo_").count() == 9
    assert TelegramBot.objects.count() == 2
    assert VkBot.objects.count() == 2
    assert Ticket.objects.filter(company__contact_email__endswith="@demo.transport.local").count() == 12
    assert Ticket.objects.filter(title__startswith="[DEMO]").count() == 0
    assert ChannelMessage.objects.filter(metadata__demo_seed=True).count() == 12
    assert set(
        ChannelMessage.objects.filter(metadata__demo_seed=True).values_list("channel", flat=True)
    ) == {
        ChannelMessage.Channel.TELEGRAM,
        ChannelMessage.Channel.VK,
    }
    assert TicketResponse.objects.filter(
        ticket__company__contact_email__endswith="@demo.transport.local"
    ).count() > 0

    mosmetro_categories = set(
        Ticket.objects.filter(company__contact_email="mosmetro@demo.transport.local")
        .values_list("category", flat=True)
    )
    mosmetro_channels = set(
        ChannelMessage.objects.filter(
            ticket__company__contact_email="mosmetro@demo.transport.local",
            metadata__demo_seed=True,
        ).values_list("channel", flat=True)
    )
    assert mosmetro_categories == {
        Ticket.Category.COMPLAINT,
        Ticket.Category.INCIDENT,
        Ticket.Category.REQUEST,
        Ticket.Category.PAYMENT,
        Ticket.Category.PRAISE,
        Ticket.Category.SUGGESTION,
    }
    assert mosmetro_channels == {
        ChannelMessage.Channel.TELEGRAM,
        ChannelMessage.Channel.VK,
    }

    operator = User.objects.get(username="demo_mosmetro_operator_1")
    assert operator.check_password("DemoPass123!")


@pytest.mark.django_db
def test_seed_demo_data_replaces_previous_demo_dataset():
    options = {
        "companies": 2,
        "tickets": 12,
        "password": "DemoPass123!",
        "skip_index": True,
    }

    call_command("seed_demo_data", **options)
    call_command("seed_demo_data", **options)

    assert Company.objects.filter(contact_email__endswith="@demo.transport.local").count() == 2
    assert User.objects.filter(username__startswith="demo_").count() == 9
    assert Ticket.objects.filter(company__contact_email__endswith="@demo.transport.local").count() == 12
    assert ChannelMessage.objects.filter(metadata__demo_seed=True).count() == 12
