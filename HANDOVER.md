# Project Handover Document

**From:** Security Engineering (POC)
**To:** Engineering Team
**Date:** February 2026
**Status:** Proof of Concept - Ready for Production Implementation

---

## Executive Summary

This document provides a handover of a GitHub App webhook system designed to automate security scanning of pull requests. The POC demonstrates a working distributed architecture that receives GitHub webhooks, stores PR metadata, and fans out work to specialized security scanning workers via Redis streams.

**The infrastructure is functional. The scanning implementations are stubbed and require completion.**

---

## What Was Built

### Purpose

A GitHub App that automatically triggers security scans when pull requests are opened or updated. The system is designed to:

1. Receive GitHub webhook events for PRs
2. Validate webhook signatures (security)
3. Store PR metadata for processing
4. Distribute work to multiple scanning services
5. Collect results and (eventually) post back to GitHub

### Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│   GitHub    │────▶│   Smee.io   │────▶│   API Service   │
│  Webhooks   │     │   (proxy)   │     │   (FastAPI)     │
└─────────────┘     └─────────────┘     └────────┬────────┘
                                                 │
                                                 ▼
                                        ┌─────────────────┐
                                        │     Redis       │
                                        │  (streams +     │
                                        │   storage)      │
                                        └────────┬────────┘
                           ┌─────────────────────┼─────────────────────┐
                           ▼                     ▼                     ▼
                    ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
                    │  Blackduck  │       │    KICS     │       │ Checkmarks  │
                    │   Worker    │       │   Worker    │       │  (stub)     │
                    └─────────────┘       └─────────────┘       └─────────────┘
