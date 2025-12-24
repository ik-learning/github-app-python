# FastAPI and GitHub Integration Guide

**Last Updated:** December 24, 2025

This document summarizes various approaches and libraries for integrating GitHub webhooks and GitHub Apps with FastAPI applications.

---

## Table of Contents

1. [Overview](#overview)
2. [Available Libraries](#available-libraries)
3. [Integration Approaches](#integration-approaches)
4. [GitHub Webhook Events](#github-webhook-events)
5. [Implementation Patterns](#implementation-patterns)
6. [Security Considerations](#security-considerations)
7. [Best Practices](#best-practices)
8. [Example Implementations](#example-implementations)
9. [Resources](#resources)

---

## Overview

GitHub webhooks allow you to build or set up integrations that subscribe to certain events on GitHub.com. When one of those events is triggered, GitHub sends an HTTP POST payload to the webhook's configured URL.

FastAPI is well-suited for handling GitHub webhooks due to:
- Fast async request handling
- Built-in request validation with Pydantic
- Automatic API documentation
- Easy integration with background task processing

---

## Available Libraries

### 1. **fastapi-githubapp** (This Project)

**Package:** `fastapi-githubapp`
**Import:** `from githubapp import GitHubApp`
**Status:** Limited public documentation; decorator-based event handling

**Basic Usage Pattern:**
```python
from githubapp import GitHubApp

github_app = GitHubApp(
    app,  # FastAPI app instance
    github_app_id=int(os.getenv("GITHUB_APP_ID")),
    github_app_key=private_key,
    github_app_secret=os.getenv("GITHUB_WEBHOOK_SECRET").encode(),
    github_app_route="/webhooks/github",
)

# Event handler with specific action
@github_app.on('pull_request.opened')
async def handle_pr_opened(payload: dict):
    pr = payload['pull_request']
    print(f"PR #{pr['number']} opened: {pr['title']}")
    return {"status": "processed"}

# Event handler for all actions of a type
@github_app.on('issues')
async def handle_all_issue_events(payload: dict):
    action = payload['action']
    issue = payload['issue']
    print(f"Issue #{issue['number']} - action: {action}")
    return {"status": "processed"}

# Another example with comments
@github_app.on('issue_comment.created')
async def handle_comment(payload: dict):
    comment = payload['comment']
    print(f"Comment by {comment['user']['login']}: {comment['body']}")
    return {"status": "processed"}
```

**Decorator Syntax:**
- Specific action: `@github_app.on('event_type.action')` - e.g., `'pull_request.opened'`
- All actions: `@github_app.on('event_type')` - e.g., `'issues'` for all issue events

**Notes:**
- Handles webhook signature verification automatically
- Provides route registration for GitHub webhooks at specified path
- Decorator-based event routing (similar to Flask patterns)
- Payload is passed as a dictionary to handler functions

### 2. **gidgethub** + **Safir**

**Package:** `gidgethub`, `safir`
**Documentation:** [Safir GitHub Apps Guide](https://safir.lsst.io/user-guide/github-apps/handling-webhooks.html)

**Features:**
- Router-based event handling
- Pydantic models for webhook payloads
- Type-safe event processing

**Example:**
```python
from safir.github.webhooks import GitHubPullRequestEventModel
from gidgethub import sansio

@webhook_router.register("pull_request", action="opened")
async def handle_pull_request_opened(
    event: sansio.Event,
    logger: BoundLogger
) -> None:
    """Handle pull request opened events."""
    pull_request_event = GitHubPullRequestEventModel.parse_obj(event.data)
    # Process the event
```

**Advantages:**
- Strong typing with Pydantic models
- Decorator-based routing
- Production-tested (used by LSST)

### 3. **fastgithub**

**Package:** `fastgithub`
**PyPI:** [fastgithub](https://pypi.org/project/fastgithub/)

**Features:**
- Webhook event dispatcher
- Token-based verification
- Decorator pattern for event handlers

**Example:**
```python
from fastgithub.endpoint.webhook_router import webhook_router
from fastgithub.webhook import GithubWebhookHandler

webhook_handler = GithubWebhookHandler(token="your-secret-token")

@webhook_handler.listen("push")
def hello(data: dict[str, Any]):
    print(f"Hello from: {data['repository']}")

app = FastAPI()
router = webhook_router(handler=webhook_handler, path="/postreceive")
app.include_router(router)
```

### 4. **PyGithub** (GitHub API Client)

**Package:** `PyGithub`
**Use Case:** GitHub API interactions (not webhook handling)

**Features:**
- Complete GitHub REST API wrapper
- Object-oriented interface
- Good for responding to webhooks with API calls

**Example:**
```python
from github import Github

g = Github(access_token)
repo = g.get_repo("owner/repo")
pr = repo.get_pull(pr_number)
pr.create_issue_comment("Thanks for your PR!")
```

### 5. **githubkit**

**Package:** `githubkit`
**Article:** [GitHub Authentication with Python/FastAPI](https://medium.com/@bhuwan.pandey9867/github-authentication-with-python-fastapi-446a20e60d5a)

**Features:**
- Modern GitHub API client
- Built for async/await
- Good FastAPI integration

---

## Integration Approaches

### Approach 1: Manual Webhook Endpoint

**Simplest approach** - Create a standard FastAPI POST endpoint to handle webhooks.

```python
from fastapi import FastAPI, Request, HTTPException
import hmac
import hashlib

app = FastAPI()

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook signature."""
    if not signature:
        return False

    sha_name, signature = signature.split('=')
    mac = hmac.new(secret.encode(), msg=payload, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), signature)

@app.post("/webhooks/github")
async def github_webhook(request: Request):
    # Verify signature
    signature = request.headers.get("X-Hub-Signature-256")
    payload = await request.body()

    if not verify_signature(payload, signature, WEBHOOK_SECRET):
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Get event type
    event_type = request.headers.get("X-GitHub-Event")

    # Parse payload
    data = await request.json()

    # Route to handlers
    if event_type == "pull_request":
        return await handle_pull_request(data)
    elif event_type == "issue_comment":
        return await handle_comment(data)

    return {"status": "ignored"}
```

**Pros:**
- Full control
- No dependencies
- Easy to understand

**Cons:**
- Manual signature verification
- Manual routing logic
- More boilerplate code

### Approach 2: Library-Based Integration

Use a library like `gidgethub` or `fastgithub` that handles verification and routing.

**Pros:**
- Less boilerplate
- Built-in security
- Type safety (with Pydantic models)

**Cons:**
- Additional dependency
- Learning curve for library API

### Approach 3: Event-Driven Architecture

Use FastAPI's background tasks or an external queue (Celery, RQ) for async processing.

```python
from fastapi import BackgroundTasks

@app.post("/webhooks/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    event_type = request.headers.get("X-GitHub-Event")

    # Process webhook asynchronously
    background_tasks.add_task(process_webhook, event_type, payload)

    # Return immediately to GitHub
    return {"status": "queued"}

async def process_webhook(event_type: str, payload: dict):
    # Time-consuming processing here
    pass
```

**Pros:**
- Fast webhook response
- Prevents timeouts
- Scalable

**Cons:**
- More complex architecture
- Requires task queue infrastructure

---

## GitHub Webhook Events

### Common Event Types

| Event | Description | Trigger |
|-------|-------------|---------|
| `pull_request` | Pull request activity | PR opened, closed, synchronized, etc. |
| `issue_comment` | Issue or PR comment | Comment created, edited, deleted |
| `pull_request_review` | PR review submitted | Review submitted, edited, dismissed |
| `pull_request_review_comment` | Comment on PR code | Review comment created, edited |
| `push` | Code pushed to repository | Commits pushed to branch |
| `issues` | Issue activity | Issue opened, closed, labeled, etc. |
| `repository` | Repository changes | Repository created, deleted, archived |
| `release` | Release activity | Release published, edited, deleted |
| `status` | Status check changes | Status updated |
| `check_run` | Check run activity | Check run created, completed |

### Event Headers

GitHub sends these headers with webhook requests:

```
X-GitHub-Event: pull_request
X-GitHub-Delivery: 12345678-1234-1234-1234-123456789012
X-Hub-Signature-256: sha256=<signature>
X-GitHub-Hook-ID: 123456
X-GitHub-Hook-Installation-Target-ID: 123456
X-GitHub-Hook-Installation-Target-Type: repository
```

### Pull Request Event Actions

The `action` field in `pull_request` events can be:
- `opened` - PR was created
- `closed` - PR was closed (check `merged` field)
- `synchronize` - New commits pushed to PR
- `reopened` - Previously closed PR was reopened
- `edited` - PR title or body edited
- `assigned` / `unassigned` - Assignee changed
- `labeled` / `unlabeled` - Label added/removed
- `review_requested` / `review_request_removed` - Reviewer changed
- `ready_for_review` - Draft PR marked ready

### Comment Event Actions

The `action` field in comment events:
- `created` - New comment added
- `edited` - Comment edited
- `deleted` - Comment deleted

---

## Implementation Patterns

### Pattern 1: Action-Based Routing

Route events based on both event type and action:

```python
async def route_webhook(event_type: str, payload: dict):
    action = payload.get("action")

    handlers = {
        ("pull_request", "opened"): handle_pr_opened,
        ("pull_request", "closed"): handle_pr_closed,
        ("pull_request", "synchronize"): handle_pr_sync,
        ("issue_comment", "created"): handle_comment_created,
    }

    handler = handlers.get((event_type, action))
    if handler:
        return await handler(payload)

    return {"status": "ignored"}
```

### Pattern 2: Event Handler Classes

Use classes to organize related event handlers:

```python
class PullRequestHandler:
    def __init__(self, github_client):
        self.github = github_client

    async def on_opened(self, payload: dict):
        pr = payload["pull_request"]
        await self.github.add_comment(
            pr["number"],
            "Thanks for your contribution!"
        )

    async def on_closed(self, payload: dict):
        pr = payload["pull_request"]
        if pr.get("merged"):
            await self.github.add_comment(
                pr["number"],
                "Merged! 🎉"
            )
```

### Pattern 3: Decorator-Based Handlers

Register handlers using decorators:

```python
webhook_handlers = {}

def on_event(event_type: str, action: str = None):
    def decorator(func):
        key = (event_type, action) if action else event_type
        webhook_handlers[key] = func
        return func
    return decorator

@on_event("pull_request", "opened")
async def handle_pr_opened(payload: dict):
    # Handle PR opened
    pass

@on_event("issue_comment", "created")
async def handle_comment(payload: dict):
    # Handle comment
    pass
```

### Pattern 4: Payload Models with Pydantic

Define typed models for webhook payloads:

```python
from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    login: str
    id: int
    avatar_url: str
    type: str

class Repository(BaseModel):
    id: int
    name: str
    full_name: str
    private: bool
    owner: User

class PullRequest(BaseModel):
    number: int
    title: str
    body: Optional[str]
    state: str
    user: User
    merged: bool
    mergeable: Optional[bool]
    html_url: str

class PullRequestEvent(BaseModel):
    action: str
    number: int
    pull_request: PullRequest
    repository: Repository
    sender: User

@app.post("/webhooks/github")
async def webhook(event: PullRequestEvent):
    # Fully typed event handling
    if event.action == "opened":
        print(f"PR #{event.number}: {event.pull_request.title}")
```

---

## Security Considerations

### 1. Webhook Signature Verification

**Always verify** the webhook signature to ensure requests come from GitHub:

```python
import hmac
import hashlib

def verify_github_signature(
    payload_body: bytes,
    signature_header: str,
    webhook_secret: str
) -> bool:
    """Verify the GitHub webhook signature."""
    if not signature_header:
        return False

    hash_algorithm, github_signature = signature_header.split('=')

    algorithm = hashlib.sha256 if hash_algorithm == 'sha256' else hashlib.sha1

    mac = hmac.new(
        webhook_secret.encode('utf-8'),
        msg=payload_body,
        digestmod=algorithm
    )
    expected_signature = mac.hexdigest()

    return hmac.compare_digest(expected_signature, github_signature)
```

### 2. Rate Limiting

Protect your endpoint from abuse:

```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@app.post("/webhooks/github", dependencies=[Depends(RateLimiter(times=100, seconds=60))])
async def webhook(request: Request):
    pass
```

### 3. Validate Payload Structure

Use Pydantic models to validate payload structure:

```python
from pydantic import BaseModel, ValidationError

try:
    event = PullRequestEvent(**payload)
except ValidationError as e:
    raise HTTPException(status_code=422, detail=str(e))
```

### 4. Timeout Handling

Respond to GitHub quickly (< 10 seconds) to avoid timeouts:

```python
@app.post("/webhooks/github")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()

    # Queue for async processing
    background_tasks.add_task(process_webhook, payload)

    # Return immediately
    return {"status": "accepted"}
```

### 5. Secret Management

**Never** hardcode secrets:

```python
import os

# Good - from environment
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")

# Bad - hardcoded
WEBHOOK_SECRET = "mysecret123"  # DON'T DO THIS
```

---

## Best Practices

### 1. Idempotency

Make webhook handlers idempotent since GitHub may send the same event multiple times:

```python
processed_deliveries = set()

async def process_webhook(delivery_id: str, payload: dict):
    if delivery_id in processed_deliveries:
        return {"status": "already_processed"}

    # Process webhook
    # ...

    processed_deliveries.add(delivery_id)
    return {"status": "processed"}
```

### 2. Logging

Log all webhook events for debugging:

```python
import logging

logger = logging.getLogger(__name__)

@app.post("/webhooks/github")
async def webhook(request: Request):
    event_type = request.headers.get("X-GitHub-Event")
    delivery_id = request.headers.get("X-GitHub-Delivery")

    logger.info(f"Received {event_type} event (delivery: {delivery_id})")

    payload = await request.json()
    logger.debug(f"Payload: {payload}")
```

### 3. Error Handling

Handle errors gracefully and return appropriate status codes:

```python
@app.post("/webhooks/github")
async def webhook(request: Request):
    try:
        payload = await request.json()
        result = await process_webhook(payload)
        return result
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=422, detail="Invalid payload")
    except Exception as e:
        logger.exception("Unexpected error processing webhook")
        raise HTTPException(status_code=500, detail="Internal server error")
```

### 4. Testing

Create test fixtures for webhook payloads:

```python
import pytest

@pytest.fixture
def pr_opened_payload():
    return {
        "action": "opened",
        "number": 1,
        "pull_request": {
            "id": 1,
            "number": 1,
            "title": "Test PR",
            "user": {"login": "testuser"},
            # ... more fields
        }
    }

async def test_pr_opened_handler(pr_opened_payload):
    result = await handle_pr_opened(pr_opened_payload)
    assert result["status"] == "processed"
```

### 5. Monitoring

Monitor webhook processing:

```python
from prometheus_client import Counter, Histogram

webhook_requests = Counter('github_webhook_requests_total', 'Total webhook requests', ['event_type'])
webhook_duration = Histogram('github_webhook_duration_seconds', 'Webhook processing time')

@app.post("/webhooks/github")
async def webhook(request: Request):
    event_type = request.headers.get("X-GitHub-Event")
    webhook_requests.labels(event_type=event_type).inc()

    with webhook_duration.time():
        return await process_webhook(await request.json())
```

---

## Example Implementations

### Example 1: Basic PR Comment Bot

```python
from fastapi import FastAPI, Request, HTTPException
from github import Github
import os

app = FastAPI()
github_client = Github(os.getenv("GITHUB_TOKEN"))

@app.post("/webhooks/github")
async def webhook(request: Request):
    event_type = request.headers.get("X-GitHub-Event")

    if event_type != "pull_request":
        return {"status": "ignored"}

    payload = await request.json()

    if payload["action"] == "opened":
        repo_name = payload["repository"]["full_name"]
        pr_number = payload["pull_request"]["number"]

        repo = github_client.get_repo(repo_name)
        pr = repo.get_pull(pr_number)

        pr.create_issue_comment(
            "Thank you for your contribution! A maintainer will review your PR soon."
        )

        return {"status": "commented"}

    return {"status": "ignored"}
```

### Example 2: Auto-Label Based on Files Changed

```python
@app.post("/webhooks/github")
async def webhook(request: Request):
    payload = await request.json()

    if payload.get("action") != "opened":
        return {"status": "ignored"}

    pr = payload["pull_request"]
    files_url = pr["_links"]["self"]["href"] + "/files"

    # Fetch changed files
    async with httpx.AsyncClient() as client:
        response = await client.get(files_url)
        files = response.json()

    # Determine labels based on files
    labels = set()
    for file in files:
        filename = file["filename"]
        if filename.startswith("docs/"):
            labels.add("documentation")
        elif filename.endswith(".py"):
            labels.add("python")
        elif filename.endswith((".js", ".ts")):
            labels.add("javascript")

    # Add labels to PR
    if labels:
        repo = github_client.get_repo(payload["repository"]["full_name"])
        pr_obj = repo.get_pull(pr["number"])
        pr_obj.add_to_labels(*labels)

    return {"status": "labeled", "labels": list(labels)}
```

### Example 3: Slash Command Handler

```python
@app.post("/webhooks/github")
async def webhook(request: Request):
    payload = await request.json()
    event_type = request.headers.get("X-GitHub-Event")

    if event_type != "issue_comment" or payload["action"] != "created":
        return {"status": "ignored"}

    comment_body = payload["comment"]["body"].strip()

    # Check for slash commands
    if comment_body.startswith("/"):
        command = comment_body.split()[0][1:]  # Remove leading /

        repo = github_client.get_repo(payload["repository"]["full_name"])
        issue = repo.get_issue(payload["issue"]["number"])

        if command == "approve":
            issue.create_reaction("rocket")
            issue.create_comment("Approved! ✅")

        elif command == "close":
            issue.edit(state="closed")
            issue.create_comment("Closed by command.")

        elif command == "assign":
            # Parse username from command
            parts = comment_body.split()
            if len(parts) > 1:
                username = parts[1].lstrip("@")
                issue.add_to_assignees(username)
                issue.create_comment(f"Assigned to @{username}")

        return {"status": "command_executed", "command": command}

    return {"status": "ignored"}
```

---

## Resources

### Official Documentation
- [GitHub Webhooks Documentation](https://docs.github.com/en/developers/webhooks-and-events/webhooks)
- [GitHub Apps Documentation](https://docs.github.com/en/developers/apps)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

### Libraries
- [PyGithub](https://github.com/PyGithub/PyGithub) - Python library for GitHub API v3
- [gidgethub](https://github.com/gidgethub/gidgethub) - Async GitHub API library
- [githubkit](https://github.com/yanyongyu/githubkit) - Modern async GitHub SDK
- [fastgithub](https://pypi.org/project/fastgithub/) - GitHub webhooks with FastAPI

### Articles and Guides
- [Safir: Handling GitHub Webhooks](https://safir.lsst.io/user-guide/github-apps/handling-webhooks.html)
- [Using FastAPI to get updates from GitHub to Telegram](https://blog.logrocket.com/using-fastapi-to-get-updates-from-github-to-telegram/)
- [Track custom GitHub metrics with webhooks and FastAPI](https://dev.to/deta/track-custom-github-repository-metrics-with-github-webhooks-fastapi-and-deta-2gi2)
- [GitHub Authentication with Python/FastAPI (githubkit)](https://medium.com/@bhuwan.pandey9867/github-authentication-with-python-fastapi-446a20e60d5a)

### Tools
- [Smee.io](https://smee.io/) - Webhook payload delivery service for local development
- [ngrok](https://ngrok.com/) - Expose local servers to the internet
- [Webhook.site](https://webhook.site/) - Test and debug webhooks

### Related Projects
- [Probot](https://probot.github.io/) - Framework for building GitHub Apps (Node.js)
- [octomachinery](https://github.com/sanitizers/octomachinery) - Framework for GitHub Apps (Python)
- [github-app-template](https://github.com/github/github-app-template) - Template for GitHub Apps

---

## Troubleshooting

### Common Issues

#### 1. Signature Verification Fails

**Problem:** `X-Hub-Signature-256` doesn't match calculated signature

**Solutions:**
- Ensure you're using the raw request body (bytes)
- Check that webhook secret matches GitHub App settings
- Verify you're using the correct hash algorithm (sha256 vs sha1)
- Don't parse JSON before verifying signature

#### 2. Webhook Timeouts

**Problem:** GitHub shows webhook delivery failures due to timeouts

**Solutions:**
- Use background tasks for long-running operations
- Return response within 10 seconds
- Queue webhooks to external task queue (Celery, RQ)
- Optimize database queries

#### 3. Missing Headers

**Problem:** `X-GitHub-Event` or other headers are None

**Solutions:**
- Check that GitHub App webhook is configured correctly
- Verify FastAPI is receiving headers (check `request.headers`)
- Ensure reverse proxy (nginx) passes headers through

#### 4. Duplicate Events

**Problem:** Same webhook delivered multiple times

**Solutions:**
- Implement idempotency using `X-GitHub-Delivery` ID
- Store processed delivery IDs
- Make handlers idempotent by design

---

## Conclusion

FastAPI provides an excellent foundation for building GitHub integrations. Key takeaways:

1. **Start simple** with manual webhook endpoints
2. **Verify signatures** to ensure security
3. **Use background tasks** for async processing
4. **Add strong typing** with Pydantic models
5. **Monitor and log** all webhook events
6. **Test thoroughly** with realistic payloads

Choose the approach that best fits your needs:
- **Manual implementation** for simple use cases
- **Library-based** (gidgethub, fastgithub) for production apps
- **Event-driven** architecture for high-scale applications

---

**Document Version:** 1.0
**Created:** December 24, 2025
**Author:** Claude Code Analysis
**Project:** github-app-python workshop
