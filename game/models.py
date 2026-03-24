"""
Models for the MassQuest game app.

CharacterProfile tracks the RPG stats tied to each user.
DailyLog records daily calorie intake and weight.
FoodEntry stores individual food items logged by the user.
"""

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class CharacterProfile(models.Model):
    """RPG character stats linked one-to-one with a Django User."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="character")
    level = models.PositiveIntegerField(default=1)
    xp = models.PositiveIntegerField(default=0)
    hp = models.PositiveIntegerField(default=100)
    max_hp = models.PositiveIntegerField(default=100)
    target_weight = models.DecimalField(max_digits=5, decimal_places=2, help_text="Target weight in kg")
    current_weight = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True, help_text="Current weight in kg"
    )

    def __str__(self) -> str:
        return f"{self.user.username} — Lv.{self.level}"


class DailyLog(models.Model):
    """Tracks a user's calories eaten and weight for a given day."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="daily_logs")
    date = models.DateField(default=timezone.localdate)
    calories_eaten = models.PositiveIntegerField(default=0)
    weight_logged = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True, help_text="Weight recorded in kg"
    )

    class Meta:
        unique_together = ("user", "date")
        ordering = ["-date"]

    def __str__(self) -> str:
        return f"{self.user.username} — {self.date} ({self.calories_eaten} kcal)"


class Quest(models.Model):
    """A daily quest assigned to a user."""

    TYPES = (
        ("calorie_goal", "Hit Calorie Goal"),
        ("log_weight",   "Log Your Weight"),
        ("big_meal",     "Eat a Big Meal"),
        ("early_meal",   "Log Before Noon"),
    )

    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quests")
    date        = models.DateField(default=timezone.localdate)
    quest_type  = models.CharField(max_length=32, choices=TYPES)
    description = models.CharField(max_length=255)
    target_value  = models.PositiveIntegerField(default=1)
    current_value = models.PositiveIntegerField(default=0)
    xp_reward   = models.PositiveIntegerField(default=50)
    completed   = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "date", "quest_type")
        ordering = ["-date", "completed"]

    def __str__(self) -> str:
        status = "✓" if self.completed else "○"
        return f"{status} {self.user.username} — {self.description} ({self.date})"


class FoodEntry(models.Model):
    """A single food item logged by a user."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="food_entries")
    name = models.CharField(max_length=255)
    calories = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user.username} — {self.name} ({self.calories} kcal)"
