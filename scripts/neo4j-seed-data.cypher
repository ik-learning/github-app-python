// ============================================================================
// Neo4j Seed Data Script - Security Scan Demo Data
// ============================================================================
// Purpose: Generate ~200 records to demonstrate key graph queries
// Run with: cat neo4j-seed-data.cypher | cypher-shell -u neo4j -p password123
// Or paste into Neo4j Browser at http://localhost:7474
// ============================================================================

// ----------------------------------------------------------------------------
// CLEANUP - Remove existing data (optional)
// ----------------------------------------------------------------------------
// MATCH (n) DETACH DELETE n;

// ----------------------------------------------------------------------------
// 1. CREATE INDEXES (run once)
// ----------------------------------------------------------------------------

CREATE CONSTRAINT repo_unique IF NOT EXISTS FOR (r:Repository) REQUIRE (r.owner, r.name) IS UNIQUE;
CREATE CONSTRAINT commit_sha_unique IF NOT EXISTS FOR (c:Commit) REQUIRE c.sha IS UNIQUE;
CREATE CONSTRAINT cve_id_unique IF NOT EXISTS FOR (cve:CVE) REQUIRE cve.cve_id IS UNIQUE;
CREATE INDEX vuln_severity IF NOT EXISTS FOR (v:Vulnerability) ON (v.severity);
CREATE INDEX dep_name IF NOT EXISTS FOR (d:Dependency) ON (d.name);
CREATE INDEX scan_scanner IF NOT EXISTS FOR (s:Scan) ON (s.scanner);

// ----------------------------------------------------------------------------
// 2. CREATE CVEs (shared across repos - key for "common vulns" query)
// ----------------------------------------------------------------------------

CREATE (cve1:CVE {
  cve_id: 'CVE-2021-44228',
  published_at: date('2021-12-10'),
  cvss_score: 10.0,
  description: 'Apache Log4j2 JNDI RCE (Log4Shell)'
})

CREATE (cve2:CVE {
  cve_id: 'CVE-2022-22965',
  published_at: date('2022-03-31'),
  cvss_score: 9.8,
  description: 'Spring Framework RCE (Spring4Shell)'
})

CREATE (cve3:CVE {
  cve_id: 'CVE-2023-34362',
  published_at: date('2023-06-02'),
  cvss_score: 9.8,
  description: 'MOVEit Transfer SQL Injection'
})

CREATE (cve4:CVE {
  cve_id: 'CVE-2021-45046',
  published_at: date('2021-12-14'),
  cvss_score: 9.0,
  description: 'Apache Log4j2 DoS and RCE'
})

CREATE (cve5:CVE {
  cve_id: 'CVE-2022-42889',
  published_at: date('2022-10-13'),
  cvss_score: 9.8,
  description: 'Apache Commons Text RCE (Text4Shell)'
})

CREATE (cve6:CVE {
  cve_id: 'CVE-2023-44487',
  published_at: date('2023-10-10'),
  cvss_score: 7.5,
  description: 'HTTP/2 Rapid Reset Attack'
})

CREATE (cve7:CVE {
  cve_id: 'CVE-2024-3094',
  published_at: date('2024-03-29'),
  cvss_score: 10.0,
  description: 'XZ Utils Backdoor'
});

// ----------------------------------------------------------------------------
// 3. CREATE DEPENDENCIES (with transitive relationships)
// ----------------------------------------------------------------------------

// Log4j dependency chain (demonstrates transitive vulns)
CREATE (d_log4j_core:Dependency {name: 'log4j-core', version: '2.14.1', ecosystem: 'maven', license: 'Apache-2.0'})
CREATE (d_log4j_api:Dependency {name: 'log4j-api', version: '2.14.1', ecosystem: 'maven', license: 'Apache-2.0'})
CREATE (d_spring_boot:Dependency {name: 'spring-boot-starter', version: '2.6.1', ecosystem: 'maven', license: 'Apache-2.0'})
CREATE (d_spring_core:Dependency {name: 'spring-core', version: '5.3.18', ecosystem: 'maven', license: 'Apache-2.0'})

// Commons chain
CREATE (d_commons_text:Dependency {name: 'commons-text', version: '1.9', ecosystem: 'maven', license: 'Apache-2.0'})
CREATE (d_commons_lang:Dependency {name: 'commons-lang3', version: '3.12.0', ecosystem: 'maven', license: 'Apache-2.0'})

// Node.js dependencies
CREATE (d_express:Dependency {name: 'express', version: '4.17.1', ecosystem: 'npm', license: 'MIT'})
CREATE (d_lodash:Dependency {name: 'lodash', version: '4.17.20', ecosystem: 'npm', license: 'MIT'})
CREATE (d_axios:Dependency {name: 'axios', version: '0.21.1', ecosystem: 'npm', license: 'MIT'})

// Python dependencies
CREATE (d_requests:Dependency {name: 'requests', version: '2.25.1', ecosystem: 'pip', license: 'Apache-2.0'})
CREATE (d_urllib3:Dependency {name: 'urllib3', version: '1.26.4', ecosystem: 'pip', license: 'MIT'})
CREATE (d_flask:Dependency {name: 'flask', version: '2.0.1', ecosystem: 'pip', license: 'BSD-3'})

// Fixed versions
CREATE (d_log4j_core_fixed:Dependency {name: 'log4j-core', version: '2.17.1', ecosystem: 'maven', license: 'Apache-2.0'})
CREATE (d_spring_core_fixed:Dependency {name: 'spring-core', version: '5.3.20', ecosystem: 'maven', license: 'Apache-2.0'})
CREATE (d_commons_text_fixed:Dependency {name: 'commons-text', version: '1.10.0', ecosystem: 'maven', license: 'Apache-2.0'});

// Link transitive dependencies
MATCH (parent:Dependency {name: 'spring-boot-starter', version: '2.6.1'})
MATCH (child1:Dependency {name: 'spring-core', version: '5.3.18'})
MATCH (child2:Dependency {name: 'log4j-core', version: '2.14.1'})
CREATE (parent)-[:DEPENDS_ON]->(child1)
CREATE (parent)-[:DEPENDS_ON]->(child2);

