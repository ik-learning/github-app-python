#!/bin/bash
# ============================================================================
# Neo4j Setup Script - Security Scan Demo Data
# ============================================================================
#
# Sets up Neo4j and loads seed data for security scan demo.
#
# ┌─────────────────────────────────────────────────────────────────────────┐
# │                         RECORD SUMMARY                                  │
# ├───────────────┬───────┬─────────────────────────────────────────────────┤
# │   Node Type   │ Count │              Description                        │
# ├───────────────┼───────┼─────────────────────────────────────────────────┤
# │ CVE           │     7 │ Log4Shell, Spring4Shell, Text4Shell, etc.       │
# │ Dependency    │    15 │ Maven, npm, pip packages (vulnerable + fixed)   │
# │ Rule          │     8 │ KICS security rules                             │
# │ Repository    │     6 │ payment-service, user-api, inventory-manager    │
# │ File          │    14 │ Terraform, K8s, Docker, config files            │
# │ User          │     5 │ Developers with different roles                 │
# │ PullRequest   │    12 │ Across all repos                                │
# │ Commit        │    16 │ Multiple commits per PR                         │
# │ Scan          │    16 │ KICS and Blackduck scans                        │
# │ Vulnerability │    18 │ Mix of infra and dependency vulns               │
# ├───────────────┼───────┼─────────────────────────────────────────────────┤
# │ TOTAL         │  ~117 │ nodes                                           │
# │ Relationships │   ~80 │ edges                                           │
# │ TOTAL RECORDS │  ~200 │                                                 │
# └───────────────┴───────┴─────────────────────────────────────────────────┘
#
# Demo Queries Included:
#   1. Which PRs introduced CVE-X? (Log4Shell across 4 repos)
#   2. Transitive dependency vulnerabilities (spring-boot -> log4j chain)
#   3. Common vulnerabilities across repositories
#   4. Vulnerability lineage (introduced -> fixed timeline)
#
# Usage:
#   ./scripts/neo4j-setup.sh           # Start Neo4j and load seed data
#   ./scripts/neo4j-setup.sh --clear   # Clear existing data first
#   ./scripts/neo4j-setup.sh --cypher  # Use Cypher file instead of Python
#   ./scripts/neo4j-setup.sh --stop    # Stop Neo4j
#   ./scripts/neo4j-setup.sh --demo    # Run demo queries
#   ./scripts/neo4j-setup.sh --stats   # Show database statistics
#
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Neo4j configuration
NEO4J_CONTAINER="neo4j"
NEO4J_USER="neo4j"
NEO4J_PASSWORD="password123"
NEO4J_HTTP_PORT="7474"
NEO4J_BOLT_PORT="7687"

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Neo4j container is running
is_neo4j_running() {
    docker ps --format '{{.Names}}' | grep -q "^${NEO4J_CONTAINER}$"
}

# Wait for Neo4j to be ready
wait_for_neo4j() {
    print_status "Waiting for Neo4j to be ready..."
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -s "http://localhost:${NEO4J_HTTP_PORT}" > /dev/null 2>&1; then
            print_status "Neo4j is ready!"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done

    print_error "Neo4j failed to start within timeout"
    return 1
}

# Start Neo4j
start_neo4j() {
    print_status "Starting Neo4j..."

    if is_neo4j_running; then
        print_warning "Neo4j is already running"
    else
        cd "$PROJECT_DIR"
        docker compose up -d neo4j
        wait_for_neo4j
    fi

    print_status "Neo4j Browser: http://localhost:${NEO4J_HTTP_PORT}"
    print_status "Bolt URL: bolt://localhost:${NEO4J_BOLT_PORT}"
}

# Stop Neo4j
stop_neo4j() {
    print_status "Stopping Neo4j..."
    cd "$PROJECT_DIR"
    docker compose stop neo4j
    print_status "Neo4j stopped"
}

