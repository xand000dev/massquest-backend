"""
DRF serializers for the MassQuest game app.
"""

from rest_framework import serializers

from game.models import CharacterProfile, DailyLog, Quest


class DailyLogSerializer(serializers.ModelSerializer):
    """Serializes a DailyLog record for read/write operations."""

    class Meta:
        model = DailyLog
        fields = ["id", "date", "calories_eaten", "weight_logged"]
        read_only_fields = ["id", "date"]


class QuestSerializer(serializers.ModelSerializer):
    """Serializes a Quest for mobile consumption."""

    class Meta:
        model = Quest
        fields = [
            "id", "quest_type", "description",
            "target_value", "current_value", "xp_reward", "completed",
        ]
        read_only_fields = fields


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
