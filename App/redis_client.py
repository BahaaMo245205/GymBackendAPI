import os

import redis.asyncio as redis

redis_client = redis.Redis(
    host="localhost",
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True,
)
