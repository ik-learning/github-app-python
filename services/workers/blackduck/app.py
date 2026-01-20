import os
import base64
import random
import time
import redis
import requests
import threading
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from model import MessagePayload, StoragePayload

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


def send_callback(callback_url: str, id: str, msg: str):
    payload = {
        "id": id,
        "msg_base64": base64.b64encode(msg.encode()).decode(),
        "app_name": APP_NAME
    }
    try:
        response = requests.post(callback_url, json=payload, timeout=10)
        logger.info(f"[{APP_NAME}] Callback sent to {callback_url}: {response.status_code}")
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
                        # 1. Read from worker stream
                        msg = MessagePayload.message(data)
                        logger.info(f"[{APP_NAME}] Received message: {msg}")

                        # 2. Fetch details from storage
                        storage_data = Redis.get(f"storage:{msg.id}")
                        if storage_data:
                            storage = StoragePayload.from_json(storage_data)
                            logger.info(f"[{APP_NAME}] Fetched storage: name={storage.name}, owner={storage.owner}, branch={storage.branch}")
                        else:
                            logger.warning(f"[{APP_NAME}] No storage found for id: {msg.id}")

                        # 3. Process - random wait 5-10 seconds
                        wait_time = random.randint(5, 10)
                        logger.info(f"[{APP_NAME}] Processing... waiting {wait_time}s")
                        time.sleep(wait_time)

                        # 4. Reply with id, msg_base64, app_name to /callback
                        if msg.callback_url:
                            result_msg = f"Processed by {APP_NAME}: {storage.name}/{storage.branch}" if storage_data else f"Processed by {APP_NAME}"
                            send_callback(msg.callback_url, msg.id, result_msg)

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
