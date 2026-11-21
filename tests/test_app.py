
import hashlib
import hmac
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_webhook_rejects_invalid_signature(monkeypatch):
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "test-webhook-secret")

    response = client.post(
        "/webhooks/razorpay",
        content=b'{"event":"payment.captured"}',
        headers={"x-razorpay-signature": "invalid-signature"},
    )

    assert response.status_code == 400


def test_webhook_ignores_unsupported_event(monkeypatch):
    secret = "test-webhook-secret"
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", secret)

    body = b'{"event":"order.paid"}'
    signature = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    response = client.post(
        "/webhooks/razorpay",
        content=body,
        headers={"x-razorpay-signature": signature},
    )

    assert response.status_code == 200
