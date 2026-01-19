#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
URL="${1:-http://localhost:8080/webhooks/github}"

curl -X POST "$URL" \
	-H "Content-Type: application/json" \
	-H "X-GitHub-Event: pull_request" \
	-d @"${SCRIPT_DIR}/fixtures/test.json"
