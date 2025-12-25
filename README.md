# github-app-python

- [Create Github App](https://docs.github.com/en/apps/creating-github-apps)
- [Smee start channel](https://smee.io/8pLy0kP1cyDzDT)
- [Docker.py](https://github.com/docker/docker-py)
- [Smee.io](https://smee.io/)

## Commands

### Python

```sh
pipenv shell
pipenv lock
pipenv sync
pip freeze
pip install --no-cache-dir -r requirements.txt
pip freeze > requirements.txt
pipenv --venv
```

## Quick Start

1. Create a new Smee channel
  - Open https://smee.io in your browser.​
  - Click Start a new channel.
  - Copy the Webhook Proxy URL at the top (for example, https://smee.io/abc123...).
  - This URL will be used as the webhook URL for your GitHub App so Smee can receive events.
  - Update `.envrc` with this channel
2. Register a GitHub App using the Smee URL
   - On GitHub, go to: `Settings → Developer settings → GitHub Apps → New GitHub App`.
   - Fill in the required fields (name, homepage URL, etc.)
   - Webhook URL -> our smee.io url `https://smee.io/abc123....`
   - Webhook secret -> `uuid`
3. Create a private key
   - Flatten ssh key with `cat <KEY_PATH> | base64`
4. Install Github App in the Github location of you choice
5. Build and run
   - `mk docker-compose-up`

## Webhook Handler: `handle_pr`

The `handle_pr` method in `src/app.py` is the main webhook handler that processes pull request synchronize events.

### Trigger Event

- **Event**: `pull_request.synchronize`
- **When**: Triggered when new commits are pushed to an existing pull request

### Functionality

1. **Payload Parsing**
   - Extracts structured data from the GitHub webhook payload using the `PullRequestPayload` model
   - Captured fields:
     - `action`: Event action type (e.g., "synchronize")
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

2. **PR Validation**
   - Validates the PR is in a valid state for processing via `is_valid_for_processing()`
   - Requirements:
     - State must be "open"
     - Not merged (`merged_at` is None)
     - Not closed (`closed_at` is None)
   - Logs warning and exits early if validation fails

3. **GitHub Comment**
   - Posts an automated bot comment to the PR
   - Comment includes:
     - Bot indicator (🤖)
     - UTC timestamp
     - Message template from `src/constants.py`

4. **Repository Cloning**
   - Clones the repository to `/tmp/{repo}-{pr_number}`
   - Uses GitHub App installation token for authentication
   - Automatically checks out the PR branch
   - Enables code analysis and processing in subsequent steps

### Data Model

See `src/model.py` for the `PullRequestPayload` dataclass structure.

### Configuration

Message templates are stored in `src/constants.py` for easy customization.

## Resources

- [Fastapi](https://github.com/fastapi/fastapi)
- [Fastapi template](https://github.com/fastapi/full-stack-fastapi-template)
- [Fastapi Github](https://pypi.org/project/fastapi-githubapp/)
- [Probot: smee](https://github.com/probot/smee-client)
- [Fastapi: medium](https://hasansajedi.medium.com/fastapi-and-github-actions-67d86c1e6c5f)
- [Github Api](https://pypi.org/project/ghapi/)
- [Github Python](https://www.geeksforgeeks.org/python/automating-some-git-commands-with-python/)
- [Github Python:git repo](https://github.com/gitpython-developers/GitPython)
- [Github PyDriller](https://github.com/ishepard/pydriller)

### Examples

- [Fastapi-githubapp example](https://github.com/primetheus/fastapi-githubapp/blob/main/samples/01-basic-webhook/app.py)
