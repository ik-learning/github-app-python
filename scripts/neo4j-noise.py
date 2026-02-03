#!/usr/bin/env python3
"""
Neo4j Noise Data Generator - Realistic Random Security Scan Data

Generates ~300 random records to make the demo more realistic.
Adds variety in repositories, PRs, commits, scans, and vulnerabilities.

┌─────────────────────────────────────────────────────────────────────────┐
│                      NOISE DATA SUMMARY                                 │
├───────────────┬───────┬─────────────────────────────────────────────────┤
│   Node Type   │ Count │              Description                        │
├───────────────┼───────┼─────────────────────────────────────────────────┤
│ Repository    │    10 │ Additional microservices and tools              │
│ User          │     8 │ More team members                               │
│ PullRequest   │    40 │ Random PRs across repos                         │
│ Commit        │    80 │ ~2 commits per PR                               │
│ Scan          │    80 │ Mix of KICS and Blackduck                       │
│ Vulnerability │    60 │ Various severities and types                    │
│ File          │    15 │ Additional source files                         │
│ Dependency    │    12 │ More packages with versions                     │
├───────────────┼───────┼─────────────────────────────────────────────────┤
│ TOTAL NODES   │  ~305 │                                                 │
│ Relationships │  ~250 │                                                 │
│ TOTAL RECORDS │  ~555 │ (combined with seed data = ~750 total)          │
└───────────────┴───────┴─────────────────────────────────────────────────┘

Usage:
    python scripts/neo4j-noise.py
    python scripts/neo4j-noise.py --count 500  # Generate more records
    python scripts/neo4j-noise.py --seed 42    # Reproducible random data
"""

import argparse
import os
import random
import string
import sys
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any

try:
    from neo4j import GraphDatabase
except ImportError:
    print("Error: neo4j package not installed. Run: pip install neo4j")
    sys.exit(1)


# =============================================================================
# REALISTIC DATA POOLS
# =============================================================================

REPO_NAMES = [
    "order-service", "cart-api", "checkout-worker", "shipping-tracker",
    "recommendation-engine", "search-service", "auth-gateway", "email-sender",
    "sms-notifier", "report-generator", "data-pipeline", "ml-inference",
    "config-server", "feature-flags", "rate-limiter", "cache-manager",
    "audit-logger", "metrics-collector", "health-monitor", "backup-service",
]

USER_NAMES = [
    ("frank-backend", "Frank Backend", "frank@acme-corp.com"),
    ("grace-frontend", "Grace Frontend", "grace@acme-corp.com"),
    ("henry-devops", "Henry DevOps", "henry@acme-corp.com"),
    ("iris-security", "Iris Security", "iris@acme-corp.com"),
    ("jack-data", "Jack Data Engineer", "jack@acme-corp.com"),
    ("kate-mobile", "Kate Mobile Dev", "kate@acme-corp.com"),
    ("leo-platform", "Leo Platform", "leo@acme-corp.com"),
    ("mia-sre", "Mia SRE", "mia@acme-corp.com"),
]

PR_TITLES = [
    "Add caching layer for {component}",
    "Fix memory leak in {component}",
    "Upgrade {dependency} to latest version",
    "Refactor {component} for better performance",
    "Add unit tests for {component}",
    "Implement retry logic for {component}",
    "Add metrics endpoint for {component}",
    "Fix race condition in {component}",
    "Add health check for {component}",
    "Optimize database queries in {component}",
    "Add pagination to {component} API",
    "Implement rate limiting for {component}",
    "Add input validation to {component}",
    "Fix timeout issues in {component}",
    "Add logging to {component}",
    "Implement graceful shutdown for {component}",
    "Add configuration options for {component}",
    "Fix null pointer exception in {component}",
    "Add error handling to {component}",
    "Implement circuit breaker for {component}",
]

COMMIT_MESSAGES = [
    "feat: add {feature}",
    "fix: resolve {issue}",
    "refactor: improve {component}",
    "test: add tests for {component}",
    "docs: update {component} documentation",
    "chore: update dependencies",
    "perf: optimize {component}",
    "style: format {component} code",
    "build: update build configuration",
    "ci: add {component} to pipeline",
]

COMPONENTS = [
    "user handler", "order processor", "payment gateway", "notification service",
    "data validator", "cache layer", "queue consumer", "API endpoint",
    "database connector", "file uploader", "email sender", "webhook handler",
]

