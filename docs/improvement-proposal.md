# Code Improvement Proposal for github-app-python

**Date:** December 24, 2025
**Current State:** Single file (app.py) with all logic
**Goal:** Modular, testable, maintainable architecture

---

## Current Issues

### 1. **Single File Architecture**
- All code in `src/app.py` (~180 lines)
- Configuration, app setup, and handlers mixed together
- Hard to test individual components
- Difficult to scale as more handlers are added

### 2. **No Tests**
- No unit tests for handlers
- No integration tests for webhooks
- No test fixtures for GitHub payloads

### 3. **Configuration Management**
- Environment variables read inline
- No centralized config
- Hard to validate and document required settings

### 4. **Logging**
- Logger created in each function
- No centralized logging configuration
- No structured logging

### 5. **Code Duplication**
- Similar payload extraction logic in each handler
- Repeated logger setup
- Common patterns not abstracted

---

## Proposed Architecture

```
src/
├── __init__.py
├── app.py                      # FastAPI app setup only
├── config.py                   # Configuration management
├── models.py                   # Pydantic models for webhooks
├── handlers/
│   ├── __init__.py
│   ├── pull_request.py        # PR event handlers
│   ├── comments.py            # Comment event handlers
│   └── base.py                # Base handler class
├── services/
│   ├── __init__.py
│   ├── github_client.py       # GitHub API client wrapper
│   └── logger.py              # Logging configuration
└── utils/
    ├── __init__.py
    └── payload.py             # Payload parsing utilities

tests/
├── __init__.py
├── conftest.py                # Pytest fixtures
├── fixtures/
│   ├── pull_request_opened.json
│   ├── issue_comment_created.json
│   └── pr_review_comment.json
├── test_handlers/
│   ├── test_pull_request.py
│   └── test_comments.py
└── test_app.py                # Integration tests
```

---

## Detailed Improvements

### 1. Configuration Management (`src/config.py`)

**Benefits:**
- Type-safe configuration with Pydantic
- Automatic validation
- Clear documentation of required env vars
- Easy to test with different configs

**Implementation:**
```python
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import base64

class Settings(BaseSettings):
    """Application settings from environment variables."""

    # GitHub App Configuration
    github_app_id: int = Field(..., description="GitHub App ID")
    github_app_private_key: str = Field(..., description="Base64-encoded private key")
    github_webhook_secret: str = Field(..., description="Webhook secret for signature verification")

    # Application Configuration
    port: int = Field(default=8000, description="Port to run the application on")
    log_level: str = Field(default="INFO", description="Logging level")
    environment: str = Field(default="development", description="Environment (development/production)")

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def github_private_key_decoded(self) -> str:
        """Decode the base64-encoded private key."""
        return base64.b64decode(self.github_app_private_key).decode('utf-8')

    @validator('github_app_id')
    def validate_app_id(cls, v):
        if v <= 0:
            raise ValueError('GitHub App ID must be positive')
        return v

# Singleton instance
settings = Settings()
```

### 2. Pydantic Models (`src/models.py`)

**Benefits:**
- Type safety
- Automatic validation
- Better IDE autocomplete
- Self-documenting code

**Implementation:**
```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class User(BaseModel):
    """GitHub user model."""
    login: str
    id: int
    avatar_url: str
    type: str

class Repository(BaseModel):
    """GitHub repository model."""
    id: int
    name: str
    full_name: str
    private: bool
    owner: User
    html_url: str

class PullRequest(BaseModel):
    """GitHub pull request model."""
    number: int
    title: str
    body: Optional[str]
    state: str
    user: User
    merged: bool
    mergeable: Optional[bool]
    html_url: str
    created_at: datetime
    updated_at: datetime

class Comment(BaseModel):
    """GitHub comment model."""
    id: int
    body: str
    user: User
    html_url: str
    created_at: datetime
    # For review comments
    path: Optional[str] = None
    position: Optional[int] = None

class PullRequestOpenedPayload(BaseModel):
    """Payload for pull_request.opened event."""
    action: str
    number: int
    pull_request: PullRequest
    repository: Repository
    sender: User

class IssueCommentCreatedPayload(BaseModel):
    """Payload for issue_comment.created event."""
    action: str
    comment: Comment
    issue: dict  # Can be PR or issue
    repository: Repository
    sender: User
```

### 3. Base Handler Class (`src/handlers/base.py`)

