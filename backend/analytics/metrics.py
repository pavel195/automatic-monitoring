from datetime import timedelta

from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F
from django.utils import timezone

from tickets.models import Ticket


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

    breakdown = queryset.values("category").annotate(total=Count("id"))

    return {
        "total": queryset.count(),
        "resolved": resolved.count(),
        "mtta_seconds": mtta.total_seconds() if mtta else None,
        "mttr_seconds": mttr.total_seconds() if mttr else None,
        "category_breakdown": list(breakdown),
    }

