from django.contrib import admin

from .models import Company, TelegramBot, UserProfile


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "contact_email", "created_at", "approved_at")
    list_filter = ("status", "created_at")
    search_fields = ("name", "contact_email")
    readonly_fields = ("created_at", "updated_at", "approved_at")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "role", "phone", "created_at")
    list_filter = ("role", "company")
    search_fields = ("user__username", "user__email", "phone")


@admin.register(TelegramBot)
class TelegramBotAdmin(admin.ModelAdmin):
    list_display = ("company", "bot_username", "status", "created_at")
    list_filter = ("status", "company")
    search_fields = ("bot_username", "company__name")

