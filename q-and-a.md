# Q&A - Anticipated Engineer Questions

**Purpose:** Prepared answers for demo/handover call questions.

---

## Architecture & Design Decisions

### 1. Why Redis Streams over Kafka/RabbitMQ/SQS?

**Question:** What's the expected message volume? Do we need persistence guarantees beyond Redis?

**Answer:**
Redis Streams was chosen for the POC because:
- **Simplicity:** Single dependency for both storage and message queue
- **Low latency:** In-memory with optional persistence (AOF enabled in `docker-compose.yaml`)
- **Consumer groups:** Built-in support for competing consumers (`XREADGROUP`)
- **Lightweight:** No separate cluster management (vs. Kafka/RabbitMQ)

**Expected volume:** Low-to-medium (PR events, not high-frequency). For a typical org, expect 10-100 PRs/day.

**Production considerations:**
- If volume exceeds 1000s of messages/sec or need cross-region replication → consider Kafka
- If need guaranteed delivery with complex routing → consider RabbitMQ
- Current setup has AOF persistence enabled (`redis-server --appendonly yes`)

---

### 2. Why separate workers per scanner vs. one worker with plugins?

**Question:** How do we add new scanner types? Is there shared code we should extract?

**Answer:**
**Rationale for separate workers:**
- **Isolation:** Different dependencies (KICS needs Go binary, Blackduck needs JRE + 200MB JAR)
- **Independent scaling:** Blackduck scans take longer → scale differently than KICS
- **Failure isolation:** One scanner crashing doesn't affect others
- **Deployment flexibility:** Update KICS without touching Blackduck

**Adding a new scanner:**
1. Create `services/workers/<scanner-name>/` directory
2. Copy worker template (app.py, model.py, Dockerfile)
3. Add infra Dockerfile if special dependencies needed
4. Add stream name to API fan-out list
5. Add service to `docker-compose.yaml`

**Shared code to extract:**
- `model.py` (MessagePayload, StoragePayload) - duplicated across workers
- `stream_listener()` pattern - nearly identical in blackduck/kicks
- `send_callback()` function - identical

Consider creating a `services/workers/common/` package.

---

### 3. Why fan-out at the API vs. letting workers subscribe to a single stream?

**Question:** What if we want selective scanning (only KICS for IaC repos)?

**Answer:**
**Current design:** API pushes to multiple streams (`worker-1`, `worker-kics`), each worker reads its own stream.

**Why this approach:**
- **Explicit control:** API decides which scanners run
- **Visibility:** Easy to see which streams received messages
- **Simple workers:** Workers don't need filtering logic

**For selective scanning (future):**
- API can check repo contents/labels before fan-out
- Example: Only push to `worker-kics` stream if repo contains `.tf`, `.yaml`, or `Dockerfile`
- Could add `scan_types` field to webhook config per repo

**Alternative (single stream):**
- All workers read from one stream, filter locally
- Pro: Simpler API
- Con: All workers receive all messages, wasted processing

---

## Operational Concerns

### 4. What happens when a worker crashes mid-scan?

**Question:** Are messages re-delivered? Is there a visibility timeout?

**Answer:**
**Current behavior:**
- Workers use Redis consumer groups with `XREADGROUP`
- Messages are tracked per-consumer until `XACK` is called
- If worker crashes before `XACK`, message stays in Pending Entries List (PEL)

**Recovery mechanism:**
- Currently **NOT implemented** - pending messages are orphaned
- Need to add: `XAUTOCLAIM` or `XPENDING` + `XCLAIM` logic to reclaim old messages

**Recommended fix:**
```python
# Add to worker startup - claim messages pending > 60 seconds
messages = Redis.xautoclaim(STREAM_NAME, CONSUMER_GROUP, CONSUMER_NAME,
                            min_idle_time=60000, start_id='0-0', count=10)
```

**Current safeguard:** Messages are deleted after ACK (`XDEL`) to prevent reprocessing.

---

### 5. How do we scale workers?

**Question:** Can we run multiple instances of the same worker? How does consumer group balancing work?

**Answer:**
**Yes, multiple instances are supported.** Redis consumer groups handle this automatically.

