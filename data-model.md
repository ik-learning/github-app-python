# Data Model - Neo4j Graph Database

**Purpose:** Store and query security scan data from GitHub PR workflows.

**Why Neo4j:** Graph databases excel at traversing relationships - finding which PRs introduced vulnerabilities, tracking dependency chains, and correlating findings across repositories.

---

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SECURITY SCAN DATA MODEL                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Repository ──HAS_PR──> PullRequest ──CONTAINS_COMMIT──> Commit            │
│       │                                                      │              │
│       │ HAS_DEPENDENCY                              SCANNED_BY              │
│       ▼                                                      ▼              │
│   Dependency ──HAS_CVE──> CVE <──MAPS_TO── Vulnerability <── Scan          │
│                                                   │                         │
│                                          IN_FILE / IN_DEPENDENCY            │
│                                                   ▼                         │
│                                            File / Dependency                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Node Types

### Core Entities

| Node | Properties | Description |
|------|------------|-------------|
| **Repository** | `name`, `owner`, `url`, `default_branch` | GitHub repository |
| **PullRequest** | `number`, `title`, `state`, `created_at`, `merged_at` | PR that triggered scans |
| **Commit** | `sha`, `message`, `author`, `timestamp` | Individual commit in a PR |
| **User** | `login`, `email`, `name` | GitHub user (author/reviewer) |

### Scan Entities

| Node | Properties | Description |
|------|------------|-------------|
| **Scan** | `id`, `scanner`, `started_at`, `completed_at`, `status` | Single scan execution (KICS or Blackduck) |
| **Vulnerability** | `id`, `severity`, `title`, `description`, `cwe_id`, `cvss_score`, `remediation` | Detected security issue |
| **Rule** | `rule_id`, `name`, `scanner`, `category`, `severity` | Scanner rule that was violated |

### Code & Dependency Entities

| Node | Properties | Description |
|------|------------|-------------|
| **File** | `path`, `language` | Source file in repository |
| **Dependency** | `name`, `version`, `ecosystem`, `license` | Third-party dependency (npm, pip, maven) |
| **CVE** | `cve_id`, `published_at`, `cvss_score`, `description` | Common Vulnerabilities and Exposures entry |

---

## Node Definitions (Cypher)

```cypher
// Repository
CREATE (r:Repository {
  name: 'string',           // e.g., 'my-app'
  owner: 'string',          // e.g., 'acme-corp'
  url: 'string',            // e.g., 'https://github.com/acme-corp/my-app'
  default_branch: 'string'  // e.g., 'main'
})

// PullRequest
CREATE (pr:PullRequest {
  number: 42,               // PR number
  title: 'string',          // PR title
  state: 'string',          // 'open', 'closed', 'merged'
  created_at: datetime(),
  merged_at: datetime()     // null if not merged
})

// Commit
CREATE (c:Commit {
  sha: 'string',            // Full commit SHA
  message: 'string',        // Commit message
  author: 'string',         // Author username
  timestamp: datetime()
})

// Scan
CREATE (s:Scan {
  id: 'string',             // UUID
  scanner: 'string',        // 'KICS' or 'BLACKDUCK'
  started_at: datetime(),
  completed_at: datetime(),
  status: 'string'          // 'pending', 'running', 'completed', 'failed'
})

// Vulnerability
CREATE (v:Vulnerability {
  id: 'string',             // UUID
  severity: 'string',       // 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'
  title: 'string',
  description: 'string',
  cwe_id: 'string',         // e.g., 'CWE-79'
  cvss_score: 7.5,          // 0.0 - 10.0
  remediation: 'string'     // Fix recommendation
})

// Rule
CREATE (rule:Rule {
  rule_id: 'string',        // Scanner-specific ID
  name: 'string',
  scanner: 'string',        // 'KICS' or 'BLACKDUCK'
  category: 'string',       // e.g., 'Encryption', 'Access Control'
  severity: 'string'
})

// File
CREATE (f:File {
  path: 'string',           // e.g., 'src/infra/s3.tf'
  language: 'string'        // e.g., 'terraform', 'python', 'yaml'
})

// Dependency
CREATE (d:Dependency {
  name: 'string',           // e.g., 'log4j-core'
  version: 'string',        // e.g., '2.14.1'
  ecosystem: 'string',      // 'npm', 'pip', 'maven', 'go'
  license: 'string'         // e.g., 'MIT', 'Apache-2.0'
})

// CVE
CREATE (cve:CVE {
  cve_id: 'string',         // e.g., 'CVE-2021-44228'
  published_at: date(),
  cvss_score: 10.0,
  description: 'string'
})

// User
CREATE (u:User {
  login: 'string',          // GitHub username
  email: 'string',
  name: 'string'
})
```

