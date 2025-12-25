import os
from fastapi import FastAPI
from githubapp import GitHubApp, with_rate_limit_handling
import logging
from concurrent.futures import ThreadPoolExecutor

from utils import read_file, analyze_repository_structure, decode_base64_key
from model import PullRequestPayload
from cache import TokenCache
from repo import RepositoryManager

# Thread pool for background tasks
executor = ThreadPoolExecutor(max_workers=3)

# Token cache instance
token_cache = TokenCache(buffer_minutes=5)

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

# Decode the base64-encoded private key
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

@app.get("/status")
def index():
    return {"status": "ok"}


# Background worker for the heavy processing (runs in thread pool)
def _process_pr_sync(payload):
    """
    Process pull request synchronize event in the background.

    This method orchestrates the following operations:
    1. Parse webhook payload and extract PR data
    2. Get or refresh GitHub App installation access token (cached)
    3. Clone the repository and checkout the PR branch
    4. Analyze repository structure (count files and directories)
    5. Post a summary comment to the PR with processing results
    6. Clean up: delete the cloned repository

    Args:
        payload: GitHub webhook payload dictionary

    Note:
        Runs in a background thread via ThreadPoolExecutor.
        Repository is cloned to /tmp/{repo}-{pr_number}-{short_sha} and deleted after processing.
    """
    try:
        pr_data = PullRequestPayload.from_webhook(payload)
        token = token_cache.get_token(pr_data.install_id, github_app.get_access_token)
        client = github_app.client()

        # Setup repository (clone and checkout)
        repo_manager = RepositoryManager(pr_data, token)

        try:
            clone_dir = repo_manager.setup()
            repo_stats = analyze_repository_structure(clone_dir)
            repo_manager.post_comment(client, repo_stats)
            logger.info(f"Background processing for PR #{pr_data.number} finished successfully")
        finally:
            repo_manager.cleanup()

    except Exception:
        logger.exception("Background PR processing failed")

@github_app.on('pull_request.synchronize')
@with_rate_limit_handling(github_app)
def handle_pr():
    # Capture payload immediately to avoid race conditions
    payload = dict(github_app.payload)
    # Submit to thread pool for background processing
    executor.submit(_process_pr_sync, payload)
    logger.info("PR synchronize event accepted for background processing")
    return {"status": "accepted"}

@app.get("/test")
async def read_root():
    return {"Hello": "World"}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), log_level="info", reload=True)
