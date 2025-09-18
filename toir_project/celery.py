import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "toir_project.settings")

app = Celery("toir")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
