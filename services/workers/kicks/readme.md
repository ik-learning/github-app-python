# KICS Worker

Security scanning worker that runs [KICS](https://kics.io/) (Keeping Infrastructure as Code Secure) scans on repositories.

- https://docs.kics.io/dev/getting-started/
- https://docs.kics.io/latest/getting-started/
- https://hub.docker.com/r/checkmarx/kics
- https://github.com/Checkmarx/kics/blob/master/Dockerfile

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                             KICS Worker                                   │
│                                                                           │
│  ┌──────────┐     ┌───────────────┐                                      │
│  │  app.py  │────▶│ processor.py  │                                      │
│  │          │     │ (orchestrator)│                                      │
│  │ - Stream │     └───────┬───────┘                                      │
│  │   reader │             │                                              │
│  │ - Health │      ┌──────┼──────┬──────────┐                            │
│  │   check  │      │      │      │          │                            │
│  └──────────┘      ▼      ▼      ▼          ▼                            │
│              ┌────────┐ ┌────────┐ ┌──────────┐                          │
│              │ git.py │ │scan.py │ │comment.py│                          │
│              │        │ │        │ │          │                          │
│              │- Clone │ │- Run   │ │- PR body │                          │
│              │- Post  │ │  KICS  │ │- Summary │                          │
│              │  comment│ │- Parse │ │- Callback│                          │
│              │- Check │ │  JSON  │ │  message │                          │
│              │  runs  │ │        │ │          │                          │
│              │- Cleanup│ │        │ │          │                          │
│              └────────┘ └────────┘ └──────────┘                          │
└──────────────────────────────────────────────────────────────────────────┘
```

## Module Responsibilities

| Module | Class | Responsibility |
|--------|-------|----------------|
| `app.py` | - | Stream listener, health endpoint, startup checks |
| `processor.py` | `Processor` | Orchestrates workflow |
| `git.py` | `GitHub` | Clone, PR comments, check runs, cleanup |
| `scan.py` | `Scan` | Execute KICS binary, parse results |
| `comment.py` | `Comment` | Build markdown comments and summaries |

## Startup Behavior

```
Container Start
      │
      ▼
┌─────────────────┐
│ check_kics_     │
│ installed()     │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
  Found    Not Found
    │         │
    ▼         ▼
  Log       Log error
  version   sys.exit(1)
    │         │
    ▼         ▼
  Continue  Docker
  startup   restarts
```

## Processing Flow

```
┌─────────┐
│  Redis  │
│ Stream  │
└────┬────┘
     │ 1. Message received
     ▼
┌─────────────┐
│ processor.py│
└──────┬──────┘
       │ 2. Retrieve storage from Redis
       ▼
┌─────────────┐
│   git.py    │
│   clone()   │
└──────┬──────┘
       │ 3. Clone repo (GitPython)
       ▼
┌─────────────┐
│  scan.py    │
│   run()     │
└──────┬──────┘
       │ 4. Execute KICS, parse results
       ▼
┌─────────────┐
│   git.py    │
│ post_pr_    │
│ comment()   │
└──────┬──────┘
       │ 5. Post markdown to PR
       ▼
┌─────────────┐
│   git.py    │
│ create_     │
│ check_run() │
└──────┬──────┘
       │ 6. Create annotations
       ▼
┌─────────────┐
│ processor.py│
│ callback()  │
└──────┬──────┘
       │ 7. Notify coordinator
       ▼
┌─────────────┐
│   git.py    │
│  cleanup()  │
└──────┬──────┘
       │ 8. Remove cloned repo
       ▼
   os._exit(0)
       │
       ▼
 Docker restart
```

## Classes

### `GitHub` (git.py)

Handles all GitHub/Git operations.

```python
github = GitHub(token, app_name)

# Clone repository
ctx = github.clone(owner, name, branch, pr_id, commit_sha)

# Post PR comment
github.post_pr_comment(ctx, markdown_body)

# Create check run with annotations
github.create_check_run(ctx, name, conclusion, title, summary, annotations)

# Cleanup
github.cleanup(ctx)
```

### `RepoContext` (git.py)

Context object for a cloned repository.

| Field | Type | Description |
|-------|------|-------------|
| `path` | str | Local filesystem path |
| `owner` | str | Repository owner |
| `name` | str | Repository name |
| `branch` | str | Branch name |
| `pr_id` | int | Pull request number |
| `commit_sha` | str | Commit SHA |

### `Scan` (scan.py)

Executes KICS scans.

```python
scanner = Scan(app_name)
result = scanner.run(repo_path)
```

### `ScanResult` (scan.py)

| Field | Type | Description |
|-------|------|-------------|
| `success` | bool | Scan completed without errors |
| `total_issues` | int | Total security issues found |
| `severity_counters` | dict | Count by severity level |
| `files_scanned` | int | Number of files analyzed |
| `files_parsed` | int | Number of files parsed |
| `queries_total` | int | Number of KICS queries executed |
| `execution_time_seconds` | float | Scan duration |
| `queries` | list | Detailed findings |
| `error_message` | str | Error if scan failed |

### `Comment` (comment.py)

Builds markdown content for GitHub.

```python
comment = Comment(app_name)

comment.pr_comment(result)        # Full PR comment markdown
comment.check_run_summary(result) # Short summary for check run
comment.callback_message(result)  # Message for coordinator callback
```

### `Processor` (processor.py)

Orchestrates the complete workflow.

```python
processor = Processor(app_name, redis_client)
processor.process(msg)
```

## Ephemeral Worker Pattern

```
Message received → Process → os._exit(0) → Docker restart
```

**Benefits:**
- No memory leaks accumulate
- No stale state between scans
- Clean environment for each repository

## GitHub Integration

### PR Comment

```markdown
## ⚠️ KICS Security Scan Results

| Severity | Count |
|----------|-------|
| 🔴 CRITICAL | 1 |
| 🟠 HIGH | 3 |
...
```

### Check Run Conclusion

| Condition | Conclusion |
|-----------|------------|
| Scan failed | `failure` |
| CRITICAL > 0 | `failure` |
| HIGH > 0 | `neutral` |
| Otherwise | `success` |

### Annotations

Inline code annotations on affected files, batched in groups of 50 (GitHub API limit).

## Dependencies

| Package | Purpose |
|---------|---------|
| `GitPython` | Repository cloning |
| `requests` | GitHub API calls |
| `redis` | Stream consumption |
| `fastapi` | Health check endpoint |

## External References

- https://github.com/Checkmarx/kics
- https://github.com/Checkmarx/kics-github-action
- https://kics.io/
