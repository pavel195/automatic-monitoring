from datetime import timedelta

from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F
from django.utils import timezone

from tickets.models import ChannelMessage, Ticket


def aggregate_metrics():
    now = timezone.now()
    last_day = now - timedelta(days=1)

    queryset = Ticket.objects.filter(created_at__gte=last_day)
    resolved = queryset.exclude(resolved_at__isnull=True)

    mtta = queryset.exclude(acknowledged_at__isnull=True).aggregate(
        value=Avg(
            ExpressionWrapper(
                F("acknowledged_at") - F("created_at"),
                output_field=DurationField(),
            )
        )
    )["value"]

    mttr = resolved.aggregate(
        value=Avg(
            ExpressionWrapper(
                F("resolved_at") - F("created_at"),
                output_field=DurationField(),
            )
        )
    )["value"]

    category_breakdown = queryset.values("category").annotate(total=Count("id"))
    sentiment_breakdown = queryset.values("sentiment").annotate(total=Count("id"))
    status_breakdown = queryset.values("status").annotate(total=Count("id"))
    transport_total = queryset.filter(is_transport=True).count()
    total = queryset.count()

    channel_queryset = ChannelMessage.objects.filter(received_at__gte=last_day)
    channel_breakdown = (
        channel_queryset.values("channel")
        .annotate(total=Count("id"))
        .order_by("-total")
    )
    open_count = queryset.exclude(status=Ticket.Status.CLOSED).count()
    new_count = queryset.filter(status=Ticket.Status.NEW).count()

    return {
        "total": total,
        "resolved": resolved.count(),
        "mtta_seconds": mtta.total_seconds() if mtta else None,
        "mttr_seconds": mttr.total_seconds() if mttr else None,
        "category_breakdown": list(category_breakdown),
        "sentiment_breakdown": list(sentiment_breakdown),
        "status_breakdown": list(status_breakdown),
        "channel_breakdown": list(channel_breakdown),
        "open_count": open_count,
        "new_count": new_count,
        "messages_total": channel_queryset.count(),
        "transport_total": transport_total,
        "transport_share": transport_total / total if total else 0,
    }

