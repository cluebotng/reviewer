import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cbng_reviewer.settings")

app = Celery("cbng_reviewer")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
