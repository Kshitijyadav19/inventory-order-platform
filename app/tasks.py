from app.celery_app import celery_app

@celery_app.task(name="app.tasks.health_check")
def health_check_task():
    return {"status": "ok", "service": "inventory-order-platform-worker"}

# Add email/low-stock notification tasks here after configuring an email provider.