MATCH (parent:Dependency {name: 'log4j-core', version: '2.14.1'})
MATCH (child:Dependency {name: 'log4j-api', version: '2.14.1'})
CREATE (parent)-[:DEPENDS_ON]->(child);

MATCH (parent:Dependency {name: 'commons-text', version: '1.9'})
MATCH (child:Dependency {name: 'commons-lang3', version: '3.12.0'})
CREATE (parent)-[:DEPENDS_ON]->(child);

MATCH (parent:Dependency {name: 'express', version: '4.17.1'})
MATCH (child:Dependency {name: 'lodash', version: '4.17.20'})
CREATE (parent)-[:DEPENDS_ON]->(child);

MATCH (parent:Dependency {name: 'requests', version: '2.25.1'})
MATCH (child:Dependency {name: 'urllib3', version: '1.26.4'})
CREATE (parent)-[:DEPENDS_ON]->(child);

// Link CVEs to vulnerable dependencies
MATCH (d:Dependency {name: 'log4j-core', version: '2.14.1'})
MATCH (cve:CVE {cve_id: 'CVE-2021-44228'})
CREATE (d)-[:HAS_CVE]->(cve);

MATCH (d:Dependency {name: 'log4j-core', version: '2.14.1'})
MATCH (cve:CVE {cve_id: 'CVE-2021-45046'})
CREATE (d)-[:HAS_CVE]->(cve);

MATCH (d:Dependency {name: 'spring-core', version: '5.3.18'})
MATCH (cve:CVE {cve_id: 'CVE-2022-22965'})
CREATE (d)-[:HAS_CVE]->(cve);

MATCH (d:Dependency {name: 'commons-text', version: '1.9'})
MATCH (cve:CVE {cve_id: 'CVE-2022-42889'})
CREATE (d)-[:HAS_CVE]->(cve);

// ----------------------------------------------------------------------------
// 4. CREATE KICS RULES
// ----------------------------------------------------------------------------

CREATE (r1:Rule {rule_id: 'a227ec01-f97a-4084-91a4-47b350c1db54', name: 'S3 Bucket SSE Disabled', scanner: 'KICS', category: 'Encryption', severity: 'HIGH'})
CREATE (r2:Rule {rule_id: 'b5c77288-f9c8-4864-ad8c-4e3d3ab4bc78', name: 'Security Group Unrestricted Ingress', scanner: 'KICS', category: 'Networking', severity: 'CRITICAL'})
CREATE (r3:Rule {rule_id: 'c8b34e84-2a58-4e21-b9c7-32a1dec5f6ab', name: 'IAM Policy Allows All Resources', scanner: 'KICS', category: 'Access Control', severity: 'HIGH'})
CREATE (r4:Rule {rule_id: 'd9a45f12-8c67-4b39-9e12-54a2bc3e7f89', name: 'Container Running as Root', scanner: 'KICS', category: 'Container Security', severity: 'MEDIUM'})
CREATE (r5:Rule {rule_id: 'e1b23c45-6d78-4f90-a123-bc456def7890', name: 'Missing Resource Limits', scanner: 'KICS', category: 'Resource Management', severity: 'LOW'})
CREATE (r6:Rule {rule_id: 'f2c34d56-7e89-4a01-b234-cd567ef89012', name: 'Secrets in Environment Variables', scanner: 'KICS', category: 'Secret Management', severity: 'CRITICAL'})
CREATE (r7:Rule {rule_id: 'g3d45e67-8f90-4b12-c345-de678f901234', name: 'RDS Publicly Accessible', scanner: 'KICS', category: 'Networking', severity: 'HIGH'})
CREATE (r8:Rule {rule_id: 'h4e56f78-9012-4c23-d456-ef789a012345', name: 'CloudTrail Disabled', scanner: 'KICS', category: 'Logging', severity: 'MEDIUM'});

// ----------------------------------------------------------------------------
// 5. CREATE REPOSITORIES
// ----------------------------------------------------------------------------

CREATE (repo1:Repository {name: 'payment-service', owner: 'acme-corp', url: 'https://github.com/acme-corp/payment-service', default_branch: 'main'})
CREATE (repo2:Repository {name: 'user-api', owner: 'acme-corp', url: 'https://github.com/acme-corp/user-api', default_branch: 'main'})
CREATE (repo3:Repository {name: 'inventory-manager', owner: 'acme-corp', url: 'https://github.com/acme-corp/inventory-manager', default_branch: 'main'})
CREATE (repo4:Repository {name: 'notification-worker', owner: 'acme-corp', url: 'https://github.com/acme-corp/notification-worker', default_branch: 'main'})
CREATE (repo5:Repository {name: 'analytics-dashboard', owner: 'acme-corp', url: 'https://github.com/acme-corp/analytics-dashboard', default_branch: 'main'})
CREATE (repo6:Repository {name: 'shared-infra', owner: 'acme-corp', url: 'https://github.com/acme-corp/shared-infra', default_branch: 'main'});

// Link repositories to dependencies (showing same vulnerable dep across repos)
MATCH (r:Repository {name: 'payment-service'}), (d:Dependency {name: 'log4j-core', version: '2.14.1'}) CREATE (r)-[:HAS_DEPENDENCY]->(d);
MATCH (r:Repository {name: 'user-api'}), (d:Dependency {name: 'log4j-core', version: '2.14.1'}) CREATE (r)-[:HAS_DEPENDENCY]->(d);
MATCH (r:Repository {name: 'inventory-manager'}), (d:Dependency {name: 'log4j-core', version: '2.14.1'}) CREATE (r)-[:HAS_DEPENDENCY]->(d);
MATCH (r:Repository {name: 'notification-worker'}), (d:Dependency {name: 'spring-boot-starter', version: '2.6.1'}) CREATE (r)-[:HAS_DEPENDENCY]->(d);
MATCH (r:Repository {name: 'analytics-dashboard'}), (d:Dependency {name: 'commons-text', version: '1.9'}) CREATE (r)-[:HAS_DEPENDENCY]->(d);
MATCH (r:Repository {name: 'payment-service'}), (d:Dependency {name: 'spring-core', version: '5.3.18'}) CREATE (r)-[:HAS_DEPENDENCY]->(d);
MATCH (r:Repository {name: 'user-api'}), (d:Dependency {name: 'express', version: '4.17.1'}) CREATE (r)-[:HAS_DEPENDENCY]->(d);
MATCH (r:Repository {name: 'shared-infra'}), (d:Dependency {name: 'flask', version: '2.0.1'}) CREATE (r)-[:HAS_DEPENDENCY]->(d);

