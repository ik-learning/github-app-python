#!/usr/bin/env python3
"""
Ephemeral Blackduck Worker - processes ONE message then exits.
Docker restart policy handles the restart.
"""
import os
import sys
import time
import redis
import logging
from model import MessagePayload
from processor import Processor
from scan import check_blackduck_installed, BlackduckNotFoundError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

STREAM_NAME = os.getenv("STREAM_NAME", "worker-blackduck")
APP_NAME = os.getenv("APP_NAME", "blackduck-worker")
CONSUMER_GROUP = os.getenv("CONSUMER_GROUP", "workers")
CONSUMER_NAME = os.getenv("CONSUMER_NAME", APP_NAME or "consumer-1")


def main():
    logger.info(f"[{APP_NAME}] Starting Blackduck Worker...")

    # Check Blackduck is installed
    try:
        blackduck_version = check_blackduck_installed()
        logger.info(f"[{APP_NAME}] Blackduck check passed: {blackduck_version}")
    except BlackduckNotFoundError as e:
        logger.error(f"[{APP_NAME}] Blackduck not found: {e}")
        sys.exit(1)

    # Connect to Redis
    r = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        decode_responses=True
    )

    # Ensure consumer group exists
    try:
        r.xgroup_create(STREAM_NAME, CONSUMER_GROUP, id="0", mkstream=True)
        logger.info(f"[{APP_NAME}] Created consumer group: {CONSUMER_GROUP}")
    except redis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise
        logger.info(f"[{APP_NAME}] Consumer group {CONSUMER_GROUP} already exists")

    processor = Processor(APP_NAME, r)
    logger.info(f"[{APP_NAME}] Listening on stream: {STREAM_NAME}")

    # Main loop - wait for ONE message, process it, then exit
    while True:
        try:
            messages = r.xreadgroup(
                CONSUMER_GROUP, CONSUMER_NAME,
                {STREAM_NAME: ">"},
                block=5000, count=1
            )

            if not messages:
                continue

            for stream, entries in messages:
                for entry_id, data in entries:
                    msg = MessagePayload.message(data)
                    logger.info(f"[{APP_NAME}] Received: {msg}")

                    processor.process(msg)

                    r.xack(STREAM_NAME, CONSUMER_GROUP, entry_id)
                    r.xdel(STREAM_NAME, entry_id)
                    logger.info(f"[{APP_NAME}] Done. Exiting for clean restart.")
                    sys.exit(0)  # Exit cleanly, Docker will restart

        except redis.ConnectionError as e:
            logger.error(f"[{APP_NAME}] Redis connection error: {e}")
            time.sleep(5)
        except Exception as e:
            logger.error(f"[{APP_NAME}] Error: {e}")
            time.sleep(1)


if __name__ == "__main__":
    main()
