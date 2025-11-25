from rest_framework import serializers

from tickets.models import Assignment, ChannelMessage, Ticket


class ChannelMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChannelMessage
        fields = "__all__"
        read_only_fields = ("ticket", "created_at")


class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = "__all__"


class TicketSerializer(serializers.ModelSerializer):
    messages = ChannelMessageSerializer(many=True, read_only=True)
    assignments = AssignmentSerializer(many=True, read_only=True)

    class Meta:
        model = Ticket
        fields = "__all__"

