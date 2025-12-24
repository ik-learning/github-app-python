"""Unit tests for pull request event handlers."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_pr_created_success(pr_opened_payload):
    """Test that handle_pr_created processes PR opened events correctly."""
    # Import the handler
    from src.app import handle_pr_created

    # Call the handler
    result = await handle_pr_created(pr_opened_payload)

    # Assertions
    assert result["status"] == "processed"
    assert result["event"] == "pull_request.opened"
    assert result["pr_number"] == 42
    assert "message" in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_pr_created_extracts_correct_data(pr_opened_payload):
    """Test that handler extracts correct data from payload."""
    from src.app import handle_pr_created

    # Mock logger to capture log calls
    with patch('src.app.logging.getLogger') as mock_logger:
        mock_log_instance = MagicMock()
        mock_logger.return_value = mock_log_instance

        result = await handle_pr_created(pr_opened_payload)

        # Verify logging was called
        assert mock_log_instance.info.called

        # Verify the call contains expected data
        log_calls = [str(call) for call in mock_log_instance.info.call_args_list]
        assert any("42" in str(call) for call in log_calls)  # PR number
        assert any("Add awesome new feature" in str(call) for call in log_calls)  # Title
        assert any("octocat" in str(call) for call in log_calls)  # Author


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_pr_created_with_missing_fields():
    """Test handler with minimal/missing payload fields."""
    from src.app import handle_pr_created

    minimal_payload = {
        "action": "opened",
        "pull_request": {
            "number": 1,
            "user": {}
        },
        "repository": {}
    }

    result = await handle_pr_created(minimal_payload)

    # Should still process without errors
    assert result["status"] == "processed"
    assert result["pr_number"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_pr_created_returns_dict():
    """Test that handler returns a dictionary."""
    from src.app import handle_pr_created

    payload = {
        "pull_request": {"number": 999, "user": {}},
        "repository": {}
    }

    result = await handle_pr_created(payload)

    assert isinstance(result, dict)
    assert "status" in result
    assert "pr_number" in result
