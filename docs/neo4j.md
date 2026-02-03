# Neo4j Security Graph

This document describes the Neo4j graph model for security scan data and recommended visualization settings.

## Graph Model

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           SECURITY SCAN GRAPH                                 │
│                                                                               │
│  ┌──────────┐    ┌─────────────┐    ┌────────┐    ┌──────┐                   │
│  │Repository│───▶│ PullRequest │───▶│ Commit │───▶│ Scan │                   │
│  └────┬─────┘    └──────┬──────┘    └────────┘    └──┬───┘                   │
│       │                 │                            │                        │
│       │                 │                            ▼                        │
│       │                 │                     ┌──────────────┐                │
│       │                 │                     │Vulnerability │                │
│       │                 │                     └──────┬───────┘                │
│       │                 │                            │                        │
│       ▼                 ▼                            ▼                        │
│  ┌────────┐        ┌────────┐                  ┌─────────┐                    │
│  │  File  │        │  User  │                  │   CVE   │                    │
│  └────────┘        └────────┘                  └─────────┘                    │
│                                                                               │
│  ┌────────────┐    ┌──────┐                                                  │
│  │ Dependency │───▶│ CVE  │                                                  │
│  └────────────┘    └──────┘                                                  │
│                                                                               │
│  ┌──────┐                                                                    │
│  │ Rule │  (KICS security rules)                                             │
│  └──────┘                                                                    │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Node Types

| Label | Description | Key Properties |
|-------|-------------|----------------|
| `Repository` | GitHub repository | `owner`, `name`, `full_name` |
| `PullRequest` | Pull request | `number`, `title`, `created_at`, `merged_at` |
| `Commit` | Git commit | `sha`, `message`, `created_at` |
| `Scan` | Security scan execution | `scan_id`, `scanner`, `status` |
| `Vulnerability` | Detected security issue | `vuln_id`, `severity`, `title` |
| `CVE` | Common Vulnerabilities and Exposures | `cve_id`, `cvss_score`, `published` |
| `Dependency` | Package dependency | `name`, `version`, `ecosystem` |
| `File` | Source file | `path`, `type` |
| `User` | Developer/author | `login`, `name`, `email` |
| `Rule` | KICS security rule | `rule_id`, `name`, `severity` |

## Relationships

| Relationship | From | To | Description |
|--------------|------|-----|-------------|
| `HAS_PR` | Repository | PullRequest | Repository contains PR |
| `CONTAINS_COMMIT` | PullRequest | Commit | PR includes commit |
| `SCANNED_BY` | Commit | Scan | Commit was scanned |
| `DETECTED` | Scan | Vulnerability | Scan found vulnerability |
| `MAPS_TO` | Vulnerability | CVE | Vulnerability maps to CVE |
| `HAS_DEPENDENCY` | Repository | Dependency | Repository uses dependency |
| `DEPENDS_ON` | Dependency | Dependency | Transitive dependency |
| `HAS_CVE` | Dependency | CVE | Dependency has known CVE |
| `CONTAINS_FILE` | Repository | File | Repository contains file |
| `IN_FILE` | Vulnerability | File | Vulnerability found in file |
| `OPENED_BY` | PullRequest | User | PR author |
| `VIOLATES` | Vulnerability | Rule | Vulnerability violates rule |

## Color Scheme

Recommended colors for Neo4j Browser visualization:

| Entity | Color | Hex | Rationale |
|--------|-------|-----|-----------|
| **CVE** | Red | `#E74C3C` | Danger/threat |
| **Vulnerability** | Orange | `#E67E22` | Warning/detected issues |
| **Repository** | Blue | `#3498DB` | Primary entity |
| **PullRequest** | Cyan | `#00BCD4` | Change in progress |
| **Commit** | Light Blue | `#5DADE2` | Related to PR |
| **Scan** | Purple | `#9B59B6` | Process/action |
| **Dependency** | Teal | `#1ABC9C` | External/third-party |
| **File** | Gray | `#7F8C8D` | Neutral artifact |
| **User** | Green | `#27AE60` | People |
| **Rule** | Yellow | `#F1C40F` | Policy/configuration |

## GRASS Stylesheet

Copy and import in Neo4j Browser via `:style` command:

