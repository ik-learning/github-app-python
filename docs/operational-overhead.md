# Operational Overhead - Custom Security Scanning Solution

This document outlines the operational overhead required to run a custom centralized security scanning solution at scale (100-500 repositories).

## 1. Infrastructure Management

| Component | What You Need |
|-----------|---------------|
| Container orchestration | Kubernetes/ECS/Docker Swarm setup, upgrades |
| Redis | HA setup (Sentinel/Cluster), backup, recovery |
| Networking | VPC, load balancers, DNS, certificates |
| Storage | Persistent volumes for scan artifacts, logs |
| Secrets | Vault/AWS Secrets Manager for GitHub tokens |

## 2. Monitoring & Observability

### Metrics (Prometheus/Datadog)
- Queue depth (messages pending)
- Processing time per scan
- Worker restart count
- Redis memory/connections
- Container CPU/memory
- Callback success/failure rate

### Logging (ELK/Splunk/CloudWatch)
- Centralized log aggregation
- Log retention policies
- Search/correlation across workers

### Tracing (Jaeger/X-Ray)
- Request flow: webhook → API → Redis → worker → PR
- Latency breakdown

### Alerting
- Queue backing up > 100 messages
- Worker crash loop
- Redis connection failures
- Scan duration > threshold
- GitHub API rate limits

## 3. Reliability & High Availability

| Concern | Implementation |
|---------|----------------|
| Redis failure | Redis Sentinel (min 3 nodes) or managed Redis |
| Worker crashes | Health checks, restart policies |
| API downtime | Multiple replicas, load balancer |
| Data loss | Redis AOF persistence, backups |
| Network partitions | Retry logic, circuit breakers |
| Poison messages | Dead letter queue for failed scans |
| Duplicate processing | Idempotency keys, exactly-once semantics |

## 4. Scaling Challenges

```
100 repos × 10 PRs/day = 1,000 scans/day (manageable)
500 repos × 20 PRs/day = 10,000 scans/day (need auto-scaling)
```

### Questions to answer:
- How many concurrent workers?
- Worker per scan type or shared?
- Horizontal pod autoscaler based on queue depth?
- Resource limits per worker (KICS/Blackduck are memory-heavy)
- Rate limiting to protect GitHub API (5,000 req/hr)

## 5. Security Operations

| Area | Tasks |
|------|-------|
| Patching | Base images, dependencies (weekly/monthly) |
| Vulnerability scanning | Scan your own containers |
| Secret rotation | GitHub App private key, tokens |
| Network policies | Worker isolation, egress rules |
| Audit logs | Who triggered what, access logs |
| Compliance | SOC2/ISO27001 evidence collection |

## 6. Day 2 Operations (Ongoing)

| Task | Frequency |
|------|-----------|
| Dependency updates | Weekly |
| Container image rebuilds | Weekly/on CVE |
| Redis maintenance | Monthly |
| Kubernetes upgrades | Quarterly |
| Capacity planning | Quarterly |
| Runbook updates | Ongoing |
| Cost optimization | Monthly review |
| GitHub API changes | As needed |
| Scan tool version updates | Monthly |

## 7. Incident Management

### Things that will break:

1. **Redis OOM** → workers stuck → PRs waiting
2. **GitHub rate limited** → callbacks fail → silent failures
3. **Worker memory leak** → OOMKilled → restart loop
4. **Bad repo crashes scanner** → poison message
5. **Network timeout** → partial processing → duplicate comments
6. **Certificate expiry** → webhooks fail silently

### You need:
- Runbooks for each failure mode
- On-call rotation
- Incident response process
- Post-mortem culture

## 8. Cost Estimation (AWS example, 500 repos)

| Item | Monthly Cost |
|------|--------------|
| EKS cluster (control plane + nodes) | ~$150 |
| Redis (ElastiCache) | ~$50-150 |
| Load Balancer | ~$20 |
| Storage (EBS/S3) | ~$20 |
| Monitoring (Datadog) | ~$100-500 |
| Logging | ~$50-100 |
| **Engineer time** | **~10-20% of 1 FTE ongoing** |
| **Total** | **~$400-1000/month + engineer time** |

## 9. Summary

| Overhead Category | Effort |
|------------------|--------|
| Initial setup | 2-4 weeks |
| Monitoring/alerting | 1-2 weeks |
| HA/reliability | 1-2 weeks |
| Ongoing maintenance | 10-20% FTE |
| On-call burden | Shared rotation |

**The real cost isn't infrastructure—it's the engineering time to build, maintain, and be on-call for a distributed system.**

## Alternative: Hybrid Approach

Consider using GitHub App webhook to trigger GitHub Actions via `workflow_dispatch`:

```
PR opened → GitHub App → workflow_dispatch API → triggers shared workflow
```

Benefits:
- Security team controls trigger logic centrally
- No workflow files needed in each repo
- GitHub manages runners/scaling
- Eliminates most operational overhead above