DEPENDENCIES_NOISE = [
    ("jackson-databind", ["2.12.3", "2.13.0", "2.14.1"], "maven"),
    ("guava", ["30.1-jre", "31.0-jre", "32.0-jre"], "maven"),
    ("netty", ["4.1.65", "4.1.70", "4.1.85"], "maven"),
    ("hibernate-core", ["5.4.32", "5.6.0", "6.1.0"], "maven"),
    ("react", ["17.0.2", "18.0.0", "18.2.0"], "npm"),
    ("webpack", ["5.64.0", "5.70.0", "5.88.0"], "npm"),
    ("typescript", ["4.5.0", "4.9.0", "5.0.0"], "npm"),
    ("django", ["3.2.10", "4.0.0", "4.2.0"], "pip"),
    ("sqlalchemy", ["1.4.25", "1.4.40", "2.0.0"], "pip"),
    ("celery", ["5.2.0", "5.2.7", "5.3.0"], "pip"),
    ("boto3", ["1.20.0", "1.26.0", "1.28.0"], "pip"),
    ("kubernetes", ["21.7.0", "25.3.0", "27.2.0"], "pip"),
]

FILES_NOISE = [
    ("src/main/java/com/acme/Service.java", "java"),
    ("src/main/java/com/acme/Controller.java", "java"),
    ("src/main/java/com/acme/Repository.java", "java"),
    ("src/components/Dashboard.tsx", "typescript"),
    ("src/components/UserProfile.tsx", "typescript"),
    ("src/api/client.ts", "typescript"),
    ("app/services/processor.py", "python"),
    ("app/models/entity.py", "python"),
    ("app/api/routes.py", "python"),
    ("helm/values.yaml", "yaml"),
    ("helm/templates/deployment.yaml", "yaml"),
    ("terraform/modules/vpc/main.tf", "terraform"),
    ("terraform/modules/eks/main.tf", "terraform"),
    ("ansible/playbooks/deploy.yml", "yaml"),
    (".gitlab-ci.yml", "yaml"),
]

KICS_FINDINGS = [
    ("Container Image Not Pinned", "MEDIUM", "CWE-829", 5.5, "Pin container images to specific versions"),
    ("Missing Network Policy", "MEDIUM", "CWE-284", 5.0, "Add Kubernetes NetworkPolicy"),
    ("Privileged Container", "HIGH", "CWE-250", 7.5, "Remove privileged: true"),
    ("Host Path Volume Mount", "MEDIUM", "CWE-668", 5.5, "Avoid hostPath mounts"),
    ("Missing Pod Security Policy", "MEDIUM", "CWE-693", 5.0, "Implement PodSecurityPolicy"),
    ("Insecure TLS Version", "HIGH", "CWE-326", 7.0, "Use TLS 1.2 or higher"),
    ("Hardcoded Password", "CRITICAL", "CWE-798", 9.0, "Use secrets management"),
    ("Open Ingress", "HIGH", "CWE-284", 7.5, "Restrict ingress CIDR"),
    ("Missing Encryption at Rest", "HIGH", "CWE-311", 7.0, "Enable encryption"),
    ("Overly Permissive CORS", "MEDIUM", "CWE-942", 5.5, "Restrict CORS origins"),
    ("SQL Injection Risk", "CRITICAL", "CWE-89", 9.5, "Use parameterized queries"),
    ("XSS Vulnerability", "HIGH", "CWE-79", 7.5, "Sanitize user input"),
    ("Missing HTTPS Redirect", "MEDIUM", "CWE-319", 5.0, "Force HTTPS"),
    ("Weak Cryptography", "HIGH", "CWE-327", 7.0, "Use strong algorithms"),
    ("Debug Mode Enabled", "LOW", "CWE-489", 3.5, "Disable debug in production"),
]

BLACKDUCK_FINDINGS = [
    ("Prototype Pollution in lodash", "HIGH", "CWE-1321", 7.5, "Upgrade lodash"),
    ("ReDoS in validator.js", "MEDIUM", "CWE-1333", 5.5, "Upgrade validator"),
    ("Path Traversal in archiver", "HIGH", "CWE-22", 7.5, "Upgrade archiver"),
    ("Command Injection in shell-quote", "CRITICAL", "CWE-78", 9.0, "Upgrade shell-quote"),
    ("Denial of Service in minimist", "MEDIUM", "CWE-400", 5.0, "Upgrade minimist"),
    ("Buffer Overflow in node-forge", "HIGH", "CWE-120", 7.5, "Upgrade node-forge"),
    ("XML External Entity in xml2js", "HIGH", "CWE-611", 7.5, "Upgrade xml2js"),
    ("Insecure Deserialization in serialize-javascript", "CRITICAL", "CWE-502", 9.5, "Upgrade package"),
    ("Information Exposure in debug", "LOW", "CWE-200", 3.5, "Upgrade debug"),
    ("Memory Corruption in jpeg-js", "HIGH", "CWE-787", 7.5, "Upgrade jpeg-js"),
]


