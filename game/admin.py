"""
Django admin configuration for MassQuest — founder dashboard.
"""

from django.contrib import admin
from django.utils.html import format_html

from game.game_engine import GameEngine
from game.models import CharacterProfile, DailyLog, FoodEntry

admin.site.site_header = "MassQuest Admin"
admin.site.site_title = "MassQuest"
admin.site.index_title = "Founder Dashboard"


@admin.register(CharacterProfile)
class CharacterProfileAdmin(admin.ModelAdmin):
    list_display = (
        "username",
        "level",
        "rank",
        "xp",
        "hp_display",
        "current_weight",
        "target_weight",
        "kcal_to_goal",
    )
    list_filter = ("level",)
    search_fields = ("user__username", "user__first_name")
    readonly_fields = ("rank", "kcal_to_goal")
    ordering = ("-level", "-xp")

    @admin.display(description="Username")
    def username(self, obj):
        return obj.user.username

    @admin.display(description="Rank")
    def rank(self, obj):
        rank = GameEngine.get_rank(obj.level)
        colours = {
            "Novice": "#888888",
            "Warrior": "#2e86de",
            "Titan": "#8e44ad",
            "God": "#f39c12",
        }
        colour = colours.get(rank, "#000")
        return format_html('<b style="color:{}">{}</b>', colour, rank)

    @admin.display(description="HP")
    def hp_display(self, obj):
        pct = (obj.hp / obj.max_hp) * 100 if obj.max_hp else 0
        colour = "#27ae60" if pct > 60 else "#e67e22" if pct > 30 else "#e74c3c"
        return format_html(
            '{}/{} <span style="color:{};font-weight:bold">({}%)</span>',
            obj.hp,
            obj.max_hp,
            colour,
            int(pct),
        )

    @admin.display(description="kcal to Goal")
    def kcal_to_goal(self, obj):
        if obj.current_weight is None or obj.target_weight is None:
            return "—"
        delta_kg = float(obj.target_weight) - float(obj.current_weight)
        if delta_kg <= 0:
            return format_html('<b style="color:#27ae60">Goal reached! 🏆</b>')
        kcal = int(delta_kg * 7700)
        return f"{kcal:,} kcal ({delta_kg:+.1f} kg)"


@admin.register(DailyLog)
class DailyLogAdmin(admin.ModelAdmin):
    list_display = ("username", "date", "calories_eaten", "weight_logged")
    list_filter = ("date",)
    search_fields = ("user__username",)
    ordering = ("-date",)
    date_hierarchy = "date"

    @admin.display(description="Username")
    def username(self, obj):
        return obj.user.username


@admin.register(FoodEntry)
class FoodEntryAdmin(admin.ModelAdmin):
    list_display = ("username", "name", "calories", "created_at")
    search_fields = ("user__username", "name")
    ordering = ("-created_at",)

    @admin.display(description="Username")
    def username(self, obj):
        return obj.user.username