// ----------------------------------------------------------------------------
// 6. CREATE FILES
// ----------------------------------------------------------------------------

CREATE (f1:File {path: 'infra/terraform/s3.tf', language: 'terraform'})
CREATE (f2:File {path: 'infra/terraform/security-groups.tf', language: 'terraform'})
CREATE (f3:File {path: 'infra/terraform/iam.tf', language: 'terraform'})
CREATE (f4:File {path: 'infra/terraform/rds.tf', language: 'terraform'})
CREATE (f5:File {path: 'k8s/deployment.yaml', language: 'yaml'})
CREATE (f6:File {path: 'k8s/service.yaml', language: 'yaml'})
CREATE (f7:File {path: 'docker/Dockerfile', language: 'dockerfile'})
CREATE (f8:File {path: 'docker/docker-compose.yaml', language: 'yaml'})
CREATE (f9:File {path: 'src/main/resources/application.yaml', language: 'yaml'})
CREATE (f10:File {path: 'pom.xml', language: 'xml'})
CREATE (f11:File {path: 'package.json', language: 'json'})
CREATE (f12:File {path: 'requirements.txt', language: 'text'})
CREATE (f13:File {path: '.github/workflows/ci.yaml', language: 'yaml'})
CREATE (f14:File {path: 'infra/cloudformation/main.yaml', language: 'yaml'});

// ----------------------------------------------------------------------------
// 7. CREATE USERS
// ----------------------------------------------------------------------------

CREATE (u1:User {login: 'alice-dev', email: 'alice@acme-corp.com', name: 'Alice Developer'})
CREATE (u2:User {login: 'bob-sec', email: 'bob@acme-corp.com', name: 'Bob Security'})
CREATE (u3:User {login: 'charlie-ops', email: 'charlie@acme-corp.com', name: 'Charlie DevOps'})
CREATE (u4:User {login: 'diana-lead', email: 'diana@acme-corp.com', name: 'Diana Tech Lead'})
CREATE (u5:User {login: 'eve-junior', email: 'eve@acme-corp.com', name: 'Eve Junior Dev'});

// ============================================================================
// 8. CREATE PULL REQUESTS, COMMITS, SCANS, AND VULNERABILITIES
// ============================================================================

// ----------------------------------------------------------------------------
// REPO 1: payment-service - Shows vulnerability lineage (introduced -> fixed)
// ----------------------------------------------------------------------------

// PR #101 - Introduces Log4Shell vulnerability
MATCH (repo:Repository {name: 'payment-service'})
MATCH (user:User {login: 'eve-junior'})
CREATE (pr:PullRequest {
  number: 101,
  title: 'Add logging framework for payment transactions',
  state: 'merged',
  created_at: datetime('2021-11-15T10:00:00Z'),
  merged_at: datetime('2021-11-16T14:00:00Z')
})
CREATE (repo)-[:HAS_PR]->(pr)
CREATE (pr)-[:OPENED_BY]->(user)

CREATE (c1:Commit {
  sha: 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f60101',
  message: 'Add log4j dependency for structured logging',
  author: 'eve-junior',
  timestamp: datetime('2021-11-15T10:30:00Z')
})
CREATE (pr)-[:CONTAINS_COMMIT]->(c1)

CREATE (scan1:Scan {
  id: 'scan-ps-101-bd',
  scanner: 'BLACKDUCK',
  started_at: datetime('2021-11-15T10:35:00Z'),
  completed_at: datetime('2021-11-15T10:40:00Z'),
  status: 'completed'
})
CREATE (c1)-[:SCANNED_BY]->(scan1)

WITH scan1
MATCH (cve:CVE {cve_id: 'CVE-2021-44228'})
MATCH (dep:Dependency {name: 'log4j-core', version: '2.14.1'})
CREATE (v:Vulnerability {
  id: 'vuln-ps-101-001',
  severity: 'CRITICAL',
  title: 'Log4Shell RCE in log4j-core',
  description: 'Remote code execution via JNDI lookup',
  cwe_id: 'CWE-502',
  cvss_score: 10.0,
  remediation: 'Upgrade to log4j-core 2.17.1 or later'
})
CREATE (scan1)-[:DETECTED]->(v)
CREATE (v)-[:IN_DEPENDENCY]->(dep)
CREATE (v)-[:MAPS_TO]->(cve);

// PR #115 - Fixes Log4Shell (shows lineage)
MATCH (repo:Repository {name: 'payment-service'})
MATCH (user:User {login: 'bob-sec'})
CREATE (pr:PullRequest {
  number: 115,
  title: 'SECURITY: Upgrade log4j to fix CVE-2021-44228',
  state: 'merged',
  created_at: datetime('2021-12-13T08:00:00Z'),
  merged_at: datetime('2021-12-13T09:30:00Z')
})
CREATE (repo)-[:HAS_PR]->(pr)
CREATE (pr)-[:OPENED_BY]->(user)

CREATE (c1:Commit {
  sha: 'b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f60115',
  message: 'Upgrade log4j-core to 2.17.1',
  author: 'bob-sec',
  timestamp: datetime('2021-12-13T08:30:00Z')
})
CREATE (pr)-[:CONTAINS_COMMIT]->(c1)

CREATE (scan1:Scan {
  id: 'scan-ps-115-bd',
  scanner: 'BLACKDUCK',
  started_at: datetime('2021-12-13T08:35:00Z'),
  completed_at: datetime('2021-12-13T08:40:00Z'),
  status: 'completed'
})
CREATE (c1)-[:SCANNED_BY]->(scan1);
// No vulnerabilities detected - clean scan after fix

