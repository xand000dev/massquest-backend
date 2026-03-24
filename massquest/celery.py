"""
Celery application entry point for MassQuest.

Start the worker:
    celery -A massquest worker -l info

Start the beat scheduler:
    celery -A massquest beat -l info
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "massquest.settings")

app = Celery("massquest")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