```

### Message Flow

1. **GitHub → API:** PR event triggers webhook to `/webhooks/github`
2. **API validates:** Webhook signature verified using shared secret
3. **API stores:** PR metadata saved to Redis (`storage:{uuid}`)
4. **API fans out:** Messages published to worker streams (`worker-1`, `worker-kics`)
5. **Workers consume:** Each worker reads from its dedicated Redis stream
6. **Workers process:** (Currently stubbed - actual scanning TBD)
7. **Workers callback:** Results POSTed back to API via `/callback`

---

## Current State

### What Works

| Component | Status | Notes |
|-----------|--------|-------|
| API webhook receiver | ✅ Working | Validates GitHub signatures |
| Redis integration | ✅ Working | Storage + streams configured |
| Message fan-out | ✅ Working | `/fanout` endpoint tested |
| Worker stream consumers | ✅ Working | Consumer groups configured |
| Callback mechanism | ✅ Working | Workers can POST results |
| Docker orchestration | ✅ Working | 6 services networked |
| Health checks | ✅ Working | `/status` endpoints |
| Local dev (Smee proxy) | ✅ Working | Tunnels GitHub webhooks |

### What's Incomplete

| Component | Status | Required Work |
|-----------|--------|---------------|
| Blackduck scanning | ⚠️ Stubbed | Implement actual scan logic |
| KICS scanning | ⚠️ Stubbed | Clone repo, run KICS, parse results |
| Checkmarks worker | ❌ Not started | Define requirements |
| GitHub PR comments | ❌ Not started | Post scan results back to PR |
| Error handling | ⚠️ Basic | Needs retry logic, dead letter queue |
| Tests | ⚠️ Configured | No test implementations |
| Secrets management | ⚠️ Env vars | Production secrets solution needed |

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| API Framework | FastAPI + Uvicorn | Async webhook handling |
| GitHub Integration | fastapi-githubapp | Webhook auth & signature validation |
| Message Queue | Redis Streams | Reliable work distribution |
| Container Runtime | Docker Compose | Local orchestration |
| Language | Python 3.x | All services |
| Git Operations | GitPython | (For repo cloning in workers) |

---

## Project Structure

```
github-app-python/
│
├── services/                        # Application services
│   ├── api/                         # Main webhook receiver service
│   │   ├── __init__.py
│   │   ├── app.py                   # FastAPI application (webhook handlers, fanout, callback)
│   │   ├── model.py                 # Pydantic data models (PRInfo, etc.)
│   │   ├── utils.py                 # Helpers (base64 decoding, datetime formatting)
│   │   ├── Dockerfile               # API service container
│   │   └── readme.md                # API service documentation
│   │
│   └── workers/                     # Background worker services
│       ├── blackduck/               # Blackduck security scanning worker
│       │   ├── app.py               # Stream consumer + callback logic
│       │   ├── model.py             # Worker-specific models
│       │   ├── Dockerfile           # Blackduck worker container
│       │   └── readme.md            # Worker documentation
│       │
│       ├── kicks/                   # KICS infrastructure scanning worker
│       │   ├── app.py               # KICS worker (stubbed)
│       │   ├── model.py             # Worker-specific models
│       │   ├── Dockerfile           # KICS worker container
│       │   └── readme.md            # Worker documentation
│       │
│       └── checkmarks/              # (Future) Third scanning worker
│           └── Dockerfile           # Placeholder container
│
├── infra/                           # Infrastructure & build files
│   ├── Dockerfile.python            # Base Python image for all services
│   ├── Dockerfile.blackduck         # Blackduck-specific dependencies
│   ├── Dockerfile.kicks             # KICS-specific dependencies
│   ├── Dockerfile.smee              # Smee.io webhook proxy image
│   └── helpers.mk                   # Makefile helper targets
│
├── scripts/                         # Development & testing scripts
│   ├── curl.sh                      # Manual API testing
│   ├── post-pr-opened.sh            # Simulate PR webhook
│   └── fixtures/                    # Test data
│       ├── pr-opened.json           # Sample PR opened webhook payload
│       └── test.json                # Generic test fixture
│
├── docs/                            # Additional documentation
│   ├── blackduck.md                 # Blackduck integration notes
│   └── mix.md                       # Miscellaneous docs
│
├── input/                           # Input data directory
│   └── input.json                   # Sample input configuration
│
├── status/                          # Status images/artifacts
│   └── *.jpg                        # Status screenshots
│
├── docker-compose.yaml              # Service orchestration (6 services)
├── Dockerfile                       # Root Dockerfile (alternative build)
├── Dockerfile.deps                  # Dependencies image
├── Makefile                         # Build commands (build, up, logs, etc.)
├── Pipfile                          # Python dependencies (pipenv)
├── Pipfile.lock                     # Locked dependency versions
├── pytest.ini                       # Pytest configuration
├── scan.py                          # Standalone scan script
├── status.py                        # Status checking utility
│
├── HANDOVER.md                      # This document
├── README.md                        # Project overview & setup
├── PROJECT_ANALYSIS.md              # Detailed project analysis
├── diagrams.md                      # Architecture diagrams
│
├── .pre-commit-config.yaml          # Pre-commit hooks configuration
├── .envrc                           # direnv environment config
├── .editorconfig                    # Editor configuration
├── .gitignore                       # Git ignore rules
└── .dockerignore                    # Docker ignore rules
```

---

## Infrastructure Dockerfiles

The `infra/` directory contains base images that service Dockerfiles extend from. These establish the dependency layers for the system.

### Dockerfile.python (Base Python Image)

The foundation image for all Python services.

```dockerfile
FROM python:3-slim
# Installs pipenv and project dependencies from Pipfile.lock
```

**Build:** `docker build -f infra/Dockerfile.python -t python-deps .`

**Provides:**
- Python 3 slim runtime
- All Python dependencies via pipenv (redis, fastapi, uvicorn, etc.)

**Used by:** All service Dockerfiles extend this image

---

### Dockerfile.blackduck (Blackduck Scanner Image)

Extends `python-deps` with Blackduck scanning tools.

```dockerfile
FROM python-deps:latest
# Adds: JRE, Blackduck Detect JAR, Bridge CLI
```

**Build:** `docker build -f infra/Dockerfile.blackduck -t blackduck-deps .`

**Provides:**
- Java Runtime (default-jre-headless) - required for Detect
- Blackduck Detect v11.1.0 JAR (`/root/.blackduck/bridge/tools/`)
- Bridge CLI thin client (`/opt/bridge-cli/`)
- Git, curl, ca-certificates

**Environment:**
- `PATH` includes `/opt/bridge-cli`

**Used by:** `services/workers/blackduck/Dockerfile`

---

### Dockerfile.kicks (KICS Scanner Image)

Extends `python-deps` with KICS infrastructure scanner.

```dockerfile
FROM checkmarx/kics:latest AS kics  # Multi-stage: grab binary
FROM python-deps:latest
# Copies KICS binary and query assets from official image
```

**Build:** `docker build -f infra/Dockerfile.kicks -t kicks-deps .`

**Provides:**
- KICS binary (`/opt/kics/kics`)
- KICS query assets (`/opt/kics/assets/queries`)
- Git, curl, ca-certificates

**Environment:**
- `PATH` includes `/opt/kics`
- `KICS_QUERIES_PATH=/opt/kics/assets/queries`

**Used by:** `services/workers/kicks/Dockerfile`

---

### Dockerfile.smee (Webhook Proxy Image)

Standalone Node.js image for local development webhook tunneling.

```dockerfile
FROM node:20-alpine
# Installs smee-client globally
```

**Build:** `docker build -f infra/Dockerfile.smee -t smee .`

**Provides:**
- Node.js 20 Alpine runtime
- [smee-client](https://github.com/probot/smee-client) - GitHub webhook proxy

**Environment:**
- `NODE_DEBUG=smee` (verbose logging)
- Requires `SMEE_URL` and `SMEE_TARGET` at runtime

**Command:** `smee --url $SMEE_URL --target $SMEE_TARGET`

**Used by:** `docker-compose.yaml` smee service

---

### Build Order

Images must be built in dependency order:

```bash
# 1. Base Python image (no dependencies)
docker build -f infra/Dockerfile.python -t python-deps .

