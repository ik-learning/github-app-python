# Blackduck Worker

Security scanning worker that runs [Blackduck](https://www.blackduck.com/) SCA (Software Composition Analysis) scans on repositories.

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          Blackduck Worker                                 │
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
│              │- Post  │ │  Black │ │- Summary │                          │
│              │  comment│ │  duck  │ │- Callback│                          │
│              │- Check │ │- Parse │ │  message │                          │
│              │  runs  │ │  JSON  │ │          │                          │
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
| `scan.py` | `Scan` | Execute Blackduck CLI, parse results |
| `comment.py` | `Comment` | Build markdown comments and summaries |

## Startup Behavior

```
Container Start
      │
      ▼
┌─────────────────┐
│ check_blackduck_│
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
       │ 4. Execute Blackduck, parse results
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

ctx = github.clone(owner, name, branch, pr_id, commit_sha)
github.post_pr_comment(ctx, markdown_body)
github.create_check_run(ctx, name, conclusion, title, summary, annotations)
github.cleanup(ctx)
```

### `Scan` (scan.py)

Executes Blackduck scans.

```python
scanner = Scan(app_name)
result = scanner.run(repo_path, project_name)
```

### `ScanResult` (scan.py)

| Field | Type | Description |
|-------|------|-------------|
| `success` | bool | Scan completed without errors |
| `total_issues` | int | Total vulnerabilities found |
| `severity_counters` | dict | Count by severity level |
| `components_scanned` | int | Number of components analyzed |
| `policy_violations` | int | Policy violations detected |
| `execution_time_seconds` | float | Scan duration |
| `vulnerabilities` | list | Detailed vulnerability findings |
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

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BLACKDUCK_CLI` | `bridge-cli` | Path to Blackduck CLI |
| `BLACKDUCK_URL` | - | Blackduck server URL |
| `BLACKDUCK_API_TOKEN` | - | Blackduck API token |
| `GITHUB_TOKEN` | - | GitHub token for API access |
| `TEST_MODE` | `false` | Use test repos instead of target |
| `STREAM_NAME` | `worker-1` | Redis stream name |
| `APP_NAME` | `blackduck-worker` | Application name |

## Test Mode

When `TEST_MODE=true`, clones public vulnerable repos instead of target:

```python
TEST_REPOS = [
    {"owner": "juice-shop", "name": "juice-shop", "branch": "master"},
    {"owner": "OWASP", "name": "WebGoat", "branch": "main"},
    {"owner": "OWASP", "name": "NodeGoat", "branch": "master"},
    {"owner": "madhuakula", "name": "kubernetes-goat", "branch": "master"},
]
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
## ⚠️ Blackduck Security Scan Results

| Severity | Count |
|----------|-------|
| 🔴 CRITICAL | 2 |
| 🟠 HIGH | 5 |
...
```

### Check Run Conclusion

| Condition | Conclusion |
|-----------|------------|
| Scan failed | `failure` |
| CRITICAL > 0 | `failure` |
| HIGH > 0 | `neutral` |
| Otherwise | `success` |

## Dependencies

| Package | Purpose |
|---------|---------|
| `GitPython` | Repository cloning |
| `requests` | GitHub API calls |
| `redis` | Stream consumption |
| `fastapi` | Health check endpoint |

## External References

- https://www.blackduck.com/
- https://sig-product-docs.synopsys.com/bundle/bridge
- https://community.synopsys.com/s/topic/0TO34000000gGZNGA2/black-duck