// PR #120 - Adds infrastructure with KICS issues
MATCH (repo:Repository {name: 'payment-service'})
MATCH (user:User {login: 'charlie-ops'})
CREATE (pr:PullRequest {
  number: 120,
  title: 'Add Terraform for payment service infrastructure',
  state: 'merged',
  created_at: datetime('2022-01-10T09:00:00Z'),
  merged_at: datetime('2022-01-11T16:00:00Z')
})
CREATE (repo)-[:HAS_PR]->(pr)
CREATE (pr)-[:OPENED_BY]->(user)

CREATE (c1:Commit {
  sha: 'c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f60120a',
  message: 'Add S3 bucket for payment receipts',
  author: 'charlie-ops',
  timestamp: datetime('2022-01-10T09:30:00Z')
})
CREATE (c2:Commit {
  sha: 'c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f60120b',
  message: 'Add security groups for payment API',
  author: 'charlie-ops',
  timestamp: datetime('2022-01-10T14:00:00Z')
})
CREATE (pr)-[:CONTAINS_COMMIT]->(c1)
CREATE (pr)-[:CONTAINS_COMMIT]->(c2)

WITH c1, c2
MATCH (f_s3:File {path: 'infra/terraform/s3.tf'})
MATCH (f_sg:File {path: 'infra/terraform/security-groups.tf'})
MATCH (rule_s3:Rule {name: 'S3 Bucket SSE Disabled'})
MATCH (rule_sg:Rule {name: 'Security Group Unrestricted Ingress'})

CREATE (scan1:Scan {
  id: 'scan-ps-120a-kics',
  scanner: 'KICS',
  started_at: datetime('2022-01-10T09:35:00Z'),
  completed_at: datetime('2022-01-10T09:38:00Z'),
  status: 'completed'
})
CREATE (c1)-[:SCANNED_BY]->(scan1)
CREATE (c1)-[:MODIFIES]->(f_s3)

CREATE (v1:Vulnerability {
  id: 'vuln-ps-120-001',
  severity: 'HIGH',
  title: 'S3 Bucket Without Server-Side Encryption',
  description: 'Payment receipts bucket does not have encryption enabled',
  cwe_id: 'CWE-311',
  cvss_score: 7.5,
  remediation: 'Enable SSE-S3 or SSE-KMS encryption'
})
CREATE (scan1)-[:DETECTED]->(v1)
CREATE (v1)-[:IN_FILE {line: 15, column: 1}]->(f_s3)
CREATE (v1)-[:VIOLATES]->(rule_s3)
CREATE (scan1)-[:USED_RULE]->(rule_s3)

CREATE (scan2:Scan {
  id: 'scan-ps-120b-kics',
  scanner: 'KICS',
  started_at: datetime('2022-01-10T14:05:00Z'),
  completed_at: datetime('2022-01-10T14:08:00Z'),
  status: 'completed'
})
CREATE (c2)-[:SCANNED_BY]->(scan2)
CREATE (c2)-[:MODIFIES]->(f_sg)

CREATE (v2:Vulnerability {
  id: 'vuln-ps-120-002',
  severity: 'CRITICAL',
  title: 'Security Group Allows Unrestricted Ingress on Port 22',
  description: 'SSH port open to 0.0.0.0/0',
  cwe_id: 'CWE-284',
  cvss_score: 9.1,
  remediation: 'Restrict ingress to specific IP ranges'
})
CREATE (scan2)-[:DETECTED]->(v2)
CREATE (v2)-[:IN_FILE {line: 28, column: 5}]->(f_sg)
CREATE (v2)-[:VIOLATES]->(rule_sg)
CREATE (scan2)-[:USED_RULE]->(rule_sg);

// ----------------------------------------------------------------------------
// REPO 2: user-api - Also has Log4Shell (common vuln across repos)
// ----------------------------------------------------------------------------

MATCH (repo:Repository {name: 'user-api'})
MATCH (user:User {login: 'alice-dev'})
CREATE (pr:PullRequest {
  number: 45,
  title: 'Implement user authentication service',
  state: 'merged',
  created_at: datetime('2021-10-20T11:00:00Z'),
  merged_at: datetime('2021-10-21T15:00:00Z')
})
CREATE (repo)-[:HAS_PR]->(pr)
CREATE (pr)-[:OPENED_BY]->(user)

CREATE (c1:Commit {
  sha: 'd4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b20045',
  message: 'Add authentication with JWT and logging',
  author: 'alice-dev',
  timestamp: datetime('2021-10-20T11:30:00Z')
})
CREATE (pr)-[:CONTAINS_COMMIT]->(c1)

CREATE (scan1:Scan {
  id: 'scan-ua-45-bd',
  scanner: 'BLACKDUCK',
  started_at: datetime('2021-10-20T11:35:00Z'),
  completed_at: datetime('2021-10-20T11:42:00Z'),
  status: 'completed'
})
CREATE (c1)-[:SCANNED_BY]->(scan1)

WITH scan1
MATCH (cve:CVE {cve_id: 'CVE-2021-44228'})
MATCH (dep:Dependency {name: 'log4j-core', version: '2.14.1'})
CREATE (v:Vulnerability {
  id: 'vuln-ua-45-001',
  severity: 'CRITICAL',
  title: 'Log4Shell RCE in log4j-core',
  description: 'Remote code execution via JNDI lookup',
  cwe_id: 'CWE-502',
  cvss_score: 10.0,
  remediation: 'Upgrade to log4j-core 2.17.1 or later'
})
CREATE (scan1)-[:DETECTED]->(v)
CREATE (v)-[:IN_DEPENDENCY]->(dep)
CREATE (v)-[:MAPS_TO]->(cve);

// PR #52 - Adds Kubernetes deployment with issues
MATCH (repo:Repository {name: 'user-api'})
MATCH (user:User {login: 'charlie-ops'})
CREATE (pr:PullRequest {
  number: 52,
  title: 'Add Kubernetes manifests for user-api',
  state: 'open',
  created_at: datetime('2022-02-15T10:00:00Z'),
  merged_at: null
})
CREATE (repo)-[:HAS_PR]->(pr)
CREATE (pr)-[:OPENED_BY]->(user)

