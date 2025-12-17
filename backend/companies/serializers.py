from rest_framework import serializers

from companies.models import Company, TelegramBot, UserProfile


class CompanySerializer(serializers.ModelSerializer):
    """Сериализатор для компании."""

    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "description",
            "status",
            "contact_email",
            "contact_phone",
            "default_ack_sla_minutes",
            "default_resolve_sla_minutes",
            "created_at",
            "updated_at",
            "approved_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at", "approved_at"]


class CompanyRegisterSerializer(serializers.ModelSerializer):
    """Сериализатор для регистрации новой компании."""

    admin_email = serializers.EmailField(write_only=True, required=True)
    admin_password = serializers.CharField(write_only=True, required=True, min_length=8)
    admin_first_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    admin_last_name = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Company
        fields = [
            "name",
            "description",
            "contact_email",
            "contact_phone",
            "admin_email",
            "admin_password",
            "admin_first_name",
            "admin_last_name",
        ]

    def validate_contact_email(self, value):
        """Валидация email компании."""
        if Company.objects.filter(contact_email=value).exists():
            raise serializers.ValidationError("Компания с таким email уже зарегистрирована.")
        return value

    def validate_admin_email(self, value):
        """Валидация email администратора."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if User.objects.filter(email=value).exists() or User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует.")
        return value

    def create(self, validated_data):
        """Создание компании и администратора."""
        from django.contrib.auth import get_user_model
        from django.db import transaction

        User = get_user_model()

        admin_email = validated_data.pop("admin_email")
        admin_password = validated_data.pop("admin_password")
        admin_first_name = validated_data.pop("admin_first_name", "")
        admin_last_name = validated_data.pop("admin_last_name", "")

        # Используем транзакцию для атомарности операции
        try:
            with transaction.atomic():
                # Создаем компанию
                company = Company.objects.create(**validated_data)

                # Создаем пользователя-администратора
                user = User.objects.create_user(
                    username=admin_email,
                    email=admin_email,
                    password=admin_password,
                    first_name=admin_first_name,
                    last_name=admin_last_name,
                )

                # Создаем профиль администратора компании
                UserProfile.objects.create(
                    user=user,
                    company=company,
                    role=UserProfile.Role.COMPANY_ADMIN,
                )

                return company
        except Exception as e:
            # Если что-то пошло не так, поднимаем ValidationError
            raise serializers.ValidationError({
                'admin_email': [f'Не удалось создать пользователя: {str(e)}']
            })


class TelegramBotSerializer(serializers.ModelSerializer):
    """Сериализатор для Telegram бота."""

    class Meta:
        model = TelegramBot
        fields = [
            "id",
            "company",
            "bot_token",
            "bot_username",
            "chat_ids",
            "discussion_chat_ids",
            "allow_direct",
            "status",
            "last_error",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "company",  # Компания устанавливается автоматически из профиля пользователя
            "bot_username",
            "status",
            "last_error",
            "created_at",
            "updated_at",
        ]

    def validate_bot_token(self, value):
        """Валидация токена бота через Telegram API."""
        import requests
        import logging

        logger = logging.getLogger(__name__)
        
        if not value or not value.strip():
            raise serializers.ValidationError("Токен бота не может быть пустым.")

        try:
            logger.info(f"Проверка токена бота через Telegram API...")
            response = requests.get(
                f"https://api.telegram.org/bot{value.strip()}/getMe", timeout=10
            )
            logger.info(f"Ответ от Telegram API: status={response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Данные от Telegram API: {data}")
                if data.get("ok"):
                    # Сохраняем username бота в контексте
                    if not hasattr(self, '_bot_username'):
                        self._bot_username = data["result"].get("username", "")
                    logger.info(f"Токен валиден, username бота: {self._bot_username}")
                    return value.strip()
                else:
                    error_desc = data.get("description", "Неизвестная ошибка")
                    logger.error(f"Telegram API вернул ошибку: {error_desc}")
                    raise serializers.ValidationError(f"Неверный токен бота: {error_desc}")
            else:
                logger.error(f"Telegram API вернул статус {response.status_code}")
                raise serializers.ValidationError(f"Не удалось проверить токен бота. Статус: {response.status_code}")
        except requests.Timeout:
            logger.error("Таймаут при проверке токена бота")
            raise serializers.ValidationError("Таймаут при проверке токена бота. Проверьте подключение к интернету.")
        except requests.RequestException as e:
            logger.error(f"Ошибка при проверке токена бота: {str(e)}")
            raise serializers.ValidationError(f"Не удалось проверить токен бота: {str(e)}")

    def create(self, validated_data):
        """Создание бота с валидацией."""
        # Получаем username из валидации токена
        bot_username = getattr(self, "_bot_username", "")
        # Если username не был получен, пытаемся получить его снова
        if not bot_username:
            import requests
            try:
                response = requests.get(
                    f"https://api.telegram.org/bot{validated_data['bot_token']}/getMe",
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("ok"):
                        bot_username = data["result"].get("username", "")
            except Exception:
                pass
        
        bot = TelegramBot.objects.create(
            **validated_data,
            bot_username=bot_username,
            status=TelegramBot.Status.ACTIVE,
        )
        return bot


class UserProfileSerializer(serializers.ModelSerializer):
    """Сериализатор для профиля пользователя."""

    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "user",
            "username",
            "email",
            "first_name",
            "last_name",
            "company",
            "company_name",
            "role",
            "phone",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

