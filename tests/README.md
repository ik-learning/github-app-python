# Tests

This directory contains all tests for the GitHub App.

## Structure

```
tests/
├── conftest.py                 # Pytest configuration and shared fixtures
├── fixtures/                   # JSON fixtures for webhook payloads
│   ├── pull_request_opened.json
│   ├── pull_request_closed.json
│   ├── pull_request_closed_merged.json
│   ├── issue_comment_created.json
│   └── pr_review_comment_created.json
├── test_handlers/              # Unit tests for event handlers
│   ├── test_pull_request.py
│   └── test_comments.py
└── test_app.py                 # Integration tests for FastAPI app
```

## Running Tests

### Install Dependencies

```bash
pipenv install --dev
```

### Run All Tests

```bash
make test
# or
pipenv run pytest
```

### Run with Verbose Output

```bash
make test-verbose
# or
pipenv run pytest -vv
```

### Run with Coverage Report

```bash
make test-coverage
# or
pipenv run pytest --cov=src --cov-report=term-missing --cov-report=html
```

This will generate:
- Terminal coverage report
- HTML coverage report in `htmlcov/` directory

### Run Specific Test Types

**Unit tests only:**
```bash
make test-unit
# or
pipenv run pytest -m unit
```

**Integration tests only:**
```bash
make test-integration
# or
pipenv run pytest -m integration
```

### Run Specific Test File

```bash
pipenv run pytest tests/test_app.py
```

### Run Specific Test Function

```bash
pipenv run pytest tests/test_app.py::test_health_check_endpoint
```

## Writing Tests

### Test Fixtures

Shared fixtures are defined in `conftest.py`:

- `fixtures_dir` - Path to fixtures directory
- `load_fixture(filename)` - Load JSON fixture by filename
- `pr_opened_payload` - Pull request opened event
- `pr_closed_payload` - Pull request closed event
- `pr_closed_merged_payload` - Pull request closed (merged) event
- `issue_comment_created_payload` - Issue comment created event
- `pr_review_comment_payload` - PR review comment created event

### Example Unit Test

```python
import pytest

@pytest.mark.unit
@pytest.mark.asyncio
async def test_handler(pr_opened_payload):
    from src.app import handle_pr_created

    result = await handle_pr_created(pr_opened_payload)

    assert result["status"] == "processed"
    assert result["pr_number"] == 42
```

### Example Integration Test

```python
import pytest
from fastapi.testclient import TestClient

@pytest.mark.integration
def test_endpoint(client):
    response = client.get("/status")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

## Test Markers

Tests are marked with these markers:

- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (slower, test multiple components)
- `@pytest.mark.slow` - Slow tests (can be skipped in CI)

## Coverage

Target coverage: >90%

View coverage report:
```bash
make test-coverage
open htmlcov/index.html
```

## Continuous Integration

Tests run automatically on:
- Every commit (if CI is configured)
- Before merging PRs
- On main branch

## Troubleshooting

### Import Errors

If you get import errors, make sure you're in the project root:
```bash
cd /path/to/github-app-python
pipenv run pytest
```

### Fixture Not Found

Make sure `conftest.py` is in the tests directory and fixtures are properly defined.

### Async Test Fails

Make sure you have `pytest-asyncio` installed and use `@pytest.mark.asyncio` decorator:
```bash
pipenv install --dev pytest-asyncio
```

### Environment Variable Errors

Tests mock environment variables. If you see errors about missing env vars, check that `mock_env_vars` fixture is being used in integration tests.