---

## Relationships

### Relationship Diagram

```
                                    ┌──────────────┐
                                    │  Repository  │
                                    └──────┬───────┘
                                           │
                          ┌────────────────┼────────────────┐
                          │ HAS_PR         │ HAS_DEPENDENCY │
                          ▼                │                │
                   ┌─────────────┐         │                │
                   │ PullRequest │         │                │
                   └──────┬──────┘         │                │
                          │                │                │
               CONTAINS   │                │                │
               COMMIT     │                ▼                │
                          ▼         ┌────────────┐          │
                    ┌──────────┐    │ Dependency │◄─────────┘
                    │  Commit  │    └─────┬──────┘
                    └────┬─────┘          │
                         │                │ HAS_CVE
              ┌──────────┼──────────┐     ▼
              │ SCANNED  │ MODIFIES │  ┌──────────┐
              ▼          ▼          │  │   CVE    │
        ┌──────────┐  ┌──────┐      │  └────▲─────┘
        │   Scan   │  │ File │◄─────┼───────│─────────────┐
        └────┬─────┘  └──────┘      │       │ MAPS_TO     │
             │           ▲          │       │             │
             │ DETECTED  │ IN_FILE  │  ┌────┴──────────┐  │
             ▼           │          │  │ Vulnerability │──┘
      ┌──────────────────┴──────────┴──┴───────┬───────┘
      │                                        │
      │                           VIOLATES     │ IN_DEPENDENCY
      │                                        ▼
      │                                 ┌────────────┐
      └────────────────────────────────►│    Rule    │
                    USED_RULE           └────────────┘
```

### Relationship Definitions

```cypher
// Repository relationships
(:Repository)-[:HAS_PR]->(:PullRequest)
(:Repository)-[:HAS_DEPENDENCY]->(:Dependency)
(:Repository)-[:CONTAINS_FILE]->(:File)

// PullRequest relationships
(:PullRequest)-[:CONTAINS_COMMIT]->(:Commit)
(:PullRequest)-[:OPENED_BY]->(:User)
(:PullRequest)-[:REVIEWED_BY]->(:User)

// Commit relationships
(:Commit)-[:AUTHORED_BY]->(:User)
(:Commit)-[:MODIFIES {additions: 10, deletions: 5}]->(:File)
(:Commit)-[:SCANNED_BY]->(:Scan)

// Scan relationships
(:Scan)-[:DETECTED]->(:Vulnerability)
(:Scan)-[:USED_RULE]->(:Rule)

// Vulnerability relationships
(:Vulnerability)-[:IN_FILE {line: 42, column: 1}]->(:File)
(:Vulnerability)-[:IN_DEPENDENCY]->(:Dependency)
(:Vulnerability)-[:VIOLATES]->(:Rule)
(:Vulnerability)-[:MAPS_TO]->(:CVE)

// Dependency relationships
(:Dependency)-[:DEPENDS_ON]->(:Dependency)  // Transitive dependencies
(:Dependency)-[:HAS_CVE]->(:CVE)
```

---

## Example: Creating Scan Data

### KICS Scan (Infrastructure Vulnerability)

