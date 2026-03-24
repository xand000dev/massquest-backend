"""
DRF serializers for the MassQuest game app.
"""

from rest_framework import serializers

from game.models import CharacterProfile, DailyLog


class DailyLogSerializer(serializers.ModelSerializer):
    """Serializes a DailyLog record for read/write operations."""

    class Meta:
        model = DailyLog
        fields = ["id", "date", "calories_eaten", "weight_logged"]
        read_only_fields = ["id", "date"]


class CharacterProfileSerializer(serializers.ModelSerializer):
    """Serializes CharacterProfile fields for status responses."""

    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = CharacterProfile
        fields = [
            "username",
            "level",
            "xp",
            "hp",
            "max_hp",
            "target_weight",
            "current_weight",
        ]
        read_only_fields = ["level", "xp", "hp", "max_hp"]
