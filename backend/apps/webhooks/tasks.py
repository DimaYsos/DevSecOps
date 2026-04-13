import json
import logging
import requests
from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

@shared_task(bind=True, queue="webhooks", max_retries=3)
def deliver_webhook(self, webhook_config_id, event_type, payload):
    from .models import WebhookConfig, WebhookDelivery

    try:
        config = WebhookConfig.objects.get(id=webhook_config_id, is_active=True)
    except WebhookConfig.DoesNotExist:
        return {"error": "Webhook config not found or inactive"}

    delivery = WebhookDelivery.objects.create(
        webhook=config, event_type=event_type, payload=payload,
        status="pending", attempts=self.request.retries + 1,
    )

    try:
        resp = requests.post(
            config.url, json=payload,
            headers={"Content-Type": "application/json", "X-Event-Type": event_type, **config.headers},
            timeout=config.timeout_seconds,
        )

        delivery.status = "success" if resp.ok else "failed"
        delivery.response_status = resp.status_code
        delivery.response_body = resp.text[:5000]
        delivery.response_headers = dict(resp.headers)
        delivery.delivered_at = timezone.now()
        delivery.save()

        if not resp.ok and self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (self.request.retries + 1))

        return {"delivery_id": str(delivery.id), "status": resp.status_code}

    except requests.RequestException as e:
        delivery.status = "failed"
        delivery.error_message = str(e)
        delivery.save()
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        return {"error": str(e)}

@shared_task(queue="notifications")
def send_notification(user_id, message, channel="email"):
    logger.info(f"Notification to {user_id} via {channel}: {message}")
    return {"sent": True}
