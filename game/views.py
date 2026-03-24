"""
API views for the MassQuest game app.

Endpoints
---------
POST /log-calories/  — add calories to today's DailyLog and award XP
POST /log-weight/    — record today's weight and check for a level-up
GET  /status/        — return the character's current RPG stats
"""

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from game.game_engine import GameEngine
from game.models import CharacterProfile, DailyLog
from game.serializers import CharacterProfileSerializer, DailyLogSerializer


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

        return Response(
            {
                "calories_eaten_today": log.calories_eaten,
                "xp_gained": xp_gained,
                "total_xp": profile.xp,
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

        leveled_up = GameEngine.check_level_up(profile)

        return Response(
            {
                "weight_logged": weight,
                "leveled_up": leveled_up,
                "current_level": profile.level,
            },
            status=status.HTTP_200_OK,
        )


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
