# Hybrid Approach: GitHub App + workflow_dispatch

This document describes a hybrid architecture that combines a lightweight GitHub App with GitHub Actions via `workflow_dispatch` to eliminate most operational overhead while maintaining centralized control.

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                        YOUR INFRASTRUCTURE                       │
│  ┌─────────────┐                                                │
│  │  GitHub App │  (lightweight - just triggers workflows)       │
│  │     API     │                                                │
│  └──────┬──────┘                                                │
└─────────┼───────────────────────────────────────────────────────┘
          │
          │ 1. Receives webhook (PR opened)
          │ 2. Calls workflow_dispatch API
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     GITHUB'S INFRASTRUCTURE                      │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Central Repo: security-team/shared-workflows           │    │
│  │                                                         │    │
│  │  .github/workflows/                                     │    │
│  │    ├── kics-scan.yml      (workflow_dispatch trigger)   │    │
│  │    └── blackduck-scan.yml (workflow_dispatch trigger)   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           │                                      │
│                           ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  GitHub-hosted Runners (or self-hosted)                 │    │
│  │  - Runs KICS scan on target repo                        │    │
│  │  - Posts PR comment                                     │    │
│  │  - Updates check status                                 │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## The API Call

```bash
# Your GitHub App triggers a workflow in the central repo
curl -X POST \
  -H "Authorization: Bearer $GITHUB_APP_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/security-team/shared-workflows/actions/workflows/kics-scan.yml/dispatches \
  -d '{
    "ref": "main",
    "inputs": {
      "target_repo": "org/some-repo",
      "pr_number": "123",
      "branch": "feature-xyz",
      "callback_url": "https://your-api/callback"
    }
  }'
```

## Central Workflow File

```yaml
# security-team/shared-workflows/.github/workflows/kics-scan.yml
name: KICS Security Scan

on:
  workflow_dispatch:
    inputs:
      target_repo:
        description: 'Repository to scan (owner/repo)'
        required: true
      pr_number:
        description: 'PR number to comment on'
        required: true
      branch:
        description: 'Branch to scan'
        required: true
      callback_url:
        description: 'Callback URL for completion notification'
        required: false

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout target repo
        uses: actions/checkout@v4
        with:
          repository: ${{ inputs.target_repo }}
          ref: ${{ inputs.branch }}
          token: ${{ secrets.REPO_ACCESS_TOKEN }}

      - name: Run KICS scan
        uses: checkmarx/kics-github-action@v2
        with:
          path: '.'
          output_path: 'results'

      - name: Post PR comment
        uses: actions/github-script@v7
        with:
          github-token: ${{ secrets.REPO_ACCESS_TOKEN }}
          script: |
            const [owner, repo] = '${{ inputs.target_repo }}'.split('/');
            await github.rest.issues.createComment({
              owner,
              repo,
              issue_number: ${{ inputs.pr_number }},
              body: '## KICS Scan Results\n...'
            });

      - name: Send callback (optional)
        if: inputs.callback_url != ''
        run: |
          curl -X POST "${{ inputs.callback_url }}" \
            -H "Content-Type: application/json" \
            -d '{"status": "completed", "pr": "${{ inputs.pr_number }}"}'
```

## Code Changes

### Before (Custom Workers)

```python
# API receives webhook → pushes to Redis → worker processes → posts comment
```

### After (workflow_dispatch)

```python
# api/app.py
@app.post("/webhook")
async def webhook(request: Request):
    payload = await request.json()

    if payload.get("action") == "opened":
        repo = payload["repository"]["full_name"]
        pr_number = payload["pull_request"]["number"]
        branch = payload["pull_request"]["head"]["ref"]

        # Trigger workflow instead of queuing to Redis
        trigger_workflow(
            workflow="kics-scan.yml",
            inputs={
                "target_repo": repo,
                "pr_number": str(pr_number),
                "branch": branch
            }
        )

    return {"status": "triggered"}


def trigger_workflow(workflow: str, inputs: dict):
    token = get_github_app_token()
    requests.post(
        f"https://api.github.com/repos/security-team/shared-workflows/actions/workflows/{workflow}/dispatches",
        headers={"Authorization": f"Bearer {token}"},
        json={"ref": "main", "inputs": inputs}
    )
```

## What You Eliminate

| Component | Status |
|-----------|--------|
| Redis | **Gone** |
| Worker containers | **Gone** |
| Consumer groups | **Gone** |
| Message acknowledgment | **Gone** |
| Worker scaling | **GitHub's problem** |
| Runner maintenance | **GitHub's problem** |
| Retry logic | **Built into Actions** |

## What You Keep

| Component | Purpose |
|-----------|---------|
| GitHub App | Receive webhooks, trigger workflows |
| Lightweight API | Route webhooks, call workflow_dispatch |
| Central workflow repo | Security team owns and updates |

## Cost Comparison

```
Custom Solution:
  Infrastructure:  $400-1000/month
  Engineer time:   10-20% FTE
  On-call:         Yes

Hybrid (workflow_dispatch):
  Infrastructure:  ~$20/month (tiny API container)
  GitHub Actions:  Free tier = 2,000 mins/month
                   Or: $0.008/min (Linux runner)
  Engineer time:   <5% FTE
  On-call:         Minimal (just the API)
```

## Limitations

| Limitation | Details |
|------------|---------|
| Workflow must exist in a repo | But you control that repo |
| GitHub Actions minutes | Cost at high scale, but predictable |
| 6-hour job limit | Fine for most scans |
| Rate limits | 1,000 workflow_dispatch/hour per repo |
| Cross-org complexity | Need app installed + token permissions |

## Benefits Summary

1. **Zero repo changes** - Target repos don't need any workflow files
2. **Centralized control** - Security team owns the workflow definitions
3. **GitHub manages scaling** - No worker infrastructure to manage
4. **Native PR integration** - Check runs, annotations, comments built-in
5. **Minimal operational overhead** - Just a lightweight API to maintain
6. **Audit trail** - GitHub Actions logs everything automatically
