import os
import json
import redis
import threading
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

STREAM_NAME = os.getenv("STREAM_NAME", "worker-1")
APP_NAME = os.getenv("APP_NAME")

Redis = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

def stream_listener():
    last_id = "0"
    logger.info(f"Subscribing to stream: {STREAM_NAME}")

    while True:
        try:
            messages = Redis.xread({STREAM_NAME: last_id}, block=0, count=1)
            for stream, entries in messages:
                for entry_id, data in entries:
                    last_id = entry_id
                    logger.info(f"Received message: {data}")
        except redis.ConnectionError as e:
            logger.error(f"Redis connection error: {e}")
        except Exception as e:
            logger.error(f"Error reading stream: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    thread = threading.Thread(target=stream_listener, daemon=True)
    thread.start()
    logger.info(f"Worker started, listening on stream: {STREAM_NAME}")
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/status")
def status():
    try:
        Redis.ping()
        redis_status = "ok"
    except redis.ConnectionError:
        redis_status = "error"
    return {
            "status": "ok",
            "redis": redis_status,
            "stream": STREAM_NAME,
            "app": APP_NAME
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)), log_level="info")
