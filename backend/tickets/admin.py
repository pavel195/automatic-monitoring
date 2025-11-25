from django.contrib import admin

from .models import Assignment, ChannelMessage, Ticket


@admin.register(ChannelMessage)
class ChannelMessageAdmin(admin.ModelAdmin):
    list_display = ("external_id", "channel", "received_at", "ticket")
    list_filter = ("channel",)
    search_fields = ("external_id", "payload")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "priority", "status", "created_at")
    list_filter = ("category", "priority", "status")
    search_fields = ("title", "messages__payload")


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("ticket", "assignee", "channel", "created_at")

