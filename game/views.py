"""
API views for the MassQuest game app.

Endpoints
---------
POST /register/      — create user + CharacterProfile (no auth required)
POST /set-target/    — set target_weight on CharacterProfile
POST /log-calories/  — add calories to today's DailyLog and award XP
POST /log-weight/    — record today's weight and check for a level-up
GET  /status/        — return the character's current RPG stats
GET  /quests/        — return today's daily quests (created on first call)
"""

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from game.game_engine import GameEngine
from game.models import CharacterProfile, DailyLog
from game.serializers import CharacterProfileSerializer, DailyLogSerializer, QuestSerializer


class RegisterView(APIView):
    """
    POST /register/

    Body: { "username": <str>, "password": <str> }

    Creates a Django User and a default CharacterProfile (target_weight=80).
    No authentication required.
    """

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        username = request.data.get("username", "").strip()
        password = request.data.get("password", "")

        if not username or not password:
            return Response({"detail": "username and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({"detail": "Username already taken."}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(username=username, password=password)
        CharacterProfile.objects.create(user=user, target_weight=80)
        token, _ = Token.objects.get_or_create(user=user)

        return Response({"id": user.id, "username": user.username, "token": token.key}, status=status.HTTP_201_CREATED)


class SetTargetView(APIView):
    """
    POST /set-target/

    Body: { "target_weight": <float> }

    Updates the CharacterProfile's target_weight.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        target = request.data.get("target_weight")

        try:
            target = float(target)
            if target <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response({"detail": "target_weight must be a positive number."}, status=status.HTTP_400_BAD_REQUEST)

        profile = request.user.character
        profile.target_weight = target
        profile.save(update_fields=["target_weight"])

        game_status = GameEngine.get_status(profile)
        return Response({**CharacterProfileSerializer(profile).data, **game_status}, status=status.HTTP_200_OK)


def _get_or_create_today_log(user) -> DailyLog:
    """Return (or create) the DailyLog entry for today."""
    log, _ = DailyLog.objects.get_or_create(user=user, date=timezone.localdate())
    return log


class LogCaloriesView(APIView):
    """
    POST /log-calories/

    Body: { "calories": <int> }

    Adds the supplied calories to today's DailyLog and converts them to XP
    on the user's CharacterProfile.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        calories = request.data.get("calories")

        if calories is None:
            return Response({"detail": "calories is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            calories = int(calories)
        except (TypeError, ValueError):
            return Response({"detail": "calories must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

        if calories <= 0:
            return Response({"detail": "calories must be a positive integer."}, status=status.HTTP_400_BAD_REQUEST)

        log = _get_or_create_today_log(request.user)
        log.calories_eaten += calories
        log.save(update_fields=["calories_eaten"])

        profile = request.user.character
        xp_gained = GameEngine.calories_to_xp(calories)
        profile.xp += xp_gained
        profile.save(update_fields=["xp"])
        GameEngine.update_streak(profile)

        # Update quests; award bonus XP for completions
        completed_quests = GameEngine.update_quests_for_calories(request.user, calories, log)
        bonus_xp = 0
        for _ in completed_quests:
            from game.models import Quest
            try:
                q = Quest.objects.get(user=request.user, date=timezone.localdate(),
                                      quest_type="calorie_goal")
                bonus_xp += q.xp_reward
            except Quest.DoesNotExist:
                pass
        if bonus_xp:
            profile.xp += bonus_xp
            profile.save(update_fields=["xp"])

        return Response(
            {
                "calories_eaten_today": log.calories_eaten,
                "xp_gained": xp_gained + bonus_xp,
                "total_xp": profile.xp,
                "quests_completed": completed_quests,
            },
            status=status.HTTP_200_OK,
        )


class LogWeightView(APIView):
    """
    POST /log-weight/

    Body: { "weight": <float> }

    Records today's weight on both the DailyLog and the CharacterProfile,
    then checks whether a level-up threshold has been crossed.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        weight = request.data.get("weight")

        if weight is None:
            return Response({"detail": "weight is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            weight = float(weight)
        except (TypeError, ValueError):
            return Response({"detail": "weight must be a number."}, status=status.HTTP_400_BAD_REQUEST)

        if weight <= 0:
            return Response({"detail": "weight must be a positive number."}, status=status.HTTP_400_BAD_REQUEST)

        log = _get_or_create_today_log(request.user)
        log.weight_logged = weight
        log.save(update_fields=["weight_logged"])

        profile = request.user.character
        profile.current_weight = weight
        profile.save(update_fields=["current_weight"])

        GameEngine.update_streak(profile)
        leveled_up = GameEngine.check_level_up(profile)

        completed_quests = GameEngine.update_quests_for_weight(request.user)
        if completed_quests:
            from game.models import Quest
            try:
                q = Quest.objects.get(user=request.user, date=timezone.localdate(),
                                      quest_type="log_weight")
                profile.xp += q.xp_reward
                profile.save(update_fields=["xp"])
            except Quest.DoesNotExist:
                pass

        return Response(
            {
                "weight_logged": weight,
                "leveled_up": leveled_up,
                "current_level": profile.level,
                "quests_completed": completed_quests,
            },
            status=status.HTTP_200_OK,
        )


class QuestsView(APIView):
    """
    GET /quests/

    Returns today's daily quests, creating them on first call.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        quests = GameEngine.get_or_create_daily_quests(request.user)
        return Response(QuestSerializer(quests, many=True).data)


class StatusView(APIView):
    """
    GET /status/

    Returns the authenticated user's full character status including rank.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        try:
            profile = request.user.character
        except CharacterProfile.DoesNotExist:
            return Response({"detail": "Character profile not found."}, status=status.HTTP_404_NOT_FOUND)

        game_status = GameEngine.get_status(profile)
        profile_data = CharacterProfileSerializer(profile).data

        return Response({**profile_data, **game_status}, status=status.HTTP_200_OK)
