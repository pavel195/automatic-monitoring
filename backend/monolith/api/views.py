from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from analytics.metrics import aggregate_metrics
from analytics.search_indexer import search_tickets
from routing.tasks import classify_message
from tickets.models import Assignment, ChannelMessage, Ticket, TicketResponse
from tickets.services import TicketResponseService

from .serializers import (
    AssignmentSerializer,
    ChannelMessageSerializer,
    TicketResponseSerializer,
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
    queryset = (
        Ticket.objects.prefetch_related("messages", "responses")
        .select_related("assigned_to")
        .all()
    )
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

    @action(detail=True, methods=["post"])
    def respond(self, request, pk=None):
        ticket = self.get_object()
        body = request.data.get("body", "").strip()
        if not body:
            return Response({"detail": "Текст ответа обязателен"}, status=400)
        service = TicketResponseService()
        response = service.respond(
            ticket=ticket,
            body=body,
            author=request.user if request.user.is_authenticated else None,
        )
        serializer = TicketResponseSerializer(response)
        return Response(serializer.data, status=201)


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


class TicketResponseViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TicketResponse.objects.select_related("ticket", "author").all()
    serializer_class = TicketResponseSerializer
    permission_classes = [permissions.AllowAny]