```cypher
// 1. Create or match repository
MERGE (r:Repository {owner: 'acme-corp', name: 'my-app'})
SET r.url = 'https://github.com/acme-corp/my-app'

// 2. Create PR and commit
CREATE (pr:PullRequest {
  number: 42,
  title: 'Add Terraform for AWS infrastructure',
  state: 'open',
  created_at: datetime()
})

CREATE (c:Commit {
  sha: 'abc123def456789',
  message: 'Add S3 bucket configuration',
  author: 'developer1',
  timestamp: datetime()
})

// 3. Link repository -> PR -> commit
MATCH (r:Repository {owner: 'acme-corp', name: 'my-app'})
MATCH (pr:PullRequest {number: 42})
MATCH (c:Commit {sha: 'abc123def456789'})
CREATE (r)-[:HAS_PR]->(pr)
CREATE (pr)-[:CONTAINS_COMMIT]->(c)

// 4. Create KICS scan
CREATE (s:Scan {
  id: randomUUID(),
  scanner: 'KICS',
  started_at: datetime(),
  completed_at: datetime(),
  status: 'completed'
})

// 5. Create vulnerability, file, and rule
CREATE (v:Vulnerability {
  id: randomUUID(),
  severity: 'HIGH',
  title: 'S3 Bucket Without Encryption',
  description: 'S3 bucket does not have server-side encryption enabled',
  cwe_id: 'CWE-311',
  cvss_score: 7.5,
  remediation: 'Enable SSE-S3 or SSE-KMS encryption on the bucket'
})

CREATE (f:File {
  path: 'infra/terraform/s3.tf',
  language: 'terraform'
})

MERGE (rule:Rule {rule_id: 'a227ec01-f97a-4084-91a4-47b350c1db54'})
SET rule.name = 'S3 Bucket SSE Disabled',
    rule.scanner = 'KICS',
    rule.category = 'Encryption',
    rule.severity = 'HIGH'

// 6. Link everything together
MATCH (c:Commit {sha: 'abc123def456789'})
MATCH (s:Scan {scanner: 'KICS'}) WHERE s.status = 'completed'
MATCH (v:Vulnerability {title: 'S3 Bucket Without Encryption'})
MATCH (f:File {path: 'infra/terraform/s3.tf'})
MATCH (rule:Rule {rule_id: 'a227ec01-f97a-4084-91a4-47b350c1db54'})
CREATE (c)-[:SCANNED_BY]->(s)
CREATE (s)-[:DETECTED]->(v)
CREATE (s)-[:USED_RULE]->(rule)
CREATE (v)-[:IN_FILE {line: 15, column: 1}]->(f)
CREATE (v)-[:VIOLATES]->(rule)
CREATE (c)-[:MODIFIES]->(f)
```

### Blackduck Scan (Dependency Vulnerability)

```cypher
// 1. Create Blackduck scan
CREATE (s:Scan {
  id: randomUUID(),
  scanner: 'BLACKDUCK',
  started_at: datetime(),
  completed_at: datetime(),
  status: 'completed'
})

// 2. Create dependency and CVE
CREATE (dep:Dependency {
  name: 'log4j-core',
  version: '2.14.1',
  ecosystem: 'maven',
  license: 'Apache-2.0'
})

CREATE (cve:CVE {
  cve_id: 'CVE-2021-44228',
  published_at: date('2021-12-10'),
  cvss_score: 10.0,
  description: 'Apache Log4j2 JNDI features do not protect against attacker controlled LDAP and other JNDI related endpoints'
})

// 3. Create vulnerability linked to dependency
CREATE (v:Vulnerability {
  id: randomUUID(),
  severity: 'CRITICAL',
  title: 'Log4Shell Remote Code Execution',
  description: 'Remote code execution via JNDI lookup in log messages',
  cwe_id: 'CWE-502',
  cvss_score: 10.0,
  remediation: 'Upgrade to log4j-core 2.17.0 or later'
})

// 4. Link scan results
MATCH (c:Commit {sha: 'abc123def456789'})
MATCH (r:Repository {owner: 'acme-corp', name: 'my-app'})
MATCH (s:Scan {scanner: 'BLACKDUCK'}) WHERE s.status = 'completed'
MATCH (v:Vulnerability {title: 'Log4Shell Remote Code Execution'})
MATCH (dep:Dependency {name: 'log4j-core', version: '2.14.1'})
MATCH (cve:CVE {cve_id: 'CVE-2021-44228'})
CREATE (c)-[:SCANNED_BY]->(s)
CREATE (s)-[:DETECTED]->(v)
CREATE (v)-[:IN_DEPENDENCY]->(dep)
CREATE (v)-[:MAPS_TO]->(cve)
CREATE (dep)-[:HAS_CVE]->(cve)
CREATE (r)-[:HAS_DEPENDENCY]->(dep)
```