# Load seed data using Cypher file
load_cypher_seed() {
    print_status "Loading seed data from Cypher file..."

    local cypher_file="$SCRIPT_DIR/neo4j-seed-data.cypher"

    if [ ! -f "$cypher_file" ]; then
        print_error "Cypher file not found: $cypher_file"
        exit 1
    fi

    # Clear if requested
    if [ "$CLEAR_DATA" = true ]; then
        print_status "Clearing existing data..."
        docker exec -i "$NEO4J_CONTAINER" cypher-shell \
            -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
            "MATCH (n) DETACH DELETE n;"
    fi

    # Load seed data
    cat "$cypher_file" | docker exec -i "$NEO4J_CONTAINER" cypher-shell \
        -u "$NEO4J_USER" -p "$NEO4J_PASSWORD"

    print_status "Seed data loaded successfully!"
}

# Load seed data using Python script
load_python_seed() {
    print_status "Loading seed data using Python script..."

    local python_script="$SCRIPT_DIR/neo4j-seed.py"

    if [ ! -f "$python_script" ]; then
        print_error "Python script not found: $python_script"
        exit 1
    fi

    # Check if neo4j package is installed
    if ! python3 -c "import neo4j" 2>/dev/null; then
        print_warning "neo4j package not installed. Installing..."
        pip install neo4j
    fi

    # Build arguments
    local args="--uri bolt://localhost:${NEO4J_BOLT_PORT}"
    args="$args --user $NEO4J_USER"
    args="$args --password $NEO4J_PASSWORD"

    if [ "$CLEAR_DATA" = true ]; then
        args="$args --clear"
    fi

    python3 "$python_script" $args

    print_status "Seed data loaded successfully!"
}

# Show statistics
show_stats() {
    print_status "Database statistics:"

    docker exec -i "$NEO4J_CONTAINER" cypher-shell \
        -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
        "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count ORDER BY count DESC;"

    echo ""

    docker exec -i "$NEO4J_CONTAINER" cypher-shell \
        -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
        "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count ORDER BY count DESC;"
}

# Run demo queries
run_demo_queries() {
    print_status "Running demo queries..."

    echo ""
    echo "=== Query 1: Which PRs introduced Log4Shell? ==="
    docker exec -i "$NEO4J_CONTAINER" cypher-shell \
        -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
        "MATCH (r:Repository)-[:HAS_PR]->(pr:PullRequest)
               -[:CONTAINS_COMMIT]->(c:Commit)
               -[:SCANNED_BY]->(s:Scan)
               -[:DETECTED]->(v:Vulnerability)
               -[:MAPS_TO]->(cve:CVE {cve_id: 'CVE-2021-44228'})
         RETURN r.name AS repo, pr.number AS pr, substring(pr.title, 0, 50) AS title
         ORDER BY pr.created_at;"

    echo ""
    echo "=== Query 2: Common vulnerabilities across repos ==="
    docker exec -i "$NEO4J_CONTAINER" cypher-shell \
        -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
        "MATCH (r:Repository)-[:HAS_PR]->(:PullRequest)
               -[:CONTAINS_COMMIT]->(:Commit)
               -[:SCANNED_BY]->(:Scan)
               -[:DETECTED]->(v:Vulnerability)
               -[:MAPS_TO]->(cve:CVE)
         WITH cve, collect(DISTINCT r.name) AS repos, count(DISTINCT r) AS cnt
         WHERE cnt > 1
         RETURN cve.cve_id, cnt AS repo_count, repos
         ORDER BY cnt DESC;"
}

# Load noise data
load_noise_data() {
    print_status "Loading noise data (~300 additional records)..."

    local python_script="$SCRIPT_DIR/neo4j-noise.py"

    if [ ! -f "$python_script" ]; then
        print_error "Noise script not found: $python_script"
        exit 1
    fi

    # Check if neo4j package is installed
    if ! python3 -c "import neo4j" 2>/dev/null; then
        print_warning "neo4j package not installed. Installing..."
        pip install neo4j
    fi

    local args="--uri bolt://localhost:${NEO4J_BOLT_PORT}"
    args="$args --user $NEO4J_USER"
    args="$args --password $NEO4J_PASSWORD"
    args="$args --count ${NOISE_COUNT:-40}"

    if [ -n "$RANDOM_SEED" ]; then
        args="$args --seed $RANDOM_SEED"
    fi

    python3 "$python_script" $args

    print_status "Noise data loaded successfully!"
}

