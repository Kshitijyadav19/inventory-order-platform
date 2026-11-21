import hashlib, hmac
def verify_checkout_signature(order_id: str, payment_id: str, signature: str, secret: str) -> bool:
    expected=hmac.new(secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()
    return bool(signature) and hmac.compare_digest(expected, signature)
def verify_webhook_signature(body: bytes, signature: str, secret: str) -> bool:
    expected=hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return bool(signature) and hmac.compare_digest(expected, signature)
