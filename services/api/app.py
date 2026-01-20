import os
import json
import uuid
import redis
from fastapi import FastAPI
from githubapp import GitHubApp, with_rate_limit_handling
import logging

from utils import read_file, decode_base64_key
from model import StoragePayload

# Configure logging
logging.basicConfig(
    # level=logging.DEBUG,
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
app = FastAPI()
logger.info(read_file("settings.ini"))

# Validate required environment variables
required_env_vars = ["GITHUB_APP_ID", "GITHUB_APP_PRIVATE_KEY", "GITHUB_WEBHOOK_SECRET"]
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

private_key_base64 = os.getenv("GITHUB_APP_PRIVATE_KEY")
private_key = decode_base64_key(private_key_base64)

github_app = GitHubApp(
    app,
    github_app_id=int(os.getenv("GITHUB_APP_ID")),
    github_app_key=private_key,
    github_app_secret=os.getenv("GITHUB_WEBHOOK_SECRET").encode(),
    github_app_route="/webhooks/github",
)

github_app.init_app(app, route="/webhooks/github")

Redis = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True
        )

@app.get("/status")
def index():
    try:
        Redis.ping()
        redis_status = "ok"
    except redis.ConnectionError:
        redis_status = "error"
    return {"status": "ok", "redis": redis_status}

@app.post("/fanout")
def fanout():
    id = str(uuid.uuid7())
    storage = {
        "id": id,
        "name": "repo",
        "owner": "octocat",
        "branch": "feature-branch",
        "prId": 42,
    }

    worker = {
        "id": id,
        "callback_url": "http://api:8000/callback"
    }

    # Store the full payload in Redis for long storage
    Redis.set(f"storage:{id}", json.dumps(storage))
    logger.debug(f"Storage saved with key: storage:{id}")

    # "worker-2", "worker-3"
    streams = ["worker-1"]

    for stream in streams:
        Redis.xadd(stream, {"data": json.dumps(worker)})
        logger.debug(f"Message sent to stream: {stream} with id: {id}")

    return {"status": "ok", "streams": streams, "id": id}


@app.post("/callback")
def callback(payload: dict):
    id = payload.get("id")
    app_name = payload.get("app_name")
    msg_base64 = payload.get("msg_base64")

    # Read storage data by id
    storage_data = Redis.get(f"storage:{id}")
    if storage_data:
        storage = StoragePayload.from_json(storage_data)
        logger.info(f"Callback from {app_name} - name: {storage.name}, owner: {storage.owner}, branch: {storage.branch}")
        logger.info(f"Message: {msg_base64}")
    else:
        logger.warning(f"Callback from {app_name} - no storage found for id: {id}")

    return {"status": "ok", "id": id}


@github_app.on('pull_request.opened')
@github_app.on('pull_request.synchronize')
@with_rate_limit_handling(github_app)
def handle_pr():
    # Capture payload immediately to avoid race conditions
    payload = dict(github_app.payload)
    print("payload ->> ", payload)
    # Submit to a worker for background processing
    logger.info("PR event accepted for background processing")
    # make request to redis queue
    # 1. blackduck scan
    # 2. checkmarks scan
    # 3. kicks scan
    return {"status": "accepted"}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), log_level="info", reload=True)
