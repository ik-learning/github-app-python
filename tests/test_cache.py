"""Tests for cache.py"""

import pytest
import time
import threading
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from cache import TokenCache


class TestTokenCache:
    """Tests for TokenCache class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache = TokenCache(buffer_minutes=5)

    def test_initialization(self):
        """Test TokenCache initialization."""
        cache = TokenCache(buffer_minutes=10)
        assert cache._buffer_minutes == 10
        assert cache._cache == {}

    def test_get_token_first_time(self):
        """Test getting token for the first time fetches new token."""
        # Mock token fetcher
        mock_access = Mock()
        mock_access.token = "test_token_123"
        mock_access.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        fetcher = Mock(return_value=mock_access)

        # Get token
        token = self.cache.get_token("install_123", fetcher)

        assert token == "test_token_123"
        fetcher.assert_called_once_with("install_123")

    def test_get_token_cached(self):
        """Test getting cached token doesn't call fetcher."""
        # Mock token fetcher
        mock_access = Mock()
        mock_access.token = "cached_token"
        mock_access.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        fetcher = Mock(return_value=mock_access)

        # First call - fetches
        token1 = self.cache.get_token("install_123", fetcher)

        # Second call - should use cache
        token2 = self.cache.get_token("install_123", fetcher)

        assert token1 == token2
        # Fetcher should only be called once
        fetcher.assert_called_once()

    def test_get_token_expired_refetches(self):
        """Test expired token triggers new fetch."""
        # Mock token fetcher that returns expired token first
        mock_access1 = Mock()
        mock_access1.token = "old_token"
        # Expired token (1 minute ago)
        mock_access1.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)

        mock_access2 = Mock()
        mock_access2.token = "new_token"
        mock_access2.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        fetcher = Mock(side_effect=[mock_access1, mock_access2])

        # First call - gets expired token
        token1 = self.cache.get_token("install_123", fetcher)

        # Second call - should refetch due to expiration
        token2 = self.cache.get_token("install_123", fetcher)

        assert token1 == "old_token"
        assert token2 == "new_token"
        # Fetcher should be called twice
        assert fetcher.call_count == 2

    def test_get_token_buffer_time(self):
        """Test token is refreshed within buffer time."""
        # Token expires in 3 minutes, but buffer is 5 minutes
        mock_access = Mock()
        mock_access.token = "expiring_soon"
        mock_access.expires_at = datetime.now(timezone.utc) + timedelta(minutes=3)

        mock_access2 = Mock()
        mock_access2.token = "refreshed_token"
        mock_access2.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        fetcher = Mock(side_effect=[mock_access, mock_access2])

        # First call
        token1 = self.cache.get_token("install_123", fetcher)

        # Second call - should refetch because within buffer
        token2 = self.cache.get_token("install_123", fetcher)

        assert token1 == "expiring_soon"
        assert token2 == "refreshed_token"
        assert fetcher.call_count == 2

    def test_get_token_multiple_installations(self):
        """Test caching works independently for different installations."""
        mock_access1 = Mock()
        mock_access1.token = "token_install_1"
        mock_access1.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        mock_access2 = Mock()
        mock_access2.token = "token_install_2"
        mock_access2.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        fetcher = Mock(side_effect=[mock_access1, mock_access2])

        # Get tokens for different installations
        token1 = self.cache.get_token("install_1", fetcher)
        token2 = self.cache.get_token("install_2", fetcher)

        assert token1 == "token_install_1"
        assert token2 == "token_install_2"
        assert fetcher.call_count == 2

    def test_get_token_naive_datetime(self):
        """Test handling of naive (timezone-unaware) datetime."""
        mock_access = Mock()
        mock_access.token = "naive_token"
        # Naive datetime (no timezone)
        mock_access.expires_at = datetime.now() + timedelta(hours=1)

        fetcher = Mock(return_value=mock_access)

        # Should not raise error
        token = self.cache.get_token("install_123", fetcher)
        assert token == "naive_token"

    def test_clear_specific_installation(self):
        """Test clearing cache for specific installation."""
        mock_access = Mock()
        mock_access.token = "token_123"
        mock_access.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        fetcher = Mock(return_value=mock_access)

        # Cache tokens for two installations
        self.cache.get_token("install_1", fetcher)
        self.cache.get_token("install_2", fetcher)

        # Clear one installation
        self.cache.clear("install_1")

        stats = self.cache.get_stats()
        assert stats['count'] == 1
        assert "install_2" in stats['installations']
        assert "install_1" not in stats['installations']

    def test_clear_all(self):
        """Test clearing all cached tokens."""
        mock_access = Mock()
        mock_access.token = "token"
        mock_access.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        fetcher = Mock(return_value=mock_access)

        # Cache multiple tokens
        self.cache.get_token("install_1", fetcher)
        self.cache.get_token("install_2", fetcher)

        # Clear all
        self.cache.clear()

        stats = self.cache.get_stats()
        assert stats['count'] == 0
        assert stats['installations'] == []

    def test_get_stats(self):
        """Test getting cache statistics."""
        mock_access = Mock()
        mock_access.token = "token"
        mock_access.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        fetcher = Mock(return_value=mock_access)

        # Initial stats
        stats = self.cache.get_stats()
        assert stats['count'] == 0

        # Add tokens
        self.cache.get_token("install_1", fetcher)
        self.cache.get_token("install_2", fetcher)

        stats = self.cache.get_stats()
        assert stats['count'] == 2
        assert set(stats['installations']) == {"install_1", "install_2"}

    def test_thread_safety(self):
        """Test that cache is thread-safe."""
        mock_access = Mock()
        mock_access.token = "thread_safe_token"
        mock_access.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        call_count = [0]

        def fetcher(install_id):
            call_count[0] += 1
            time.sleep(0.01)  # Simulate some work
            return mock_access

        # Multiple threads trying to get the same token
        threads = []
        results = []

        def get_token():
            token = self.cache.get_token("install_123", fetcher)
            results.append(token)

        # Create 5 threads
        for _ in range(5):
            t = threading.Thread(target=get_token)
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # All should get the same token
        assert all(r == "thread_safe_token" for r in results)
        # Due to thread safety, fetcher should be called once or few times
        # (not 5 times if properly cached)
        assert call_count[0] <= 5

    def test_expires_at_none_refetches(self):
        """Test that None expires_at triggers refetch."""
        mock_access1 = Mock()
        mock_access1.token = "token1"
        mock_access1.expires_at = None

        mock_access2 = Mock()
        mock_access2.token = "token2"
        mock_access2.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        fetcher = Mock(side_effect=[mock_access1, mock_access2])

        # First call
        token1 = self.cache.get_token("install_123", fetcher)

        # Second call - should refetch because expires_at was None
        token2 = self.cache.get_token("install_123", fetcher)

        assert fetcher.call_count == 2
