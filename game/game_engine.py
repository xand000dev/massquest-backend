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

    # ------------------------------------------------------------------
    # Daily quests
    # ------------------------------------------------------------------

    @staticmethod
    def get_or_create_daily_quests(user) -> list:
        """
        Return today's quests for user, creating them if they don't exist.

        Quest 1 — always: hit 2,000 kcal
        Quest 2 — rotates by weekday:
          Mon/Thu/Sun → log weight
          Tue/Fri     → eat a single big meal (≥800 kcal)
          Wed/Sat     → log first meal before noon
        """
        from game.models import Quest

        today = timezone.localdate()

        quest1, _ = Quest.objects.get_or_create(
            user=user, date=today, quest_type="calorie_goal",
            defaults={
                "description": "Eat at least 2,000 kcal today",
                "target_value": 2000,
                "xp_reward": 50,
            },
        )

        dow = today.weekday()  # 0=Mon … 6=Sun
        if dow in (0, 3, 6):
            q2_type = "log_weight"
            q2 = {"description": "Log your weight today", "target_value": 1, "xp_reward": 30}
        elif dow in (1, 4):
            q2_type = "big_meal"
            q2 = {"description": "Log a single meal over 800 kcal", "target_value": 800, "xp_reward": 40}
        else:
            q2_type = "early_meal"
            q2 = {"description": "Log your first meal before noon", "target_value": 1, "xp_reward": 35}

        quest2, _ = Quest.objects.get_or_create(
            user=user, date=today, quest_type=q2_type, defaults=q2,
        )
        return [quest1, quest2]

    @staticmethod
    def update_quests_for_calories(user, calories_this_session: int, log) -> list[str]:
        """
        Called after logging calories. Updates calorie_goal and big_meal quests.
        Returns list of newly-completed quest descriptions.
        """
        from game.models import Quest

        today = timezone.localdate()
        newly_done: list[str] = []

        # calorie_goal — use total log calories
        try:
            cq = Quest.objects.get(user=user, date=today, quest_type="calorie_goal")
            if not cq.completed:
                cq.current_value = log.calories_eaten
                if cq.current_value >= cq.target_value:
                    cq.completed = True
                    newly_done.append(cq.description)
                cq.save(update_fields=["current_value", "completed"])
        except Quest.DoesNotExist:
            pass

        # big_meal — any single session ≥ 800 kcal
        if calories_this_session >= 800:
            try:
                bq = Quest.objects.get(user=user, date=today, quest_type="big_meal")
                if not bq.completed:
                    bq.current_value = calories_this_session
                    bq.completed = True
                    bq.save(update_fields=["current_value", "completed"])
                    newly_done.append(bq.description)
            except Quest.DoesNotExist:
                pass

        return newly_done

    @staticmethod
    def update_quests_for_weight(user) -> list[str]:
        """Called after logging weight. Marks log_weight quest complete."""
        from game.models import Quest

        today = timezone.localdate()
        newly_done: list[str] = []
        try:
            wq = Quest.objects.get(user=user, date=today, quest_type="log_weight")
            if not wq.completed:
                wq.current_value = 1
                wq.completed = True
                wq.save(update_fields=["current_value", "completed"])
                newly_done.append(wq.description)
        except Quest.DoesNotExist:
            pass
        return newly_done

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