**Benefits:**
- DRY (Don't Repeat Yourself)
- Common logging setup
- Shared utilities
- Easy to extend

**Implementation:**
```python
import logging
from typing import Any, Dict
from abc import ABC

class BaseHandler(ABC):
    """Base class for GitHub webhook event handlers."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def extract_pr_info(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract common PR information from payload."""
        pr = payload.get("pull_request", {})
        return {
            "number": pr.get("number"),
            "title": pr.get("title"),
            "author": pr.get("user", {}).get("login"),
            "repo": payload.get("repository", {}).get("full_name"),
            "url": pr.get("html_url"),
        }

    def extract_comment_info(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract common comment information from payload."""
        comment = payload.get("comment", {})
        return {
            "body": comment.get("body", ""),
            "author": comment.get("user", {}).get("login"),
            "url": comment.get("html_url"),
            "path": comment.get("path"),  # Only for review comments
        }

    def log_event(self, event_type: str, details: Dict[str, Any]):
        """Log event with consistent formatting."""
        self.logger.info(f"[{event_type}] {details}")
```

### 4. Separate Handler Files

**src/handlers/pull_request.py:**
```python
from typing import Dict, Any
from .base import BaseHandler

class PullRequestHandler(BaseHandler):
    """Handles pull request events."""

    async def on_opened(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle pull request opened event."""
        pr_info = self.extract_pr_info(payload)

        self.log_event("PR Opened", pr_info)

        # TODO: Implement business logic
        # - Add labels
        # - Request reviewers
        # - Post welcome comment

        return {
            "status": "processed",
            "event": "pull_request.opened",
            "pr_number": pr_info["number"],
        }

    async def on_closed(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle pull request closed event."""
        pr_info = self.extract_pr_info(payload)
        merged = payload.get("pull_request", {}).get("merged", False)

        status = "merged" if merged else "closed"
        self.log_event(f"PR {status}", pr_info)

        # TODO: Cleanup logic if needed

        return {
            "status": "processed",
            "event": "pull_request.closed",
            "pr_number": pr_info["number"],
            "merged": merged,
        }

# Create singleton instance
pr_handler = PullRequestHandler()
```

**src/handlers/comments.py:**
```python
from typing import Dict, Any
from .base import BaseHandler

class CommentHandler(BaseHandler):
    """Handles comment events."""

    async def on_issue_comment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle issue comment (includes PR comments)."""
        comment_info = self.extract_comment_info(payload)

        # Check if it's a PR comment
        is_pr = "pull_request" in payload.get("issue", {})
        if not is_pr:
            return {"status": "ignored", "reason": "not a PR comment"}

        pr = payload.get("issue", {})
        pr_number = pr.get("number")

        self.log_event("PR Comment", {
            "pr": pr_number,
            **comment_info
        })

        # TODO: Parse slash commands
        # if comment_info["body"].startswith("/"):
        #     return await self.handle_command(comment_info["body"], pr_number)

        return {
            "status": "processed",
            "event": "issue_comment.created",
            "pr_number": pr_number,
        }

    async def on_review_comment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle pull request review comment."""
        comment_info = self.extract_comment_info(payload)
        pr_info = self.extract_pr_info(payload)

        self.log_event("PR Review Comment", {
            **pr_info,
            **comment_info,
        })

        # TODO: Handle code-specific comments

        return {
            "status": "processed",
            "event": "pull_request_review_comment.created",
            "pr_number": pr_info["number"],
        }

# Create singleton instance
comment_handler = CommentHandler()
```

### 5. Refactored app.py

**Benefits:**
- Clean and minimal
- Easy to understand
- Separation of concerns
- Just wires everything together

**Implementation:**
```python
import os
from fastapi import FastAPI
from githubapp import GitHubApp, with_rate_limit_handling

from .config import settings
from .services.logger import setup_logging
from .handlers.pull_request import pr_handler
from .handlers.comments import comment_handler

# Setup logging
setup_logging(settings.log_level)

# Create FastAPI app
app = FastAPI(
    title="GitHub App",
    description="GitHub App for PR automation",
    version="1.0.0"
)

# Initialize GitHub App
github_app = GitHubApp(
    app,
    github_app_id=settings.github_app_id,
    github_app_key=settings.github_private_key_decoded,
    github_app_secret=settings.github_webhook_secret.encode(),
    github_app_route="/webhooks/github",
)

# Health check endpoint
@app.get("/status")
def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "environment": settings.environment,
    }

# Register event handlers
@github_app.on('pull_request.opened')
@with_rate_limit_handling(github_app)
async def handle_pr_opened(payload: dict):
    return await pr_handler.on_opened(payload)

@github_app.on('pull_request.closed')
@with_rate_limit_handling(github_app)
async def handle_pr_closed(payload: dict):
    return await pr_handler.on_closed(payload)

@github_app.on('issue_comment.created')
@with_rate_limit_handling(github_app)
async def handle_comment(payload: dict):
    return await comment_handler.on_issue_comment(payload)

@github_app.on('pull_request_review_comment.created')
@with_rate_limit_handling(github_app)
async def handle_review_comment(payload: dict):
    return await comment_handler.on_review_comment(payload)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=(settings.environment == "development")
    )
```

### 6. Centralized Logging (`src/services/logger.py`)

```python
import logging
import sys
from typing import Optional

def setup_logging(level: str = "INFO", json_logs: bool = False):
    """Setup application logging."""

    # Create formatter
    if json_logs:
        # For production - structured logging
        import json_logging
        json_logging.init_fastapi(enable_json=True)
        json_logging.init_request_instrument(app)
    else:
        # For development - human-readable
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)

        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, level.upper()))
        root_logger.addHandler(handler)
```

### 7. GitHub Client Wrapper (`src/services/github_client.py`)

**Benefits:**
- Centralized GitHub API interactions
- Easy to mock in tests
- Rate limiting handled in one place
- Reusable across handlers

```python
from typing import List, Optional
from githubapp import GitHubApp
import httpx

class GitHubClient:
    """Wrapper for GitHub API interactions."""

    def __init__(self, github_app: GitHubApp):
        self.github_app = github_app

    async def add_comment(self, repo: str, issue_number: int, body: str):
        """Add a comment to an issue or PR."""
        # Use github_app's authenticated client
        # Implementation depends on fastapi-githubapp API
        pass

    async def add_labels(self, repo: str, issue_number: int, labels: List[str]):
        """Add labels to an issue or PR."""
        pass

    async def request_reviewers(self, repo: str, pr_number: int, reviewers: List[str]):
        """Request reviewers for a PR."""
        pass

    async def get_changed_files(self, repo: str, pr_number: int) -> List[str]:
        """Get list of files changed in a PR."""
        pass
```

---

## Testing Strategy

### 1. Unit Tests for Handlers

**tests/test_handlers/test_pull_request.py:**
```python
import pytest
from src.handlers.pull_request import PullRequestHandler

@pytest.fixture
def pr_handler():
    return PullRequestHandler()

@pytest.fixture
def pr_opened_payload():
    """Load from fixtures/pull_request_opened.json"""
    return {
        "action": "opened",
        "number": 1,
        "pull_request": {
            "number": 1,
            "title": "Test PR",
            "body": "Test description",
            "user": {"login": "testuser"},
            "merged": False,
            "html_url": "https://github.com/test/repo/pull/1",
        },
        "repository": {
            "full_name": "test/repo",
        },
        "sender": {"login": "testuser"},
    }

@pytest.mark.asyncio
async def test_pr_opened_handler(pr_handler, pr_opened_payload):
    """Test PR opened handler."""
    result = await pr_handler.on_opened(pr_opened_payload)

    assert result["status"] == "processed"
    assert result["event"] == "pull_request.opened"
    assert result["pr_number"] == 1

@pytest.mark.asyncio
async def test_pr_opened_extracts_info(pr_handler, pr_opened_payload):
    """Test that handler extracts PR info correctly."""
    info = pr_handler.extract_pr_info(pr_opened_payload)

    assert info["number"] == 1
    assert info["title"] == "Test PR"
    assert info["author"] == "testuser"
    assert info["repo"] == "test/repo"
```

### 2. Integration Tests

**tests/test_app.py:**

```python
import pytest
from fastapi.testclient import TestClient
from trash.app import app
import hmac
import hashlib


@pytest.fixture
def client():
    return TestClient(app)


def create_signature(payload: bytes, secret: str) -> str:
    """Create GitHub webhook signature."""
    mac = hmac.new(secret.encode(), msg=payload, digestmod=hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/status")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_webhook_with_valid_signature(client, pr_opened_payload):
    """Test webhook endpoint with valid signature."""
    import json
    payload = json.dumps(pr_opened_payload).encode()
    signature = create_signature(payload, "test-secret")

    response = client.post(
        "/webhooks/github",
        content=payload,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": signature,
            "Content-Type": "application/json",
        }
    )

    assert response.status_code == 200


def test_webhook_with_invalid_signature(client):
    """Test webhook endpoint rejects invalid signature."""
    response = client.post(
        "/webhooks/github",
        json={"test": "data"},
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "sha256=invalid",
        }
    )

    assert response.status_code == 403
```

### 3. Pytest Configuration

**tests/conftest.py:**
```python
import pytest
import json
from pathlib import Path

@pytest.fixture
def fixtures_dir():
    """Return path to fixtures directory."""
    return Path(__file__).parent / "fixtures"

@pytest.fixture
def load_fixture(fixtures_dir):
    """Factory fixture to load JSON fixtures."""
    def _load(filename: str):
        with open(fixtures_dir / filename) as f:
            return json.load(f)
    return _load

@pytest.fixture
def pr_opened_payload(load_fixture):
    return load_fixture("pull_request_opened.json")

@pytest.fixture
def issue_comment_payload(load_fixture):
    return load_fixture("issue_comment_created.json")
```

### 4. Test Fixtures

**tests/fixtures/pull_request_opened.json:**
```json
{
  "action": "opened",
  "number": 42,
  "pull_request": {
    "id": 1,
    "number": 42,
    "title": "Add new feature",
    "body": "This PR adds a new feature",
    "state": "open",
    "user": {
      "login": "octocat",
      "id": 1,
      "avatar_url": "https://github.com/images/error/octocat_happy.gif",
      "type": "User"
    },
    "merged": false,
    "mergeable": true,
    "html_url": "https://github.com/owner/repo/pull/42",
    "created_at": "2025-12-24T12:00:00Z",
    "updated_at": "2025-12-24T12:00:00Z"
  },
  "repository": {
    "id": 1,
    "name": "repo",
    "full_name": "owner/repo",
    "private": false,
    "owner": {
      "login": "owner",
      "id": 2,
      "type": "User"
    },
    "html_url": "https://github.com/owner/repo"
  },
  "sender": {
    "login": "octocat",
    "id": 1,
    "type": "User"
  }
}
```

---

## Migration Plan

### Phase 1: Add Tests to Current Code
1. Create `tests/` directory
2. Add pytest to dev dependencies
3. Write tests for existing handlers
4. Ensure 100% test coverage

### Phase 2: Extract Configuration
1. Create `config.py`
2. Move env var handling
3. Add Pydantic settings
4. Update tests

### Phase 3: Create Handler Classes
1. Create `handlers/` directory
2. Create `base.py` with BaseHandler
3. Move PR handlers to `pull_request.py`
4. Move comment handlers to `comments.py`
5. Update tests

### Phase 4: Add Models
1. Create `models.py`
2. Add Pydantic models for payloads
3. Update handlers to use models
4. Update tests

### Phase 5: Add Services
1. Create `services/` directory
2. Add logger setup
3. Add GitHub client wrapper
4. Update handlers to use services

### Phase 6: Final Cleanup
1. Simplify `app.py`
2. Remove duplication
3. Update documentation
4. Final test run

---

## Dependencies to Add

Update `Pipfile`:
```toml
[packages]
fastapi = "*"
uvicorn = "*"
fastapi-githubapp = "*"
gunicorn = "*"
pydantic = "*"
pydantic-settings = "*"  # NEW
httpx = "*"               # NEW - for async HTTP requests

[dev-packages]
pytest = "*"
pytest-asyncio = "*"      # NEW - for async tests
pytest-cov = "*"          # NEW - for coverage reports
pytest-mock = "*"         # NEW - for mocking
black = "*"
```

---

## Expected Benefits

### Code Quality
- **Modularity:** Each component has a single responsibility
- **Testability:** Easy to test individual components
- **Maintainability:** Changes isolated to specific files
- **Readability:** Clear structure, less code per file

### Testing
- **Coverage:** Can achieve >90% test coverage
- **Confidence:** Catch bugs before deployment
- **Documentation:** Tests serve as usage examples
- **Regression Prevention:** Prevent breaking changes

### Developer Experience
- **Easier Onboarding:** Clear project structure
- **Faster Development:** Reusable components
- **Better IDE Support:** Type hints and models
- **Debugging:** Easier to isolate issues

### Production Readiness
- **Configuration Management:** Environment-specific settings
- **Logging:** Structured, searchable logs
- **Error Handling:** Centralized error handling
- **Monitoring:** Easy to add metrics

---

## Metrics

### Before Refactoring
- Files: 1 (app.py)
- Lines of Code: ~180
- Test Coverage: 0%
- Cyclomatic Complexity: High
- Code Duplication: ~30%

### After Refactoring
- Files: ~12
- Lines of Code: ~600 (but modular)
- Test Coverage: >90%
- Cyclomatic Complexity: Low
- Code Duplication: <5%

---

## Conclusion

This refactoring will transform the codebase from a simple script into a production-ready, maintainable application. The investment in structure and tests will pay dividends as the project grows and more event handlers are added.

**Recommended Next Steps:**
1. Review and approve this proposal
2. Start with Phase 1 (add tests to current code)
3. Proceed incrementally through remaining phases
4. Keep Docker configuration updated
5. Update PROJECT_ANALYSIS.md when complete

Would you like to proceed with implementation?