# 2. Scanner images (depend on python-deps)
docker build -f infra/Dockerfile.blackduck -t blackduck-deps .
docker build -f infra/Dockerfile.kicks -t kicks-deps .

# 3. Smee image (independent)
docker build -f infra/Dockerfile.smee -t smee .
```

Or use the Makefile: `make build`

---

## Configuration

### Environment Variables

| Variable | Service | Description |
|----------|---------|-------------|
| `GITHUB_APP_ID` | API | GitHub App identifier |
| `GITHUB_APP_PRIVATE_KEY` | API | Base64-encoded PEM private key |
| `GITHUB_WEBHOOK_SECRET` | API | Shared secret for signature validation |
| `REDIS_HOST` | All | Redis hostname (default: `localhost`) |
| `REDIS_PORT` | All | Redis port (default: `6379`) |
| `SMEE_URL` | Smee | Smee.io channel URL |
| `STREAM_NAME` | Workers | Redis stream to consume from |
| `APP_NAME` | Workers | Consumer group identifier |

### GitHub App Settings

Required permissions:
- **Pull Requests:** Read & Write (to post comments)
- **Contents:** Read (to access repo files)

Required webhook events:
- `pull_request.opened`
- `pull_request.synchronize`

---

## Key Code Locations

### API Service (`services/api/app.py`)

```python
# Webhook handler - line ~80
@github_app.on('pull_request.opened')
@github_app.on('pull_request.synchronize')
async def handle_pr(event: sansio.Event):
    # Stores PR data, fans out to workers
```

### Worker Pattern (`services/workers/blackduck/app.py`)

```python
# Stream consumer loop - line ~50
while True:
    messages = redis_client.xreadgroup(
        groupname=consumer_group,
        consumername=consumer_name,
        streams={stream_name: '>'},
        block=5000
    )
    # Process and callback
```

### Callback Endpoint (`services/api/app.py`)

```python
# Receives worker results - line ~60
@app.post("/callback")
async def callback(request: Request):
    # Logs result, could update PR
