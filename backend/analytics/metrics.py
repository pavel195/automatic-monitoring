from datetime import timedelta

from django.db.models import (
    Avg, Count, DurationField, ExpressionWrapper, F,
    Case, When, CharField,
)
from django.db.models.functions import TruncHour, TruncDay
from django.utils import timezone

from tickets.models import ChannelMessage, Ticket


def aggregate_metrics(company=None, period="24h"):
    """Агрегация метрик с опциональной фильтрацией по компании и периоду."""
    now = timezone.now()
    period_map = {"24h": 1, "7d": 7, "30d": 30}
    days = period_map.get(period, 1)
    start = now - timedelta(days=days)

    queryset = Ticket.objects.filter(created_at__gte=start)
    if company:
        queryset = queryset.filter(company=company)
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
    mode_breakdown = queryset.values("transport_mode").annotate(total=Count("id"))
    transport_total = queryset.filter(is_transport=True).count()
    total = queryset.count()

    topic_expr = Case(
        When(is_transport=True, then=F("transport_mode")),
        default=F("category"),
        output_field=CharField(),
    )
    topic_breakdown = (
        queryset.annotate(topic=topic_expr)
        .values("topic")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    channel_queryset = ChannelMessage.objects.filter(received_at__gte=start)
    if company:
        channel_queryset = channel_queryset.filter(company=company)
    channel_breakdown = (
        channel_queryset.values("channel")
        .annotate(total=Count("id"))
        .order_by("-total")
    )
    open_count = queryset.exclude(status=Ticket.Status.CLOSED).count()
    new_count = queryset.filter(status=Ticket.Status.NEW).count()

    # Additional dashboard metrics
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    tickets_today = Ticket.objects.filter(created_at__gte=today_start)
    tickets_this_week = Ticket.objects.filter(created_at__gte=week_start)
    if company:
        tickets_today = tickets_today.filter(company=company)
        tickets_this_week = tickets_this_week.filter(company=company)

    sla_breached = Ticket.objects.filter(
        ack_deadline__lt=now,
        status=Ticket.Status.NEW,
    )
    if company:
        sla_breached = sla_breached.filter(company=company)

    # Flow counts
    in_progress_count = queryset.filter(status=Ticket.Status.IN_PROGRESS).count()
    resolved_count = resolved.count()

    # Recent activity
    recent_tickets = (
        Ticket.objects.order_by("-updated_at")
    )
    if company:
        recent_tickets = recent_tickets.filter(company=company)
    recent_activity = list(
        recent_tickets[:10].values("id", "title", "status", "category", "priority", "updated_at")
    )

    # Time series
    time_series = aggregate_time_series(company=company, period=period)

    return {
        "total": total,
        "resolved": resolved_count,
        "mtta_seconds": mtta.total_seconds() if mtta else None,
        "mttr_seconds": mttr.total_seconds() if mttr else None,
        "category_breakdown": list(category_breakdown),
        "topic_breakdown": list(topic_breakdown),
        "sentiment_breakdown": list(sentiment_breakdown),
        "status_breakdown": list(status_breakdown),
        "mode_breakdown": list(mode_breakdown),
        "channel_breakdown": list(channel_breakdown),
        "open_count": open_count,
        "new_count": new_count,
        "messages_total": channel_queryset.count(),
        "transport_total": transport_total,
        "transport_share": transport_total / total if total else 0,
        # New fields
        "tickets_today": tickets_today.count(),
        "tickets_this_week": tickets_this_week.count(),
        "sla_breached_count": sla_breached.count(),
        "in_progress_count": in_progress_count,
        "recent_activity": recent_activity,
        "time_series": time_series,
    }


def aggregate_time_series(company=None, period="24h"):
    """Генерация данных временных рядов для графиков."""
    now = timezone.now()
    period_map = {"24h": 1, "7d": 7, "30d": 30}
    days = period_map.get(period, 1)
    start = now - timedelta(days=days)

    queryset = Ticket.objects.filter(created_at__gte=start)
    if company:
        queryset = queryset.filter(company=company)

    # Use hourly for 24h, daily for 7d/30d
    if period == "24h":
        trunc_fn = TruncHour
    else:
        trunc_fn = TruncDay

    data = (
        queryset.annotate(period=trunc_fn("created_at"))
        .values("period")
        .annotate(count=Count("id"))
        .order_by("period")
    )

    return [
        {"timestamp": item["period"].isoformat(), "count": item["count"]}
        for item in data
    ]
