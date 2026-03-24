"""
Celery tasks for MassQuest.

Scheduled tasks
---------------
midnight_penalty — runs daily at 23:59 UTC.
    Applies an HP penalty to every CharacterProfile whose user has not
    created a DailyLog entry for today. Logs a warning when HP falls
    below 40 after the penalty.
"""

import logging

from celery import shared_task
from django.contrib.auth.models import User
from django.utils import timezone

from game.game_engine import GameEngine
from game.models import CharacterProfile, DailyLog

logger = logging.getLogger(__name__)

HP_WARNING_THRESHOLD = 40


@shared_task(name="game.tasks.midnight_penalty")
def midnight_penalty() -> dict:
    """
    Apply HP penalty to users who skipped logging today.

    Returns a summary dict with the number of users penalised, levelled
    down, and warned.
    """
    today = timezone.localdate()

    logged_user_ids = DailyLog.objects.filter(date=today).values_list("user_id", flat=True)

    profiles = CharacterProfile.objects.filter(
        user__is_active=True,
    ).exclude(
        user_id__in=logged_user_ids,
    ).select_related("user")

    stats = {"penalised": 0, "levelled_down": 0, "hp_warnings": 0}

    for profile in profiles:
        result = GameEngine.apply_hp_penalty(profile)
        stats["penalised"] += 1

        username = profile.user.username

        if profile.streak > 0:
            profile.streak = 0
            profile.save(update_fields=["streak"])
            logger.info("midnight_penalty: %s streak reset to 0.", username)

        if result["levelled_down"]:
            stats["levelled_down"] += 1
            logger.warning(
                "midnight_penalty: %s lost a level (now Lv.%d) — HP hit 0.",
                username,
                profile.level,
            )

        if result["hp_after"] < HP_WARNING_THRESHOLD:
            stats["hp_warnings"] += 1
            logger.warning(
                "midnight_penalty: %s HP critically low — %d/%d HP remaining.",
                username,
                result["hp_after"],
                profile.max_hp,
            )

        logger.info(
            "midnight_penalty: %s penalised. HP %d → %d.",
            username,
            result["hp_before"],
            result["hp_after"],
        )

    logger.info("midnight_penalty complete: %s", stats)
    return stats
