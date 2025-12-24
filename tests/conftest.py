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
def mock_github_app(mocker):
    """Mock GitHubApp instance."""
    return mocker.MagicMock()
