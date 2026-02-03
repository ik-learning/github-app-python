import os
import sys
import time
import redis
import threading
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from model import MessagePayload
from processor import Processor
from scan import check_kics_installed, KicsNotFoundError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.info("Starting KICS Worker...")

# Check KICS is installed on startup
try:
    kics_version = check_kics_installed()
    logger.info(f"KICS check passed: {kics_version}")
except KicsNotFoundError as e:
    logger.error(f"KICS not found: {e}")
    logger.error("Worker cannot start without KICS. Exiting.")
    sys.exit(1)

STREAM_NAME = os.getenv("STREAM_NAME", "worker-kics")
APP_NAME = os.getenv("APP_NAME", "kics-worker")

Redis = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

CONSUMER_GROUP = os.getenv("CONSUMER_GROUP", "workers")
CONSUMER_NAME = os.getenv("CONSUMER_NAME", APP_NAME or "consumer-1")


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

    processor = Processor(APP_NAME, Redis)

    while True:
        try:
            logger.debug(f"[{APP_NAME}] Waiting for messages on {STREAM_NAME}...")
            messages = Redis.xreadgroup(
                CONSUMER_GROUP, CONSUMER_NAME,
                {STREAM_NAME: ">"},
                block=5000, count=1
            )
            if messages:
                for stream, entries in messages:
                    for entry_id, data in entries:
                        msg = MessagePayload.message(data)
                        logger.info(f"[{APP_NAME}] Received message: {msg}")

                        processor.process(msg)

                        Redis.xack(STREAM_NAME, CONSUMER_GROUP, entry_id)
                        Redis.xdel(STREAM_NAME, entry_id)
                        logger.info(f"[{APP_NAME}] Processed and removed: {entry_id}")
                        logger.info(f"[{APP_NAME}] Job complete, exiting for clean restart...")
                        os._exit(0)
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
            "app": APP_NAME,
            "kics_version": kics_version
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)), log_level="info")