class NoiseGenerator:
    """Generates realistic random security scan data."""

    def __init__(self, uri: str, user: str, password: str, seed: int = None):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        if seed is not None:
            random.seed(seed)
        self._verify_connection()

    def _verify_connection(self):
        try:
            with self.driver.session() as session:
                session.run("RETURN 1")
            print("Connected to Neo4j successfully")
        except Exception as e:
            print(f"Failed to connect to Neo4j: {e}")
            sys.exit(1)

    def close(self):
        self.driver.close()

    def _random_sha(self) -> str:
        """Generate a random commit SHA."""
        return ''.join(random.choices(string.hexdigits.lower(), k=40))

    def _random_date(self, start_year: int = 2022, end_year: int = 2024) -> datetime:
        """Generate a random datetime."""
        start = datetime(start_year, 1, 1)
        end = datetime(end_year, 12, 31)
        delta = end - start
        random_days = random.randint(0, delta.days)
        random_hours = random.randint(8, 18)
        random_minutes = random.randint(0, 59)
        return start + timedelta(days=random_days, hours=random_hours, minutes=random_minutes)

    def _random_severity(self) -> str:
        """Generate weighted random severity."""
        return random.choices(
            ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
            weights=[10, 25, 40, 25]
        )[0]

    def generate_users(self) -> List[Dict]:
        """Generate additional users."""
        users = []
        with self.driver.session() as session:
            for login, name, email in USER_NAMES:
                session.run("""
                    MERGE (u:User {login: $login})
                    SET u.name = $name, u.email = $email
                """, login=login, name=name, email=email)
                users.append({"login": login, "name": name})
        print(f"Created {len(users)} additional users")
        return users

    def generate_repositories(self, count: int = 10) -> List[str]:
        """Generate additional repositories."""
        repos = random.sample(REPO_NAMES, min(count, len(REPO_NAMES)))
        with self.driver.session() as session:
            for name in repos:
                session.run("""
                    MERGE (r:Repository {name: $name, owner: 'acme-corp'})
                    SET r.url = 'https://github.com/acme-corp/' + $name,
                        r.default_branch = 'main'
                """, name=name)
        print(f"Created {len(repos)} additional repositories")
        return repos

    def generate_files(self) -> List[Dict]:
        """Generate additional files."""
        files = []
        with self.driver.session() as session:
            for path, language in FILES_NOISE:
                session.run("""
                    MERGE (f:File {path: $path})
                    SET f.language = $language
                """, path=path, language=language)
                files.append({"path": path, "language": language})
        print(f"Created {len(files)} additional files")
        return files

    def generate_dependencies(self) -> List[Dict]:
        """Generate additional dependencies."""
        deps = []
        with self.driver.session() as session:
            for name, versions, ecosystem in DEPENDENCIES_NOISE:
                for version in versions:
                    session.run("""
                        MERGE (d:Dependency {name: $name, version: $version})
                        SET d.ecosystem = $ecosystem, d.license = 'Apache-2.0'
                    """, name=name, version=version, ecosystem=ecosystem)
                    deps.append({"name": name, "version": version})
        print(f"Created {len(deps)} additional dependencies")
        return deps

    def generate_prs_with_scans(self, repos: List[str], users: List[Dict],
                                pr_count: int = 40) -> Dict[str, int]:
        """Generate PRs, commits, scans, and vulnerabilities."""
        stats = {"prs": 0, "commits": 0, "scans": 0, "vulns": 0}

        with self.driver.session() as session:
            # Get existing files for linking
            files_result = session.run("MATCH (f:File) RETURN f.path AS path")
            available_files = [r["path"] for r in files_result]

            # Get existing dependencies for linking
            deps_result = session.run("MATCH (d:Dependency) RETURN d.name AS name, d.version AS version")
            available_deps = [(r["name"], r["version"]) for r in deps_result]

            # Get existing rules
            rules_result = session.run("MATCH (r:Rule) RETURN r.name AS name")
            available_rules = [r["name"] for r in rules_result]

            # Get existing CVEs
            cves_result = session.run("MATCH (c:CVE) RETURN c.cve_id AS id")
            available_cves = [r["id"] for r in cves_result]

            for _ in range(pr_count):
                repo = random.choice(repos)
                user = random.choice(users)
                pr_date = self._random_date()
                pr_number = random.randint(100, 999)
                component = random.choice(COMPONENTS)
                dependency = random.choice(["lodash", "jackson", "spring", "django", "react"])

                pr_title = random.choice(PR_TITLES).format(
                    component=component,
                    dependency=dependency
                )

                # Randomly decide PR state
                is_merged = random.random() > 0.2
                pr_state = "merged" if is_merged else "open"
                merged_at = (pr_date + timedelta(days=random.randint(1, 5))) if is_merged else None

                # Create PR
                session.run("""
                    MATCH (r:Repository {name: $repo})
                    MATCH (u:User {login: $user})
                    CREATE (pr:PullRequest {
                        number: $number,
                        title: $title,
                        state: $state,
                        created_at: datetime($created_at)
                    })
                    CREATE (r)-[:HAS_PR]->(pr)
                    CREATE (pr)-[:OPENED_BY]->(u)
                    WITH pr
                    WHERE $merged_at IS NOT NULL
                    SET pr.merged_at = datetime($merged_at)
                """, repo=repo, user=user["login"], number=pr_number,
                     title=pr_title, state=pr_state,
                     created_at=pr_date.isoformat(),
                     merged_at=merged_at.isoformat() if merged_at else None)
                stats["prs"] += 1

                # Create 1-3 commits per PR
                commit_count = random.randint(1, 3)
                commit_date = pr_date

                for i in range(commit_count):
                    commit_sha = self._random_sha()
                    commit_msg = random.choice(COMMIT_MESSAGES).format(
                        feature=component,
                        issue=f"issue with {component}",
                        component=component
                    )
                    commit_date = commit_date + timedelta(hours=random.randint(1, 8))

                    session.run("""
                        MATCH (pr:PullRequest {number: $pr_number})
                              <-[:HAS_PR]-(r:Repository {name: $repo})
                        CREATE (c:Commit {
                            sha: $sha,
                            message: $message,
                            author: $author,
                            timestamp: datetime($timestamp)
                        })
                        CREATE (pr)-[:CONTAINS_COMMIT]->(c)
                    """, pr_number=pr_number, repo=repo, sha=commit_sha,
                         message=commit_msg, author=user["login"],
                         timestamp=commit_date.isoformat())
                    stats["commits"] += 1

                    # Create scan for each commit (70% chance)
                    if random.random() > 0.3:
                        scanner = random.choice(["KICS", "BLACKDUCK"])
                        scan_id = f"scan-noise-{uuid.uuid4().hex[:8]}"

                        session.run("""
                            MATCH (c:Commit {sha: $sha})
                            CREATE (s:Scan {
                                id: $scan_id,
                                scanner: $scanner,
                                started_at: datetime($started),
                                completed_at: datetime($completed),
                                status: 'completed'
                            })
                            CREATE (c)-[:SCANNED_BY]->(s)
                        """, sha=commit_sha, scan_id=scan_id, scanner=scanner,
                             started=commit_date.isoformat(),
                             completed=(commit_date + timedelta(minutes=random.randint(2, 15))).isoformat())
                        stats["scans"] += 1

                        # Create 0-3 vulnerabilities per scan (60% chance of having vulns)
                        if random.random() > 0.4:
                            vuln_count = random.randint(1, 3)
                            findings = KICS_FINDINGS if scanner == "KICS" else BLACKDUCK_FINDINGS

                            for _ in range(vuln_count):
                                finding = random.choice(findings)
                                vuln_id = f"vuln-noise-{uuid.uuid4().hex[:8]}"

                                session.run("""
                                    MATCH (s:Scan {id: $scan_id})
                                    CREATE (v:Vulnerability {
                                        id: $vuln_id,
                                        severity: $severity,
                                        title: $title,
                                        description: $title,
                                        cwe_id: $cwe,
                                        cvss_score: $cvss,
                                        remediation: $remediation
                                    })
                                    CREATE (s)-[:DETECTED]->(v)
                                """, scan_id=scan_id, vuln_id=vuln_id,
                                     severity=finding[1], title=finding[0],
                                     cwe=finding[2], cvss=finding[3],
                                     remediation=finding[4])
                                stats["vulns"] += 1

                                # Link to file (KICS) or dependency (Blackduck)
                                if scanner == "KICS" and available_files:
                                    file_path = random.choice(available_files)
                                    line = random.randint(10, 200)
                                    session.run("""
                                        MATCH (v:Vulnerability {id: $vuln_id})
                                        MATCH (f:File {path: $path})
                                        CREATE (v)-[:IN_FILE {line: $line}]->(f)
                                    """, vuln_id=vuln_id, path=file_path, line=line)

                                    # Link to rule if available
                                    if available_rules:
                                        rule_name = random.choice(available_rules)
                                        session.run("""
                                            MATCH (v:Vulnerability {id: $vuln_id})
                                            MATCH (r:Rule {name: $rule})
                                            MERGE (v)-[:VIOLATES]->(r)
                                        """, vuln_id=vuln_id, rule=rule_name)

                                elif scanner == "BLACKDUCK" and available_deps:
                                    dep = random.choice(available_deps)
                                    session.run("""
                                        MATCH (v:Vulnerability {id: $vuln_id})
                                        MATCH (d:Dependency {name: $name, version: $version})
                                        CREATE (v)-[:IN_DEPENDENCY]->(d)
                                    """, vuln_id=vuln_id, name=dep[0], version=dep[1])

                                    # Link to CVE if available (30% chance)
                                    if available_cves and random.random() > 0.7:
                                        cve_id = random.choice(available_cves)
                                        session.run("""
                                            MATCH (v:Vulnerability {id: $vuln_id})
                                            MATCH (c:CVE {cve_id: $cve})
                                            MERGE (v)-[:MAPS_TO]->(c)
                                        """, vuln_id=vuln_id, cve=cve_id)

        print(f"Created {stats['prs']} PRs, {stats['commits']} commits, "
            f"{stats['scans']} scans, {stats['vulns']} vulnerabilities")
        return stats

    def print_stats(self):
        """Print database statistics."""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] AS label, count(*) AS count
                ORDER BY count DESC
            """)
            print("\n" + "="*50)
            print("DATABASE STATISTICS (after noise generation)")
            print("="*50)
            total_nodes = 0
            for record in result:
                print(f"  {record['label']:20} {record['count']:>6}")
                total_nodes += record['count']

            result = session.run("""
                MATCH ()-[r]->()
                RETURN count(r) AS count
            """)
            total_rels = result.single()["count"]

            print("-"*50)
            print(f"  {'TOTAL NODES':20} {total_nodes:>6}")
            print(f"  {'TOTAL RELATIONSHIPS':20} {total_rels:>6}")
            print(f"  {'TOTAL RECORDS':20} {total_nodes + total_rels:>6}")
            print("="*50)

    def generate_all(self, pr_count: int = 40):
        """Generate all noise data."""
        print("\n" + "="*50)
        print("GENERATING NOISE DATA")
        print("="*50 + "\n")

        users = self.generate_users()
        repos = self.generate_repositories(count=10)
        self.generate_files()
        self.generate_dependencies()
        self.generate_prs_with_scans(repos, users, pr_count=pr_count)
        self.print_stats()


def main():
    parser = argparse.ArgumentParser(description="Generate noise data for Neo4j security scan demo")
    parser.add_argument("--uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                        help="Neo4j URI (default: bolt://localhost:7687)")
    parser.add_argument("--user", default=os.getenv("NEO4J_USER", "neo4j"),
                        help="Neo4j username (default: neo4j)")
    parser.add_argument("--password", default=os.getenv("NEO4J_PASSWORD", "password123"),
                        help="Neo4j password (default: password123)")
    parser.add_argument("--count", type=int, default=40,
                        help="Number of PRs to generate (default: 40, generates ~300 records)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducible data")

    args = parser.parse_args()

    print(f"Connecting to Neo4j at {args.uri}...")
    generator = NoiseGenerator(args.uri, args.user, args.password, seed=args.seed)

    try:
        generator.generate_all(pr_count=args.count)
        print("\nNoise generation complete!")
        print("Run demo queries: python scripts/neo4j-seed.py --demo-only")
    finally:
        generator.close()


if __name__ == "__main__":
    main()