**How it works:**
- All workers in same `CONSUMER_GROUP` (default: `"workers"`) share the stream
- Each message delivered to only ONE consumer in the group
- Redis round-robins between available consumers

**To scale:**
```yaml
# docker-compose.yaml
worker-1:
  deploy:
    replicas: 3
```

Or in Kubernetes:
```yaml
spec:
  replicas: 3
```

**Important:** Each instance needs unique `CONSUMER_NAME` (currently uses `APP_NAME`, would need `APP_NAME-{instance_id}`).

---

### 6. What's the message retention/TTL policy?

**Question:** Old messages never expire currently - is there a cleanup job?

**Answer:**
**Current state:** No TTL configured. Messages deleted immediately after processing (`XDEL`).

**Storage keys (`storage:{id}`):** No expiration - will accumulate forever.

**Recommended fixes:**
1. Add TTL to storage keys:
   ```python
   Redis.setex(f"storage:{id}", 86400, json.dumps(storage))  # 24hr TTL
   ```

2. Add stream max length:
   ```python
   Redis.xadd(stream, {"data": msg}, maxlen=10000)  # Keep last 10k
   ```

3. Or use `XTRIM` in a cleanup job:
   ```bash
   redis-cli XTRIM worker-1 MAXLEN ~ 1000
   ```

---

### 7. How do we monitor this in production?

**Question:** What metrics should we track? Where are the dashboards?

**Answer:**
**Currently available:**
- `/status` endpoint on API and each worker (health + Redis connectivity)
- Basic logging to stdout (Docker logs)

**Recommended metrics to add:**
| Metric | Source | Purpose |
|--------|--------|---------|
| `webhook_events_received` | API | Ingest rate |
| `messages_published{stream}` | API | Fan-out health |
| `messages_processed{worker}` | Workers | Throughput |
| `processing_duration_seconds` | Workers | Scan performance |
| `callback_success/failure` | Workers | Integration health |
| `redis_stream_length{stream}` | Redis | Backlog monitoring |
| `redis_pending_messages{stream,consumer}` | Redis | Stuck messages |

**Integration options:**
- Prometheus + Grafana (add `/metrics` endpoint with `prometheus-fastapi-instrumentator`)
- Datadog (add `ddtrace` instrumentation)
- CloudWatch (if on AWS)

**No dashboards exist currently.**

---

## Security Questions

### 8. How are secrets managed?

**Question:** Base64 in env vars isn't production-ready - what's the plan? Who rotates the GitHub App private key?

**Answer:**
**Current state:**
- `GITHUB_APP_PRIVATE_KEY`: Base64-encoded PEM in environment variable
- `GITHUB_WEBHOOK_SECRET`: Plain text in environment variable
- Loaded via shell: `export GITHUB_APP_PRIVATE_KEY=$(base64 -i private-key.pem)`

**Why Base64:** Avoids newline issues in env vars (PEM files have multiple lines).

**Production recommendations:**
| Option | Complexity | Notes |
|--------|------------|-------|
| Kubernetes Secrets | Low | Mount as files, not env vars |
| HashiCorp Vault | Medium | Dynamic secrets, audit logging |
| AWS Secrets Manager | Medium | Native if on AWS/EKS |
| Azure Key Vault | Medium | Native if on Azure/AKS |

**Key rotation:**
- GitHub App private keys can be rotated in GitHub App settings
- Generate new key → update secret store → restart services
- No automated rotation implemented

**Code change needed:** Support reading key from file path, not just env var.

---

### 9. Is the callback endpoint authenticated?

**Question:** Can anyone POST to `/callback`? Should workers use a shared secret?

**Answer:**
**Current state: NO AUTHENTICATION.** Anyone can POST to `/callback`.

```python
# services/api/app.py:86
@app.post("/callback")
def callback(payload: dict):  # No auth check
```

**Risk:** Attacker could inject fake scan results.

**Recommended fixes:**

1. **Shared secret (simple):**
   ```python
   CALLBACK_SECRET = os.getenv("CALLBACK_SECRET")

   @app.post("/callback")
   def callback(payload: dict, x_callback_secret: str = Header(...)):
       if x_callback_secret != CALLBACK_SECRET:
           raise HTTPException(401, "Invalid callback secret")
   ```