CREATE (c1:Commit {
  sha: 'e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c30052',
  message: 'Add deployment and service manifests',
  author: 'charlie-ops',
  timestamp: datetime('2022-02-15T10:30:00Z')
})
CREATE (pr)-[:CONTAINS_COMMIT]->(c1)

WITH c1
MATCH (f_deploy:File {path: 'k8s/deployment.yaml'})
MATCH (rule_root:Rule {name: 'Container Running as Root'})
MATCH (rule_limits:Rule {name: 'Missing Resource Limits'})

CREATE (scan1:Scan {
  id: 'scan-ua-52-kics',
  scanner: 'KICS',
  started_at: datetime('2022-02-15T10:35:00Z'),
  completed_at: datetime('2022-02-15T10:38:00Z'),
  status: 'completed'
})
CREATE (c1)-[:SCANNED_BY]->(scan1)
CREATE (c1)-[:MODIFIES]->(f_deploy)

CREATE (v1:Vulnerability {
  id: 'vuln-ua-52-001',
  severity: 'MEDIUM',
  title: 'Container Running as Root User',
  description: 'Pod security context does not specify non-root user',
  cwe_id: 'CWE-250',
  cvss_score: 5.5,
  remediation: 'Set securityContext.runAsNonRoot: true'
})
CREATE (v2:Vulnerability {
  id: 'vuln-ua-52-002',
  severity: 'LOW',
  title: 'Missing CPU and Memory Limits',
  description: 'Container does not specify resource limits',
  cwe_id: 'CWE-770',
  cvss_score: 3.5,
  remediation: 'Add resources.limits section'
})
CREATE (scan1)-[:DETECTED]->(v1)
CREATE (scan1)-[:DETECTED]->(v2)
CREATE (v1)-[:IN_FILE {line: 22, column: 8}]->(f_deploy)
CREATE (v2)-[:IN_FILE {line: 18, column: 8}]->(f_deploy)
CREATE (v1)-[:VIOLATES]->(rule_root)
CREATE (v2)-[:VIOLATES]->(rule_limits)
CREATE (scan1)-[:USED_RULE]->(rule_root)
CREATE (scan1)-[:USED_RULE]->(rule_limits);

// ----------------------------------------------------------------------------
// REPO 3: inventory-manager - Log4Shell + Spring4Shell (multiple CVEs)
// ----------------------------------------------------------------------------

MATCH (repo:Repository {name: 'inventory-manager'})
MATCH (user:User {login: 'diana-lead'})
CREATE (pr:PullRequest {
  number: 78,
  title: 'Migrate to Spring Boot for inventory management',
  state: 'merged',
  created_at: datetime('2022-02-01T09:00:00Z'),
  merged_at: datetime('2022-02-03T17:00:00Z')
})
CREATE (repo)-[:HAS_PR]->(pr)
CREATE (pr)-[:OPENED_BY]->(user)

CREATE (c1:Commit {
  sha: 'f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d40078',
  message: 'Add Spring Boot starter with logging',
  author: 'diana-lead',
  timestamp: datetime('2022-02-01T09:30:00Z')
})
CREATE (pr)-[:CONTAINS_COMMIT]->(c1)

CREATE (scan1:Scan {
  id: 'scan-im-78-bd',
  scanner: 'BLACKDUCK',
  started_at: datetime('2022-02-01T09:35:00Z'),
  completed_at: datetime('2022-02-01T09:50:00Z'),
  status: 'completed'
})
CREATE (c1)-[:SCANNED_BY]->(scan1)

WITH scan1
MATCH (cve1:CVE {cve_id: 'CVE-2021-44228'})
MATCH (cve2:CVE {cve_id: 'CVE-2022-22965'})
MATCH (dep_log4j:Dependency {name: 'log4j-core', version: '2.14.1'})
MATCH (dep_spring:Dependency {name: 'spring-core', version: '5.3.18'})

CREATE (v1:Vulnerability {
  id: 'vuln-im-78-001',
  severity: 'CRITICAL',
  title: 'Log4Shell RCE in log4j-core',
  description: 'Remote code execution via JNDI lookup',
  cwe_id: 'CWE-502',
  cvss_score: 10.0,
  remediation: 'Upgrade to log4j-core 2.17.1 or later'
})
CREATE (v2:Vulnerability {
  id: 'vuln-im-78-002',
  severity: 'CRITICAL',
  title: 'Spring4Shell RCE in spring-core',
  description: 'Remote code execution via data binding',
  cwe_id: 'CWE-94',
  cvss_score: 9.8,
  remediation: 'Upgrade to spring-core 5.3.20 or later'
})
CREATE (scan1)-[:DETECTED]->(v1)
CREATE (scan1)-[:DETECTED]->(v2)
CREATE (v1)-[:IN_DEPENDENCY]->(dep_log4j)
CREATE (v2)-[:IN_DEPENDENCY]->(dep_spring)
CREATE (v1)-[:MAPS_TO]->(cve1)
CREATE (v2)-[:MAPS_TO]->(cve2);

// ----------------------------------------------------------------------------
// REPO 4: notification-worker - Transitive dependency vulnerability
// ----------------------------------------------------------------------------

MATCH (repo:Repository {name: 'notification-worker'})
MATCH (user:User {login: 'eve-junior'})
CREATE (pr:PullRequest {
  number: 23,
  title: 'Initialize notification worker service',
  state: 'merged',
  created_at: datetime('2022-03-10T14:00:00Z'),
  merged_at: datetime('2022-03-11T10:00:00Z')
})
CREATE (repo)-[:HAS_PR]->(pr)
CREATE (pr)-[:OPENED_BY]->(user)

CREATE (c1:Commit {
  sha: 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e50023',
  message: 'Add spring-boot-starter for message processing',
  author: 'eve-junior',
  timestamp: datetime('2022-03-10T14:30:00Z')
})
CREATE (pr)-[:CONTAINS_COMMIT]->(c1)

