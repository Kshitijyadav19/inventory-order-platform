import os
from dotenv import load_dotenv
from celery import Celery

load_dotenv()
_broker = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
celery_app = Celery("inventory_order_platform", broker=_broker, backend=_backend, include=["app.tasks"])
celery_app.conf.update(task_serializer="json", accept_content=["json"], result_serializer="json", timezone="UTC", enable_utc=True)