2. **Network isolation (defense in depth):**
   - Keep callback endpoint internal-only (not exposed via ingress)
   - Currently OK in Docker network, but verify in production

3. **Message signing:**
   - Workers sign payload with HMAC
   - API verifies signature

---

### 10. Is Redis authenticated?

**Question:** Currently no auth - what's the production config?

**Answer:**
**Current state: NO AUTHENTICATION.**

```yaml
# docker-compose.yaml
redis:
  image: "redis:8"
  command: redis-server --appendonly yes  # No --requirepass
```

**Risk:** Any container on the network can read/write Redis data.

**Recommended fixes:**

1. **Add password:**
   ```yaml
   redis:
     command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
   ```

2. **Update clients:**
   ```python
   Redis = redis.Redis(
       host=os.getenv("REDIS_HOST"),
       port=int(os.getenv("REDIS_PORT", 6379)),
       password=os.getenv("REDIS_PASSWORD"),  # Add this
       decode_responses=True
   )
   ```

3. **Production:** Use managed Redis (ElastiCache, Azure Cache, etc.) with:
   - TLS encryption
   - IAM authentication (AWS) or Azure AD
   - VPC/private networking

---

## Implementation Gaps

### 11. What exactly should the scanners do?

**Question:** Clone the repo? Use GitHub API for file contents? Full repo scan vs. changed files only? Where do scan results get stored?

**Answer:**
**Current state:** Workers receive PR metadata but scanning is stubbed (`time.sleep(5)`).

**Recommended implementation:**

| Scanner | Approach | Notes |
|---------|----------|-------|
| **KICS** | Clone repo → run `kics scan` | Needs full repo for context |
| **Blackduck** | Clone repo → run Detect JAR | Full dependency analysis |

**Clone approach (recommended):**
```python
from git import Repo

def clone_repo(owner: str, name: str, branch: str, token: str) -> str:
    url = f"https://x-access-token:{token}@github.com/{owner}/{name}.git"
    path = f"/tmp/repos/{owner}-{name}-{branch}"
    Repo.clone_from(url, path, branch=branch, depth=1)
    return path
```

**GitHub API approach (alternative):**
- Use for changed-files-only scanning
- `GET /repos/{owner}/{repo}/pulls/{pull_number}/files`
- Less resource-intensive but limited context

**Results storage:**
- Short-term: Redis (`scan_result:{id}`) with TTL
- Long-term: PostgreSQL or S3 for audit/compliance
- Currently: Only logged, not persisted

---

### 12. How do we post results back to GitHub?

**Question:** PR comments? Check runs? Status checks? What format should results be in?

**Answer:**
**Options:**

| Method | Visibility | Best For |
|--------|------------|----------|
| **PR Comment** | In PR thread | Human-readable summaries |
| **Check Run** | Checks tab, PR status | Detailed results with annotations |
| **Status Check** | PR status badge | Simple pass/fail |

**Recommended: Check Runs** (best UX)

```python
# In callback handler, after receiving results
from githubapp import GitHubApp

async def post_check_run(installation_id, owner, repo, head_sha, results):
    gh = await github_app.get_installation_client(installation_id)
    await gh.post(f"/repos/{owner}/{repo}/check-runs", data={
        "name": "KICS Security Scan",
        "head_sha": head_sha,
        "status": "completed",
        "conclusion": "success" if results.passed else "failure",
        "output": {
            "title": "KICS Scan Results",
            "summary": f"Found {results.issue_count} issues",
            "annotations": [...]  # Line-level findings
        }
    })
```

**Required GitHub App permissions:**
- `checks: write`
- `pull_requests: read`

---

### 13. What's the expected scan duration?

**Question:** Blackduck can take 10+ minutes - how does that affect the flow?

**Answer:**
**Expected durations:**
| Scanner | Typical Duration | Factors |
|---------|------------------|---------|
| KICS | 30s - 2min | Repo size, file count |
| Blackduck | 5 - 15min | Dependencies, network speed |

**Current handling:**
- Workers block during scan (synchronous)
- `block=5000` in `XREADGROUP` - 5 second timeout for new messages
- No overall timeout on scan execution

