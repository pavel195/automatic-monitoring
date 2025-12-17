"""Система разрешений для работы с компаниями и тикетами."""

from rest_framework import permissions


class IsCompanyMember(permissions.BasePermission):
    """Разрешение для членов компании (операторы и администраторы)."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if hasattr(request.user, "profile"):
            return request.user.profile.role in [
                "operator",
                "company_admin",
                "superadmin",
            ]
        return False

    def has_object_permission(self, request, view, obj):
        """Проверка доступа к конкретному объекту."""
        if not request.user.is_authenticated:
            return False

        # Супер-администратор имеет доступ ко всему
        if hasattr(request.user, "profile") and request.user.profile.is_superadmin():
            return True

        # Для тикетов проверяем принадлежность к компании
        if hasattr(obj, "company"):
            company = obj.company
            if company is None:
                return False
            if hasattr(request.user, "profile"):
                profile = request.user.profile
                # Администратор компании имеет доступ ко всем тикетам своей компании
                if profile.is_company_admin() and profile.company == company:
                    return True
                # Оператор имеет доступ к тикетам своей компании
                if profile.role == "operator" and profile.company == company:
                    return True
            return False

        # Для компаний проверяем права управления
        if hasattr(obj, "users"):
            # Это компания
            if hasattr(request.user, "profile"):
                profile = request.user.profile
                return profile.can_manage_company(obj)
            return False

        return False


class IsCompanyAdmin(permissions.BasePermission):
    """Разрешение только для администраторов компании и супер-администраторов."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if hasattr(request.user, "profile"):
            return request.user.profile.role in ["company_admin", "superadmin"]
        return False


class IsSuperAdmin(permissions.BasePermission):
    """Разрешение только для супер-администраторов."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if hasattr(request.user, "profile"):
            return request.user.profile.is_superadmin()
        return False


class CompanyObjectPermission(permissions.BasePermission):
    """Разрешение для работы с объектами компании."""

    def has_object_permission(self, request, view, obj):
        """Проверка доступа к объекту на основе компании."""
        if not request.user.is_authenticated:
            return False

        # Супер-администратор имеет доступ ко всему
        if hasattr(request.user, "profile") and request.user.profile.is_superadmin():
            return True

        # Получаем компанию из объекта
        company = None
        if hasattr(obj, "company"):
            company = obj.company
        elif hasattr(obj, "ticket") and hasattr(obj.ticket, "company"):
            company = obj.ticket.company

        if company is None:
            return False

        # Проверяем принадлежность пользователя к компании
        if hasattr(request.user, "profile"):
            profile = request.user.profile
            if profile.company == company:
                return True
            # Администратор компании может управлять всеми объектами своей компании
            if profile.is_company_admin() and profile.company == company:
                return True

        return False