CREATE (scan1:Scan {
  id: 'scan-nw-23-bd',
  scanner: 'BLACKDUCK',
  started_at: datetime('2022-03-10T14:35:00Z'),
  completed_at: datetime('2022-03-10T14:55:00Z'),
  status: 'completed'
})
CREATE (c1)-[:SCANNED_BY]->(scan1)

WITH scan1
MATCH (cve:CVE {cve_id: 'CVE-2021-44228'})
MATCH (dep_starter:Dependency {name: 'spring-boot-starter', version: '2.6.1'})
MATCH (dep_log4j:Dependency {name: 'log4j-core', version: '2.14.1'})

// Vulnerability found through transitive dependency
CREATE (v:Vulnerability {
  id: 'vuln-nw-23-001',
  severity: 'CRITICAL',
  title: 'Log4Shell via transitive dependency spring-boot-starter -> log4j-core',
  description: 'Transitive dependency contains critical RCE vulnerability',
  cwe_id: 'CWE-502',
  cvss_score: 10.0,
  remediation: 'Override log4j-core version to 2.17.1 in dependency management'
})
CREATE (scan1)-[:DETECTED]->(v)
CREATE (v)-[:IN_DEPENDENCY]->(dep_starter)
CREATE (v)-[:MAPS_TO]->(cve);

// ----------------------------------------------------------------------------
// REPO 5: analytics-dashboard - Text4Shell vulnerability
// ----------------------------------------------------------------------------

MATCH (repo:Repository {name: 'analytics-dashboard'})
MATCH (user:User {login: 'alice-dev'})
CREATE (pr:PullRequest {
  number: 89,
  title: 'Add report generation with text templating',
  state: 'merged',
  created_at: datetime('2022-09-20T11:00:00Z'),
  merged_at: datetime('2022-09-21T09:00:00Z')
})
CREATE (repo)-[:HAS_PR]->(pr)
CREATE (pr)-[:OPENED_BY]->(user)

CREATE (c1:Commit {
  sha: 'b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f60089',
  message: 'Add commons-text for report string interpolation',
  author: 'alice-dev',
  timestamp: datetime('2022-09-20T11:30:00Z')
})
CREATE (pr)-[:CONTAINS_COMMIT]->(c1)

CREATE (scan1:Scan {
  id: 'scan-ad-89-bd',
  scanner: 'BLACKDUCK',
  started_at: datetime('2022-09-20T11:35:00Z'),
  completed_at: datetime('2022-09-20T11:45:00Z'),
  status: 'completed'
})
CREATE (c1)-[:SCANNED_BY]->(scan1)

WITH scan1
MATCH (cve:CVE {cve_id: 'CVE-2022-42889'})
MATCH (dep:Dependency {name: 'commons-text', version: '1.9'})

CREATE (v:Vulnerability {
  id: 'vuln-ad-89-001',
  severity: 'CRITICAL',
  title: 'Text4Shell RCE in commons-text',
  description: 'Remote code execution via string interpolation',
  cwe_id: 'CWE-94',
  cvss_score: 9.8,
  remediation: 'Upgrade to commons-text 1.10.0 or later'
})
CREATE (scan1)-[:DETECTED]->(v)
CREATE (v)-[:IN_DEPENDENCY]->(dep)
CREATE (v)-[:MAPS_TO]->(cve);

// ----------------------------------------------------------------------------
// REPO 6: shared-infra - Multiple KICS findings
// ----------------------------------------------------------------------------

MATCH (repo:Repository {name: 'shared-infra'})
MATCH (user:User {login: 'charlie-ops'})
CREATE (pr:PullRequest {
  number: 201,
  title: 'Add shared Terraform modules for AWS',
  state: 'open',
  created_at: datetime('2022-04-01T08:00:00Z'),
  merged_at: null
})
CREATE (repo)-[:HAS_PR]->(pr)
CREATE (pr)-[:OPENED_BY]->(user)

CREATE (c1:Commit {
  sha: 'c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a10201a',
  message: 'Add IAM module',
  author: 'charlie-ops',
  timestamp: datetime('2022-04-01T08:30:00Z')
})
CREATE (c2:Commit {
  sha: 'c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a10201b',
  message: 'Add RDS module',
  author: 'charlie-ops',
  timestamp: datetime('2022-04-01T10:00:00Z')
})
CREATE (c3:Commit {
  sha: 'c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a10201c',
  message: 'Add CI workflow with secrets',
  author: 'charlie-ops',
  timestamp: datetime('2022-04-01T14:00:00Z')
})
CREATE (pr)-[:CONTAINS_COMMIT]->(c1)
CREATE (pr)-[:CONTAINS_COMMIT]->(c2)
CREATE (pr)-[:CONTAINS_COMMIT]->(c3)

WITH c1, c2, c3
MATCH (f_iam:File {path: 'infra/terraform/iam.tf'})
MATCH (f_rds:File {path: 'infra/terraform/rds.tf'})
MATCH (f_ci:File {path: '.github/workflows/ci.yaml'})
MATCH (rule_iam:Rule {name: 'IAM Policy Allows All Resources'})
MATCH (rule_rds:Rule {name: 'RDS Publicly Accessible'})
MATCH (rule_secrets:Rule {name: 'Secrets in Environment Variables'})

CREATE (scan1:Scan {
  id: 'scan-si-201a-kics',
  scanner: 'KICS',
  started_at: datetime('2022-04-01T08:35:00Z'),
  completed_at: datetime('2022-04-01T08:38:00Z'),
  status: 'completed'
})
CREATE (c1)-[:SCANNED_BY]->(scan1)
CREATE (c1)-[:MODIFIES]->(f_iam)

CREATE (v1:Vulnerability {
  id: 'vuln-si-201-001',
  severity: 'HIGH',
  title: 'IAM Policy with Wildcard Resources',
  description: 'IAM policy uses Resource: * allowing access to all resources',
  cwe_id: 'CWE-732',
  cvss_score: 7.5,
  remediation: 'Restrict Resource to specific ARNs'
})
CREATE (scan1)-[:DETECTED]->(v1)
CREATE (v1)-[:IN_FILE {line: 12, column: 3}]->(f_iam)
CREATE (v1)-[:VIOLATES]->(rule_iam)
CREATE (scan1)-[:USED_RULE]->(rule_iam)

