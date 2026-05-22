from datetime import datetime, time, timedelta

import pytest
from django.utils import timezone

from analytics.metrics import aggregate_metrics
from tickets.models import Ticket


@pytest.mark.django_db
def test_metrics_include_the_full_selected_date_range(ticket_factory):
    today = timezone.localdate()
    start = timezone.make_aware(datetime.combine(today - timedelta(days=2), time.min))
    end = timezone.make_aware(datetime.combine(today, time.max))

    in_range = ticket_factory()
    Ticket.objects.filter(id=in_range.id).update(created_at=start + timedelta(hours=3))

    on_end_date = ticket_factory()
    Ticket.objects.filter(id=on_end_date.id).update(created_at=end - timedelta(hours=1))

    out_of_range = ticket_factory()
    Ticket.objects.filter(id=out_of_range.id).update(created_at=start - timedelta(seconds=1))

    metrics = aggregate_metrics(start=start, end=end)

    assert metrics["total"] == 2
    assert sum(point["count"] for point in metrics["time_series"]) == 2
