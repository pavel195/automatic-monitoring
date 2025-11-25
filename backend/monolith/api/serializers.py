from rest_framework import serializers

from tickets.models import Assignment, ChannelMessage, Ticket, TicketResponse


class ChannelMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChannelMessage
        fields = "__all__"
        read_only_fields = ("ticket", "created_at")


class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = "__all__"


class TicketResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketResponse
        fields = "__all__"
        read_only_fields = ("status", "external_message_id", "sent_at")


class TicketSerializer(serializers.ModelSerializer):
    messages = ChannelMessageSerializer(many=True, read_only=True)
    assignments = AssignmentSerializer(many=True, read_only=True)
    responses = TicketResponseSerializer(many=True, read_only=True)

    class Meta:
        model = Ticket
        fields = "__all__"

