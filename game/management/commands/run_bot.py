"""
Management command to start the MassQuest Telegram bot.

Usage:
    python manage.py run_bot
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Start the MassQuest Telegram bot (long-polling)."

    def handle(self, *args, **options):
        from game.bot import build_application

        self.stdout.write("Starting MassQuest bot... (Ctrl+C to stop)")
        app = build_application()
        app.run_polling(drop_pending_updates=True)
