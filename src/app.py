import os
import base64
from datetime import datetime
from fastapi import FastAPI
from githubapp import GitHubApp, with_rate_limit_handling
import logging
from git import Repo

from utils import read_file
from model import PullRequestPayload
from constants import BOT_COMMENT_TEMPLATE

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

@github_app.on('pull_request.synchronize')
@with_rate_limit_handling(github_app)
def handle_pr():
    """
    Handler for when a pull request is synchronized (new commits pushed).
    """
    logger.info(f"[PR Event] Processing pull_request.synchronize")

    # Parse the webhook payload
    pr_data = PullRequestPayload.from_webhook(github_app.payload)

    logger.info(f"Repository: {pr_data.repository}")
    logger.info(f"Branch: {pr_data.branch}")
    logger.info(f"Commit SHA: {pr_data.commit_sha}")
    logger.info(f"Sender: {pr_data.sender_login}")
    logger.info(f"Default Branch: {pr_data.default_branch}")
    logger.info(f"PR Number: {pr_data.number}")

    # Validate PR state
    if not pr_data.is_valid_for_processing():
        logger.warning(
            f"PR #{pr_data.number} is not valid for processing. "
            f"State: {pr_data.state}, Merged: {pr_data.merged_at is not None}, "
            f"Closed: {pr_data.closed_at is not None}"
        )
        return

    logger.info(f"PR #{pr_data.number} is valid and ready for processing")

    # Get rate-limited client
    client = github_app.client()

    # Extract owner and repo from repository full name (format: "owner/repo")
    owner, repo = pr_data.repository.split('/')

    # Prepare comment body with timestamp
    current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    comment_body = BOT_COMMENT_TEMPLATE.format(timestamp=current_time)

    try:
        client.issues.create_comment(
            owner=owner,
            repo=repo,
            issue_number=pr_data.number,
            body=comment_body
        )
        logger.info(f"Successfully posted comment to PR #{pr_data.number}")
    except Exception as e:
        logger.error(f"Failed to post comment to PR #{pr_data.number}: {str(e)}")

    # Clone the repository and checkout to the PR branch
    # The client is already authenticated with an installation token
    # Access the token from the client's authorization header
    try:
        auth_header = client._session.headers.get('Authorization', '')
        installation_token = auth_header.replace('token ', '').replace('Bearer ', '')
        logger.info(f"Successfully extracted installation token (length: {len(installation_token)})")
    except Exception as e:
        logger.error(f"Failed to extract installation token from client: {str(e)}")
        return

    clone_dir = f"/tmp/{repo}-{pr_data.number}"

    try:
        # Construct authenticated clone URL
        authenticated_url = pr_data.clone_url.replace(
            "https://",
            f"https://x-access-token:{installation_token}@"
        )

        logger.info(f"Cloning repository to {clone_dir}")
        repo_obj = Repo.clone_from(authenticated_url, clone_dir)

        # Checkout to the PR branch
        logger.info(f"Checking out branch: {pr_data.branch}")
        repo_obj.git.checkout(pr_data.branch)

        logger.info(f"Successfully cloned and checked out to branch {pr_data.branch}")

    except Exception as e:
        logger.error(f"Failed to clone repository or checkout branch: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), log_level="info", reload=True)
