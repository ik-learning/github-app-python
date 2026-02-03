import base64
import random
import time
import logging
import requests
from model import StoragePayload

logger = logging.getLogger(__name__)


class Processor:
    def __init__(self, app_name: str, redis_client):
        self.app_name = app_name
        self.redis = redis_client

    def process(self, msg):
        """
        Main processing entry point.
        1. Retrieve storage data from Redis
        2. Run scan
        3. Send callback to coordinator
        4. Push comment to pull request
        """
        # 1. Retrieve from Redis
        storage = self._retrieve_storage(msg.id)

        # 2. Run scan
        result = self._run_scan(storage)

        # 3. Send callback to coordinator
        if msg.callback_url:
            self._send_callback(msg.callback_url, msg.id, result)

        # 4. Push comment to pull request
        self._push_pr_comment(storage, result)

    def _retrieve_storage(self, id: str) -> StoragePayload | None:
        """Retrieve storage data from Redis."""
        storage_data = self.redis.get(f"storage:{id}")

        if storage_data:
            storage = StoragePayload.from_json(storage_data)
            logger.info(f"[{self.app_name}] Fetched storage: name={storage.name}, owner={storage.owner}, branch={storage.branch}")
            return storage

        logger.warning(f"[{self.app_name}] No storage found for id: {id}")
        return None

    def _run_scan(self, storage: StoragePayload | None) -> str:
        """
        Run Blackduck scan on the repository.

        TODO: Implement actual Blackduck scanning logic
        """
        if not storage:
            return "No storage data available for scan"

        logger.info(f"[{self.app_name}] Running Blackduck scan for {storage.owner}/{storage.name} branch={storage.branch}")

        # Placeholder - random wait 5-10 seconds
        wait_time = random.randint(5, 10)
        logger.info(f"[{self.app_name}] Processing... waiting {wait_time}s")
        time.sleep(wait_time)

        return f"Blackduck scan completed for {storage.owner}/{storage.name} on branch {storage.branch}"

    def _send_callback(self, callback_url: str, id: str, msg: str):
        """Send callback to coordinator."""
        payload = {
            "id": id,
            "msg_base64": base64.b64encode(msg.encode()).decode(),
            "app_name": self.app_name
        }
        try:
            response = requests.post(callback_url, json=payload, timeout=10)
            logger.info(f"[{self.app_name}] Callback sent to {callback_url}: {response.status_code}")
        except requests.RequestException as e:
            logger.error(f"[{self.app_name}] Callback failed: {e}")

    def _push_pr_comment(self, storage: StoragePayload | None, result: str):
        """
        Push comment to pull request.

        TODO: Implement GitHub PR comment:
        - Use GitHub API to post comment on PR
        - Include scan results summary
        """
        if not storage:
            logger.warning(f"[{self.app_name}] Cannot push PR comment: no storage data")
            return

        logger.info(f"[{self.app_name}] Pushing PR comment for {storage.owner}/{storage.name}")
        # TODO: Implement GitHub API call to post PR comment
