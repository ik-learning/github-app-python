import os
import base64
from fastapi import FastAPI
from githubapp import GitHubApp, with_rate_limit_handling
# GitHubAppMiddleware, GitHubAppEventHandler

app = FastAPI()

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

@app.get("/status")
def index():
    return {"status": "ok"}

# GitHub Webhook Event Handlers
@github_app.on('pull_request.opened')
@with_rate_limit_handling(github_app)
async def handle_pr_created(payload: dict) -> dict:
    """
    Stub handler for when a pull request is created/opened.

    Payload contains:
    - action: "opened"
    - pull_request: Full PR object
    - repository: Repository info
    - sender: User who opened the PR

    TODO: Implement your logic:
    - Add labels based on files changed
    - Request reviews from team members
    - Post welcome comment
    - Run automated checks
    """
    import logging
    logger = logging.getLogger(__name__)

    pr = payload.get("pull_request", {})
    pr_number = pr.get("number")
    pr_title = pr.get("title")
    pr_author = pr.get("user", {}).get("login")
    repo_name = payload.get("repository", {}).get("full_name")
    pr_url = pr.get("html_url")

    logger.info(f"[STUB] PR Created: #{pr_number} - {pr_title}")
    logger.info(f"[STUB]   Author: {pr_author}")
    logger.info(f"[STUB]   Repo: {repo_name}")
    logger.info(f"[STUB]   URL: {pr_url}")

    # TODO: Add your custom logic here
    # Example:
    # - github_api.add_comment(pr_number, "Thank you for your contribution!")
    # - github_api.add_labels(pr_number, ["needs-review"])
    # - github_api.request_reviewers(pr_number, ["team-member1", "team-member2"])

    return {
        "status": "processed",
        "event": "pull_request.opened",
        "pr_number": pr_number,
        "message": "PR created event processed (stub)"
    }


@github_app.on('issue_comment.created')
@with_rate_limit_handling(github_app)
async def handle_pr_comment_added(payload: dict) -> dict:
    """
    Stub handler for when a comment is added to a pull request.

    This handles both:
    - issue_comment events (general PR comments)
    - pull_request_review_comment events (code review comments)

    Payload contains:
    - action: "created"
    - comment: Comment object with body, user, etc.
    - issue or pull_request: PR info
    - repository: Repository info

    TODO: Implement your logic:
    - Parse slash commands (/approve, /merge, etc.)
    - Trigger bot responses
    - Update PR status based on comments
    - Notify other team members
    """
    import logging
    logger = logging.getLogger(__name__)

    comment = payload.get("comment", {})
    comment_body = comment.get("body", "")
    comment_author = comment.get("user", {}).get("login")
    comment_url = comment.get("html_url")

    # Determine if this is a general comment or review comment
    is_review_comment = "path" in comment  # Review comments have file path
    pr = payload.get("pull_request") or payload.get("issue", {})
    pr_number = pr.get("number")

    comment_type = "review comment" if is_review_comment else "comment"
    file_path = comment.get("path") if is_review_comment else None

    logger.info(f"[STUB] PR {comment_type} added on PR #{pr_number} by {comment_author}")
    if file_path:
        logger.info(f"[STUB]   File: {file_path}")
    logger.info(f"[STUB]   Comment: {comment_body[:100]}...")
    logger.info(f"[STUB]   URL: {comment_url}")

    # TODO: Add your custom logic here
    # Example: Handle slash commands
    # if comment_body.startswith("/approve"):
    #     github_api.approve_pr(pr_number)
    #     return {"status": "approved", "pr_number": pr_number}
    # elif comment_body.startswith("/merge"):
    #     github_api.merge_pr(pr_number)
    #     return {"status": "merged", "pr_number": pr_number}

    return {
        "status": "processed",
        "event": "comment.created",
        "pr_number": pr_number,
        "comment_type": comment_type,
        "author": comment_author,
        "message": "PR comment event processed (stub)"
    }


# Additional event handlers for PR review comments
@github_app.on('pull_request_review_comment.created')
async def handle_pr_review_comment(payload: dict) -> dict:
    """
    Stub handler for code review comments on PRs.

    This is triggered when someone comments on a specific line of code.
    Different from general PR comments (issue_comment).
    """
    import logging
    logger = logging.getLogger(__name__)

    comment = payload.get("comment", {})
    pr = payload.get("pull_request", {})
    pr_number = pr.get("number")
    comment_body = comment.get("body", "")
    comment_author = comment.get("user", {}).get("login")
    file_path = comment.get("path")

    logger.info(f"[STUB] Review comment on PR #{pr_number} by {comment_author}")
    logger.info(f"[STUB]   File: {file_path}")
    logger.info(f"[STUB]   Comment: {comment_body[:100]}...")

    # TODO: Add logic for handling code review comments
    # Example: Auto-respond to specific review patterns

    return {
        "status": "processed",
        "event": "pull_request_review_comment.created",
        "pr_number": pr_number,
        "file": file_path,
        "message": "Review comment processed (stub)"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), log_level="info", reload=True)
