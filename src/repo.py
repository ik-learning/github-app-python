"""Repository management for GitHub App."""

import os
import shutil
import logging
from datetime import datetime
from git import Repo
from constants import BOT_COMMENT_TEMPLATE

logger = logging.getLogger(__name__)


class RepositoryManager:
    """Manages repository cloning, checkout, and cleanup operations."""

    def __init__(self, pr_data, token):
        """
        Initialize repository manager.

        Args:
            pr_data: PullRequestPayload object with PR information
            token: GitHub App installation access token
        """
        self.pr_data = pr_data
        self.token = token
        self.clone_dir = None
        self._repo_obj = None

    def setup(self):
        """
        Clone repository and checkout PR branch.

        Returns:
            str: Path to cloned repository directory

        Raises:
            GitCommandError: If clone or checkout fails
        """
        # Extract owner and repo from repository full name
        owner, repo = self.pr_data.repository.split('/')

        # Create unique clone directory with commit SHA
        short_sha = self.pr_data.commit_sha[:7]
        self.clone_dir = f"/tmp/{repo}-{self.pr_data.number}-{short_sha}"

        # Construct authenticated clone URL
        authenticated_url = self.pr_data.clone_url.replace(
            "https://",
            f"https://x-access-token:{self.token}@"
        )

        # Clone repository
        logger.info(f"Cloning repository to {self.clone_dir}")
        self._repo_obj = Repo.clone_from(authenticated_url, self.clone_dir)

        # Checkout PR branch
        logger.info(f"Checking out branch: {self.pr_data.branch}")
        self._repo_obj.git.checkout(self.pr_data.branch)

        logger.info(f"Repository setup complete: {self.clone_dir}")
        return self.clone_dir

    def cleanup(self):
        """
        Remove cloned repository directory.

        Deletes the entire clone directory and all its contents.
        Safe to call even if directory doesn't exist.
        """
        if self.clone_dir and os.path.exists(self.clone_dir):
            logger.debug(f"Cleaning up: removing {self.clone_dir}")
            shutil.rmtree(self.clone_dir)
            logger.debug(f"Successfully removed {self.clone_dir}")
        else:
            logger.debug("No clone directory to clean up")

    def get_clone_dir(self):
        """
        Get the clone directory path.

        Returns:
            str: Clone directory path or None if not set up
        """
        return self.clone_dir

    def post_comment(self, client, repo_stats):
        """
        Post a summary comment to the pull request.

        Args:
            client: GitHub API client
            repo_stats: Dictionary with 'file_count' and 'dir_count'
        """
        owner, repo = self.pr_data.repository.split('/')
        current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')

        comment_body = BOT_COMMENT_TEMPLATE.format(
            timestamp=current_time,
            clone_dir=self.clone_dir,
            branch=self.pr_data.branch,
            file_count=repo_stats['file_count'],
            dir_count=repo_stats['dir_count']
        )

        logger.info(f"Posting comment to PR #{self.pr_data.number}")
        client.issues.create_comment(
            owner=owner,
            repo=repo,
            issue_number=self.pr_data.number,
            body=comment_body
        )
        logger.info(f"Successfully posted comment to PR #{self.pr_data.number}")
