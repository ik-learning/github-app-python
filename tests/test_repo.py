"""Tests for repo.py"""

import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from repo import RepositoryManager
from model import PullRequestPayload


class TestRepositoryManager:
    """Tests for RepositoryManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock PR data
        self.pr_data = Mock()
        self.pr_data.repository = 'owner/test-repo'
        self.pr_data.number = 42
        self.pr_data.commit_sha = 'abc123def456'
        self.pr_data.branch = 'feature-branch'
        self.pr_data.clone_url = 'https://github.com/owner/test-repo.git'

        self.token = 'test_token_123'

    def test_initialization(self):
        """Test RepositoryManager initialization."""
        manager = RepositoryManager(self.pr_data, self.token)

        assert manager.pr_data == self.pr_data
        assert manager.token == self.token
        assert manager.clone_dir is None
        assert manager._repo_obj is None

    @patch('repo.Repo')
    def test_setup_clones_and_checkouts(self, mock_repo_class):
        """Test setup method clones repository and checks out branch."""
        mock_repo = MagicMock()
        mock_repo_class.clone_from.return_value = mock_repo

        manager = RepositoryManager(self.pr_data, self.token)
        clone_dir = manager.setup()

        # Verify clone directory format
        assert clone_dir == f"/tmp/test-repo-42-abc123d"
        assert manager.clone_dir == clone_dir

        # Verify clone_from was called with correct arguments
        expected_url = 'https://x-access-token:test_token_123@github.com/owner/test-repo.git'
        mock_repo_class.clone_from.assert_called_once_with(expected_url, clone_dir)

        # Verify checkout was called
        mock_repo.git.checkout.assert_called_once_with('feature-branch')

    @patch('repo.Repo')
    def test_setup_constructs_authenticated_url(self, mock_repo_class):
        """Test setup constructs correct authenticated URL."""
        manager = RepositoryManager(self.pr_data, self.token)
        manager.setup()

        # Get the URL that was passed to clone_from
        call_args = mock_repo_class.clone_from.call_args
        clone_url = call_args[0][0]

        assert clone_url.startswith('https://x-access-token:')
        assert 'test_token_123@github.com' in clone_url
        assert clone_url.endswith('owner/test-repo.git')

    @patch('repo.Repo')
    def test_setup_short_sha_format(self, mock_repo_class):
        """Test setup uses first 7 characters of commit SHA."""
        self.pr_data.commit_sha = 'abcdefghijklmnop'

        manager = RepositoryManager(self.pr_data, self.token)
        clone_dir = manager.setup()

        assert 'abcdefg' in clone_dir
        assert 'abcdefgh' not in clone_dir

    @patch('repo.shutil.rmtree')
    @patch('repo.os.path.exists')
    def test_cleanup_removes_directory(self, mock_exists, mock_rmtree):
        """Test cleanup removes clone directory."""
        mock_exists.return_value = True

        manager = RepositoryManager(self.pr_data, self.token)
        manager.clone_dir = '/tmp/test-repo-42-abc123d'

        manager.cleanup()

        mock_exists.assert_called_once_with('/tmp/test-repo-42-abc123d')
        mock_rmtree.assert_called_once_with('/tmp/test-repo-42-abc123d')

    @patch('repo.shutil.rmtree')
    @patch('repo.os.path.exists')
    def test_cleanup_handles_nonexistent_directory(self, mock_exists, mock_rmtree):
        """Test cleanup handles case when directory doesn't exist."""
        mock_exists.return_value = False

        manager = RepositoryManager(self.pr_data, self.token)
        manager.clone_dir = '/tmp/nonexistent'

        # Should not raise error
        manager.cleanup()

        mock_exists.assert_called_once()
        mock_rmtree.assert_not_called()

    @patch('repo.shutil.rmtree')
    @patch('repo.os.path.exists')
    def test_cleanup_handles_none_clone_dir(self, mock_exists, mock_rmtree):
        """Test cleanup handles case when clone_dir is None."""
        manager = RepositoryManager(self.pr_data, self.token)
        manager.clone_dir = None

        # Should not raise error
        manager.cleanup()

        mock_exists.assert_not_called()
        mock_rmtree.assert_not_called()

    def test_get_clone_dir_returns_path(self):
        """Test get_clone_dir returns clone directory path."""
        manager = RepositoryManager(self.pr_data, self.token)
        manager.clone_dir = '/tmp/test-dir'

        assert manager.get_clone_dir() == '/tmp/test-dir'

    def test_get_clone_dir_returns_none_before_setup(self):
        """Test get_clone_dir returns None before setup is called."""
        manager = RepositoryManager(self.pr_data, self.token)

        assert manager.get_clone_dir() is None

    @patch('repo.BOT_COMMENT_TEMPLATE', '🤖 {timestamp} {clone_dir} {branch} {file_count} {dir_count}')
    def test_post_comment_formats_correctly(self):
        """Test post_comment formats comment body correctly."""
        mock_client = Mock()

        manager = RepositoryManager(self.pr_data, self.token)
        manager.clone_dir = '/tmp/test-repo-42-abc123d'

        repo_stats = {'file_count': 10, 'dir_count': 3}

        manager.post_comment(mock_client, repo_stats)

        # Verify create_comment was called
        mock_client.issues.create_comment.assert_called_once()

        # Get the call arguments
        call_args = mock_client.issues.create_comment.call_args
        kwargs = call_args.kwargs

        assert kwargs['owner'] == 'owner'
        assert kwargs['repo'] == 'test-repo'
        assert kwargs['issue_number'] == 42

        # Verify body contains expected values
        body = kwargs['body']
        assert '10' in body  # file_count
        assert '3' in body   # dir_count
        assert '/tmp/test-repo-42-abc123d' in body  # clone_dir
        assert 'feature-branch' in body  # branch

    def test_post_comment_splits_repository_correctly(self):
        """Test post_comment correctly splits owner/repo."""
        mock_client = Mock()
        self.pr_data.repository = 'test-owner/test-repo'

        manager = RepositoryManager(self.pr_data, self.token)
        manager.clone_dir = '/tmp/test'

        manager.post_comment(mock_client, {'file_count': 1, 'dir_count': 1})

        call_kwargs = mock_client.issues.create_comment.call_args.kwargs
        assert call_kwargs['owner'] == 'test-owner'
        assert call_kwargs['repo'] == 'test-repo'

    def test_post_comment_uses_pr_number(self):
        """Test post_comment uses correct PR number."""
        mock_client = Mock()
        self.pr_data.number = 99

        manager = RepositoryManager(self.pr_data, self.token)
        manager.clone_dir = '/tmp/test'

        manager.post_comment(mock_client, {'file_count': 1, 'dir_count': 1})

        call_kwargs = mock_client.issues.create_comment.call_args.kwargs
        assert call_kwargs['issue_number'] == 99

    @patch('repo.Repo')
    @patch('repo.shutil.rmtree')
    @patch('repo.os.path.exists')
    def test_full_workflow(self, mock_exists, mock_rmtree, mock_repo_class):
        """Test complete workflow: setup -> post_comment -> cleanup."""
        mock_exists.return_value = True
        mock_repo = MagicMock()
        mock_repo_class.clone_from.return_value = mock_repo
        mock_client = Mock()

        manager = RepositoryManager(self.pr_data, self.token)

        # Setup
        clone_dir = manager.setup()
        assert clone_dir is not None

        # Post comment
        manager.post_comment(mock_client, {'file_count': 5, 'dir_count': 2})
        mock_client.issues.create_comment.assert_called_once()

        # Cleanup
        manager.cleanup()
        mock_rmtree.assert_called_once_with(clone_dir)

    @patch('repo.Repo')
    def test_setup_with_different_tokens(self, mock_repo_class):
        """Test setup works with different token formats."""
        tokens = [
            'ghp_1234567890',
            'ghs_abcdefghij',
            'simple_token',
            'token-with-dashes'
        ]

        for token in tokens:
            manager = RepositoryManager(self.pr_data, token)
            manager.setup()

            call_url = mock_repo_class.clone_from.call_args[0][0]
            assert f'x-access-token:{token}@' in call_url

    @patch('repo.Repo')
    def test_setup_preserves_repo_object(self, mock_repo_class):
        """Test setup stores repo object for potential future use."""
        mock_repo = MagicMock()
        mock_repo_class.clone_from.return_value = mock_repo

        manager = RepositoryManager(self.pr_data, self.token)
        manager.setup()

        assert manager._repo_obj is mock_repo

    def test_repository_name_in_clone_dir(self):
        """Test clone directory includes repository name."""
        self.pr_data.repository = 'myorg/myrepo'

        manager = RepositoryManager(self.pr_data, self.token)

        # We can't call setup without mocking, but we can test the logic
        repo_name = self.pr_data.repository.split('/')[1]
        short_sha = self.pr_data.commit_sha[:7]
        expected_dir = f"/tmp/{repo_name}-{self.pr_data.number}-{short_sha}"

        with patch('repo.Repo'):
            clone_dir = manager.setup()
            assert clone_dir == expected_dir

    @patch('repo.datetime')
    def test_post_comment_includes_timestamp(self, mock_datetime):
        """Test post_comment includes UTC timestamp."""
        mock_datetime.utcnow.return_value.strftime.return_value = '2025-12-25 10:30:00 UTC'
        mock_client = Mock()

        manager = RepositoryManager(self.pr_data, self.token)
        manager.clone_dir = '/tmp/test'

        manager.post_comment(mock_client, {'file_count': 1, 'dir_count': 1})

        call_kwargs = mock_client.issues.create_comment.call_args.kwargs
        assert '2025-12-25 10:30:00 UTC' in call_kwargs['body']