```grass
node {
  diameter: 50px;
  color: #A5ABB6;
  border-color: #9AA1AC;
  border-width: 2px;
  text-color-internal: #FFFFFF;
  font-size: 10px;
}

node.CVE {
  color: #E74C3C;
  border-color: #C0392B;
  caption: "{cve_id}";
}

node.Vulnerability {
  color: #E67E22;
  border-color: #D35400;
  caption: "{severity}";
}

node.Repository {
  color: #3498DB;
  border-color: #2980B9;
  diameter: 65px;
  caption: "{name}";
}

node.PullRequest {
  color: #00BCD4;
  border-color: #00ACC1;
  caption: "PR#{number}";
}

node.Commit {
  color: #5DADE2;
  border-color: #3498DB;
  diameter: 40px;
  caption: "{sha}";
}

node.Scan {
  color: #9B59B6;
  border-color: #8E44AD;
  caption: "{scanner}";
}

node.Dependency {
  color: #1ABC9C;
  border-color: #16A085;
  caption: "{name}";
}

node.File {
  color: #7F8C8D;
  border-color: #6C7A7D;
  diameter: 40px;
  caption: "{path}";
}

node.User {
  color: #27AE60;
  border-color: #229954;
  caption: "{login}";
}

node.Rule {
  color: #F1C40F;
  border-color: #D4AC0D;
  caption: "{name}";
}

relationship {
  color: #A5ABB6;
  shaft-width: 1px;
  font-size: 8px;
  padding: 3px;
  text-color-external: #000000;
  text-color-internal: #FFFFFF;
  caption: "<type>";
}

relationship.DETECTED {
  color: #E74C3C;
  shaft-width: 2px;
}

relationship.MAPS_TO {
  color: #E67E22;
}

relationship.HAS_CVE {
  color: #E74C3C;
}
```

## Importing Styles

### From Docker Container (Recommended)

The stylesheet is mounted at `/opt/neo4j-custom/style.grass` in the container.

1. Open Neo4j Browser: http://localhost:7474
2. Type `:style` and press Enter
3. Drag and drop `infra/neo4j/style.grass` from your local machine

Or copy from container:
```bash
docker cp neo4j:/opt/neo4j-custom/style.grass ./style.grass
```

### Manual Import

1. Open Neo4j Browser (http://localhost:7474)
2. Type `:style` and press Enter
3. Click "Export" to backup current styles (optional)
4. Drag and drop `infra/neo4j/style.grass` into the style panel

### Neo4j Desktop (with Bloom)

For richer visualization with saveable perspectives:

1. Download [Neo4j Desktop](https://neo4j.com/download/)
2. Create Project → Add Database → "Connect to Remote DBMS"
3. Connection URL: `bolt://localhost:7687`
4. No authentication (disabled in dev)
5. Click "Connect"
6. Open **Bloom** from the sidebar for advanced visualization

### Programmatic Import

Neo4j Browser styles are stored in browser localStorage, not in the database. Therefore, styles cannot be applied via Python/Cypher.

**Workarounds:**

1. **Neo4j Desktop** - Connect to Docker, use Bloom with saveable Perspectives
2. **Custom Application** - Build visualization with D3.js/vis.js where you control colors

## Seed Script Usage

```bash
# Full demo data
python scripts/neo4j-seed.py --clear

# Demo data + noise
python scripts/neo4j-seed.py --clear --noise 500

# Only noise data
python scripts/neo4j-seed.py --clear --noise-only 1000

# Run demo queries only
python scripts/neo4j-seed.py --demo-only
```

## Example Queries

### Find PRs that introduced a specific CVE

```cypher
MATCH (r:Repository)-[:HAS_PR]->(pr:PullRequest)
      -[:CONTAINS_COMMIT]->(:Commit)
      -[:SCANNED_BY]->(:Scan)
      -[:DETECTED]->(:Vulnerability)
      -[:MAPS_TO]->(cve:CVE {cve_id: 'CVE-2021-44228'})
RETURN r.name AS repo, pr.number AS pr, pr.title AS title
```

### Transitive dependency vulnerabilities

```cypher
MATCH path = (r:Repository)-[:HAS_DEPENDENCY]->(d1:Dependency)
      -[:DEPENDS_ON*1..3]->(d2:Dependency)-[:HAS_CVE]->(cve:CVE)
RETURN r.name AS repo,
       d1.name AS direct_dep,
       d2.name AS vuln_dep,
       cve.cve_id, cve.cvss_score
ORDER BY cve.cvss_score DESC
```

### Vulnerabilities by severity across repos

```cypher
MATCH (r:Repository)-[:HAS_PR]->(:PullRequest)
      -[:CONTAINS_COMMIT]->(:Commit)
      -[:SCANNED_BY]->(:Scan)
      -[:DETECTED]->(v:Vulnerability)
RETURN r.name AS repo, v.severity, count(v) AS count
ORDER BY repo, v.severity
```

### Filter out noise data

```cypher
MATCH (r:Repository)
WHERE r.is_noise IS NULL OR r.is_noise = false
RETURN r
```
