#!/usr/bin/env python3
import argparse
import json
import random
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from status import Status

SAMPLE_POLICIES = [
    "Scan_Policy_License_Medium_Sev",
    "Scan_Policy_Security_High_Sev",
    "Scan_Policy_Security_Medium_Sev",
    "Scan_Policy_License_High_Sev",
]

SAMPLE_COMPONENTS = [
    "PyJWT 2.10.1 (pypi:PyJWT/2.10.1)",
    "Starlette 0.45.2 (pypi:starlette/0.45.2)",
    "python-certifi 2025.6.15 (pypi:certifi/2025.6.15)",
    "urllib3 2.5.0 (pypi:urllib3/2.5.0)",
    "requests 2.31.0 (pypi:requests/2.31.0)",
    "cryptography 41.0.0 (pypi:cryptography/41.0.0)",
]


def generate_mock_policy_violation_status():
    policies = random.sample(SAMPLE_POLICIES, random.randint(1, 3))
    components = random.sample(SAMPLE_COMPONENTS, random.randint(2, 4))

    sub_messages = [
        "Critical and blocking policy violations for",
        f"  * Components: {random.randint(0, 2)}",
        f"  * Security: {random.randint(0, 3)}",
        f"  * License: {random.randint(0, 2)}",
        f"  * Other: {random.randint(0, 5)}",
        "Other policy violations",
        "  * Components: 0",
        "  * Security: 0",
        "  * License: 0",
        "  * Other: 0",
        "Policies Violated:",
    ]
    sub_messages.extend([f"  {p}" for p in policies])
    sub_messages.append("Components with Policy Violations:")
    sub_messages.extend([f"  {c}" for c in components])
    sub_messages.append("Components with Policy Violation Warnings:")

    return Status(
        issues=[],
        overall_status=[{
            "key": "FAILURE_POLICY_VIOLATION",
            "status": "Detect found policy violations."
        }],
        results=[{
            "location": "/scan/.bridge/mock/status/status.json",
            "message": "Rapid Scan Result: (for more detail look in the log for Rapid Scan",
            "sub_messages": sub_messages
        }]
    )


def run_scan(thread_id, verbose, tail, delay, simulate_violation=False):
    time.sleep(delay)
    print(f"[Thread {thread_id + 1}] Incoming webhook received. Processing...")
    cmd = [
        "bridge-cli",
        "--stage", "blackducksca",
        "--input", "input/input.json",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    output_lines = []
    if result.stdout:
        output_lines.extend(result.stdout.splitlines())
    if result.stderr:
        output_lines.extend(result.stderr.splitlines())

    # Extract status file path
    status_file = None
    status_content = None
    for line in output_lines:
        match = re.search(r"Creating status file: (.+/status\.json)", line)
        if match:
            status_file = match.group(1)
            break

    if status_file and Path(status_file).exists():
        with open(status_file) as f:
            status_content = Status.from_dict(json.load(f))

    # Simulate policy violation for designated threads
    if simulate_violation:
        status_content = generate_mock_policy_violation_status()
        status_file = "/scan/.bridge/mock/status/status.json"

    if verbose:
        return thread_id, result.returncode, output_lines, status_content, status_file
    else:
        return thread_id, result.returncode, output_lines[-tail:], status_content, status_file


def main():
    parser = argparse.ArgumentParser(description="Run Black Duck scan")
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Output all logs to stdout"
    )
    parser.add_argument(
        "--tail",
        type=int,
        default=3,
        help="Number of lines to show at the end (default: 3)"
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=5,
        help="Number of parallel threads (default: 5)"
    )
    args = parser.parse_args()

    exit_code = 0

    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = {}
        for i in range(args.threads):
            if i == 0:
                delay = random.uniform(10, 15)
            else:
                delay = random.uniform(5, 10) + (i * random.uniform(5, 10))
            simulate_violation = (i + 1) % 2 == 0  # Every 2nd thread (2, 4, ...)
            futures[executor.submit(run_scan, i, args.verbose, args.tail, delay, simulate_violation)] = i

        for future in as_completed(futures):
            thread_id, returncode, lines, status_content, status_file = future.result()
            print(f"\n=== Thread {thread_id + 1} (exit code: {returncode}) ===")
            if status_file:
                print(f"Status file: {status_file}")
            for line in lines:
                print(line)
            if status_content:
                print(f"\n--- Status ---")
                print(json.dumps(status_content.to_dict(), indent=2))
                if status_content.has_policy_violations():
                    print(f"\n--- Policy Violations Detected ---")
                    summary = status_content.get_policy_violations_summary()
                    if summary:
                        print(json.dumps(summary, indent=2))
            if returncode != 0:
                exit_code = returncode

    print("\nWaiting for incoming requests. Terminate with CTRL+C")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
