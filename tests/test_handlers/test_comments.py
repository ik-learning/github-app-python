"""Unit tests for comment event handlers."""
import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_pr_comment_added_success(issue_comment_created_payload):
    """Test that handle_pr_comment_added processes comments correctly."""
    from trash.app import handle_pr_comment_added

    result = await handle_pr_comment_added(issue_comment_created_payload)

    assert result["status"] == "processed"
    assert result["event"] == "comment.created"
    assert result["pr_number"] == 42
    assert result["comment_type"] == "comment"
    assert result["author"] == "reviewer"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_pr_comment_extracts_comment_body(issue_comment_created_payload):
    """Test that handler extracts comment body correctly."""
    from trash.app import handle_pr_comment_added

    with patch('src.app.logging.getLogger') as mock_logger:
        mock_log_instance = MagicMock()
        mock_logger.return_value = mock_log_instance

        await handle_pr_comment_added(issue_comment_created_payload)

        # Verify comment body is logged
        log_calls = [str(call) for call in mock_log_instance.info.call_args_list]
        assert any("This looks great" in str(call) for call in log_calls)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_pr_comment_with_slash_command():
    """Test handler with a slash command in comment."""
    from trash.app import handle_pr_comment_added

    payload = {
        "comment": {
            "body": "/approve",
            "user": {"login": "reviewer"},
            "html_url": "https://github.com/owner/repo/pull/1#comment"
        },
        "issue": {
            "number": 1,
            "pull_request": {"url": "https://api.github.com/repos/owner/repo/pulls/1"}
        }
    }

    result = await handle_pr_comment_added(payload)

    # Currently just logs, but structure should be correct
    assert result["status"] == "processed"
    assert result["pr_number"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_pr_review_comment_success(pr_review_comment_payload):
    """Test that handle_pr_review_comment processes review comments correctly."""
    from trash.app import handle_pr_review_comment

    result = await handle_pr_review_comment(pr_review_comment_payload)

    assert result["status"] == "processed"
    assert result["event"] == "pull_request_review_comment.created"
    assert result["pr_number"] == 42
    assert result["file"] == "src/app.py"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_pr_review_comment_logs_file_path(pr_review_comment_payload):
    """Test that review comment handler logs the file path."""
    from trash.app import handle_pr_review_comment

    with patch('src.app.logging.getLogger') as mock_logger:
        mock_log_instance = MagicMock()
        mock_logger.return_value = mock_log_instance

        await handle_pr_review_comment(pr_review_comment_payload)

        # Verify file path is logged
        log_calls = [str(call) for call in mock_log_instance.info.call_args_list]
        assert any("src/app.py" in str(call) for call in log_calls)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_comment_handler_with_minimal_payload():
    """Test comment handler with minimal payload."""
    from trash.app import handle_pr_comment_added

    minimal_payload = {
        "comment": {"body": "test", "user": {"login": "user"}},
        "issue": {"number": 1}
    }

    result = await handle_pr_comment_added(minimal_payload)

    assert result["status"] == "processed"