```

---

## How to Run Locally

### Prerequisites

1. Docker & Docker Compose installed
2. GitHub App created (see README.md for setup)
3. Smee.io channel for webhook proxying

### Quick Start

```bash
# 1. Set environment variables
export GITHUB_APP_ID=<your-app-id>
export GITHUB_APP_PRIVATE_KEY=$(base64 -i private-key.pem)
export GITHUB_WEBHOOK_SECRET=<your-secret>
export SMEE_URL=https://smee.io/<your-channel>

# 2. Build images
make build

# 3. Start services
make up

# 4. View logs
make logs
```

### Testing the Flow

1. Open a PR on a repo where the GitHub App is installed
2. Watch logs: `docker-compose logs -f api worker-1 worker-kics`
3. Observe webhook received → stored → fanned out → processed → callback

---

## Recommendations for Production

### High Priority

1. **Implement actual scanning logic**
   - `services/workers/blackduck/app.py` - integrate Blackduck SDK
   - `services/workers/kicks/app.py` - clone repo, run `kics scan`, parse JSON output

2. **Add GitHub PR integration**
   - Use `github_app` client to post check runs or comments
   - Show scan results directly on the PR

3. **Secrets management**
   - Replace env vars with secrets manager (Vault, AWS Secrets Manager, etc.)
   - Rotate GitHub App private key

4. **Error handling & observability**
   - Add structured logging (JSON)
   - Implement retry logic for failed scans
   - Add dead letter queue for poison messages
   - Integrate with monitoring (Prometheus, Datadog, etc.)

### Medium Priority

5. **Container orchestration**
   - Kubernetes manifests or Helm charts
   - Horizontal pod autoscaling for workers
   - Proper health/readiness probes

6. **Testing**
   - Unit tests for utility functions
   - Integration tests with mock GitHub webhooks
   - Load testing for worker throughput

7. **CI/CD pipeline**
   - Automated builds and image publishing
   - Security scanning of containers
   - Deployment automation

### Lower Priority

8. **Database persistence**
   - Consider PostgreSQL for audit logs
   - Redis for hot data only

9. **Rate limiting**
   - GitHub API rate limit handling (decorators exist but need implementation)
   - Worker throughput limits

---

## Known Issues & Technical Debt

1. **Hardcoded stream names** - Workers have stream names in code and env vars; consider config service
2. **No graceful shutdown** - Workers should handle SIGTERM properly
3. **Base64 key handling** - Works but adds complexity; consider mounted secrets
4. **Blocking Redis reads** - 5-second timeout is arbitrary; tune for production
5. **No message TTL** - Old messages in Redis never expire; add cleanup job

---

## Security Considerations

### Implemented

- Webhook signature validation using HMAC-SHA256
- Base64-encoded private key (not plaintext in env)
- Internal Docker network (services not exposed)

### Needs Attention

- [ ] Secrets should not be in environment variables for production
- [ ] Redis should have authentication enabled
- [ ] Container images should be scanned for vulnerabilities
- [ ] API should have rate limiting for external endpoints
- [ ] Worker callbacks should verify source

---

## Questions for Engineering Team

Before implementation, consider:

1. **Deployment target** - Kubernetes? ECS? Cloud Run?
2. **Secrets management** - Vault? Cloud-native secrets?
3. **Observability stack** - What monitoring/logging tools are in use?
4. **Scaling requirements** - Expected PR volume? Worker scaling strategy?
5. **Scan result storage** - Where should historical scan data live?
6. **GitHub App scope** - Organization-wide? Per-repo installation?

---

## Resources

- [GitHub Apps Documentation](https://docs.github.com/en/apps)
- [Redis Streams](https://redis.io/docs/data-types/streams/)
- [KICS Scanner](https://github.com/Checkmarx/kics)
- [Blackduck Documentation](https://synopsys.atlassian.net/wiki/spaces/INTDOCS)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

## Contact

For questions about this POC, contact the Security Engineering team.

---

*This document was prepared as part of the POC handover. The engineering team should review the codebase alongside this document and reach out with any questions before beginning production implementation.*