**Concerns:**
- Long scans block the worker thread
- No way to cancel in-progress scans
- User sees no progress on PR

**Recommendations:**
1. Add scan timeout:
   ```python
   import signal
   signal.alarm(600)  # 10 minute timeout
   ```

2. Post "in progress" check run immediately, update when complete

3. Consider async scanning:
   - Worker spawns subprocess
   - Polls for completion
   - Can handle multiple scans concurrently

---

## Deployment & Reliability

### 14. What's the target deployment platform?

**Question:** Kubernetes? ECS? Cloud Run?

**Answer:**
**Current state:** Docker Compose only. No production deployment configs.

**Recommended path:**

| Platform | Effort | Best For |
|----------|--------|----------|
| **Kubernetes** | Medium | Existing K8s clusters, complex scaling |
| **ECS Fargate** | Low | AWS shops, simpler ops |
| **Cloud Run** | Low | GCP shops, auto-scaling |

**What's needed:**
- [ ] Kubernetes manifests or Helm chart
- [ ] Health/readiness probes (already have `/status`)
- [ ] Resource limits (CPU/memory)
- [ ] Horizontal Pod Autoscaler configs
- [ ] Ingress/load balancer for API
- [ ] Managed Redis (ElastiCache/Memorystore)

**Smee not needed in production** - GitHub webhooks hit API directly via public endpoint.

---

### 15. What happens if Redis goes down?

**Question:** Is there a circuit breaker? Do we need Redis clustering/sentinel?

**Answer:**
**Current behavior:**
- API: `/status` returns `redis: "error"`, but webhook handler would crash
- Workers: Catch `redis.ConnectionError`, sleep 5s, retry forever

```python
# services/workers/blackduck/app.py:101
except redis.ConnectionError as e:
    logger.error(f"[{APP_NAME}] Redis connection error: {e}")
    time.sleep(5)  # Retry loop
```

**No circuit breaker implemented.**

**Recommendations:**
1. **Circuit breaker** (e.g., `pybreaker`):
   ```python
   from pybreaker import CircuitBreaker
   redis_breaker = CircuitBreaker(fail_max=5, reset_timeout=60)

   @redis_breaker
   def publish_message(stream, data):
       Redis.xadd(stream, data)
   ```

2. **Redis high availability:**
   - Development: Single node is fine
   - Production: Redis Sentinel or Redis Cluster
   - Managed: ElastiCache Multi-AZ, Azure Cache Premium

3. **Graceful degradation:**
   - API could queue webhooks locally if Redis down (with risk of loss)
   - Return 503 to GitHub (will retry)

---

### 16. How do we handle GitHub API rate limits?

**Question:** The decorators exist but aren't implemented.

**Answer:**
**Current state:** Decorator exists but is a passthrough.

```python
# services/api/app.py:106
@with_rate_limit_handling(github_app)
def handle_pr():
    ...
```

The `@with_rate_limit_handling` decorator is from `fastapi-githubapp` library and should handle rate limits automatically by:
- Checking `X-RateLimit-Remaining` header
- Sleeping until `X-RateLimit-Reset` if exhausted

**Rate limits:**
| Resource | Limit | Reset |
|----------|-------|-------|
| GitHub App installation | 5,000/hr | Rolling |
| Search API | 30/min | Rolling |