CREATE (scan2:Scan {
  id: 'scan-si-201b-kics',
  scanner: 'KICS',
  started_at: datetime('2022-04-01T10:05:00Z'),
  completed_at: datetime('2022-04-01T10:08:00Z'),
  status: 'completed'
})
CREATE (c2)-[:SCANNED_BY]->(scan2)
CREATE (c2)-[:MODIFIES]->(f_rds)

CREATE (v2:Vulnerability {
  id: 'vuln-si-201-002',
  severity: 'HIGH',
  title: 'RDS Instance Publicly Accessible',
  description: 'RDS instance has publicly_accessible set to true',
  cwe_id: 'CWE-284',
  cvss_score: 8.0,
  remediation: 'Set publicly_accessible = false'
})
CREATE (scan2)-[:DETECTED]->(v2)
CREATE (v2)-[:IN_FILE {line: 8, column: 3}]->(f_rds)
CREATE (v2)-[:VIOLATES]->(rule_rds)
CREATE (scan2)-[:USED_RULE]->(rule_rds)

CREATE (scan3:Scan {
  id: 'scan-si-201c-kics',
  scanner: 'KICS',
  started_at: datetime('2022-04-01T14:05:00Z'),
  completed_at: datetime('2022-04-01T14:08:00Z'),
  status: 'completed'
})
CREATE (c3)-[:SCANNED_BY]->(scan3)
CREATE (c3)-[:MODIFIES]->(f_ci)

CREATE (v3:Vulnerability {
  id: 'vuln-si-201-003',
  severity: 'CRITICAL',
  title: 'Hardcoded AWS Credentials in CI Workflow',
  description: 'AWS_SECRET_ACCESS_KEY exposed in environment variables',
  cwe_id: 'CWE-798',
  cvss_score: 9.5,
  remediation: 'Use GitHub secrets or OIDC for AWS authentication'
})
CREATE (scan3)-[:DETECTED]->(v3)
CREATE (v3)-[:IN_FILE {line: 25, column: 10}]->(f_ci)
CREATE (v3)-[:VIOLATES]->(rule_secrets)
CREATE (scan3)-[:USED_RULE]->(rule_secrets);

// ----------------------------------------------------------------------------
// Additional PRs to reach ~200 records
// ----------------------------------------------------------------------------

// payment-service PR #125 - More infra work
MATCH (repo:Repository {name: 'payment-service'})
MATCH (user:User {login: 'diana-lead'})
CREATE (pr:PullRequest {
  number: 125,
  title: 'Add CloudWatch logging configuration',
  state: 'merged',
  created_at: datetime('2022-05-15T09:00:00Z'),
  merged_at: datetime('2022-05-16T11:00:00Z')
})
CREATE (repo)-[:HAS_PR]->(pr)
CREATE (pr)-[:OPENED_BY]->(user)

CREATE (c1:Commit {
  sha: 'd4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b20125',
  message: 'Add CloudTrail configuration',
  author: 'diana-lead',
  timestamp: datetime('2022-05-15T09:30:00Z')
})
CREATE (pr)-[:CONTAINS_COMMIT]->(c1)

WITH c1
MATCH (f_cf:File {path: 'infra/cloudformation/main.yaml'})
MATCH (rule_ct:Rule {name: 'CloudTrail Disabled'})

CREATE (scan1:Scan {
  id: 'scan-ps-125-kics',
  scanner: 'KICS',
  started_at: datetime('2022-05-15T09:35:00Z'),
  completed_at: datetime('2022-05-15T09:38:00Z'),
  status: 'completed'
})
CREATE (c1)-[:SCANNED_BY]->(scan1)
CREATE (c1)-[:MODIFIES]->(f_cf)

CREATE (v1:Vulnerability {
  id: 'vuln-ps-125-001',
  severity: 'MEDIUM',
  title: 'CloudTrail Log File Validation Disabled',
  description: 'CloudTrail does not have log file validation enabled',
  cwe_id: 'CWE-354',
  cvss_score: 5.0,
  remediation: 'Enable EnableLogFileValidation'
})
CREATE (scan1)-[:DETECTED]->(v1)
CREATE (v1)-[:IN_FILE {line: 45, column: 6}]->(f_cf)
CREATE (v1)-[:VIOLATES]->(rule_ct)
CREATE (scan1)-[:USED_RULE]->(rule_ct);

// user-api PR #60 - Docker security
MATCH (repo:Repository {name: 'user-api'})
MATCH (user:User {login: 'bob-sec'})
CREATE (pr:PullRequest {
  number: 60,
  title: 'Improve Docker security configuration',
  state: 'merged',
  created_at: datetime('2022-06-01T10:00:00Z'),
  merged_at: datetime('2022-06-02T14:00:00Z')
})
CREATE (repo)-[:HAS_PR]->(pr)
CREATE (pr)-[:OPENED_BY]->(user)

CREATE (c1:Commit {
  sha: 'e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c30060',
  message: 'Update Dockerfile with security best practices',
  author: 'bob-sec',
  timestamp: datetime('2022-06-01T10:30:00Z')
})
CREATE (pr)-[:CONTAINS_COMMIT]->(c1)

WITH c1
MATCH (f_docker:File {path: 'docker/Dockerfile'})
MATCH (rule_root:Rule {name: 'Container Running as Root'})

CREATE (scan1:Scan {
  id: 'scan-ua-60-kics',
  scanner: 'KICS',
  started_at: datetime('2022-06-01T10:35:00Z'),
  completed_at: datetime('2022-06-01T10:38:00Z'),
  status: 'completed'
})
CREATE (c1)-[:SCANNED_BY]->(scan1)
CREATE (c1)-[:MODIFIES]->(f_docker);
// Clean scan - no vulnerabilities (after fixing)