# Print usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --clear        Clear existing data before loading seed data"
    echo "  --cypher       Use Cypher file instead of Python script"
    echo "  --python       Use Python script (default)"
    echo "  --noise        Add ~300 random noise records after seed data"
    echo "  --noise-only   Only add noise data (assumes seed exists)"
    echo "  --noise-count  Number of PRs for noise generation (default: 40)"
    echo "  --seed N       Random seed for reproducible noise data"
    echo "  --stop         Stop Neo4j container"
    echo "  --stats        Show database statistics"
    echo "  --demo         Run demo queries"
    echo "  --help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                       # Start Neo4j and load seed data"
    echo "  $0 --clear               # Clear data and reload"
    echo "  $0 --noise               # Load seed + noise data (~500 records)"
    echo "  $0 --clear --noise       # Fresh start with all data (~500 records)"
    echo "  $0 --noise-only          # Add noise to existing data"
    echo "  $0 --noise-count 100     # Generate more noise (~750 records)"
    echo "  $0 --demo                # Run demo queries"
    echo "  $0 --stop                # Stop Neo4j"
}

# Parse arguments
CLEAR_DATA=false
USE_CYPHER=false
STOP_ONLY=false
STATS_ONLY=false
DEMO_ONLY=false
ADD_NOISE=false
NOISE_ONLY=false
NOISE_COUNT=40
RANDOM_SEED=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --clear)
            CLEAR_DATA=true
            shift
            ;;
        --cypher)
            USE_CYPHER=true
            shift
            ;;
        --python)
            USE_CYPHER=false
            shift
            ;;
        --noise)
            ADD_NOISE=true
            shift
            ;;
        --noise-only)
            NOISE_ONLY=true
            shift
            ;;
        --noise-count)
            NOISE_COUNT="$2"
            shift 2
            ;;
        --seed)
            RANDOM_SEED="$2"
            shift 2
            ;;
        --stop)
            STOP_ONLY=true
            shift
            ;;
        --stats)
            STATS_ONLY=true
            shift
            ;;
        --demo)
            DEMO_ONLY=true
            shift
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    if [ "$STOP_ONLY" = true ]; then
        stop_neo4j
        exit 0
    fi

    if [ "$STATS_ONLY" = true ]; then
        if ! is_neo4j_running; then
            print_error "Neo4j is not running"
            exit 1
        fi
        show_stats
        exit 0
    fi

    if [ "$DEMO_ONLY" = true ]; then
        if ! is_neo4j_running; then
            print_error "Neo4j is not running"
            exit 1
        fi
        run_demo_queries
        exit 0
    fi

    if [ "$NOISE_ONLY" = true ]; then
        if ! is_neo4j_running; then
            print_error "Neo4j is not running. Start with: $0"
            exit 1
        fi
        load_noise_data
        show_stats
        exit 0
    fi

    # Default: start Neo4j and load seed data
    start_neo4j

    if [ "$USE_CYPHER" = true ]; then
        load_cypher_seed
    else
        load_python_seed
    fi

    # Add noise data if requested
    if [ "$ADD_NOISE" = true ]; then
        echo ""
        load_noise_data
    fi

    echo ""
    print_status "Setup complete!"
    echo ""
    echo "┌─────────────────────────────────────────────────────────────────┐"
    echo "│                        NEXT STEPS                               │"
    echo "├─────────────────────────────────────────────────────────────────┤"
    echo "│  1. Open Neo4j Browser: http://localhost:${NEO4J_HTTP_PORT}                   │"
    echo "│  2. Login with: ${NEO4J_USER} / ${NEO4J_PASSWORD}                             │"
    echo "│  3. Run demo queries: $0 --demo                     │"
    echo "│  4. View statistics:  $0 --stats                    │"
    if [ "$ADD_NOISE" = false ]; then
    echo "│  5. Add noise data:   $0 --noise-only               │"
    fi
    echo "└─────────────────────────────────────────────────────────────────┘"
}

main
