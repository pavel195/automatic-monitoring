from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from analytics.metrics import aggregate_metrics
from analytics.search_indexer import search_tickets
from companies.permissions import CompanyObjectPermission, IsCompanyMember
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
    queryset = ChannelMessage.objects.select_related("ticket", "company").all()
    serializer_class = ChannelMessageSerializer
    permission_classes = [IsCompanyMember, CompanyObjectPermission]

    def get_queryset(self):
        """Фильтрация сообщений по правам доступа."""
        queryset = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()

        if hasattr(user, "profile"):
            profile = user.profile
            # Супер-администратор видит все сообщения
            if profile.is_superadmin():
                return queryset
            # Остальные видят только сообщения своей компании
            if profile.company:
                return queryset.filter(company=profile.company)

        return queryset.none()

    @action(detail=True, methods=["post"])
    def classify(self, request, pk=None):
        classify_message.delay(pk)
        return Response({"status": "queued"})


class TicketViewSet(viewsets.ModelViewSet):
    queryset = (
        Ticket.objects.prefetch_related("messages", "responses")
        .select_related("assigned_to", "company")
        .all()
    )
    serializer_class = TicketSerializer
    permission_classes = [IsCompanyMember, CompanyObjectPermission]

    def get_queryset(self):
        """Фильтрация тикетов по правам доступа."""
        queryset = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()

        if hasattr(user, "profile"):
            profile = user.profile
            # Супер-администратор видит все тикеты
            if profile.is_superadmin():
                return queryset
            # Остальные видят только тикеты своей компании
            if profile.company:
                return queryset.filter(company=profile.company)

        return queryset.none()

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
    queryset = Assignment.objects.select_related("ticket", "ticket__company").all()
    serializer_class = AssignmentSerializer
    permission_classes = [IsCompanyMember, CompanyObjectPermission]

    def get_queryset(self):
        """Фильтрация назначений по правам доступа."""
        queryset = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()

        if hasattr(user, "profile"):
            profile = user.profile
            # Супер-администратор видит все назначения
            if profile.is_superadmin():
                return queryset
            # Остальные видят только назначения тикетов своей компании
            if profile.company:
                return queryset.filter(ticket__company=profile.company)

        return queryset.none()


class AnalyticsMetricsView(APIView):
    permission_classes = [IsCompanyMember]

    def get(self, request):
        """Метрики с фильтрацией по компании и периоду."""
        user = request.user
        company = None
        if hasattr(user, "profile") and user.profile.company:
            company = user.profile.company
        period = request.query_params.get("period", "24h")
        if period not in ("24h", "7d", "30d"):
            period = "24h"
        return Response(aggregate_metrics(company=company, period=period))


class SearchView(APIView):
    permission_classes = [IsCompanyMember]

    def get(self, request):
        """Поиск с фильтрацией по компании."""
        query = request.query_params.get("q", "")
        if not query:
            return Response({"hits": []})
        user = request.user
        company = None
        if hasattr(user, "profile") and user.profile.company:
            company = user.profile.company
        result = search_tickets(query, company=company)
        return Response(result)


class TicketResponseViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TicketResponse.objects.select_related("ticket", "ticket__company", "author").all()
    serializer_class = TicketResponseSerializer
    permission_classes = [IsCompanyMember, CompanyObjectPermission]

    def get_queryset(self):
        """Фильтрация ответов по правам доступа."""
        queryset = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()

        if hasattr(user, "profile"):
            profile = user.profile
            # Супер-администратор видит все ответы
            if profile.is_superadmin():
                return queryset
            # Остальные видят только ответы тикетов своей компании
            if profile.company:
                return queryset.filter(ticket__company=profile.company)

        return queryset.none()

