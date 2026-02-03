#!/usr/bin/env python3
"""
Neo4j Seed Data Script - Security Scan Demo Data

Loads ~200 records into Neo4j to demonstrate security scan data model.
Showcases: CVE tracking, transitive dependencies, cross-repo vulnerabilities, lineage.

┌─────────────────────────────────────────────────────────────────────────┐
│                         RECORD SUMMARY                                  │
├───────────────┬───────┬─────────────────────────────────────────────────┤
│   Node Type   │ Count │              Description                        │
├───────────────┼───────┼─────────────────────────────────────────────────┤
│ CVE           │     7 │ Log4Shell, Spring4Shell, Text4Shell, etc.       │
│ Dependency    │    15 │ Maven, npm, pip packages (vulnerable + fixed)   │
│ Rule          │     8 │ KICS security rules                             │
│ Repository    │     6 │ payment-service, user-api, inventory-manager    │
│ File          │    14 │ Terraform, K8s, Docker, config files            │
│ User          │     5 │ Developers with different roles                 │
│ PullRequest   │    12 │ Across all repos                                │
│ Commit        │    16 │ Multiple commits per PR                         │
│ Scan          │    16 │ KICS and Blackduck scans                        │
│ Vulnerability │    18 │ Mix of infra and dependency vulns               │
├───────────────┼───────┼─────────────────────────────────────────────────┤
│ TOTAL         │  ~117 │ nodes                                           │
│ Relationships │   ~80 │ edges                                           │
│ TOTAL RECORDS │  ~200 │                                                 │
└───────────────┴───────┴─────────────────────────────────────────────────┘

Demo Queries:
  1. Which PRs introduced CVE-X? (Log4Shell across 4 repos)
  2. Transitive dependency vulnerabilities (spring-boot -> log4j chain)
  3. Common vulnerabilities across repositories
  4. Vulnerability lineage (introduced -> fixed timeline)

Usage:
    python scripts/neo4j-seed.py
    python scripts/neo4j-seed.py --uri bolt://localhost:7687 --password mypassword
    python scripts/neo4j-seed.py --clear  # Clear existing data first
    python scripts/neo4j-seed.py --demo-only  # Run demo queries only
    python scripts/neo4j-seed.py --noise 500  # Add 500 noise records on top of demo data
    python scripts/neo4j-seed.py --noise-only 500  # Only noise, no demo data
    python scripts/neo4j-seed.py --clear --noise-only 1000  # Fresh DB with only noise
"""

import argparse
import os
import sys
import random
import string
import uuid
from datetime import datetime, date, timedelta
from typing import Optional

try:
    from neo4j import GraphDatabase
except ImportError:
    print("Error: neo4j package not installed. Run: pip install neo4j")
    sys.exit(1)


