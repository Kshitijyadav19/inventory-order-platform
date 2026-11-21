import hashlib, hmac
from app.payment_security import verify_checkout_signature, verify_webhook_signature
def test_checkout_signature_valid_and_invalid():
    secret="test-secret"; msg="order_123|pay_456".encode(); sig=hmac.new(secret.encode(),msg,hashlib.sha256).hexdigest()
    assert verify_checkout_signature("order_123","pay_456",sig,secret)
    assert not verify_checkout_signature("order_123","pay_456","bad",secret)
def test_webhook_signature():
    secret="webhook-secret"; body=b'{"event":"payment.captured"}'; sig=hmac.new(secret.encode(),body,hashlib.sha256).hexdigest()
    assert verify_webhook_signature(body,sig,secret)
    assert not verify_webhook_signature(body,sig,"wrong-secret")
