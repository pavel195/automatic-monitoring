from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AnalyticsMetricsView,
    AssignmentViewSet,
    ChannelMessageViewSet,
    SearchView,
    TicketViewSet,
)

router = DefaultRouter()
router.register("messages", ChannelMessageViewSet)
router.register("tickets", TicketViewSet)
router.register("assignments", AssignmentViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("analytics/metrics/", AnalyticsMetricsView.as_view(), name="metrics"),
    path("search", SearchView.as_view(), name="search"),
]

