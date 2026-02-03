import os
import base64
import random
import logging
import requests

from model import StoragePayload
from scan import Scan, ScanResult
from git import GitHub
from comment import Comment

logger = logging.getLogger(__name__)

# Test mode: clone public vulnerable repo instead of target repo
TEST_MODE = os.getenv("TEST_MODE", "").lower() in ("true", "1", "yes")
TEST_REPOS = [
    {"owner": "Checkmarx", "name": "Goatlin", "branch": "master"},  # https://github.com/Checkmarx/Goatlin
    {"owner": "Checkmarx", "name": "kics-github-action-demo", "branch": "main"},  # https://github.com/Checkmarx/kics-github-action-demo
    {"owner": "bridgecrewio", "name": "terragoat", "branch": "master"},  # https://github.com/bridgecrewio/terragoat
    {"owner": "NeuraLegion", "name": "helmcharts", "branch": "main"},  # https://github.com/NeuraLegion/helmcharts
]


class Processor:
    """Orchestrates the scan workflow: clone, scan, report, cleanup."""

    def __init__(self, app_name: str, redis_client):
        self.app_name = app_name
        self.redis = redis_client
        self.comment = Comment(app_name)

    def process(self, msg):
        """
        Main processing entry point.
        1. Retrieve storage data from Redis
        2. Clone repository
        3. Run scan
        4. Post PR comment
        5. Create check run
        6. Send callback to coordinator
        7. Cleanup
        """
        # 1. Retrieve from Redis
        storage = self._retrieve_storage(msg.id)
        if not storage:
            self._send_callback(msg.callback_url, msg.id, "No storage data found")
            return

        # Initialize GitHub client
        github_token = self._get_github_token(storage.installation_id)
        github = GitHub(github_token, self.app_name)

        ctx = None
        try:
            # 2. Clone repository (use test repo if TEST_MODE enabled)
            if TEST_MODE:
                test_repo = random.choice(TEST_REPOS)
                logger.info(f"[{self.app_name}] TEST_MODE: scanning {test_repo['owner']}/{test_repo['name']}, posting to {storage.owner}/{storage.name}")
                ctx = github.clone(
                    owner=test_repo["owner"],
                    name=test_repo["name"],
                    branch=test_repo["branch"],
                    pr_id=storage.prId,
                    commit_sha=storage.commit_sha
                )
                # Override owner/name for posting to original repo
                ctx.owner = storage.owner
                ctx.name = storage.name
            else:
                ctx = github.clone(
                    owner=storage.owner,
                    name=storage.name,
                    branch=storage.branch,
                    pr_id=storage.prId,
                    commit_sha=storage.commit_sha
                )

            # 3. Run scan
            scanner = Scan(self.app_name)
            result = scanner.run(ctx.path)

            # 4. Post PR comment
            github.post_pr_comment(ctx, self.comment.pr_comment(result))

            # 5. Create check run with annotations
            github.create_check_run(
                ctx=ctx,
                name="KICS Security Scan",
                conclusion=self._determine_conclusion(result),
                title="KICS Security Scan Results",
                summary=self.comment.check_run_summary(result),
                annotations=self._build_annotations(result)
            )

            # 6. Send callback to coordinator
            if msg.callback_url:
                self._send_callback(msg.callback_url, msg.id, self.comment.callback_message(result))

        finally:
            # 7. Cleanup
            if ctx:
                github.cleanup(ctx)

    def _retrieve_storage(self, id: str) -> StoragePayload | None:
        """Retrieve storage data from Redis."""
        storage_data = self.redis.get(f"storage:{id}")

        if storage_data:
            storage = StoragePayload.from_json(storage_data)
            logger.info(f"[{self.app_name}] Fetched storage: name={storage.name}, owner={storage.owner}, branch={storage.branch}")
            return storage

        logger.warning(f"[{self.app_name}] No storage found for id: {id}")
        return None

    def _get_github_token(self, installation_id: int) -> str:
        """
        Get GitHub App installation access token.

        TODO: Implement GitHub App token generation
        """
        token = os.getenv("GITHUB_TOKEN", "")

        if not token and installation_id:
            logger.warning(f"[{self.app_name}] No GitHub token, installation_id={installation_id}")

        return token

    def _determine_conclusion(self, result: ScanResult) -> str:
        """Determine check run conclusion based on results."""
        if not result.success:
            return "failure"
        if result.severity_counters.get("CRITICAL", 0) > 0:
            return "failure"
        if result.severity_counters.get("HIGH", 0) > 0:
            return "neutral"
        return "success"

    def _build_annotations(self, result: ScanResult) -> list:
        """Build GitHub annotations from scan results."""
        severity_to_level = {
            "CRITICAL": "failure",
            "HIGH": "failure",
            "MEDIUM": "warning",
            "LOW": "warning",
            "INFO": "notice"
        }

        annotations = []
        for query in result.queries:
            severity = query.get("severity", "INFO")
            level = severity_to_level.get(severity, "notice")

            for file in query.get("files", []):
                annotations.append({
                    "path": file.get("file_name", ""),
                    "start_line": file.get("line", 1),
                    "end_line": file.get("line", 1),
                    "annotation_level": level,
                    "title": query.get("query_name", "Security Issue"),
                    "message": query.get("description", "No description available")
                })

        return annotations

    def _send_callback(self, callback_url: str, id: str, msg: str):
        """Send callback to coordinator."""
        if not callback_url:
            return

        payload = {
            "id": id,
            "msg_base64": base64.b64encode(msg.encode()).decode(),
            "app_name": self.app_name
        }
        try:
            response = requests.post(callback_url, json=payload, timeout=10)
            logger.info(f"[{self.app_name}] Callback sent: {response.status_code}")
        except requests.RequestException as e:
            logger.error(f"[{self.app_name}] Callback failed: {e}")
