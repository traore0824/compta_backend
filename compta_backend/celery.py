from __future__ import absolute_import, unicode_literals
import os
from celery import Celery, shared_task
from celery.schedules import crontab
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'box_backend.settings')
app = Celery("box_backend")
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
app.conf.broker_connection_retry_on_startup = True

app.conf.beat_schedule = {
    "daily_message_8": {
        "task": "box.tasks.daily_message",
        "schedule": crontab(hour=8, minute=0),
    },
    "daily_message_2": {
        "task": "box.tasks.daily_message",
        "schedule": crontab(hour=21, minute=0),
    },
    "delete_disable_caisse_task": {
        "task": "box.tasks.delete_disable_caisse",
        "schedule": crontab(hour="*/3"),
    },
    #######
    "reminder_payment_red_moning": {
        "task": "box.tasks.reminder_payment_red_moning",
        "schedule": crontab(hour=8, minute=0),
    },
    "reminder_payment_red_afternoon": {
        "task": "box.tasks.reminder_payment_red_afternoon",
        "schedule": crontab(hour=14, minute=0),
    },
    "reminder_payment_red_evining": {
        "task": "box.tasks.reminder_payment_red_evining",
        "schedule": crontab(hour=21, minute=0),
    },
    "reminder_payment_yellow_evening": {
        "task": "box.tasks.reminder_payment_yellow_evening",
        "schedule": crontab(hour=21, minute=0),
    },
    "reminder_payment_yellow_morning": {
        "task": "box.tasks.reminder_payment_yellow_morning",
        "schedule": crontab(hour=8, minute=0),
    },
    "reminder_payment_day_evining": {
        "task": "box.tasks.reminder_payment_day_evining",
        "schedule": crontab(hour=21, minute=0),
    },
    "reminder_payment_day_morning": {
        "task": "box.tasks.reminder_payment_day_morning",
        "schedule": crontab(hour=8, minute=0),
    },
    # "envoyer-notif-21h": {
    #     "task": "add",
    #     "schedule": crontab(hour=21, minute=0),
    # }
}
