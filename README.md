# github-app-python

A GitHub App that automatically processes pull request synchronize events, analyzes repository structure, and posts summary comments.

**Features:**
- 🤖 Automated PR processing on new commits
- 📊 Repository structure analysis (file/directory counting)
- 💾 Token caching for efficiency (5-minute buffer)
- 🧹 Automatic cleanup after processing
- ✅ Comprehensive test coverage
- 🔄 Background processing with ThreadPoolExecutor

## Table of Contents
- [Environment Variables](#environment-variables)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [GitHub App Permissions](#github-app-permissions)
- [Webhook Handler](#webhook-handler-handle_pr)
- [Testing](#testing)
- [Development Commands](#development-commands)
- [Troubleshooting](#troubleshooting)
- [Resources](#resources)

## Environment Variables

Required environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `GITHUB_APP_ID` | Your GitHub App ID | `123456` |
| `GITHUB_APP_PRIVATE_KEY` | Base64-encoded private key | `LS0tLS1CRUdJTi...` |
| `GITHUB_WEBHOOK_SECRET` | Webhook secret (use UUID) | `550e8400-e29b-41d4-a716-446655440000` |
| `PORT` | Server port (optional) | `8000` (default) |

### Encoding Private Key

```bash
cat path/to/private-key.pem | base64
```

## Quick Start

### 1. Create a new Smee channel
- Open [https://smee.io](https://smee.io) in your browser
- Click "Start a new channel"
- Copy the Webhook Proxy URL (e.g., `https://smee.io/abc123...`)
- Update `.envrc` with this channel URL

### 2. Register a GitHub App
- Go to: `Settings → Developer settings → GitHub Apps → New GitHub App`
- Fill in the required fields:
  - **Name**: Your app name
  - **Homepage URL**: Your repository URL
  - **Webhook URL**: Your Smee.io URL from step 1
  - **Webhook secret**: Generate a UUID for security (e.g., `550e8400-e29b-41d4-a716-446655440000`)

#### Configure Permissions
Set the following **Repository permissions**:

| Permission | Access | Purpose |
|------------|--------|---------|
| **Contents** | Read | Clone repository and analyze files |
| **Pull requests** | Read and write | Read PR data and post comments |
| **Metadata** | Read | Repository metadata (automatic) |

#### Subscribe to Events
Under "Subscribe to events", check:
- ✅ **Pull request**

This enables the app to receive `pull_request.synchronize` webhook events.

### 3. Create and configure private key
- In your GitHub App settings, generate a private key
- Download the `.pem` file
- Encode it to base64:
  ```bash
  cat path/to/private-key.pem | base64
  ```
- Add to your environment variables

### 4. Install GitHub App
- Install the app in your chosen repository or organization

### 5. Build and run
```bash
mk docker-compose-up
```

## Architecture

### Code Structure

```
src/
├── app.py          # Main FastAPI application and webhook handler
├── model.py        # Data models (PullRequestPayload)
├── cache.py        # Token caching (TokenCache class)
├── repo.py         # Repository operations (RepositoryManager class)
├── utils.py        # Utility functions
└── constants.py    # Configuration constants

tests/
├── test_app.py     # Application tests
├── test_cache.py   # Cache functionality tests
├── test_model.py   # Data model tests
├── test_repo.py    # Repository manager tests
└── test_utils.py   # Utility function tests
```

### Key Components

#### TokenCache (`src/cache.py`)
- Thread-safe token caching
- 5-minute expiration buffer
- Automatic token refresh
- Handles timezone-aware and naive datetimes

#### RepositoryManager (`src/repo.py`)
- Clone repository with authentication
- Checkout PR branch
- Post comments to PRs
- Automatic cleanup after processing

#### PullRequestPayload (`src/model.py`)
- Structured webhook payload parsing
- PR validation logic
- Extracts all relevant PR data

### Processing Flow

```
Webhook Event → Validate → Cache Token → Clone Repo → Analyze → Comment → Cleanup
     ↓              ↓           ↓            ↓           ↓         ↓         ↓
  handle_pr   is_valid()  get_token()   setup()    analyze()  post()   cleanup()
```

### Key Features

- **Token Caching**: Installation tokens cached with 5-minute buffer to reduce API calls
- **Background Processing**: Uses ThreadPoolExecutor for non-blocking webhook responses
- **Automatic Cleanup**: Repositories deleted after processing to save disk space
- **Repository Analysis**: Recursively counts files and directories (excluding .git)
- **Unique Clone Directories**: Format: `/tmp/{repo}-{pr_number}-{short_sha}`

## GitHub App Permissions

### Required Permissions

The app requires the following GitHub App permissions to function:

| Permission | Access Level | Why Required |
|------------|-------------|--------------|
| **Contents** | Read | • Clone repository<br>• Read files and directory structure<br>• Analyze repository contents |
| **Pull requests** | Read & Write | • Receive PR webhook events<br>• Read PR metadata (branch, SHA, state)<br>• Post comments on PRs |
| **Metadata** | Read | • Repository information<br>• Clone URLs<br>• Default branch info<br>*(Automatically included)* |

### Required Webhook Events

Subscribe to the following events in your GitHub App settings:

- ✅ **Pull request** - Receives `pull_request.synchronize` events

### Verification Steps

After configuring permissions:

**1. Verify Installation Token:**
```bash
# Check logs for successful token fetch
# Should see: "Fetching new token for installation {id}"
# Should see: "Token cached, expires at {timestamp}"
```

**2. Test Repository Access:**
```bash
# Push to a PR branch
# Should see in logs: "Cloning repository to /tmp/..."
# Should see: "Successfully cloned and checked out to branch {name}"
```

**3. Verify Comment Posting:**
- Check that bot comment appears on PR
- Comment should include file/directory counts
- Comment should have 🤖 bot indicator

### Common Permission Issues

| Error | Cause | Solution |
|-------|-------|----------|
| `403: Resource not accessible` | Insufficient permissions | Check app has required permissions enabled |
| `404: Not Found` | App not installed | Install app on repository |
| `Authentication failed` | Invalid token | Verify private key is correct |
| `Invalid signature` | Wrong webhook secret | Update `GITHUB_WEBHOOK_SECRET` to match app |

### Configuration Checklist

Before deploying, ensure:
- [ ] Repository permissions set: Contents (Read), Pull requests (Read & Write)
- [ ] Subscribed to "Pull request" events
- [ ] App installed on target repository/organization
- [ ] Webhook secret configured and matches environment variable
- [ ] Private key properly encoded and set in environment

## Webhook Handler: `handle_pr`

The `handle_pr` method in `src/app.py` is the main webhook handler that processes pull request synchronize events.

### Trigger Event

- **Event**: `pull_request.synchronize`
- **When**: Triggered when new commits are pushed to an existing pull request

### Functionality

#### 1. Payload Parsing
Extracts structured data from the GitHub webhook payload using the `PullRequestPayload` model.

**Captured fields:**
- `action`: Event action type (e.g., "synchronize")
- `install_id`: GitHub App installation ID
- `repository`: Full repository name (owner/repo)
- `branch`: PR branch name
- `commit_sha`: Latest commit SHA
- `sender_login`: GitHub username who triggered the event
- `default_branch`: Repository's default branch
- `number`: Pull request number
- `state`: PR state (open, closed)
- `merged_at`: Merge timestamp (None if not merged)
- `closed_at`: Close timestamp (None if not closed)
- `clone_url`: HTTPS clone URL for the repository

#### 2. PR Validation
Validates the PR is in a valid state for processing via `is_valid_for_processing()`.

**Requirements:**
- State must be "open"
- Not merged (`merged_at` is None)
- Not closed (`closed_at` is None)

Logs warning and exits early if validation fails.

#### 3. Token Management
- Retrieves cached installation token or fetches new one
- Tokens cached for efficiency (5-minute buffer before expiration)
- Automatic refresh when expired

#### 4. Repository Cloning
- Clones the repository to `/tmp/{repo}-{pr_number}-{short_sha}`
- Uses GitHub App installation token for authentication
- Automatically checks out the PR branch
- Unique directory per commit (uses first 7 chars of SHA)

#### 5. Repository Analysis
- Recursively analyzes repository structure
- Counts files and directories
- Excludes `.git` directory from analysis
- Logs complete directory tree structure

#### 6. GitHub Comment
Posts an automated bot comment to the PR with:
- 🤖 Bot indicator
- Clone directory location
- Branch name
- File count
- Directory count
- UTC timestamp

Comment template can be customized in `src/constants.py`.

#### 7. Cleanup
- Automatically deletes cloned repository after processing
- Ensures disk space is conserved
- Runs even if errors occur (finally block)

### Data Model

See `src/model.py` for the `PullRequestPayload` dataclass structure.

### Configuration

Message templates are stored in `src/constants.py` for easy customization.

## Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test Files

```bash
pytest tests/test_utils.py -v
pytest tests/test_cache.py -v
pytest tests/test_model.py -v
pytest tests/test_repo.py -v
```

### Run Without Coverage

If you don't have pytest-cov installed:

```bash
pytest tests/ -v --no-cov
```

### Run With Coverage

```bash
pytest tests/ --cov=src --cov-report=html
```

Then open `htmlcov/index.html` in your browser to view the coverage report.

### Test Coverage

- **test_utils.py**: 29 tests covering utility functions
- **test_cache.py**: 16 tests covering token caching
- **test_model.py**: 12 tests covering data models
- **test_repo.py**: 20 tests covering repository operations

## Development Commands

### Python Environment

```bash
# Activate virtual environment
pipenv shell

# Install dependencies
pipenv sync

# Lock dependencies
pipenv lock

# Freeze requirements
pip freeze > requirements.txt

# Install from requirements
pip install --no-cache-dir -r requirements.txt

# Show virtual environment path
pipenv --venv
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src

# Run specific test class
pytest tests/test_cache.py::TestTokenCache -v

# Run specific test
pytest tests/test_utils.py::TestDecodeBase64Key::test_decode_valid_base64_key -v
```

### Docker

```bash
# Build and run with docker-compose
mk docker-compose-up

# Stop containers
mk docker-compose-down

# View logs
docker-compose logs -f
```

## Troubleshooting

### Token Issues

**Problem**: `Failed to decode base64 key`
- **Solution**: Ensure private key is properly base64 encoded without newlines
- **Check**: Run `cat key.pem | base64 | tr -d '\n'`

**Problem**: Token expired errors
- **Solution**: Check token cache expiration (5-minute buffer)
- **Action**: Clear cache by restarting the application

### Clone Failures

**Problem**: `Authentication failed for repository`
- **Solution**: Verify GitHub App has repository access
- **Check**: Installation permissions - requires **Contents: Read**
- **Verify**: App is installed on the repository
- **See**: [GitHub App Permissions](#github-app-permissions) section

**Problem**: `403: Resource not accessible by integration`
- **Solution**: Missing required permissions
- **Check**: Repository permissions include Contents (Read) and Pull requests (Read & Write)
- **Fix**: Update permissions in GitHub App settings → Permissions & events

**Problem**: `Directory already exists`
- **Solution**: This shouldn't happen with unique SHA-based naming
- **Debug**: Check cleanup logic in `repo.py`

**Problem**: Cannot post comments to PR
- **Solution**: Missing Pull requests write permission
- **Check**: GitHub App has "Pull requests: Read and write" enabled
- **Verify**: App is installed with correct permissions

### Test Failures

**Problem**: `No module named 'pytest-cov'`
- **Solution**: Install pytest-cov: `pip install pytest-cov`
- **Alternative**: Run with `pytest --no-cov`

**Problem**: Tests pass locally but fail in CI
- **Solution**: Check environment variables are set
- **Verify**: Python version compatibility (3.14+)

### Webhook Issues

**Problem**: Webhook not triggering
- **Solution**: Check Smee.io channel is running
- **Verify**: Webhook secret matches in both GitHub and `.envrc`
- **Check**: GitHub App is installed and has correct permissions

**Problem**: `Invalid signature` errors
- **Solution**: Webhook secret mismatch
- **Fix**: Update `GITHUB_WEBHOOK_SECRET` to match GitHub App settings

## Resources

### Documentation
- [Create GitHub App](https://docs.github.com/en/apps/creating-github-apps)
- [Smee.io](https://smee.io/) - Webhook proxy for local development
- [How to get tokens](https://github.com/marketplace/actions/create-github-app-token#use-app-token-with-actionscheckout)

### Libraries
- [FastAPI](https://github.com/fastapi/fastapi)
- [FastAPI Template](https://github.com/fastapi/full-stack-fastapi-template)
- [FastAPI GitHubApp](https://pypi.org/project/fastapi-githubapp/)
- [GitPython](https://github.com/gitpython-developers/GitPython)
- [PyDriller](https://github.com/ishepard/pydriller)
- [Docker.py](https://github.com/docker/docker-py)

### Tutorials
- [FastAPI and GitHub Actions](https://hasansajedi.medium.com/fastapi-and-github-actions-67d86c1e6c5f)
- [Automating Git with Python](https://www.geeksforgeeks.org/python/automating-some-git-commands-with-python/)
- [GitHub API Python](https://pypi.org/project/ghapi/)

### Tools
- [Probot Smee](https://github.com/probot/smee-client) - Alternative Smee client

### Examples
- [FastAPI-GitHubApp Example](https://github.com/primetheus/fastapi-githubapp/blob/main/samples/01-basic-webhook/app.py)

## License

See LICENSE file for details.

## Contributing

Contributions are welcome! Please ensure:
- All tests pass: `pytest tests/ -v`
- Code follows existing style
- New features include tests
- Documentation is updated
