import os
import base64
import redis
import requests
import threading
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from model import MessagePayload

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.info("Starting Blackduck Worker...")

STREAM_NAME = os.getenv("STREAM_NAME", "worker-1")
APP_NAME = os.getenv("APP_NAME")

Redis = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

CONSUMER_GROUP = os.getenv("CONSUMER_GROUP", "workers")
CONSUMER_NAME = os.getenv("CONSUMER_NAME", APP_NAME or "consumer-1")


def send_callback(callback_url: str, trace_id: str):
    msg = f"hello from {APP_NAME}"
    payload = {
        "trace_id": trace_id,
        "msg_base64": base64.b64encode(msg.encode()).decode()
    }
    try:
        response = requests.post(callback_url, json=payload, timeout=10)
        logger.debug(f"[{APP_NAME}] Callback sent to {callback_url}: {response.status_code}")
    except requests.RequestException as e:
        logger.error(f"[{APP_NAME}] Callback failed: {e}")


def ensure_consumer_group():
    try:
        Redis.xgroup_create(STREAM_NAME, CONSUMER_GROUP, id="0", mkstream=True)
        logger.info(f"[{APP_NAME}] Created consumer group: {CONSUMER_GROUP}")
    except redis.ResponseError as e:
        if "BUSYGROUP" in str(e):
            logger.info(f"[{APP_NAME}] Consumer group {CONSUMER_GROUP} already exists")
        else:
            raise


def stream_listener():
    import time
    ensure_consumer_group()
    logger.info(f"[{APP_NAME}] Starting stream listener for: {STREAM_NAME}")

    while True:
        try:
            logger.debug(f"[{APP_NAME}] Waiting for messages on {STREAM_NAME}...")
            # ">" means read only new messages not yet delivered to other consumers
            messages = Redis.xreadgroup(
                CONSUMER_GROUP, CONSUMER_NAME,
                {STREAM_NAME: ">"},
                block=5000, count=1
            )
            if messages:
                for stream, entries in messages:
                    for entry_id, data in entries:
                        logger.info(data)
                        msg = MessagePayload.message(data)
                        logger.info(f"[{APP_NAME}] Received message: {msg}")
                        # Send callback on completion
                        if msg.callbackUrl:
                            send_callback(msg.callbackUrl, msg.trace_id)
                        # Acknowledge and delete after processing
                        Redis.xack(STREAM_NAME, CONSUMER_GROUP, entry_id)
                        Redis.xdel(STREAM_NAME, entry_id)
                        logger.debug(f"[{APP_NAME}] Processed and removed: {entry_id}")
            else:
                logger.debug(f"[{APP_NAME}] No messages, continuing...")
        except redis.ConnectionError as e:
            logger.error(f"[{APP_NAME}] Redis connection error: {e}")
            time.sleep(5)
        except Exception as e:
            logger.error(f"[{APP_NAME}] Error reading stream: {e}")
            time.sleep(1)


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