// inventory-manager PR #85 - Partial fix
MATCH (repo:Repository {name: 'inventory-manager'})
MATCH (user:User {login: 'bob-sec'})
CREATE (pr:PullRequest {
  number: 85,
  title: 'Upgrade Spring to fix Spring4Shell',
  state: 'merged',
  created_at: datetime('2022-04-05T08:00:00Z'),
  merged_at: datetime('2022-04-05T12:00:00Z')
})
CREATE (repo)-[:HAS_PR]->(pr)
CREATE (pr)-[:OPENED_BY]->(user)

CREATE (c1:Commit {
  sha: 'f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d40085',
  message: 'Upgrade spring-core to 5.3.20',
  author: 'bob-sec',
  timestamp: datetime('2022-04-05T08:30:00Z')
})
CREATE (pr)-[:CONTAINS_COMMIT]->(c1)

CREATE (scan1:Scan {
  id: 'scan-im-85-bd',
  scanner: 'BLACKDUCK',
  started_at: datetime('2022-04-05T08:35:00Z'),
  completed_at: datetime('2022-04-05T08:50:00Z'),
  status: 'completed'
})
CREATE (c1)-[:SCANNED_BY]->(scan1)

WITH scan1
MATCH (cve:CVE {cve_id: 'CVE-2021-44228'})
MATCH (dep:Dependency {name: 'log4j-core', version: '2.14.1'})

// Still has Log4Shell - only Spring was fixed
CREATE (v:Vulnerability {
  id: 'vuln-im-85-001',
  severity: 'CRITICAL',
  title: 'Log4Shell RCE in log4j-core (still present)',
  description: 'Log4j vulnerability not yet remediated',
  cwe_id: 'CWE-502',
  cvss_score: 10.0,
  remediation: 'Upgrade to log4j-core 2.17.1 or later'
})
CREATE (scan1)-[:DETECTED]->(v)
CREATE (v)-[:IN_DEPENDENCY]->(dep)
CREATE (v)-[:MAPS_TO]->(cve);

// ============================================================================
// VERIFICATION QUERIES
// ============================================================================

// Count all nodes
// MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count ORDER BY count DESC;

// Count all relationships
// MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count ORDER BY count DESC;

// ============================================================================
// DEMO QUERIES - Copy these to showcase the data model
// ============================================================================

// ----------------------------------------------------------------------------
// QUERY 1: Which PRs introduced a specific CVE (Log4Shell)?
// ----------------------------------------------------------------------------
// MATCH (r:Repository)-[:HAS_PR]->(pr:PullRequest)
//       -[:CONTAINS_COMMIT]->(c:Commit)
//       -[:SCANNED_BY]->(s:Scan)
//       -[:DETECTED]->(v:Vulnerability)
//       -[:MAPS_TO]->(cve:CVE {cve_id: 'CVE-2021-44228'})
// RETURN r.owner + '/' + r.name AS repository,
//        pr.number AS pr_number,
//        pr.title AS pr_title,
//        pr.created_at AS introduced_date,
//        v.title AS vulnerability
// ORDER BY pr.created_at;

// ----------------------------------------------------------------------------
// QUERY 2: Transitive dependency vulnerabilities
// ----------------------------------------------------------------------------
// MATCH path = (r:Repository)-[:HAS_DEPENDENCY]->(d1:Dependency)
//       -[:DEPENDS_ON*1..3]->(d2:Dependency)-[:HAS_CVE]->(cve:CVE)
// RETURN r.name AS repository,
//        d1.name + '@' + d1.version AS direct_dependency,
//        [rel IN relationships(path) WHERE type(rel) = 'DEPENDS_ON' |
//         endNode(rel).name + '@' + endNode(rel).version] AS dependency_chain,
//        cve.cve_id,
//        cve.cvss_score
// ORDER BY cve.cvss_score DESC;

// ----------------------------------------------------------------------------
// QUERY 3: Common vulnerabilities across repositories
// ----------------------------------------------------------------------------
// MATCH (r:Repository)-[:HAS_PR]->(:PullRequest)
//       -[:CONTAINS_COMMIT]->(:Commit)
//       -[:SCANNED_BY]->(:Scan)
//       -[:DETECTED]->(v:Vulnerability)
//       -[:MAPS_TO]->(cve:CVE)
// WITH cve, collect(DISTINCT r.name) AS affected_repos, count(DISTINCT r) AS repo_count
// WHERE repo_count > 1
// RETURN cve.cve_id,
//        cve.description,
//        cve.cvss_score,
//        repo_count,
//        affected_repos
// ORDER BY repo_count DESC, cve.cvss_score DESC;

// ----------------------------------------------------------------------------
// QUERY 4: Vulnerability lineage (introduced -> fixed)
// ----------------------------------------------------------------------------
// MATCH (r:Repository {name: 'payment-service'})-[:HAS_PR]->(pr1:PullRequest)
//       -[:CONTAINS_COMMIT]->(c1:Commit)
//       -[:SCANNED_BY]->(:Scan)
//       -[:DETECTED]->(v:Vulnerability)
//       -[:MAPS_TO]->(cve:CVE {cve_id: 'CVE-2021-44228'})
// OPTIONAL MATCH (r)-[:HAS_PR]->(pr2:PullRequest)
//       -[:CONTAINS_COMMIT]->(c2:Commit)
//       -[:SCANNED_BY]->(s2:Scan)
// WHERE pr2.created_at > pr1.created_at
//   AND s2.scanner = 'BLACKDUCK'
//   AND NOT EXISTS {
//     (s2)-[:DETECTED]->(:Vulnerability)-[:MAPS_TO]->(cve)
//   }
// WITH pr1, c1, v, cve, pr2, c2
// ORDER BY pr2.created_at
// WITH pr1, c1, v, cve, collect(pr2)[0] AS fixing_pr, collect(c2)[0] AS fixing_commit
// RETURN pr1.number AS introduced_in_pr,
//        pr1.title AS introduced_pr_title,
//        pr1.created_at AS introduced_date,
//        cve.cve_id,
//        v.severity,
//        fixing_pr.number AS fixed_in_pr,
//        fixing_pr.title AS fixed_pr_title,
//        fixing_pr.merged_at AS fixed_date,
//        duration.between(pr1.created_at, fixing_pr.merged_at).days AS days_to_fix;