**Recommendations:**
1. Verify decorator actually works (test with high volume)
2. Add monitoring for rate limit headers
3. For posting results, batch if possible
4. Consider caching GitHub API responses (repo metadata doesn't change often)

---

## Testing & Validation

### 17. How do we test this end-to-end without real PRs?

**Question:** Are the fixture scripts sufficient? Is there a mock GitHub webhook generator?

**Answer:**
**Current testing tools:**

1. **Fixture files:**
   - `scripts/fixtures/pr-opened.json` - Sample webhook payload
   - `scripts/post-pr-opened.sh` - Sends fixture to API

2. **Manual fan-out:**
   ```bash
   curl -X POST http://localhost:8080/fanout
   ```
   This bypasses GitHub entirely and tests Redis → Workers → Callback.

3. **Smee.io for real webhooks:**
   - Create test repo with GitHub App installed
   - Open PR → webhook flows through Smee → local API

**Recommended additions:**

1. **Webhook simulator:**
   ```python
   # tests/conftest.py
   @pytest.fixture
   def mock_webhook():
       return {
           "action": "opened",
           "pull_request": {"number": 1, "head": {"sha": "abc123"}},
           "repository": {"name": "test", "owner": {"login": "testorg"}}
       }
   ```

2. **Integration test with testcontainers:**
   ```python
   from testcontainers.redis import RedisContainer

   def test_full_flow():
       with RedisContainer() as redis:
           # Start API, workers, send webhook, verify callback
   ```

---

### 18. What's the test coverage expectation?

**Question:** pytest is configured but no tests exist.

**Answer:**
**Current state:**
- `pytest.ini` exists
- `pytest-cov`, `pytest-mock`, `pytest-asyncio` in dev dependencies
- **Zero tests implemented**

**Recommended coverage targets:**

| Component | Priority | Target |
|-----------|----------|--------|
| `utils.py` (base64, datetime) | High | 100% |
| `model.py` (data classes) | High | 100% |
| Webhook signature validation | High | 100% |
| Stream consumer logic | Medium | 80% |
| Callback handling | Medium | 80% |
| Integration (API → Redis → Worker) | Medium | Key paths |

**Quick wins:**
```python
# tests/test_utils.py
def test_decode_base64_key():
    encoded = base64.b64encode(b"test-key").decode()
    assert decode_base64_key(encoded) == "test-key"

# tests/test_model.py
def test_storage_payload_from_json():
    json_str = '{"id": "1", "name": "repo", "owner": "org", "branch": "main"}'
    payload = StoragePayload.from_json(json_str)
    assert payload.name == "repo"
```

---

## Data & Compliance

### 19. Where do historical scan results live?

**Question:** Redis only? Need a database? Audit/compliance requirements?

**Answer:**
**Current state:**
- PR metadata: Redis (`storage:{id}`) - no TTL
- Scan results: Logged only, not persisted
- No audit trail

**Recommendations:**

| Data | Short-term | Long-term |
|------|------------|-----------|
| PR metadata | Redis (24hr TTL) | PostgreSQL or skip |
| Scan results | Redis (7 days) | PostgreSQL + S3 |
| Audit log | - | PostgreSQL (immutable) |

**For compliance (SOC2, etc.):**
- Who triggered scan
- What was scanned (commit SHA)
- When scan ran
- What was found
- What action was taken

**Schema suggestion:**
```sql
CREATE TABLE scan_results (
    id UUID PRIMARY KEY,
    pr_id INT,
    repo_owner TEXT,
    repo_name TEXT,
    commit_sha TEXT,
    scanner TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT,
    findings JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### 20. How long do we retain PR metadata?

**Question:** GDPR/data retention policies?

**Answer:**
**Current state:** Retained forever (no TTL on Redis keys).

**What's stored:**
- `storage:{id}`: repo name, owner, branch, PR ID
- No PII directly (usernames are GitHub handles, not personal data)

**Recommendations:**
| Data Type | Retention | Justification |
|-----------|-----------|---------------|
| PR metadata | 30 days | Operational debugging |
| Scan results | 1 year | Compliance, trend analysis |
| Audit logs | 7 years | Regulatory (SOC2, etc.) |

**Implementation:**
```python
# Add TTL when storing
Redis.setex(f"storage:{id}", 30 * 86400, json.dumps(storage))  # 30 days
```

**GDPR considerations:**
- GitHub usernames may be considered pseudonymous data
- Ensure data deletion process exists if requested
- Document data flows in privacy policy

---

## Priority Questions

These are most likely to come up first - ensure answers are prepared:

| # | Topic | Why It's Critical |
|---|-------|-------------------|
| 1 | Redis vs alternatives | Architecture justification |
| 8 | Secrets management | Security concern |
| 9 | Callback authentication | Security concern |
| 11 | Scanner implementation | Core functionality gap |
| 12 | GitHub integration | Core functionality gap |
| 14 | Deployment platform | Ops planning |

---

*Last updated: February 2026*
