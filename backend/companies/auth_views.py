"""Views для аутентификации и регистрации."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

User = get_user_model()


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    """Вход пользователя и получение токена."""
    username = request.data.get("username")
    password = request.data.get("password")

    if not username or not password:
        return Response(
            {"error": "Необходимо указать username и password"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user = User.objects.get(username=username)
        if not user.check_password(password):
            return Response(
                {"error": "Неверный пароль"}, status=status.HTTP_401_UNAUTHORIZED
            )
    except User.DoesNotExist:
        return Response(
            {"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND
        )

    # Создаем или получаем токен
    token, created = Token.objects.get_or_create(user=user)

    # Получаем профиль пользователя
    profile_data = None
    if hasattr(user, "profile"):
        from companies.serializers import UserProfileSerializer

        profile_data = UserProfileSerializer(user.profile).data

    return Response(
        {
            "token": token.key,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
            "profile": profile_data,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    """Выход пользователя (удаление токена)."""
    try:
        request.user.auth_token.delete()
    except Exception:
        pass
    return Response({"message": "Выход выполнен успешно"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    """Получение информации о текущем пользователе."""
    user = request.user
    profile_data = None
    if hasattr(user, "profile"):
        from companies.serializers import UserProfileSerializer

        profile_data = UserProfileSerializer(user.profile).data

    return Response(
        {
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
            "profile": profile_data,
        }
    )

