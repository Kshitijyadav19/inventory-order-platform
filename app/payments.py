"""Payment integration boundary. Live payment routes are intentionally not enabled yet.

Configure Razorpay test credentials in .env before implementing order payment creation
and signature-verified webhook handling. Never trust a client-supplied payment status.
"""
import os
from dotenv import load_dotenv

load_dotenv()

def razorpay_configured() -> bool:
    return bool(os.getenv("RAZORPAY_KEY_ID") and os.getenv("RAZORPAY_KEY_SECRET") and os.getenv("RAZORPAY_WEBHOOK_SECRET"))
