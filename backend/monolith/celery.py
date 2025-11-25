import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "monolith.settings")

app = Celery("monolith")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

