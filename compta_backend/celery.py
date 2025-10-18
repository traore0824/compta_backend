from __future__ import absolute_import, unicode_literals
import os
from celery import Celery, shared_task
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "compta_backend.settings")
app = Celery("compta_backend")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
app.conf.broker_connection_retry_on_startup = True
from datetime import timedelta


app.conf.beat_schedule = {
    "update_balance_api": {
        "task": "compta.tasks.update_balance_api",
        "schedule": timedelta(minutes=5),
    },
    "send_compta_summary": {
        "task": "compta.tasks.send_compta_summary",
        "schedule": crontab(minute=0, hour="0,12"),
    },
}
