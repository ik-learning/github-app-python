import os
import base64
from datetime import datetime
from fastapi import FastAPI
from githubapp import GitHubApp, with_rate_limit_handling
import logging
from concurrent.futures import ThreadPoolExecutor
import asyncio
import threading

from utils import read_file, json_prettify, analyze_repository_structure
from model import PullRequestPayload
from constants import BOT_COMMENT_TEMPLATE
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
private_key = base64.b64decode(private_key_base64).decode('utf-8')

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


def post_pr_comment(client, pr_data, repo_stats, clone_dir):
    """
    Post a summary comment to the pull request.

    Args:
        client: GitHub API client
        pr_data: PullRequestPayload object
        repo_stats: Dictionary with 'file_count' and 'dir_count'
        clone_dir: Path to cloned repository
    """
    owner, repo = pr_data.repository.split('/')
    current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

    comment_body = BOT_COMMENT_TEMPLATE.format(
        timestamp=current_time,
        clone_dir=clone_dir,
        branch=pr_data.branch,
        file_count=repo_stats['file_count'],
        dir_count=repo_stats['dir_count']
    )

    logger.info(f"Posting comment to PR #{pr_data.number}")
    client.issues.create_comment(
        owner=owner,
        repo=repo,
        issue_number=pr_data.number,
        body=comment_body
    )
    logger.info(f"Successfully posted comment to PR #{pr_data.number}")


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
            post_pr_comment(client, pr_data, repo_stats, clone_dir)
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
