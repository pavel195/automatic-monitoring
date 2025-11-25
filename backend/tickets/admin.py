from django.contrib import admin

from .models import Assignment, ChannelMessage, Ticket, TicketResponse


@admin.register(ChannelMessage)
class ChannelMessageAdmin(admin.ModelAdmin):
    list_display = (
        "external_id",
        "channel",
        "transport_mode",
        "is_transport",
        "sentiment",
        "received_at",
        "ticket",
    )
    list_filter = ("channel", "transport_mode", "is_transport", "sentiment")
    search_fields = ("external_id", "payload")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "transport_mode",
        "category",
        "priority",
        "status",
        "sentiment",
        "is_transport",
        "created_at",
    )
    list_filter = (
        "transport_mode",
        "category",
        "priority",
        "status",
        "sentiment",
        "is_transport",
    )
    search_fields = ("title", "messages__payload")


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("ticket", "assignee", "channel", "created_at")


@admin.register(TicketResponse)
class TicketResponseAdmin(admin.ModelAdmin):
    list_display = ("ticket", "channel", "status", "created_at")
    list_filter = ("channel", "status")
    search_fields = ("ticket__title", "body")