---

## Common Queries

### 1. Which PRs introduced critical vulnerabilities?

```cypher
MATCH (r:Repository)-[:HAS_PR]->(pr:PullRequest)
      -[:CONTAINS_COMMIT]->(c:Commit)
      -[:SCANNED_BY]->(s:Scan)
      -[:DETECTED]->(v:Vulnerability)
WHERE v.severity = 'CRITICAL'
RETURN r.owner + '/' + r.name AS repo,
       pr.number AS pr_number,
       pr.title AS pr_title,
       collect(DISTINCT v.title) AS vulnerabilities,
       count(DISTINCT v) AS vuln_count
ORDER BY vuln_count DESC
```

### 2. All repositories affected by a specific CVE

```cypher
MATCH (r:Repository)-[:HAS_DEPENDENCY]->(d:Dependency)
      -[:HAS_CVE]->(cve:CVE {cve_id: 'CVE-2021-44228'})
RETURN r.owner, r.name, d.name, d.version
ORDER BY r.owner, r.name
```

### 3. Vulnerability trend over time (last 30 days)

```cypher
MATCH (r:Repository {name: 'my-app'})-[:HAS_PR]->(pr:PullRequest)
      -[:CONTAINS_COMMIT]->(c:Commit)
      -[:SCANNED_BY]->(s:Scan)
      -[:DETECTED]->(v:Vulnerability)
WHERE s.started_at > datetime() - duration('P30D')
RETURN date(s.started_at) AS scan_date,
       v.severity AS severity,
       count(v) AS count
ORDER BY scan_date, severity
```

### 4. Files with most vulnerabilities (hotspots)

```cypher
MATCH (v:Vulnerability)-[:IN_FILE]->(f:File)
RETURN f.path AS file,
       count(v) AS vulnerability_count,
       collect(DISTINCT v.severity) AS severities
ORDER BY vulnerability_count DESC
LIMIT 10
```

### 5. Transitive dependency vulnerabilities

```cypher
MATCH path = (d1:Dependency)-[:DEPENDS_ON*1..5]->(d2:Dependency)
      -[:HAS_CVE]->(cve:CVE)
WHERE d1.name = 'my-application'
RETURN d1.name AS root,
       [n IN nodes(path) | n.name + '@' + n.version] AS dependency_chain,
       cve.cve_id,
       cve.cvss_score
ORDER BY cve.cvss_score DESC
```

### 6. Compare findings between scanners

```cypher
MATCH (c:Commit)-[:SCANNED_BY]->(s1:Scan {scanner: 'KICS'})
      -[:DETECTED]->(v1:Vulnerability)
MATCH (c)-[:SCANNED_BY]->(s2:Scan {scanner: 'BLACKDUCK'})
      -[:DETECTED]->(v2:Vulnerability)
WHERE v1.cwe_id IS NOT NULL AND v1.cwe_id = v2.cwe_id
RETURN c.sha AS commit,
       v1.title AS kics_finding,
       v2.title AS blackduck_finding,
       v1.cwe_id AS common_cwe
```

### 7. Find commits that fixed vulnerabilities

```cypher
MATCH (pr:PullRequest)-[:CONTAINS_COMMIT]->(c1:Commit)
      -[:SCANNED_BY]->(:Scan)-[:DETECTED]->(v:Vulnerability)
      -[:IN_FILE]->(f:File)
WITH pr, c1, v, f
MATCH (pr)-[:CONTAINS_COMMIT]->(c2:Commit)-[:MODIFIES]->(f)
WHERE c2.timestamp > c1.timestamp
  AND NOT EXISTS {
    (c2)-[:SCANNED_BY]->(:Scan)-[:DETECTED]->(v)
  }
RETURN pr.number AS pr,
       v.title AS vulnerability,
       c1.sha AS introduced_in,
       c2.sha AS fixed_in
```

### 8. Security posture by repository

