"""Tests for model.py"""

import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from model import PullRequestPayload


class TestPullRequestPayload:
    """Tests for PullRequestPayload dataclass."""

    def test_from_webhook_complete_payload(self):
        """Test creating PullRequestPayload from complete webhook payload."""
        payload = {
            'action': 'synchronize',
            'installation': {'id': '12345'},
            'repository': {
                'full_name': 'owner/repo',
                'default_branch': 'main',
                'clone_url': 'https://github.com/owner/repo.git'
            },
            'pull_request': {
                'number': 42,
                'head': {
                    'ref': 'feature-branch',
                    'sha': 'abc123def456'
                },
                'state': 'open',
                'merged_at': None,
                'closed_at': None
            },
            'sender': {
                'login': 'testuser'
            },
            'number': 42
        }

        pr_data = PullRequestPayload.from_webhook(payload)

        assert pr_data.action == 'synchronize'
        assert pr_data.install_id == '12345'
        assert pr_data.repository == 'owner/repo'
        assert pr_data.branch == 'feature-branch'
        assert pr_data.commit_sha == 'abc123def456'
        assert pr_data.sender_login == 'testuser'
        assert pr_data.default_branch == 'main'
        assert pr_data.number == 42
        assert pr_data.state == 'open'
        assert pr_data.merged_at is None
        assert pr_data.closed_at is None
        assert pr_data.clone_url == 'https://github.com/owner/repo.git'

    def test_from_webhook_missing_fields(self):
        """Test creating PullRequestPayload with missing fields uses defaults."""
        payload = {}

        pr_data = PullRequestPayload.from_webhook(payload)

        assert pr_data.action == ''
        assert pr_data.install_id == ''
        assert pr_data.repository == ''
        assert pr_data.branch == ''
        assert pr_data.commit_sha == ''
        assert pr_data.sender_login == ''
        assert pr_data.default_branch == ''
        assert pr_data.number == 0
        assert pr_data.state == ''
        assert pr_data.merged_at is None
        assert pr_data.closed_at is None
        assert pr_data.clone_url == ''

    def test_from_webhook_partial_payload(self):
        """Test creating PullRequestPayload with partial payload."""
        payload = {
            'action': 'opened',
            'repository': {'full_name': 'owner/repo'},
            'number': 1
        }

        pr_data = PullRequestPayload.from_webhook(payload)

        assert pr_data.action == 'opened'
        assert pr_data.repository == 'owner/repo'
        assert pr_data.number == 1
        # Other fields should have defaults
        assert pr_data.branch == ''
        assert pr_data.commit_sha == ''

    def test_is_valid_for_processing_valid_pr(self):
        """Test validation passes for open, unmerged, unclosed PR."""
        payload = {
            'pull_request': {
                'state': 'open',
                'merged_at': None,
                'closed_at': None
            },
            'number': 1
        }

        pr_data = PullRequestPayload.from_webhook(payload)
        assert pr_data.is_valid_for_processing() is True

    def test_is_valid_for_processing_closed_pr(self):
        """Test validation fails for closed PR."""
        payload = {
            'pull_request': {
                'state': 'closed',
                'merged_at': None,
                'closed_at': '2025-12-25T10:00:00Z'
            },
            'number': 1
        }

        pr_data = PullRequestPayload.from_webhook(payload)
        assert pr_data.is_valid_for_processing() is False

    def test_is_valid_for_processing_merged_pr(self):
        """Test validation fails for merged PR."""
        payload = {
            'pull_request': {
                'state': 'closed',
                'merged_at': '2025-12-25T10:00:00Z',
                'closed_at': '2025-12-25T10:00:00Z'
            },
            'number': 1
        }

        pr_data = PullRequestPayload.from_webhook(payload)
        assert pr_data.is_valid_for_processing() is False

    def test_is_valid_for_processing_merged_but_state_open(self):
        """Test validation fails even if state is open but merged_at is set."""
        payload = {
            'pull_request': {
                'state': 'open',
                'merged_at': '2025-12-25T10:00:00Z',
                'closed_at': None
            },
            'number': 1
        }

        pr_data = PullRequestPayload.from_webhook(payload)
        assert pr_data.is_valid_for_processing() is False

    def test_is_valid_for_processing_closed_but_not_merged(self):
        """Test validation fails for closed but unmerged PR."""
        payload = {
            'pull_request': {
                'state': 'closed',
                'merged_at': None,
                'closed_at': '2025-12-25T10:00:00Z'
            },
            'number': 1
        }

        pr_data = PullRequestPayload.from_webhook(payload)
        assert pr_data.is_valid_for_processing() is False

    def test_nested_field_extraction(self):
        """Test proper extraction of nested fields."""
        payload = {
            'installation': {'id': 'nested_id'},
            'repository': {
                'full_name': 'owner/nested-repo',
                'default_branch': 'develop',
                'clone_url': 'https://github.com/owner/nested-repo.git'
            },
            'pull_request': {
                'head': {
                    'ref': 'feature/nested',
                    'sha': 'nested123'
                },
                'state': 'open',
                'merged_at': None,
                'closed_at': None
            },
            'sender': {'login': 'nested-user'}
        }

        pr_data = PullRequestPayload.from_webhook(payload)

        assert pr_data.install_id == 'nested_id'
        assert pr_data.repository == 'owner/nested-repo'
        assert pr_data.default_branch == 'develop'
        assert pr_data.branch == 'feature/nested'
        assert pr_data.commit_sha == 'nested123'
        assert pr_data.sender_login == 'nested-user'
        assert pr_data.clone_url == 'https://github.com/owner/nested-repo.git'

    def test_all_validation_conditions(self):
        """Test all three validation conditions must be met."""
        # Valid: all conditions met
        valid_payload = {
            'pull_request': {
                'state': 'open',
                'merged_at': None,
                'closed_at': None
            }
        }
        assert PullRequestPayload.from_webhook(valid_payload).is_valid_for_processing()

        # Invalid: wrong state
        invalid_state = {
            'pull_request': {
                'state': 'closed',
                'merged_at': None,
                'closed_at': None
            }
        }
        assert not PullRequestPayload.from_webhook(invalid_state).is_valid_for_processing()

        # Invalid: has merged_at
        invalid_merged = {
            'pull_request': {
                'state': 'open',
                'merged_at': '2025-12-25T10:00:00Z',
                'closed_at': None
            }
        }
        assert not PullRequestPayload.from_webhook(invalid_merged).is_valid_for_processing()

        # Invalid: has closed_at
        invalid_closed = {
            'pull_request': {
                'state': 'open',
                'merged_at': None,
                'closed_at': '2025-12-25T10:00:00Z'
            }
        }
        assert not PullRequestPayload.from_webhook(invalid_closed).is_valid_for_processing()
