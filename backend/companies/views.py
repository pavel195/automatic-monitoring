from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from companies.models import Company, TelegramBot, UserProfile, VkBot
from companies.permissions import (
    CompanyObjectPermission,
    IsCompanyAdmin,
    IsCompanyMember,
    IsSuperAdmin,
)
from companies.serializers import (
    CompanyRegisterSerializer,
    CompanySerializer,
    TelegramBotSerializer,
    UserProfileSerializer,
    VkBotSerializer,
)


class CompanyViewSet(viewsets.ModelViewSet):
    """ViewSet для управления компаниями."""

    serializer_class = CompanySerializer
    permission_classes = [IsCompanyMember]

    def get_queryset(self):
        """Фильтрация компаний по правам доступа."""
        user = self.request.user
        if not user.is_authenticated:
            return Company.objects.none()

        if hasattr(user, "profile"):
            profile = user.profile
            # Супер-администратор видит все компании
            if profile.is_superadmin():
                return Company.objects.all()
            # Администратор компании видит только свою компанию
            if profile.is_company_admin() and profile.company:
                return Company.objects.filter(id=profile.company.id)
            # Оператор видит только свою компанию
            if profile.role == "operator" and profile.company:
                return Company.objects.filter(id=profile.company.id)

        return Company.objects.none()

    def get_permissions(self):
        """Разные разрешения для разных действий."""
        if self.action == "register":
            return [AllowAny()]
        if self.action in ["approve", "reject"]:
            return [IsSuperAdmin()]
        if self.action in ["update", "partial_update", "destroy"]:
            return [IsCompanyAdmin()]
        return super().get_permissions()

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def register(self, request):
        """Регистрация новой компании."""
        serializer = CompanyRegisterSerializer(data=request.data)
        if serializer.is_valid():
            company = serializer.save()
            return Response(
                CompanySerializer(company).data, status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], permission_classes=[IsSuperAdmin])
    def approve(self, request, pk=None):
        """Одобрение компании супер-администратором."""
        company = self.get_object()
        company.approve(request.user)
        return Response(CompanySerializer(company).data)

    @action(detail=True, methods=["post"], permission_classes=[IsSuperAdmin])
    def reject(self, request, pk=None):
        """Отклонение компании."""
        company = self.get_object()
        company.status = Company.Status.INACTIVE
        company.save(update_fields=["status"])
        return Response(CompanySerializer(company).data)

    @action(detail=True, methods=["get"], permission_classes=[IsCompanyMember])
    def bots(self, request, pk=None):
        """Получить список ботов компании."""
        company = self.get_object()
        bots = company.bots.all()
        serializer = TelegramBotSerializer(bots, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], permission_classes=[IsCompanyMember])
    def users(self, request, pk=None):
        """Получить список пользователей компании."""
        company = self.get_object()
        users = company.users.all()
        serializer = UserProfileSerializer(users, many=True)
        return Response(serializer.data)


class TelegramBotViewSet(viewsets.ModelViewSet):
    """ViewSet для управления Telegram ботами."""

    serializer_class = TelegramBotSerializer
    permission_classes = [IsCompanyAdmin, CompanyObjectPermission]

    def get_queryset(self):
        """Фильтрация ботов по правам доступа."""
        user = self.request.user
        if not user.is_authenticated:
            return TelegramBot.objects.none()

        if hasattr(user, "profile"):
            profile = user.profile
            # Супер-администратор видит все боты
            if profile.is_superadmin():
                return TelegramBot.objects.all()
            # Остальные видят только боты своей компании
            if profile.company:
                return TelegramBot.objects.filter(company=profile.company)

        return TelegramBot.objects.none()

    def create(self, request, *args, **kwargs):
        """Создание бота с логированием ошибок."""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("Создание Telegram бота: поля=%s", sorted(request.data.keys()))
        logger.info(f"Пользователь: {request.user}, компания: {getattr(request.user.profile, 'company', None) if hasattr(request.user, 'profile') else None}")
        
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Ошибки валидации: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            logger.error(f"Ошибка при создании бота: {str(e)}", exc_info=True)
            return Response(
                {"error": f"Ошибка при создании бота: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_create(self, serializer):
        """Создание бота с привязкой к компании пользователя."""
        user = self.request.user
        if hasattr(user, "profile") and user.profile.company:
            serializer.save(company=user.profile.company)
        else:
            # Если нет компании у пользователя, возвращаем ошибку
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"company": "У пользователя нет привязанной компании. Обратитесь к администратору."})


class VkBotViewSet(viewsets.ModelViewSet):
    """ViewSet для управления VK ботами сообществ."""

    serializer_class = VkBotSerializer
    permission_classes = [IsCompanyAdmin, CompanyObjectPermission]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return VkBot.objects.none()
        if hasattr(user, "profile"):
            profile = user.profile
            if profile.is_superadmin():
                return VkBot.objects.all()
            if profile.company:
                return VkBot.objects.filter(company=profile.company)
        return VkBot.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if hasattr(user, "profile") and user.profile.company:
            serializer.save(company=user.profile.company)
        else:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"company": "У пользователя нет привязанной компании."})


class UserProfileViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для просмотра профилей пользователей."""

    serializer_class = UserProfileSerializer
    permission_classes = [IsCompanyMember]

    def get_queryset(self):
        """Фильтрация профилей по правам доступа."""
        user = self.request.user
        if not user.is_authenticated:
            return UserProfile.objects.none()

        if hasattr(user, "profile"):
            profile = user.profile
            # Супер-администратор видит все профили
            if profile.is_superadmin():
                return UserProfile.objects.all()
            # Администратор компании видит всех пользователей своей компании
            if profile.is_company_admin() and profile.company:
                return UserProfile.objects.filter(company=profile.company)
            # Оператор видит только свой профиль
            if profile.role == "operator":
                return UserProfile.objects.filter(user=user)

        return UserProfile.objects.none()
