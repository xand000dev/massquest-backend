"""
Management command to seed a test user with a CharacterProfile.

Usage:
    python manage.py seed_test_user
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from game.models import CharacterProfile


class Command(BaseCommand):
    help = "Creates test user 'xand' with a CharacterProfile."

    def handle(self, *args, **options):
        user, user_created = User.objects.get_or_create(username="xand")
        if user_created:
            user.set_password("test123")
            user.save()

        profile, profile_created = CharacterProfile.objects.get_or_create(
            user=user,
            defaults={"target_weight": 80, "current_weight": 70},
        )

        user_status = "Created" if user_created else "Already exists"
        profile_status = "Created" if profile_created else "Already exists"

        self.stdout.write(f"User '{user.username}':       {user_status}")
        self.stdout.write(f"CharacterProfile:         {profile_status}")
        self.stdout.write(
            f"  target_weight={profile.target_weight} kg  "
            f"current_weight={profile.current_weight} kg  "
            f"level={profile.level}  hp={profile.hp}/{profile.max_hp}"
        )
        self.stdout.write(self.style.SUCCESS("Done."))
