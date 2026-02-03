import os
import uuid
import shutil
import logging
from dataclasses import dataclass
from typing import Optional

import git
import requests

logger = logging.getLogger(__name__)


@dataclass
class RepoContext:
    """Context for a cloned repository."""
    path: str
    owner: str
    name: str
    branch: str
    pr_id: int
    commit_sha: str


class GitHub:
    """GitHub operations: clone, PR comments, check runs."""

    def __init__(self, token: str, app_name: str = "kics-worker"):
        self.token = token
        self.app_name = app_name
        self.base_url = "https://api.github.com"

    def clone(self, owner: str, name: str, branch: str, pr_id: int = 0, commit_sha: str = "") -> RepoContext:
        """
        Clone a repository and return context.
        Uses shallow clone (depth=1) for efficiency.
        """
        repo_dir = f"/tmp/scan-{owner}-{name}-{uuid.uuid4()}"
        clone_url = f"https://x-access-token:{self.token}@github.com/{owner}/{name}.git"

        logger.info(f"[{self.app_name}] Cloning {owner}/{name} branch={branch}")

        try:
            git.Repo.clone_from(
                clone_url,
                repo_dir,
                branch=branch,
                depth=1
            )
            logger.info(f"[{self.app_name}] Repository cloned to {repo_dir}")

            return RepoContext(
                path=repo_dir,
                owner=owner,
                name=name,
                branch=branch,
                pr_id=pr_id,
                commit_sha=commit_sha
            )
        except git.GitCommandError as e:
            raise RuntimeError(f"Git clone failed: {e}")

    def cleanup(self, ctx: RepoContext):
        """Remove cloned repository."""
        if ctx.path and os.path.exists(ctx.path):
            try:
                shutil.rmtree(ctx.path)
                logger.info(f"[{self.app_name}] Cleaned up {ctx.path}")
            except Exception as e:
                logger.warning(f"[{self.app_name}] Cleanup failed: {e}")

    def post_pr_comment(self, ctx: RepoContext, body: str):
        """Post a comment to a pull request."""
        if not ctx.pr_id:
            logger.warning(f"[{self.app_name}] No PR ID, skipping comment")
            return

        url = f"{self.base_url}/repos/{ctx.owner}/{ctx.name}/issues/{ctx.pr_id}/comments"

        try:
            response = requests.post(
                url,
                headers=self._headers(),
                json={"body": body},
                timeout=30
            )
            logger.info(f"[{self.app_name}] PR comment posted: {response.status_code}")
        except requests.RequestException as e:
            logger.error(f"[{self.app_name}] Failed to post PR comment: {e}")

    def create_check_run(
        self,
        ctx: RepoContext,
        name: str,
        conclusion: str,
        title: str,
        summary: str,
        annotations: Optional[list] = None
    ):
        """
        Create a GitHub check run with optional annotations.

        Args:
            ctx: Repository context with commit_sha
            name: Check run name
            conclusion: success, failure, neutral, cancelled, skipped, timed_out
            title: Output title
            summary: Output summary
            annotations: List of annotation dicts (path, start_line, end_line, annotation_level, title, message)
        """
        if not ctx.commit_sha:
            logger.warning(f"[{self.app_name}] No commit SHA, skipping check run")
            return

        url = f"{self.base_url}/repos/{ctx.owner}/{ctx.name}/check-runs"

        # GitHub limits annotations to 50 per request
        first_batch = (annotations or [])[:50]

        payload = {
            "name": name,
            "head_sha": ctx.commit_sha,
            "status": "completed",
            "conclusion": conclusion,
            "output": {
                "title": title,
                "summary": summary,
                "annotations": first_batch
            }
        }

        try:
            response = requests.post(
                url,
                headers=self._headers(),
                json=payload,
                timeout=30
            )
            logger.info(f"[{self.app_name}] Check run created: {response.status_code}")

            # Post remaining annotations in batches
            if annotations and len(annotations) > 50:
                check_run_id = response.json().get("id")
                if check_run_id:
                    self._post_remaining_annotations(ctx, check_run_id, title, annotations[50:])

        except requests.RequestException as e:
            logger.error(f"[{self.app_name}] Failed to create check run: {e}")

    def _post_remaining_annotations(self, ctx: RepoContext, check_run_id: int, title: str, annotations: list):
        """Post remaining annotations in batches of 50."""
        url = f"{self.base_url}/repos/{ctx.owner}/{ctx.name}/check-runs/{check_run_id}"

        for i in range(0, len(annotations), 50):
            batch = annotations[i:i + 50]
            try:
                requests.patch(
                    url,
                    headers=self._headers(),
                    json={
                        "output": {
                            "title": title,
                            "summary": "Additional annotations",
                            "annotations": batch
                        }
                    },
                    timeout=30
                )
            except requests.RequestException as e:
                logger.error(f"[{self.app_name}] Failed to post annotation batch: {e}")

    def _headers(self) -> dict:
        """Common headers for GitHub API requests."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
