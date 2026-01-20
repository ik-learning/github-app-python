import os
import json
import uuid
import redis
from fastapi import FastAPI
from githubapp import GitHubApp, with_rate_limit_handling
import logging

from utils import read_file, decode_base64_key

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
    trace_id = str(uuid.uuid7())
    message = {
        "trace_id": trace_id,
        "name": "repo",
        "owner": "octocat",
        "branch": "feature-branch",
        "prId": 42,
        "callbackUrl": "http://api:8000/callback"
    }

    streams = ["worker-1", "worker-2", "worker-3"]

    for stream in streams:
        Redis.xadd(stream, {"data": json.dumps(message)})
        logger.debug(f"Message sent to stream: {stream} with trace_id: {trace_id}")

    return {"status": "ok", "streams": streams, "trace_id": trace_id}


@app.post("/callback")
def callback(payload: dict):
    trace_id = payload.get("trace_id")
    msg_base64 = payload.get("msg_base64")
    logger.info(f"Callback received - trace_id: {trace_id}, msg_base64: {msg_base64}")
    return {"status": "ok", "trace_id": trace_id}


@github_app.on('pull_request.opened')
@github_app.on('pull_request.synchronize')
@with_rate_limit_handling(github_app)
def handle_pr():
    # Capture payload immediately to avoid race conditions
    payload = dict(github_app.payload)
    print(payload)
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
