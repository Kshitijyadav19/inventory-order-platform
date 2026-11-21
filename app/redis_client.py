import os
from dotenv import load_dotenv
from redis import Redis

load_dotenv()
redis_client = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)
