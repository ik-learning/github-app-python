"""Pytest configuration and shared fixtures."""
import json
import pytest
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
    """Load pull request opened event payload."""
    return load_fixture("pull_request_opened.json")


@pytest.fixture
def pr_closed_payload(load_fixture):
    """Load pull request closed event payload."""
    return load_fixture("pull_request_closed.json")


@pytest.fixture
def pr_closed_merged_payload(load_fixture):
    """Load pull request closed (merged) event payload."""
    return load_fixture("pull_request_closed_merged.json")


@pytest.fixture
def issue_comment_created_payload(load_fixture):
    """Load issue comment created event payload."""
    return load_fixture("issue_comment_created.json")


@pytest.fixture
def pr_review_comment_payload(load_fixture):
    """Load PR review comment created event payload."""
    return load_fixture("pr_review_comment_created.json")


@pytest.fixture
def pr_edited_payload(load_fixture):
    """Load pull request edited event payload."""
    return load_fixture("pull_request_edited.json")


@pytest.fixture
def pr_opened_real_payload(load_fixture):
    """Load real pull request opened event payload from actual GitHub webhook."""
    return load_fixture("pull_request_opened_real.json")


@pytest.fixture
def push_new_branch_payload(load_fixture):
    """Load push event for new branch creation."""
    return load_fixture("push_new_branch.json")


@pytest.fixture
def push_to_main_payload(load_fixture):
    """Load push event to main branch."""
    return load_fixture("push_to_main.json")


@pytest.fixture
def push_force_payload(load_fixture):
    """Load force push event."""
    return load_fixture("push_force.json")


@pytest.fixture
def mock_github_app(mocker):
    """Mock GitHubApp instance."""
    return mocker.MagicMock()
