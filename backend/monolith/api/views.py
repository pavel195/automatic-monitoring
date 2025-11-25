from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response

from analytics.metrics import aggregate_metrics
from analytics.search_indexer import search_tickets
from routing.tasks import classify_message
from tickets.models import Assignment, ChannelMessage, Ticket

from .serializers import (
    AssignmentSerializer,
    ChannelMessageSerializer,
    TicketSerializer,
)


class ChannelMessageViewSet(viewsets.ModelViewSet):
    queryset = ChannelMessage.objects.select_related("ticket").all()
    serializer_class = ChannelMessageSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=True, methods=["post"])
    def classify(self, request, pk=None):
        classify_message.delay(pk)
        return Response({"status": "queued"})


class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.prefetch_related("messages").all()
    serializer_class = TicketSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        ticket = self.get_object()
        user = request.user if request.user.is_authenticated else None
        ticket.mark_acknowledged(user=user)
        return Response(self.get_serializer(ticket).data)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        ticket = self.get_object()
        ticket.status = Ticket.Status.RESOLVED
        ticket.resolved_at = timezone.now()
        ticket.save(update_fields=["status", "resolved_at"])
        return Response(self.get_serializer(ticket).data)


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.select_related("ticket").all()
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.AllowAny]


class AnalyticsMetricsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(aggregate_metrics())


class SearchView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        query = request.query_params.get("q", "")
        if not query:
            return Response({"hits": []})
        result = search_tickets(query)
        return Response(result)

