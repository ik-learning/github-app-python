import os
import base64
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from githubapp import GitHubApp, with_rate_limit_handling
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# GitHubAppMiddleware, GitHubAppEventHandler

app = FastAPI()

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and log them."""
    logger.error(
        f"UNHANDLED EXCEPTION: {type(exc).__name__}: {exc}\n"
        f"Path: {request.url.path}\n"
        f"Method: {request.method}\n"
        f"Headers: {dict(request.headers)}\n"
        f"Traceback:\n{traceback.format_exc()}"
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Internal server error: {type(exc).__name__}: {str(exc)}",
            "type": type(exc).__name__
        }
    )

# Add middleware to log all requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    logger.debug(f"Headers: {dict(request.headers)}")

    # Log the event type specifically
    event_type = request.headers.get('x-github-event', 'unknown')
    logger.info(f"GitHub Event Type: {event_type}")

    try:
        response = await call_next(request)
        logger.info(f"Response status: {response.status_code}")

        # Log error status codes with more detail
        if response.status_code >= 400:
            logger.error(f"Error response {response.status_code} for {event_type} event")
            # Try to read response body if available
            try:
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk
                logger.error(f"Error response body: {body.decode()[:500]}")
                # Recreate response since we consumed the iterator
                from starlette.responses import Response
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers)
                )
            except Exception as e:
                logger.error(f"Could not read response body: {e}")

        return response
    except Exception as e:
        logger.error(f"EXCEPTION in middleware: {type(e).__name__}: {e}", exc_info=True)
        raise

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

logger = logging.getLogger(__name__)

@app.get("/status")
def index():
    return {"status": "ok"}

@github_app.on('pull_request.synchronize')
async def handle_pr_sync(payload: dict) -> dict:
    """
    Stub handler for when a pull request is synchronized (new commits pushed).

    Payload contains:
    - action: "synchronize"
    - pull_request: Full PR object
    - repository: Repository info
    - sender: User who pushed the commits
    """
    logger.info(f"[STUB] PR synchronize")

    return {
        "status": "processed",
        "event": "pull_request.synchronize",
        "pr_number": payload.get("pull_request", {}).get("number"),
        "message": "PR synchronize event processed (stub)"
    }

# GitHub Webhook Event Handlers
@github_app.on('pull_request.opened')
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
    logger.info(f"[STUB] PR Created")

    pr = payload.get("pull_request", {})
    print("PR Payload:", pr)  # Debug print to see the full PR payload
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
    print("ISSUE COMMENT CREATED")

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


@github_app.on('pull_request.edited')
async def handle_pr_edited(payload: dict) -> dict:
    """
    Stub handler for when a pull request is edited.

    Triggered when PR title or body is edited.

    Payload contains:
    - action: "edited"
    - changes: Object with "title" and/or "body" showing what changed
    - pull_request: Full PR object with updated values
    - repository: Repository info
    - sender: User who made the edit

    TODO: Implement your logic:
    - Track PR title changes
    - Monitor description updates
    - Trigger re-validation if important fields changed
    """

    logger.info(f"[STUB] PR Edited:")

    pr = payload.get("pull_request", {})
    pr_number = pr.get("number")
    pr_title = pr.get("title")
    pr_author = pr.get("user", {}).get("login")
    repo_name = payload.get("repository", {}).get("full_name")

    # Get what changed
    changes = payload.get("changes", {})
    changed_fields = list(changes.keys())

    logger.info(f"[STUB] PR Edited: #{pr_number} - {pr_title}")
    logger.info(f"[STUB]   Changed fields: {', '.join(changed_fields)}")
    logger.info(f"[STUB]   Editor: {payload.get('sender', {}).get('login')}")
    logger.info(f"[STUB]   Repo: {repo_name}")

    # Log specific changes
    if "title" in changes:
        old_title = changes["title"].get("from")
        logger.info(f"[STUB]   Title changed from: '{old_title}' to: '{pr_title}'")

    if "body" in changes:
        logger.info(f"[STUB]   Description was updated")

    # TODO: Add your custom logic here
    # Example: Re-trigger checks if title format changed
    # Example: Notify team if description was significantly updated

    return {
        "status": "processed",
        "event": "pull_request.edited",
        "pr_number": pr_number,
        "changed_fields": changed_fields,
        "message": "PR edited event processed (stub)"
    }


@github_app.on('push')
async def handle_push(payload: dict) -> dict:
    """
    Stub handler for push events.

    Triggered when commits are pushed to a repository.

    Payload contains:
    - ref: Branch reference (e.g., "refs/heads/main")
    - before: Previous commit SHA (all zeros if new branch)
    - after: New commit SHA (all zeros if branch deleted)
    - created: Boolean - was this a new branch?
    - deleted: Boolean - was this branch deleted?
    - forced: Boolean - was this a force push?
    - commits: Array of commits pushed
    - head_commit: The latest commit object
    - repository: Repository info
    - pusher: User who pushed
    - sender: GitHub user who triggered the event

    TODO: Implement your logic:
    - Trigger CI/CD pipelines
    - Validate commit messages
    - Check for specific files changed
    - Notify team of force pushes
    - Auto-deploy on main branch pushes
    """
    logger.info(f"[STUB]   Pushed to repo")

    ref = payload.get("ref", "")
    branch = ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ref

    before_sha = payload.get("before", "")
    after_sha = payload.get("after", "")

    created = payload.get("created", False)
    deleted = payload.get("deleted", False)
    forced = payload.get("forced", False)

    commits = payload.get("commits", [])
    commit_count = len(commits)

    repo_name = payload.get("repository", {}).get("full_name", "")
    pusher = payload.get("pusher", {}).get("name", "")

    # Determine event type
    if deleted:
        event_type = "branch_deleted"
        logger.info(f"[STUB] Branch Deleted: {branch} in {repo_name}")
    elif created:
        event_type = "branch_created"
        logger.info(f"[STUB] Branch Created: {branch} in {repo_name}")
    elif forced:
        event_type = "force_push"
        logger.warning(f"[STUB] Force Push: {branch} in {repo_name} by {pusher}")
    else:
        event_type = "push"
        logger.info(f"[STUB] Push: {commit_count} commit(s) to {branch} in {repo_name}")

    logger.info(f"[STUB]   Pusher: {pusher}")
    logger.info(f"[STUB]   Before: {before_sha[:8]}...")
    logger.info(f"[STUB]   After: {after_sha[:8]}...")

    # Log commit details
    if commits and not deleted:
        for commit in commits[:3]:  # Log first 3 commits
            message = commit.get("message", "").split('\n')[0]  # First line only
            author = commit.get("author", {}).get("name", "")
            logger.info(f"[STUB]     - {commit.get('id', '')[:8]}: {message} ({author})")

        if commit_count > 3:
            logger.info(f"[STUB]     ... and {commit_count - 3} more commit(s)")

    # TODO: Add your custom logic here
    # Example: if branch == "main" and not deleted:
    #     trigger_deployment()
    # Example: if forced:
    #     notify_team_of_force_push()
    # Example: validate_commit_messages(commits)

    return {
        "status": "processed",
        "event": "push",
        "event_type": event_type,
        "branch": branch,
        "commit_count": commit_count,
        "created": created,
        "deleted": deleted,
        "forced": forced,
        "message": f"Push event processed: {event_type} (stub)"
    }


# Additional event handlers for PR review comments
@github_app.on('pull_request_review_comment.created')
async def handle_pr_review_comment(payload: dict) -> dict:
    """
    Stub handler for code review comments on PRs.

    This is triggered when someone comments on a specific line of code.
    Different from general PR comments (issue_comment).
    """
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