```cypher
MATCH (r:Repository)
OPTIONAL MATCH (r)-[:HAS_PR]->(:PullRequest)
               -[:CONTAINS_COMMIT]->(:Commit)
               -[:SCANNED_BY]->(:Scan)
               -[:DETECTED]->(v:Vulnerability)
WITH r, v.severity AS severity, count(v) AS cnt
RETURN r.owner + '/' + r.name AS repository,
       sum(CASE WHEN severity = 'CRITICAL' THEN cnt ELSE 0 END) AS critical,
       sum(CASE WHEN severity = 'HIGH' THEN cnt ELSE 0 END) AS high,
       sum(CASE WHEN severity = 'MEDIUM' THEN cnt ELSE 0 END) AS medium,
       sum(CASE WHEN severity = 'LOW' THEN cnt ELSE 0 END) AS low
ORDER BY critical DESC, high DESC
```

### 9. Unresolved vulnerabilities per PR

```cypher
MATCH (pr:PullRequest {state: 'open'})-[:CONTAINS_COMMIT]->(c:Commit)
      -[:SCANNED_BY]->(s:Scan)-[:DETECTED]->(v:Vulnerability)
WITH pr, c, v
ORDER BY c.timestamp DESC
WITH pr, collect(v)[0..100] AS recent_vulns  // Latest scan results
UNWIND recent_vulns AS v
RETURN pr.number AS pr,
       pr.title AS title,
       count(v) AS open_vulnerabilities,
       collect(DISTINCT v.severity) AS severities
ORDER BY open_vulnerabilities DESC
```

### 10. Mean time to remediation

```cypher
MATCH (v:Vulnerability)<-[:DETECTED]-(s1:Scan)<-[:SCANNED_BY]-(c1:Commit)
      <-[:CONTAINS_COMMIT]-(pr:PullRequest)
WHERE NOT EXISTS {
  MATCH (pr)-[:CONTAINS_COMMIT]->(c2:Commit)-[:SCANNED_BY]->(:Scan)
        -[:DETECTED]->(v)
  WHERE c2.timestamp > c1.timestamp
}
WITH v, s1.started_at AS introduced,
     [(pr)-[:CONTAINS_COMMIT]->(cx:Commit)
      WHERE cx.timestamp > c1.timestamp | cx.timestamp][0] AS fixed
WHERE fixed IS NOT NULL
RETURN v.severity AS severity,
       avg(duration.between(introduced, fixed).days) AS avg_days_to_fix
ORDER BY avg_days_to_fix DESC
```

---

## Schema Indexes

Create indexes for optimal query performance:

```cypher
// Unique constraints
CREATE CONSTRAINT repo_unique FOR (r:Repository) REQUIRE (r.owner, r.name) IS UNIQUE;
CREATE CONSTRAINT commit_sha_unique FOR (c:Commit) REQUIRE c.sha IS UNIQUE;
CREATE CONSTRAINT cve_id_unique FOR (cve:CVE) REQUIRE cve.cve_id IS UNIQUE;
CREATE CONSTRAINT scan_id_unique FOR (s:Scan) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT vuln_id_unique FOR (v:Vulnerability) REQUIRE v.id IS UNIQUE;

// Lookup indexes
CREATE INDEX repo_name FOR (r:Repository) ON (r.name);
CREATE INDEX pr_number FOR (pr:PullRequest) ON (pr.number);
CREATE INDEX pr_state FOR (pr:PullRequest) ON (pr.state);
CREATE INDEX commit_timestamp FOR (c:Commit) ON (c.timestamp);
CREATE INDEX scan_scanner FOR (s:Scan) ON (s.scanner);
CREATE INDEX scan_status FOR (s:Scan) ON (s.status);
CREATE INDEX vuln_severity FOR (v:Vulnerability) ON (v.severity);
CREATE INDEX vuln_cwe FOR (v:Vulnerability) ON (v.cwe_id);
CREATE INDEX dep_ecosystem FOR (d:Dependency) ON (d.ecosystem);
CREATE INDEX dep_name_ver FOR (d:Dependency) ON (d.name, d.version);
CREATE INDEX rule_scanner FOR (r:Rule) ON (r.scanner);
CREATE INDEX file_path FOR (f:File) ON (f.path);
```

---

## Why Graph vs Relational?

