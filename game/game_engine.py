"""
MassQuest game engine.

Encapsulates all RPG logic: XP calculation, level-ups, HP penalties, and
rank resolution. Designed to be called from views after database writes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    from game.models import CharacterProfile


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RANKS: list[tuple[int, int, str]] = [
    (0, 5, "Novice"),
    (6, 10, "Warrior"),
    (11, 20, "Titan"),
    (21, 9999, "God"),
]

HP_PENALTY = 20


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class GameEngine:
    """Stateless service class containing all game rule logic."""

    # ------------------------------------------------------------------
    # XP
    # ------------------------------------------------------------------

    @staticmethod
    def calories_to_xp(calories: int) -> int:
        """Convert a calorie amount to XP points (calories / 10, floored)."""
        return int(calories) // 10

    # ------------------------------------------------------------------
    # Level
    # ------------------------------------------------------------------

    @staticmethod
    def check_level_up(profile: CharacterProfile) -> bool:
        """
        Level the character up if their weight has increased by ≥ 1 kg
        compared to the previous daily log that recorded a weight.

        Returns True if a level-up occurred, False otherwise.
        """
        from game.models import DailyLog  # local import to avoid circular

        previous_log = (
            DailyLog.objects.filter(user=profile.user, weight_logged__isnull=False)
            .exclude(date=timezone.localdate())
            .order_by("-date")
            .first()
        )

        if previous_log is None or previous_log.weight_logged is None:
            return False

        if profile.current_weight is None:
            return False

        gained = float(profile.current_weight) - float(previous_log.weight_logged)
        if gained >= 1.0:
            profile.level += 1
            profile.save(update_fields=["level"])
            return True

        return False

    # ------------------------------------------------------------------
    # HP
    # ------------------------------------------------------------------

    @staticmethod
    def apply_hp_penalty(profile: CharacterProfile) -> dict:
        """
        Deduct HP_PENALTY HP for missing today's log.
        If HP reaches 0, the character loses a level (minimum level 1).

        Returns a dict with keys:
            - hp_before (int)
            - hp_after  (int)
            - leveled_down (bool)
        """
        result = {"hp_before": profile.hp, "hp_after": profile.hp, "leveled_down": False}

        profile.hp = max(0, profile.hp - HP_PENALTY)
        result["hp_after"] = profile.hp

        if profile.hp == 0:
            profile.level = max(1, profile.level - 1)
            profile.hp = profile.max_hp  # restore HP after level-down
            result["hp_after"] = profile.hp
            result["leveled_down"] = True

        profile.save(update_fields=["hp", "level"])
        return result

    # ------------------------------------------------------------------
    # Status / Rank
    # ------------------------------------------------------------------

    @staticmethod
    def get_rank(level: int) -> str:
        """Return the rank name for a given level."""
        for low, high, rank in RANKS:
            if low <= level <= high:
                return rank
        return "God"

    @classmethod
    def get_status(cls, profile: CharacterProfile) -> dict:
        """
        Return a summary dict for the character's current state.

        Keys: level, xp, hp, max_hp, rank
        """
        return {
            "level": profile.level,
            "xp": profile.xp,
            "hp": profile.hp,
            "max_hp": profile.max_hp,
            "rank": cls.get_rank(profile.level),
        }
