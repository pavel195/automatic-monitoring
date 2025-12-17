from django.urls import include, path
from rest_framework.routers import DefaultRouter

from companies.auth_views import login, logout, me
from companies.views import CompanyViewSet, TelegramBotViewSet, UserProfileViewSet

router = DefaultRouter()
router.register("companies", CompanyViewSet, basename="company")
router.register("bots", TelegramBotViewSet, basename="telegrambot")
router.register("users", UserProfileViewSet, basename="userprofile")

urlpatterns = [
    path("", include(router.urls)),
    path("auth/login/", login, name="login"),
    path("auth/logout/", logout, name="logout"),
    path("auth/me/", me, name="me"),
]

