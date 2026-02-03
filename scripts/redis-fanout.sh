#!/bin/bash
# Post message to Redis streams via API /fanout endpoint
#
# Usage:
#   ./scripts/redis-fanout.sh
#   ./scripts/redis-fanout.sh --with-payload '{"owner":"acme","repo":"app","prId":42}'
#   VERBOSE=true ./scripts/redis-fanout.sh
#   ./scripts/redis-fanout.sh --help

set -e

API_URL="${API_URL:-http://localhost:8080}"
VERBOSE="${VERBOSE:-false}"
PAYLOAD="{}"

while [[ $# -gt 0 ]]; do
    case $1 in
        --with-payload)
            PAYLOAD="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --with-payload JSON  Custom payload (optional)"
            echo "  --help               Show this help"
            echo ""
            echo "Environment variables:"
            echo "  VERBOSE=true         Enable output (default: false)"
            echo "  API_URL=<url>        API URL (default: http://localhost:8080)"
            echo ""
            echo "Examples:"
            echo "  $0"
            echo "  $0 --with-payload '{\"owner\":\"acme\",\"repo\":\"webapp\",\"prId\":123}'"
            echo "  VERBOSE=true $0"
            echo ""
            echo "Payload fields (all optional, defaults used if not provided):"
            echo "  owner           Repository owner (default: test-owner)"
            echo "  repo            Repository name (default: test-repo)"
            echo "  branch          Branch name (default: main)"
            echo "  prId            Pull request number (default: 1)"
            echo "  commit_sha      Commit SHA (default: auto-generated)"
            echo "  installation_id GitHub App installation ID (default: 0)"
            echo "  streams         Comma-separated streams (default: worker-blackduck,worker-kics)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage"
            exit 1
            ;;
    esac
done

if [[ "$VERBOSE" == "true" || "$VERBOSE" == "1" ]]; then
    echo "Posting to ${API_URL}/fanout..."
    curl -s -X POST "${API_URL}/fanout" \
        -H "Content-Type: application/json" \
        -d "${PAYLOAD}" | python3 -m json.tool
    echo ""
    echo "Check worker logs: docker compose logs -f worker-blackduck worker-kics"
else
    curl -s -X POST "${API_URL}/fanout" \
        -H "Content-Type: application/json" \
        -d "${PAYLOAD}" > /dev/null
fi
