"""
MassQuest Telegram bot.

Each Telegram user is mapped to a Django User with username ``tg_<telegram_id>``.
CharacterProfile is created on /start with default target_weight=80.

Commands
--------
/start          Register and show welcome stats.
/eat <cal>      Log calories and earn XP.
/weight <kg>    Log weight and check level-up.
/status         Show full character card.
/help           List all commands.
"""

import logging

from decouple import config
from django.contrib.auth.models import User
from django.utils import timezone
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from game.game_engine import GameEngine
from game.models import CharacterProfile, DailyLog

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = config("TELEGRAM_BOT_TOKEN")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_or_create_profile(telegram_user) -> tuple[CharacterProfile, bool]:
    """Return (profile, created) for a Telegram user, creating both User and profile if needed."""
    username = f"tg_{telegram_user.id}"
    display = telegram_user.first_name or username

    user, _ = User.objects.get_or_create(
        username=username,
        defaults={"first_name": display},
    )
    profile, created = CharacterProfile.objects.get_or_create(
        user=user,
        defaults={"target_weight": 80},
    )
    return profile, created


def _character_card(profile: CharacterProfile) -> str:
    """Render the RPG status card."""
    rank = GameEngine.get_rank(profile.level)
    name = profile.user.first_name or profile.user.username
    weight_line = (
        f"⚖️ Weight: {profile.current_weight} kg → {profile.target_weight} kg target"
        if profile.current_weight
        else f"⚖️ Target: {profile.target_weight} kg (no weight logged yet)"
    )
    return (
        f"🧬 {name} | Lv.{profile.level} {rank}\n"
        f"⚔️ XP: {profile.xp}\n"
        f"❤️ HP: {profile.hp}/{profile.max_hp}\n"
        f"{weight_line}"
    )


def _get_today_log(profile: CharacterProfile) -> DailyLog:
    log, _ = DailyLog.objects.get_or_create(user=profile.user, date=timezone.localdate())
    return log


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start — register user and show welcome message."""
    profile, created = _get_or_create_profile(update.effective_user)

    if created:
        greeting = "⚔️ Welcome to MassQuest, warrior. Your quest for mass begins NOW.\n\n"
    else:
        greeting = "⚔️ Welcome back. The grind continues.\n\n"

    await update.message.reply_text(greeting + _character_card(profile))


async def cmd_eat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/eat <calories> — log calories and award XP."""
    if not context.args:
        await update.message.reply_text("Usage: /eat <calories>\nExample: /eat 600")
        return

    try:
        calories = int(context.args[0])
        if calories <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Calories must be a positive integer.")
        return

    profile, _ = _get_or_create_profile(update.effective_user)
    log = _get_today_log(profile)
    log.calories_eaten += calories
    log.save(update_fields=["calories_eaten"])

    xp_gained = GameEngine.calories_to_xp(calories)
    profile.xp += xp_gained
    profile.save(update_fields=["xp"])

    await update.message.reply_text(
        f"🍗 +{calories} kcal logged\n"
        f"⚔️ +{xp_gained} XP | Total: {profile.xp} XP\n"
        f"❤️ HP: {profile.hp}/{profile.max_hp}\n"
        f"📅 Today: {log.calories_eaten} kcal"
    )


async def cmd_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/weight <kg> — log weight and check for a level-up."""
    if not context.args:
        await update.message.reply_text("Usage: /weight <kg>\nExample: /weight 72.5")
        return

    try:
        weight = float(context.args[0])
        if weight <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Weight must be a positive number.")
        return

    profile, _ = _get_or_create_profile(update.effective_user)
    log = _get_today_log(profile)
    log.weight_logged = weight
    log.save(update_fields=["weight_logged"])

    profile.current_weight = weight
    profile.save(update_fields=["current_weight"])

    leveled_up = GameEngine.check_level_up(profile)

    if leveled_up:
        rank = GameEngine.get_rank(profile.level)
        reply = (
            f"⚖️ Weight logged: {weight} kg\n"
            f"🎉 LEVEL UP! → Lv.{profile.level} {rank}\n"
            f"⚔️ XP: {profile.xp} | ❤️ HP: {profile.hp}/{profile.max_hp}"
        )
    else:
        reply = (
            f"⚖️ Weight logged: {weight} kg\n"
            f"📈 Need +1 kg from last entry to level up.\n"
            f"⚔️ XP: {profile.xp} | ❤️ HP: {profile.hp}/{profile.max_hp}"
        )

    await update.message.reply_text(reply)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/status — show full character card."""
    profile, _ = _get_or_create_profile(update.effective_user)
    await update.message.reply_text(_character_card(profile))


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/help — list all available commands."""
    await update.message.reply_text(
        "⚔️ MassQuest Commands\n\n"
        "/start — Register & view your character\n"
        "/eat <cal> — Log calories → earn XP\n"
        "/weight <kg> — Log weight → trigger level-up\n"
        "/status — View your character card\n"
        "/help — Show this message\n\n"
        "Miss a day → −20 HP. Hit 0 HP → lose a level. Stay consistent."
    )


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------


def build_application() -> Application:
    """Build and return the configured Telegram Application."""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("eat", cmd_eat))
    app.add_handler(CommandHandler("weight", cmd_weight))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("help", cmd_help))
    return app