class SecurityGraphSeeder:
    """Seeds Neo4j with security scan demo data."""

    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self._verify_connection()

    def _verify_connection(self):
        """Verify Neo4j connection."""
        try:
            with self.driver.session() as session:
                session.run("RETURN 1")
            print("Connected to Neo4j successfully")
        except Exception as e:
            print(f"Failed to connect to Neo4j: {e}")
            sys.exit(1)

    def close(self):
        """Close the driver connection."""
        self.driver.close()

    def clear_database(self):
        """Remove all existing data."""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        print("Cleared existing data")

    def create_indexes(self):
        """Create indexes and constraints for performance."""
        indexes = [
            "CREATE CONSTRAINT repo_unique IF NOT EXISTS FOR (r:Repository) REQUIRE (r.owner, r.name) IS UNIQUE",
            "CREATE CONSTRAINT commit_sha_unique IF NOT EXISTS FOR (c:Commit) REQUIRE c.sha IS UNIQUE",
            "CREATE CONSTRAINT cve_id_unique IF NOT EXISTS FOR (cve:CVE) REQUIRE cve.cve_id IS UNIQUE",
            "CREATE INDEX vuln_severity IF NOT EXISTS FOR (v:Vulnerability) ON (v.severity)",
            "CREATE INDEX dep_name IF NOT EXISTS FOR (d:Dependency) ON (d.name)",
            "CREATE INDEX scan_scanner IF NOT EXISTS FOR (s:Scan) ON (s.scanner)",
        ]
        with self.driver.session() as session:
            for idx in indexes:
                try:
                    session.run(idx)
                except Exception as e:
                    # Index might already exist
                    pass
        print("Created indexes")

    def seed_cves(self):
        """Create CVE nodes."""
        cves = [
            {"cve_id": "CVE-2021-44228", "published": "2021-12-10", "cvss": 10.0, "desc": "Apache Log4j2 JNDI RCE (Log4Shell)"},
            {"cve_id": "CVE-2022-22965", "published": "2022-03-31", "cvss": 9.8, "desc": "Spring Framework RCE (Spring4Shell)"},
            {"cve_id": "CVE-2023-34362", "published": "2023-06-02", "cvss": 9.8, "desc": "MOVEit Transfer SQL Injection"},
            {"cve_id": "CVE-2021-45046", "published": "2021-12-14", "cvss": 9.0, "desc": "Apache Log4j2 DoS and RCE"},
            {"cve_id": "CVE-2022-42889", "published": "2022-10-13", "cvss": 9.8, "desc": "Apache Commons Text RCE (Text4Shell)"},
            {"cve_id": "CVE-2023-44487", "published": "2023-10-10", "cvss": 7.5, "desc": "HTTP/2 Rapid Reset Attack"},
            {"cve_id": "CVE-2024-3094", "published": "2024-03-29", "cvss": 10.0, "desc": "XZ Utils Backdoor"},
        ]
        with self.driver.session() as session:
            for cve in cves:
                session.run("""
                    CREATE (c:CVE {
                        cve_id: $cve_id,
                        published_at: date($published),
                        cvss_score: $cvss,
                        description: $desc
                    })
                """, cve_id=cve["cve_id"], published=cve["published"], cvss=cve["cvss"], desc=cve["desc"])
        print(f"Created {len(cves)} CVEs")

    def seed_dependencies(self):
        """Create Dependency nodes and relationships."""
        dependencies = [
            # Vulnerable versions
            {"name": "log4j-core", "version": "2.14.1", "ecosystem": "maven", "license": "Apache-2.0"},
            {"name": "log4j-api", "version": "2.14.1", "ecosystem": "maven", "license": "Apache-2.0"},
            {"name": "spring-boot-starter", "version": "2.6.1", "ecosystem": "maven", "license": "Apache-2.0"},
            {"name": "spring-core", "version": "5.3.18", "ecosystem": "maven", "license": "Apache-2.0"},
            {"name": "commons-text", "version": "1.9", "ecosystem": "maven", "license": "Apache-2.0"},
            {"name": "commons-lang3", "version": "3.12.0", "ecosystem": "maven", "license": "Apache-2.0"},
            {"name": "express", "version": "4.17.1", "ecosystem": "npm", "license": "MIT"},
            {"name": "lodash", "version": "4.17.20", "ecosystem": "npm", "license": "MIT"},
            {"name": "axios", "version": "0.21.1", "ecosystem": "npm", "license": "MIT"},
            {"name": "requests", "version": "2.25.1", "ecosystem": "pip", "license": "Apache-2.0"},
            {"name": "urllib3", "version": "1.26.4", "ecosystem": "pip", "license": "MIT"},
            {"name": "flask", "version": "2.0.1", "ecosystem": "pip", "license": "BSD-3"},
            # Fixed versions
            {"name": "log4j-core", "version": "2.17.1", "ecosystem": "maven", "license": "Apache-2.0"},
            {"name": "spring-core", "version": "5.3.20", "ecosystem": "maven", "license": "Apache-2.0"},
            {"name": "commons-text", "version": "1.10.0", "ecosystem": "maven", "license": "Apache-2.0"},
        ]

        with self.driver.session() as session:
            for dep in dependencies:
                session.run("""
                    CREATE (d:Dependency {
                        name: $name,
                        version: $version,
                        ecosystem: $ecosystem,
                        license: $license
                    })
                """, **dep)

            # Transitive dependencies
            transitive = [
                ("spring-boot-starter", "2.6.1", "spring-core", "5.3.18"),
                ("spring-boot-starter", "2.6.1", "log4j-core", "2.14.1"),
                ("log4j-core", "2.14.1", "log4j-api", "2.14.1"),
                ("commons-text", "1.9", "commons-lang3", "3.12.0"),
                ("express", "4.17.1", "lodash", "4.17.20"),
                ("requests", "2.25.1", "urllib3", "1.26.4"),
            ]
            for parent_name, parent_ver, child_name, child_ver in transitive:
                session.run("""
                    MATCH (p:Dependency {name: $pname, version: $pver})
                    MATCH (c:Dependency {name: $cname, version: $cver})
                    CREATE (p)-[:DEPENDS_ON]->(c)
                """, pname=parent_name, pver=parent_ver, cname=child_name, cver=child_ver)

            # CVE links
            cve_links = [
                ("log4j-core", "2.14.1", "CVE-2021-44228"),
                ("log4j-core", "2.14.1", "CVE-2021-45046"),
                ("spring-core", "5.3.18", "CVE-2022-22965"),
                ("commons-text", "1.9", "CVE-2022-42889"),
            ]
            for dep_name, dep_ver, cve_id in cve_links:
                session.run("""
                    MATCH (d:Dependency {name: $name, version: $ver})
                    MATCH (c:CVE {cve_id: $cve})
                    CREATE (d)-[:HAS_CVE]->(c)
                """, name=dep_name, ver=dep_ver, cve=cve_id)

        print(f"Created {len(dependencies)} dependencies with relationships")

    def seed_rules(self):
        """Create KICS Rule nodes."""
        rules = [
            {"rule_id": "a227ec01-f97a-4084-91a4-47b350c1db54", "name": "S3 Bucket SSE Disabled", "category": "Encryption", "severity": "HIGH"},
            {"rule_id": "b5c77288-f9c8-4864-ad8c-4e3d3ab4bc78", "name": "Security Group Unrestricted Ingress", "category": "Networking", "severity": "CRITICAL"},
            {"rule_id": "c8b34e84-2a58-4e21-b9c7-32a1dec5f6ab", "name": "IAM Policy Allows All Resources", "category": "Access Control", "severity": "HIGH"},
            {"rule_id": "d9a45f12-8c67-4b39-9e12-54a2bc3e7f89", "name": "Container Running as Root", "category": "Container Security", "severity": "MEDIUM"},
            {"rule_id": "e1b23c45-6d78-4f90-a123-bc456def7890", "name": "Missing Resource Limits", "category": "Resource Management", "severity": "LOW"},
            {"rule_id": "f2c34d56-7e89-4a01-b234-cd567ef89012", "name": "Secrets in Environment Variables", "category": "Secret Management", "severity": "CRITICAL"},
            {"rule_id": "g3d45e67-8f90-4b12-c345-de678f901234", "name": "RDS Publicly Accessible", "category": "Networking", "severity": "HIGH"},
            {"rule_id": "h4e56f78-9012-4c23-d456-ef789a012345", "name": "CloudTrail Disabled", "category": "Logging", "severity": "MEDIUM"},
        ]
        with self.driver.session() as session:
            for rule in rules:
                session.run("""
                    CREATE (r:Rule {
                        rule_id: $rule_id,
                        name: $name,
                        scanner: 'KICS',
                        category: $category,
                        severity: $severity
                    })
                """, **rule)
        print(f"Created {len(rules)} KICS rules")

    def seed_repositories(self):
        """Create Repository nodes."""
        repos = [
            {"name": "payment-service", "owner": "acme-corp"},
            {"name": "user-api", "owner": "acme-corp"},
            {"name": "inventory-manager", "owner": "acme-corp"},
            {"name": "notification-worker", "owner": "acme-corp"},
            {"name": "analytics-dashboard", "owner": "acme-corp"},
            {"name": "shared-infra", "owner": "acme-corp"},
        ]
        with self.driver.session() as session:
            for repo in repos:
                session.run("""
                    CREATE (r:Repository {
                        name: $name,
                        owner: $owner,
                        url: 'https://github.com/' + $owner + '/' + $name,
                        default_branch: 'main'
                    })
                """, **repo)

            # Link repos to dependencies
            repo_deps = [
                ("payment-service", "log4j-core", "2.14.1"),
                ("payment-service", "spring-core", "5.3.18"),
                ("user-api", "log4j-core", "2.14.1"),
                ("user-api", "express", "4.17.1"),
                ("inventory-manager", "log4j-core", "2.14.1"),
                ("notification-worker", "spring-boot-starter", "2.6.1"),
                ("analytics-dashboard", "commons-text", "1.9"),
                ("shared-infra", "flask", "2.0.1"),
            ]
            for repo_name, dep_name, dep_ver in repo_deps:
                session.run("""
                    MATCH (r:Repository {name: $repo})
                    MATCH (d:Dependency {name: $dep, version: $ver})
                    CREATE (r)-[:HAS_DEPENDENCY]->(d)
                """, repo=repo_name, dep=dep_name, ver=dep_ver)

        print(f"Created {len(repos)} repositories")

    def seed_files(self):
        """Create File nodes."""
        files = [
            {"path": "infra/terraform/s3.tf", "language": "terraform"},
            {"path": "infra/terraform/security-groups.tf", "language": "terraform"},
            {"path": "infra/terraform/iam.tf", "language": "terraform"},
            {"path": "infra/terraform/rds.tf", "language": "terraform"},
            {"path": "k8s/deployment.yaml", "language": "yaml"},
            {"path": "k8s/service.yaml", "language": "yaml"},
            {"path": "docker/Dockerfile", "language": "dockerfile"},
            {"path": "docker/docker-compose.yaml", "language": "yaml"},
            {"path": "src/main/resources/application.yaml", "language": "yaml"},
            {"path": "pom.xml", "language": "xml"},
            {"path": "package.json", "language": "json"},
            {"path": "requirements.txt", "language": "text"},
            {"path": ".github/workflows/ci.yaml", "language": "yaml"},
            {"path": "infra/cloudformation/main.yaml", "language": "yaml"},
        ]
        with self.driver.session() as session:
            for f in files:
                session.run("""
                    CREATE (f:File {path: $path, language: $language})
                """, **f)
        print(f"Created {len(files)} files")

    def seed_users(self):
        """Create User nodes."""
        users = [
            {"login": "alice-dev", "email": "alice@acme-corp.com", "name": "Alice Developer"},
            {"login": "bob-sec", "email": "bob@acme-corp.com", "name": "Bob Security"},
            {"login": "charlie-ops", "email": "charlie@acme-corp.com", "name": "Charlie DevOps"},
            {"login": "diana-lead", "email": "diana@acme-corp.com", "name": "Diana Tech Lead"},
            {"login": "eve-junior", "email": "eve@acme-corp.com", "name": "Eve Junior Dev"},
        ]
        with self.driver.session() as session:
            for user in users:
                session.run("""
                    CREATE (u:User {login: $login, email: $email, name: $name})
                """, **user)
        print(f"Created {len(users)} users")

    def seed_prs_and_scans(self):
        """Create PRs, Commits, Scans, and Vulnerabilities."""
        with self.driver.session() as session:
            # ================================================================
            # PAYMENT-SERVICE: Shows vulnerability lineage (introduced -> fixed)
            # ================================================================

            # PR #101 - Introduces Log4Shell
            session.run("""
                MATCH (repo:Repository {name: 'payment-service'})
                MATCH (user:User {login: 'eve-junior'})
                MATCH (cve:CVE {cve_id: 'CVE-2021-44228'})
                MATCH (dep:Dependency {name: 'log4j-core', version: '2.14.1'})

                CREATE (pr:PullRequest {
                    number: 101,
                    title: 'Add logging framework for payment transactions',
                    state: 'merged',
                    created_at: datetime('2021-11-15T10:00:00Z'),
                    merged_at: datetime('2021-11-16T14:00:00Z')
                })
                CREATE (repo)-[:HAS_PR]->(pr)
                CREATE (pr)-[:OPENED_BY]->(user)

                CREATE (c:Commit {
                    sha: 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f60101',
                    message: 'Add log4j dependency for structured logging',
                    author: 'eve-junior',
                    timestamp: datetime('2021-11-15T10:30:00Z')
                })
                CREATE (pr)-[:CONTAINS_COMMIT]->(c)

                CREATE (scan:Scan {
                    id: 'scan-ps-101-bd',
                    scanner: 'BLACKDUCK',
                    started_at: datetime('2021-11-15T10:35:00Z'),
                    completed_at: datetime('2021-11-15T10:40:00Z'),
                    status: 'completed'
                })
                CREATE (c)-[:SCANNED_BY]->(scan)

                CREATE (v:Vulnerability {
                    id: 'vuln-ps-101-001',
                    severity: 'CRITICAL',
                    title: 'Log4Shell RCE in log4j-core',
                    description: 'Remote code execution via JNDI lookup',
                    cwe_id: 'CWE-502',
                    cvss_score: 10.0,
                    remediation: 'Upgrade to log4j-core 2.17.1 or later'
                })
                CREATE (scan)-[:DETECTED]->(v)
                CREATE (v)-[:IN_DEPENDENCY]->(dep)
                CREATE (v)-[:MAPS_TO]->(cve)
            """)

            # PR #115 - Fixes Log4Shell
            session.run("""
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

                CREATE (c:Commit {
                    sha: 'b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f60115',
                    message: 'Upgrade log4j-core to 2.17.1',
                    author: 'bob-sec',
                    timestamp: datetime('2021-12-13T08:30:00Z')
                })
                CREATE (pr)-[:CONTAINS_COMMIT]->(c)

                CREATE (scan:Scan {
                    id: 'scan-ps-115-bd',
                    scanner: 'BLACKDUCK',
                    started_at: datetime('2021-12-13T08:35:00Z'),
                    completed_at: datetime('2021-12-13T08:40:00Z'),
                    status: 'completed'
                })
                CREATE (c)-[:SCANNED_BY]->(scan)
            """)

            # PR #120 - Adds infrastructure with KICS issues
            session.run("""
                MATCH (repo:Repository {name: 'payment-service'})
                MATCH (user:User {login: 'charlie-ops'})
                MATCH (f_s3:File {path: 'infra/terraform/s3.tf'})
                MATCH (f_sg:File {path: 'infra/terraform/security-groups.tf'})
                MATCH (rule_s3:Rule {name: 'S3 Bucket SSE Disabled'})
                MATCH (rule_sg:Rule {name: 'Security Group Unrestricted Ingress'})

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
                CREATE (scan2)-[:USED_RULE]->(rule_sg)
            """)

            # ================================================================
            # USER-API: Also has Log4Shell (common vuln across repos)
            # ================================================================

            session.run("""
                MATCH (repo:Repository {name: 'user-api'})
                MATCH (user:User {login: 'alice-dev'})
                MATCH (cve:CVE {cve_id: 'CVE-2021-44228'})
                MATCH (dep:Dependency {name: 'log4j-core', version: '2.14.1'})

                CREATE (pr:PullRequest {
                    number: 45,
                    title: 'Implement user authentication service',
                    state: 'merged',
                    created_at: datetime('2021-10-20T11:00:00Z'),
                    merged_at: datetime('2021-10-21T15:00:00Z')
                })
                CREATE (repo)-[:HAS_PR]->(pr)
                CREATE (pr)-[:OPENED_BY]->(user)

                CREATE (c:Commit {
                    sha: 'd4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b20045',
                    message: 'Add authentication with JWT and logging',
                    author: 'alice-dev',
                    timestamp: datetime('2021-10-20T11:30:00Z')
                })
                CREATE (pr)-[:CONTAINS_COMMIT]->(c)

                CREATE (scan:Scan {
                    id: 'scan-ua-45-bd',
                    scanner: 'BLACKDUCK',
                    started_at: datetime('2021-10-20T11:35:00Z'),
                    completed_at: datetime('2021-10-20T11:42:00Z'),
                    status: 'completed'
                })
                CREATE (c)-[:SCANNED_BY]->(scan)

                CREATE (v:Vulnerability {
                    id: 'vuln-ua-45-001',
                    severity: 'CRITICAL',
                    title: 'Log4Shell RCE in log4j-core',
                    description: 'Remote code execution via JNDI lookup',
                    cwe_id: 'CWE-502',
                    cvss_score: 10.0,
                    remediation: 'Upgrade to log4j-core 2.17.1 or later'
                })
                CREATE (scan)-[:DETECTED]->(v)
                CREATE (v)-[:IN_DEPENDENCY]->(dep)
                CREATE (v)-[:MAPS_TO]->(cve)
            """)

            # PR #52 - K8s deployment with issues
            session.run("""
                MATCH (repo:Repository {name: 'user-api'})
                MATCH (user:User {login: 'charlie-ops'})
                MATCH (f_deploy:File {path: 'k8s/deployment.yaml'})
                MATCH (rule_root:Rule {name: 'Container Running as Root'})
                MATCH (rule_limits:Rule {name: 'Missing Resource Limits'})

                CREATE (pr:PullRequest {
                    number: 52,
                    title: 'Add Kubernetes manifests for user-api',
                    state: 'open',
                    created_at: datetime('2022-02-15T10:00:00Z')
                })
                CREATE (repo)-[:HAS_PR]->(pr)
                CREATE (pr)-[:OPENED_BY]->(user)

                CREATE (c:Commit {
                    sha: 'e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c30052',
                    message: 'Add deployment and service manifests',
                    author: 'charlie-ops',
                    timestamp: datetime('2022-02-15T10:30:00Z')
                })
                CREATE (pr)-[:CONTAINS_COMMIT]->(c)

                CREATE (scan:Scan {
                    id: 'scan-ua-52-kics',
                    scanner: 'KICS',
                    started_at: datetime('2022-02-15T10:35:00Z'),
                    completed_at: datetime('2022-02-15T10:38:00Z'),
                    status: 'completed'
                })
                CREATE (c)-[:SCANNED_BY]->(scan)
                CREATE (c)-[:MODIFIES]->(f_deploy)

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
                CREATE (scan)-[:DETECTED]->(v1)
                CREATE (scan)-[:DETECTED]->(v2)
                CREATE (v1)-[:IN_FILE {line: 22, column: 8}]->(f_deploy)
                CREATE (v2)-[:IN_FILE {line: 18, column: 8}]->(f_deploy)
                CREATE (v1)-[:VIOLATES]->(rule_root)
                CREATE (v2)-[:VIOLATES]->(rule_limits)
                CREATE (scan)-[:USED_RULE]->(rule_root)
                CREATE (scan)-[:USED_RULE]->(rule_limits)
            """)

            # ================================================================
            # INVENTORY-MANAGER: Log4Shell + Spring4Shell (multiple CVEs)
            # ================================================================

            session.run("""
                MATCH (repo:Repository {name: 'inventory-manager'})
                MATCH (user:User {login: 'diana-lead'})
                MATCH (cve1:CVE {cve_id: 'CVE-2021-44228'})
                MATCH (cve2:CVE {cve_id: 'CVE-2022-22965'})
                MATCH (dep_log4j:Dependency {name: 'log4j-core', version: '2.14.1'})
                MATCH (dep_spring:Dependency {name: 'spring-core', version: '5.3.18'})

                CREATE (pr:PullRequest {
                    number: 78,
                    title: 'Migrate to Spring Boot for inventory management',
                    state: 'merged',
                    created_at: datetime('2022-02-01T09:00:00Z'),
                    merged_at: datetime('2022-02-03T17:00:00Z')
                })
                CREATE (repo)-[:HAS_PR]->(pr)
                CREATE (pr)-[:OPENED_BY]->(user)

                CREATE (c:Commit {
                    sha: 'f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d40078',
                    message: 'Add Spring Boot starter with logging',
                    author: 'diana-lead',
                    timestamp: datetime('2022-02-01T09:30:00Z')
                })
                CREATE (pr)-[:CONTAINS_COMMIT]->(c)

                CREATE (scan:Scan {
                    id: 'scan-im-78-bd',
                    scanner: 'BLACKDUCK',
                    started_at: datetime('2022-02-01T09:35:00Z'),
                    completed_at: datetime('2022-02-01T09:50:00Z'),
                    status: 'completed'
                })
                CREATE (c)-[:SCANNED_BY]->(scan)

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
                CREATE (scan)-[:DETECTED]->(v1)
                CREATE (scan)-[:DETECTED]->(v2)
                CREATE (v1)-[:IN_DEPENDENCY]->(dep_log4j)
                CREATE (v2)-[:IN_DEPENDENCY]->(dep_spring)
                CREATE (v1)-[:MAPS_TO]->(cve1)
                CREATE (v2)-[:MAPS_TO]->(cve2)
            """)

            # ================================================================
            # NOTIFICATION-WORKER: Transitive dependency vulnerability
            # ================================================================

            session.run("""
                MATCH (repo:Repository {name: 'notification-worker'})
                MATCH (user:User {login: 'eve-junior'})
                MATCH (cve:CVE {cve_id: 'CVE-2021-44228'})
                MATCH (dep_starter:Dependency {name: 'spring-boot-starter', version: '2.6.1'})

                CREATE (pr:PullRequest {
                    number: 23,
                    title: 'Initialize notification worker service',
                    state: 'merged',
                    created_at: datetime('2022-03-10T14:00:00Z'),
                    merged_at: datetime('2022-03-11T10:00:00Z')
                })
                CREATE (repo)-[:HAS_PR]->(pr)
                CREATE (pr)-[:OPENED_BY]->(user)

                CREATE (c:Commit {
                    sha: 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e50023',
                    message: 'Add spring-boot-starter for message processing',
                    author: 'eve-junior',
                    timestamp: datetime('2022-03-10T14:30:00Z')
                })
                CREATE (pr)-[:CONTAINS_COMMIT]->(c)

                CREATE (scan:Scan {
                    id: 'scan-nw-23-bd',
                    scanner: 'BLACKDUCK',
                    started_at: datetime('2022-03-10T14:35:00Z'),
                    completed_at: datetime('2022-03-10T14:55:00Z'),
                    status: 'completed'
                })
                CREATE (c)-[:SCANNED_BY]->(scan)

                CREATE (v:Vulnerability {
                    id: 'vuln-nw-23-001',
                    severity: 'CRITICAL',
                    title: 'Log4Shell via transitive dependency spring-boot-starter -> log4j-core',
                    description: 'Transitive dependency contains critical RCE vulnerability',
                    cwe_id: 'CWE-502',
                    cvss_score: 10.0,
                    remediation: 'Override log4j-core version to 2.17.1 in dependency management'
                })
                CREATE (scan)-[:DETECTED]->(v)
                CREATE (v)-[:IN_DEPENDENCY]->(dep_starter)
                CREATE (v)-[:MAPS_TO]->(cve)
            """)

            # ================================================================
            # ANALYTICS-DASHBOARD: Text4Shell vulnerability
            # ================================================================

            session.run("""
                MATCH (repo:Repository {name: 'analytics-dashboard'})
                MATCH (user:User {login: 'alice-dev'})
                MATCH (cve:CVE {cve_id: 'CVE-2022-42889'})
                MATCH (dep:Dependency {name: 'commons-text', version: '1.9'})

                CREATE (pr:PullRequest {
                    number: 89,
                    title: 'Add report generation with text templating',
                    state: 'merged',
                    created_at: datetime('2022-09-20T11:00:00Z'),
                    merged_at: datetime('2022-09-21T09:00:00Z')
                })
                CREATE (repo)-[:HAS_PR]->(pr)
                CREATE (pr)-[:OPENED_BY]->(user)

                CREATE (c:Commit {
                    sha: 'b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f60089',
                    message: 'Add commons-text for report string interpolation',
                    author: 'alice-dev',
                    timestamp: datetime('2022-09-20T11:30:00Z')
                })
                CREATE (pr)-[:CONTAINS_COMMIT]->(c)

                CREATE (scan:Scan {
                    id: 'scan-ad-89-bd',
                    scanner: 'BLACKDUCK',
                    started_at: datetime('2022-09-20T11:35:00Z'),
                    completed_at: datetime('2022-09-20T11:45:00Z'),
                    status: 'completed'
                })
                CREATE (c)-[:SCANNED_BY]->(scan)

                CREATE (v:Vulnerability {
                    id: 'vuln-ad-89-001',
                    severity: 'CRITICAL',
                    title: 'Text4Shell RCE in commons-text',
                    description: 'Remote code execution via string interpolation',
                    cwe_id: 'CWE-94',
                    cvss_score: 9.8,
                    remediation: 'Upgrade to commons-text 1.10.0 or later'
                })
                CREATE (scan)-[:DETECTED]->(v)
                CREATE (v)-[:IN_DEPENDENCY]->(dep)
                CREATE (v)-[:MAPS_TO]->(cve)
            """)

            # ================================================================
            # SHARED-INFRA: Multiple KICS findings
            # ================================================================

            session.run("""
                MATCH (repo:Repository {name: 'shared-infra'})
                MATCH (user:User {login: 'charlie-ops'})
                MATCH (f_iam:File {path: 'infra/terraform/iam.tf'})
                MATCH (f_rds:File {path: 'infra/terraform/rds.tf'})
                MATCH (f_ci:File {path: '.github/workflows/ci.yaml'})
                MATCH (rule_iam:Rule {name: 'IAM Policy Allows All Resources'})
                MATCH (rule_rds:Rule {name: 'RDS Publicly Accessible'})
                MATCH (rule_secrets:Rule {name: 'Secrets in Environment Variables'})

                CREATE (pr:PullRequest {
                    number: 201,
                    title: 'Add shared Terraform modules for AWS',
                    state: 'open',
                    created_at: datetime('2022-04-01T08:00:00Z')
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
                CREATE (scan3)-[:USED_RULE]->(rule_secrets)
            """)

            # Additional PRs for more data
            session.run("""
                MATCH (repo:Repository {name: 'payment-service'})
                MATCH (user:User {login: 'diana-lead'})
                MATCH (f_cf:File {path: 'infra/cloudformation/main.yaml'})
                MATCH (rule_ct:Rule {name: 'CloudTrail Disabled'})

                CREATE (pr:PullRequest {
                    number: 125,
                    title: 'Add CloudWatch logging configuration',
                    state: 'merged',
                    created_at: datetime('2022-05-15T09:00:00Z'),
                    merged_at: datetime('2022-05-16T11:00:00Z')
                })
                CREATE (repo)-[:HAS_PR]->(pr)
                CREATE (pr)-[:OPENED_BY]->(user)

                CREATE (c:Commit {
                    sha: 'd4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b20125',
                    message: 'Add CloudTrail configuration',
                    author: 'diana-lead',
                    timestamp: datetime('2022-05-15T09:30:00Z')
                })
                CREATE (pr)-[:CONTAINS_COMMIT]->(c)

                CREATE (scan:Scan {
                    id: 'scan-ps-125-kics',
                    scanner: 'KICS',
                    started_at: datetime('2022-05-15T09:35:00Z'),
                    completed_at: datetime('2022-05-15T09:38:00Z'),
                    status: 'completed'
                })
                CREATE (c)-[:SCANNED_BY]->(scan)
                CREATE (c)-[:MODIFIES]->(f_cf)

                CREATE (v:Vulnerability {
                    id: 'vuln-ps-125-001',
                    severity: 'MEDIUM',
                    title: 'CloudTrail Log File Validation Disabled',
                    description: 'CloudTrail does not have log file validation enabled',
                    cwe_id: 'CWE-354',
                    cvss_score: 5.0,
                    remediation: 'Enable EnableLogFileValidation'
                })
                CREATE (scan)-[:DETECTED]->(v)
                CREATE (v)-[:IN_FILE {line: 45, column: 6}]->(f_cf)
                CREATE (v)-[:VIOLATES]->(rule_ct)
                CREATE (scan)-[:USED_RULE]->(rule_ct)
            """)

            # inventory-manager partial fix
            session.run("""
                MATCH (repo:Repository {name: 'inventory-manager'})
                MATCH (user:User {login: 'bob-sec'})
                MATCH (cve:CVE {cve_id: 'CVE-2021-44228'})
                MATCH (dep:Dependency {name: 'log4j-core', version: '2.14.1'})

                CREATE (pr:PullRequest {
                    number: 85,
                    title: 'Upgrade Spring to fix Spring4Shell',
                    state: 'merged',
                    created_at: datetime('2022-04-05T08:00:00Z'),
                    merged_at: datetime('2022-04-05T12:00:00Z')
                })
                CREATE (repo)-[:HAS_PR]->(pr)
                CREATE (pr)-[:OPENED_BY]->(user)

                CREATE (c:Commit {
                    sha: 'f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d40085',
                    message: 'Upgrade spring-core to 5.3.20',
                    author: 'bob-sec',
                    timestamp: datetime('2022-04-05T08:30:00Z')
                })
                CREATE (pr)-[:CONTAINS_COMMIT]->(c)

                CREATE (scan:Scan {
                    id: 'scan-im-85-bd',
                    scanner: 'BLACKDUCK',
                    started_at: datetime('2022-04-05T08:35:00Z'),
                    completed_at: datetime('2022-04-05T08:50:00Z'),
                    status: 'completed'
                })
                CREATE (c)-[:SCANNED_BY]->(scan)

                CREATE (v:Vulnerability {
                    id: 'vuln-im-85-001',
                    severity: 'CRITICAL',
                    title: 'Log4Shell RCE in log4j-core (still present)',
                    description: 'Log4j vulnerability not yet remediated',
                    cwe_id: 'CWE-502',
                    cvss_score: 10.0,
                    remediation: 'Upgrade to log4j-core 2.17.1 or later'
                })
                CREATE (scan)-[:DETECTED]->(v)
                CREATE (v)-[:IN_DEPENDENCY]->(dep)
                CREATE (v)-[:MAPS_TO]->(cve)
            """)

        print("Created PRs, commits, scans, and vulnerabilities")

    def print_stats(self):
        """Print database statistics."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] AS label, count(*) AS count
                ORDER BY count DESC
            """)
            print("\n--- Node Statistics ---")
            total_nodes = 0
            for record in result:
                print(f"  {record['label']}: {record['count']}")
                total_nodes += record['count']
            print(f"  TOTAL NODES: {total_nodes}")

            result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) AS type, count(*) AS count
                ORDER BY count DESC
            """)
            print("\n--- Relationship Statistics ---")
            total_rels = 0
            for record in result:
                print(f"  {record['type']}: {record['count']}")
                total_rels += record['count']
            print(f"  TOTAL RELATIONSHIPS: {total_rels}")
            print(f"\n  TOTAL RECORDS: {total_nodes + total_rels}")

    def run_demo_queries(self):
        """Run and display demo queries."""
        print("\n" + "="*70)
        print("DEMO QUERIES")
        print("="*70)

        with self.driver.session() as session:
            # Query 1: Which PRs introduced Log4Shell?
            print("\n--- Query 1: Which PRs introduced CVE-2021-44228 (Log4Shell)? ---")
            result = session.run("""
                MATCH (r:Repository)-[:HAS_PR]->(pr:PullRequest)
                      -[:CONTAINS_COMMIT]->(c:Commit)
                      -[:SCANNED_BY]->(s:Scan)
                      -[:DETECTED]->(v:Vulnerability)
                      -[:MAPS_TO]->(cve:CVE {cve_id: 'CVE-2021-44228'})
                RETURN r.owner + '/' + r.name AS repository,
                       pr.number AS pr_number,
                       pr.title AS pr_title,
                       pr.created_at AS introduced_date
                ORDER BY pr.created_at
            """)
            for record in result:
                print(f"  {record['repository']} PR#{record['pr_number']}: {record['pr_title'][:50]}...")

            # Query 2: Transitive dependency vulnerabilities
            print("\n--- Query 2: Transitive dependency vulnerabilities ---")
            result = session.run("""
                MATCH path = (r:Repository)-[:HAS_DEPENDENCY]->(d1:Dependency)
                      -[:DEPENDS_ON*1..3]->(d2:Dependency)-[:HAS_CVE]->(cve:CVE)
                RETURN r.name AS repository,
                       d1.name + '@' + d1.version AS direct_dep,
                       d2.name + '@' + d2.version AS vuln_dep,
                       cve.cve_id AS cve_id,
                       cve.cvss_score AS cvss_score
                ORDER BY cve.cvss_score DESC
                LIMIT 5
            """)
            for record in result:
                print(f"  {record['repository']}: {record['direct_dep']} -> {record['vuln_dep']} ({record['cve_id']}, CVSS: {record['cvss_score']})")

            # Query 3: Common vulnerabilities across repos
            print("\n--- Query 3: Common vulnerabilities across repositories ---")
            result = session.run("""
                MATCH (r:Repository)-[:HAS_PR]->(:PullRequest)
                      -[:CONTAINS_COMMIT]->(:Commit)
                      -[:SCANNED_BY]->(:Scan)
                      -[:DETECTED]->(v:Vulnerability)
                      -[:MAPS_TO]->(cve:CVE)
                WITH cve, collect(DISTINCT r.name) AS affected_repos, count(DISTINCT r) AS repo_count
                WHERE repo_count > 1
                RETURN cve.cve_id AS cve_id, cve.cvss_score AS cvss_score, repo_count, affected_repos
                ORDER BY repo_count DESC, cve.cvss_score DESC
            """)
            for record in result:
                print(f"  {record['cve_id']} (CVSS: {record['cvss_score']}) - {record['repo_count']} repos: {record['affected_repos']}")

            # Query 4: Vulnerability lineage
            print("\n--- Query 4: Vulnerability lineage (payment-service Log4Shell) ---")
            result = session.run("""
                MATCH (r:Repository {name: 'payment-service'})-[:HAS_PR]->(pr1:PullRequest)
                      -[:CONTAINS_COMMIT]->(c1:Commit)
                      -[:SCANNED_BY]->(:Scan)
                      -[:DETECTED]->(v:Vulnerability)
                      -[:MAPS_TO]->(cve:CVE {cve_id: 'CVE-2021-44228'})
                OPTIONAL MATCH (r)-[:HAS_PR]->(pr2:PullRequest)
                      -[:CONTAINS_COMMIT]->(c2:Commit)
                      -[:SCANNED_BY]->(s2:Scan)
                WHERE pr2.created_at > pr1.created_at
                  AND s2.scanner = 'BLACKDUCK'
                  AND NOT EXISTS {
                    (s2)-[:DETECTED]->(:Vulnerability)-[:MAPS_TO]->(cve)
                  }
                WITH pr1, v, cve, pr2
                ORDER BY pr2.created_at
                WITH pr1, v, cve, collect(pr2)[0] AS fixing_pr
                RETURN pr1.number AS introduced_pr,
                       pr1.created_at AS introduced_date,
                       fixing_pr.number AS fixed_pr,
                       fixing_pr.merged_at AS fixed_date,
                       duration.between(pr1.created_at, fixing_pr.merged_at).days AS days_to_fix
            """)
            for record in result:
                print(f"  Introduced: PR#{record['introduced_pr']} ({str(record['introduced_date'])[:10]})")
                print(f"  Fixed: PR#{record['fixed_pr']} ({str(record['fixed_date'])[:10]})")
                print(f"  Days to fix: {record['days_to_fix']}")

    def seed_noise(self, count: int = 100):
        """
        Generate noise data for testing.
        Creates random repositories, PRs, commits, scans, and vulnerabilities.
        """
        print(f"\nGenerating {count} noise records...")

        orgs = ["noise-org", "test-corp", "random-inc", "fake-labs", "demo-co"]
        languages = ["python", "java", "go", "rust", "typescript", "ruby"]
        file_types = [
            ("terraform", ".tf", ["main.tf", "variables.tf", "outputs.tf", "providers.tf"]),
            ("kubernetes", ".yaml", ["deployment.yaml", "service.yaml", "configmap.yaml", "ingress.yaml"]),
            ("docker", "", ["Dockerfile", "docker-compose.yaml"]),
            ("cloudformation", ".json", ["template.json", "stack.json"]),
        ]
        severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
        scanners = ["KICS", "BLACKDUCK"]

        def random_string(length=8):
            return ''.join(random.choices(string.ascii_lowercase, k=length))

        def random_date(start_days_ago=365):
            days_ago = random.randint(1, start_days_ago)
            return datetime.now() - timedelta(days=days_ago)

        with self.driver.session() as session:
            repos_created = 0
            prs_created = 0
            vulns_created = 0

            # Generate random repositories with full graph
            num_repos = max(count // 10, 5)
            for i in range(num_repos):
                org = random.choice(orgs)
                repo_name = f"{random.choice(languages)}-{random_string()}"
                repo_id = f"{org}/{repo_name}"

                # Create repository
                session.run("""
                    MERGE (r:Repository {owner: $owner, name: $name})
                    SET r.full_name = $full_name,
                        r.language = $language,
                        r.created_at = $created_at,
                        r.is_noise = true
                """, owner=org, name=repo_name, full_name=repo_id,
                    language=random.choice(languages),
                    created_at=random_date(730).isoformat())
                repos_created += 1

                # Create random files for this repo
                infra_type, ext, file_names = random.choice(file_types)
                for fname in random.sample(file_names, min(len(file_names), random.randint(1, 3))):
                    file_path = f"infra/{fname}"
                    session.run("""
                        MATCH (r:Repository {owner: $owner, name: $name})
                        MERGE (f:File {path: $path, repository: $repo_id})
                        SET f.type = $type, f.is_noise = true
                        MERGE (r)-[:CONTAINS_FILE]->(f)
                    """, owner=org, name=repo_name, repo_id=repo_id,
                        path=file_path, type=infra_type)

                # Create PRs for this repo
                num_prs = random.randint(2, 8)
                for pr_num in range(1, num_prs + 1):
                    pr_date = random_date(180)
                    pr_title = f"{random.choice(['Fix', 'Add', 'Update', 'Refactor'])} {random_string()}"

                    session.run("""
                        MATCH (r:Repository {owner: $owner, name: $name})
                        MERGE (pr:PullRequest {repo: $repo_id, number: $pr_num})
                        SET pr.title = $title,
                            pr.created_at = $created_at,
                            pr.merged_at = $merged_at,
                            pr.is_noise = true
                        MERGE (r)-[:HAS_PR]->(pr)
                    """, owner=org, name=repo_name, repo_id=repo_id, pr_num=pr_num + 1000,
                        title=pr_title, created_at=pr_date.isoformat(),
                        merged_at=(pr_date + timedelta(days=random.randint(1, 7))).isoformat())
                    prs_created += 1

                    # Create commit for PR
                    commit_sha = uuid.uuid4().hex[:40]
                    session.run("""
                        MATCH (pr:PullRequest {repo: $repo_id, number: $pr_num})
                        MERGE (c:Commit {sha: $sha})
                        SET c.message = $message,
                            c.created_at = $created_at,
                            c.is_noise = true
                        MERGE (pr)-[:CONTAINS_COMMIT]->(c)
                    """, repo_id=repo_id, pr_num=pr_num + 1000, sha=commit_sha,
                        message=f"noise commit {random_string()}",
                        created_at=pr_date.isoformat())

                    # Create scan for commit
                    scanner = random.choice(scanners)
                    scan_id = f"scan-{uuid.uuid4().hex[:8]}"
                    session.run("""
                        MATCH (c:Commit {sha: $sha})
                        MERGE (s:Scan {scan_id: $scan_id})
                        SET s.scanner = $scanner,
                            s.started_at = $started_at,
                            s.completed_at = $completed_at,
                            s.status = 'completed',
                            s.is_noise = true
                        MERGE (c)-[:SCANNED_BY]->(s)
                    """, sha=commit_sha, scan_id=scan_id, scanner=scanner,
                        started_at=pr_date.isoformat(),
                        completed_at=(pr_date + timedelta(minutes=random.randint(1, 30))).isoformat())

                    # Create random vulnerabilities
                    num_vulns = random.randint(0, 5)
                    for v in range(num_vulns):
                        vuln_id = f"NOISE-{uuid.uuid4().hex[:8].upper()}"
                        severity = random.choices(
                            severities,
                            weights=[5, 15, 30, 35, 15]  # Weighted towards MEDIUM/LOW
                        )[0]

                        session.run("""
                            MATCH (s:Scan {scan_id: $scan_id})
                            MERGE (v:Vulnerability {vuln_id: $vuln_id})
                            SET v.severity = $severity,
                                v.title = $title,
                                v.description = $description,
                                v.is_noise = true
                            MERGE (s)-[:DETECTED]->(v)
                        """, scan_id=scan_id, vuln_id=vuln_id, severity=severity,
                            title=f"Noise vulnerability {random_string()}",
                            description=f"Auto-generated noise vulnerability for testing")
                        vulns_created += 1

            print(f"  Created {repos_created} noise repositories")
            print(f"  Created {prs_created} noise PRs with commits and scans")
            print(f"  Created {vulns_created} noise vulnerabilities")

    def seed_all(self, clear: bool = False, noise: int = 0):
        """Run all seeding operations."""
        if clear:
            self.clear_database()

        self.create_indexes()
        self.seed_cves()
        self.seed_dependencies()
        self.seed_rules()
        self.seed_repositories()
        self.seed_files()
        self.seed_users()
        self.seed_prs_and_scans()

        if noise > 0:
            self.seed_noise(noise)

        self.print_stats()
        self.run_demo_queries()


def main():
    parser = argparse.ArgumentParser(description="Seed Neo4j with security scan demo data")
    parser.add_argument("--uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                        help="Neo4j URI (default: bolt://localhost:7687)")
    parser.add_argument("--user", default=os.getenv("NEO4J_USER", "neo4j"),
                        help="Neo4j username (default: neo4j)")
    parser.add_argument("--password", default=os.getenv("NEO4J_PASSWORD", "password123"),
                        help="Neo4j password (default: password123)")
    parser.add_argument("--clear", action="store_true",
                        help="Clear existing data before seeding")
    parser.add_argument("--demo-only", action="store_true",
                        help="Only run demo queries (assumes data exists)")
    parser.add_argument("--noise", type=int, default=0, metavar="COUNT",
                        help="Generate COUNT noise records (random repos, PRs, vulns)")
    parser.add_argument("--noise-only", type=int, default=0, metavar="COUNT",
                        help="Only generate noise records, skip base demo data")

    args = parser.parse_args()

    print(f"Connecting to Neo4j at {args.uri}...")
    seeder = SecurityGraphSeeder(args.uri, args.user, args.password)

    try:
        if args.demo_only:
            seeder.print_stats()
            seeder.run_demo_queries()
        elif args.noise_only > 0:
            if args.clear:
                seeder.clear_database()
            seeder.create_indexes()
            seeder.seed_noise(args.noise_only)
            seeder.print_stats()
            print("\nNoise seeding complete!")
        else:
            seeder.seed_all(clear=args.clear, noise=args.noise)
            print("\nSeeding complete!")
    finally:
        seeder.close()


if __name__ == "__main__":
    main()
