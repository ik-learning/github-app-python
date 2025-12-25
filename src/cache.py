"""Token caching functionality for GitHub App."""

import threading
import logging
from datetime import datetime, timedelta, timezone
from utils import parse_datetime

logger = logging.getLogger(__name__)


class TokenCache:
    """Thread-safe cache for GitHub App installation tokens."""

    def __init__(self, buffer_minutes=5):
        """
        Initialize the token cache.

        Args:
            buffer_minutes: Minutes before expiration to refresh token (default: 5)
        """
        self._cache = {}
        self._lock = threading.Lock()
        self._buffer_minutes = buffer_minutes

    def get_token(self, installation_id, token_fetcher):
        """
        Get a cached token or fetch a new one if expired.

        Args:
            installation_id: GitHub App installation ID
            token_fetcher: Callable that takes installation_id and returns access token object

        Returns:
            str: Valid access token
        """
        with self._lock:
            # Check if we have a cached token
            if installation_id in self._cache:
                cached_data = self._cache[installation_id]
                # Check if token is still valid (with buffer)
                buffer_time = datetime.now(timezone.utc) + timedelta(minutes=self._buffer_minutes)
                expires_at = cached_data['expires_at']

                # Ensure both datetimes are comparable (make naive if expires_at is naive)
                if expires_at.tzinfo is None:
                    buffer_time = buffer_time.replace(tzinfo=None)

                if expires_at and expires_at > buffer_time:
                    logger.info(f"Using cached token for installation {installation_id}")
                    return cached_data['token']
                else:
                    logger.info(f"Cached token expired for installation {installation_id}")

            # Get new token using the provided fetcher
            logger.info(f"Fetching new token for installation {installation_id}")
            access = token_fetcher(installation_id)
            token = access.token

            # Parse expires_at to datetime if it's a string
            expires_at = parse_datetime(access.expires_at)

            # Cache the token
            self._cache[installation_id] = {
                'token': token,
                'expires_at': expires_at
            }

            logger.info(f"Token cached, expires at {expires_at}")
            return token

    def clear(self, installation_id=None):
        """
        Clear cached tokens.

        Args:
            installation_id: Specific installation ID to clear, or None to clear all
        """
        with self._lock:
            if installation_id:
                if installation_id in self._cache:
                    del self._cache[installation_id]
                    logger.info(f"Cleared cache for installation {installation_id}")
            else:
                self._cache.clear()
                logger.info("Cleared all cached tokens")

    def get_stats(self):
        """
        Get statistics about the token cache.

        Returns:
            dict: Cache statistics including count and installations
        """
        with self._lock:
            return {
                'count': len(self._cache),
                'installations': list(self._cache.keys())
            }
