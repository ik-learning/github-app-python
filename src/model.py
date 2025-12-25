from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class PullRequestPayload:
    """Parse and store relevant fields from a GitHub PR webhook payload."""
    action: str
    repository: str
    branch: str
    commit_sha: str
    sender_login: str
    default_branch: str
    number: int
    state: str
    merged_at: Optional[str]
    closed_at: Optional[str]
    clone_url: str

    @classmethod
    def from_webhook(cls, payload: Dict[str, Any]) -> 'PullRequestPayload':
        """Create PullRequestPayload from GitHub webhook payload."""
        return cls(
            action=payload.get('action', ''),
            repository=payload.get('repository', {}).get('full_name', ''),
            branch=payload.get('pull_request', {}).get('head', {}).get('ref', ''),
            commit_sha=payload.get('pull_request', {}).get('head', {}).get('sha', ''),
            sender_login=payload.get('sender', {}).get('login', ''),
            default_branch=payload.get('repository', {}).get('default_branch', ''),
            number=payload.get('number', 0),
            state=payload.get('pull_request', {}).get('state', ''),
            merged_at=payload.get('pull_request', {}).get('merged_at'),
            closed_at=payload.get('pull_request', {}).get('closed_at'),
            clone_url=payload.get('repository', {}).get('clone_url', '')
        )

    def is_valid_for_processing(self) -> bool:
        """
        Validate that PR is in a valid state for processing.

        Returns True if:
        - state is "open"
        - merged_at is None
        - closed_at is None
        """
        return (
            self.state == 'open' and
            self.merged_at is None and
            self.closed_at is None
        )
