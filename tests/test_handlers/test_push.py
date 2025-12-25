"""Unit tests for push event handlers."""
import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_push_new_branch(load_fixture):
    """Test push event when creating a new branch."""
    from trash.app import handle_push

    payload = load_fixture("push_new_branch.json")
    result = await handle_push(payload)

    assert result["status"] == "processed"
    assert result["event"] == "push"
    assert result["event_type"] == "branch_created"
    assert result["branch"] == "first-pull-requst"
    assert result["created"] is True
    assert result["deleted"] is False
    assert result["forced"] is False
    assert result["commit_count"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_push_to_main(load_fixture):
    """Test regular push to main branch."""
    from trash.app import handle_push

    payload = load_fixture("push_to_main.json")
    result = await handle_push(payload)

    assert result["status"] == "processed"
    assert result["event"] == "push"
    assert result["event_type"] == "push"
    assert result["branch"] == "main"
    assert result["created"] is False
    assert result["deleted"] is False
    assert result["forced"] is False
    assert result["commit_count"] == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_push_force(load_fixture):
    """Test force push event."""
    from trash.app import handle_push

    payload = load_fixture("push_force.json")

    with patch('src.app.logging.getLogger') as mock_logger:
        mock_log_instance = MagicMock()
        mock_logger.return_value = mock_log_instance

        result = await handle_push(payload)

        assert result["status"] == "processed"
        assert result["event_type"] == "force_push"
        assert result["branch"] == "feature-branch"
        assert result["forced"] is True

        # Verify warning was logged for force push
        assert mock_log_instance.warning.called


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_push_extracts_branch_name(load_fixture):
    """Test that handler correctly extracts branch name from ref."""
    from trash.app import handle_push

    payload = load_fixture("push_to_main.json")
    result = await handle_push(payload)

    # ref is "refs/heads/main", should extract "main"
    assert result["branch"] == "main"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_push_logs_commit_details(load_fixture):
    """Test that push handler logs commit information."""
    from trash.app import handle_push

    payload = load_fixture("push_to_main.json")

    with patch('src.app.logging.getLogger') as mock_logger:
        mock_log_instance = MagicMock()
        mock_logger.return_value = mock_log_instance

        await handle_push(payload)

        # Verify commits were logged
        log_calls = [str(call) for call in mock_log_instance.info.call_args_list]
        # Should log commit messages
        assert any("Fix bug in authentication" in str(call) for call in log_calls)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_push_with_many_commits():
    """Test push with more than 3 commits (should truncate log)."""
    from trash.app import handle_push

    payload = {
        "ref": "refs/heads/main",
        "before": "abc123",
        "after": "def456",
        "created": False,
        "deleted": False,
        "forced": False,
        "commits": [
            {"id": f"commit{i}", "message": f"Commit {i}", "author": {"name": "Dev"}}
            for i in range(5)
        ],
        "repository": {"full_name": "owner/repo"},
        "pusher": {"name": "pusher"}
    }

    with patch('src.app.logging.getLogger') as mock_logger:
        mock_log_instance = MagicMock()
        mock_logger.return_value = mock_log_instance

        result = await handle_push(payload)

        assert result["commit_count"] == 5

        # Should log "and 2 more commit(s)"
        log_calls = [str(call) for call in mock_log_instance.info.call_args_list]
        assert any("and 2 more commit" in str(call) for call in log_calls)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_push_branch_deleted():
    """Test push event when deleting a branch."""
    from trash.app import handle_push

    payload = {
        "ref": "refs/heads/old-branch",
        "before": "abc123",
        "after": "0000000000000000000000000000000000000000",
        "created": False,
        "deleted": True,
        "forced": False,
        "commits": [],
        "repository": {"full_name": "owner/repo"},
        "pusher": {"name": "pusher"}
    }

    result = await handle_push(payload)

    assert result["status"] == "processed"
    assert result["event_type"] == "branch_deleted"
    assert result["branch"] == "old-branch"
    assert result["deleted"] is True
    assert result["commit_count"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_push_return_structure():
    """Test that push handler returns correct structure."""
    from trash.app import handle_push

    payload = {
        "ref": "refs/heads/test",
        "before": "abc",
        "after": "def",
        "created": False,
        "deleted": False,
        "forced": False,
        "commits": [],
        "repository": {"full_name": "owner/repo"},
        "pusher": {"name": "pusher"}
    }

    result = await handle_push(payload)

    # Verify all expected fields are present
    assert "status" in result
    assert "event" in result
    assert "event_type" in result
    assert "branch" in result
    assert "commit_count" in result
    assert "created" in result
    assert "deleted" in result
    assert "forced" in result
    assert "message" in result