| Query Type | Graph (Neo4j) | Relational (PostgreSQL) |
|------------|---------------|-------------------------|
| **"Which PRs introduced CVE-X?"** | Single traversal: `(PR)->(Commit)->(Scan)->(Vuln)->(CVE)` | 4-5 table JOINs |
| **"Show transitive dependency vulnerabilities"** | Variable-length path: `[:DEPENDS_ON*1..10]` | Recursive CTE (complex, slow) |
| **"Common vulnerabilities across repos"** | Pattern matching across subgraphs | Complex subqueries with INTERSECT |
| **"Vulnerability lineage through commits"** | Natural traversal following relationships | Window functions + self-joins |
| **"Which files are modified together with vulns?"** | Co-occurrence pattern matching | GROUP BY with HAVING + subquery |
| **"Path from repo to CVE"** | `shortestPath()` function | Multiple queries or materialized paths |
| **Schema evolution** | Add properties/labels anytime | ALTER TABLE migrations |
| **Query readability** | Matches mental model of relationships | SQL expertise required |

### When to Use Graph

- **High relationship density** - Many connections between entities
- **Variable-depth queries** - "Find all transitive dependencies"
- **Pattern matching** - "Find repos with same vulnerability pattern"
- **Real-time traversals** - Dashboard queries following links

### When to Use Relational

- **Heavy aggregations** - "Sum of vulnerabilities by month"
- **Strict schema enforcement** - Compliance requirements
- **Simple CRUD operations** - Basic insert/update/delete
- **Existing PostgreSQL infrastructure** - Lower operational overhead

### Hybrid Approach

Consider using both:
- **PostgreSQL**: Audit logs, user management, simple lookups
- **Neo4j**: Relationship queries, dependency analysis, impact assessment

---

## Integration with Workers

### Worker Callback Payload

When workers complete a scan, they should POST results that can be transformed to graph data:

```json
{
  "scan_id": "uuid",
  "scanner": "KICS",
  "commit_sha": "abc123",
  "repository": {
    "owner": "acme-corp",
    "name": "my-app"
  },
  "findings": [
    {
      "id": "finding-uuid",
      "severity": "HIGH",
      "title": "S3 Bucket Without Encryption",
      "description": "...",
      "cwe_id": "CWE-311",
      "file": {
        "path": "infra/s3.tf",
        "line": 15
      },
      "rule": {
        "id": "a227ec01-f97a-4084-91a4-47b350c1db54",
        "name": "S3 Bucket SSE Disabled"
      }
    }
  ]
}
```

### Python Integration Example

```python
from neo4j import GraphDatabase

class SecurityGraphDB:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def store_scan_results(self, scan_data: dict):
        with self.driver.session() as session:
            session.execute_write(self._create_scan_graph, scan_data)

    @staticmethod
    def _create_scan_graph(tx, data):
        # Create scan node and link to commit
        tx.run("""
            MATCH (c:Commit {sha: $commit_sha})
            CREATE (s:Scan {
                id: $scan_id,
                scanner: $scanner,
                completed_at: datetime()
            })
            CREATE (c)-[:SCANNED_BY]->(s)
            WITH s
            UNWIND $findings AS finding
            CREATE (v:Vulnerability {
                id: finding.id,
                severity: finding.severity,
                title: finding.title,
                cwe_id: finding.cwe_id
            })
            CREATE (s)-[:DETECTED]->(v)
            MERGE (f:File {path: finding.file.path})
            CREATE (v)-[:IN_FILE {line: finding.file.line}]->(f)
            MERGE (r:Rule {rule_id: finding.rule.id})
            SET r.name = finding.rule.name
            CREATE (v)-[:VIOLATES]->(r)
        """, commit_sha=data['commit_sha'],
             scan_id=data['scan_id'],
             scanner=data['scanner'],
             findings=data['findings'])
```

---

## Docker Setup for Development

```yaml
# Add to docker-compose.yaml
neo4j:
  image: neo4j:5
  container_name: neo4j
  ports:
    - "7474:7474"  # HTTP
    - "7687:7687"  # Bolt
  environment:
    - NEO4J_AUTH=neo4j/password123
    - NEO4J_PLUGINS=["apoc"]
  volumes:
    - neo4j-data:/data
  networks:
    - github-app-network

volumes:
  neo4j-data:
```

Access Neo4j Browser at `http://localhost:7474`

---

*Last updated: February 2026*
