"""URL routes for the game app."""

from django.urls import path

from game.views import LogCaloriesView, LogWeightView, RegisterView, SetTargetView, StatusView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("set-target/", SetTargetView.as_view(), name="set-target"),
    path("log-calories/", LogCaloriesView.as_view(), name="log-calories"),
    path("log-weight/", LogWeightView.as_view(), name="log-weight"),
    path("status/", StatusView.as_view(), name="status"),
]
