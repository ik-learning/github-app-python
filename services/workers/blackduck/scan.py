import os
import json
import logging
import subprocess
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Blackduck scan result."""
    success: bool
    total_issues: int
    severity_counters: dict
    components_scanned: int
    policy_violations: int
    execution_time_seconds: float
    vulnerabilities: list
    error_message: Optional[str] = None


class BlackduckNotFoundError(Exception):
    """Raised when Blackduck CLI is not found."""
    pass


def check_blackduck_installed() -> str:
    """
    Check if Blackduck detect/bridge-cli is installed and return version.
    Raises BlackduckNotFoundError if not found.
    """
    bridge_cli = os.getenv("BLACKDUCK_CLI", "bridge-cli")

    try:
        result = subprocess.run(
            [bridge_cli, "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            version = result.stdout.strip() or result.stderr.strip()
            logger.info(f"Blackduck CLI found: {version}")
            return version
        else:
            raise BlackduckNotFoundError(f"Blackduck CLI returned error: {result.stderr}")
    except FileNotFoundError:
        raise BlackduckNotFoundError(f"Blackduck CLI not found at: {bridge_cli}")
    except subprocess.TimeoutExpired:
        raise BlackduckNotFoundError("Blackduck CLI version check timed out")


class Scan:
    """Blackduck security scanner. Only handles scanning, no Git/GitHub operations."""

    def __init__(self, app_name: str = "blackduck-worker"):
        self.app_name = app_name
        self.bridge_cli = os.getenv("BLACKDUCK_CLI", "bridge-cli")
        self.blackduck_url = os.getenv("BLACKDUCK_URL", "")
        self.blackduck_token = os.getenv("BLACKDUCK_API_TOKEN", "")

    def run(self, repo_path: str, project_name: str = "") -> ScanResult:
        """
        Run Blackduck scan on a directory.

        Args:
            repo_path: Path to the repository/directory to scan
            project_name: Name for the Blackduck project

        Returns:
            ScanResult with findings
        """
        try:
            output_path = os.path.join(repo_path, "blackduck-results")
            exit_code = self._execute_blackduck(repo_path, output_path, project_name)

            results_file = os.path.join(output_path, "results.json")
            return self._parse_results(results_file, exit_code)

        except Exception as e:
            logger.error(f"[{self.app_name}] Scan failed: {e}")
            return ScanResult(
                success=False,
                total_issues=0,
                severity_counters={},
                components_scanned=0,
                policy_violations=0,
                execution_time_seconds=0,
                vulnerabilities=[],
                error_message=str(e)
            )

    def _execute_blackduck(self, repo_path: str, output_path: str, project_name: str) -> int:
        """Execute Blackduck scan and return exit code."""
        os.makedirs(output_path, exist_ok=True)

        logger.info(f"[{self.app_name}] Running Blackduck scan on {repo_path}")

        # Build command based on available configuration
        cmd = [self.bridge_cli]

        if self.blackduck_url and self.blackduck_token:
            # Full Blackduck scan with server connection
            cmd.extend([
                "--stage", "blackduck",
                f"--blackduck.url={self.blackduck_url}",
                f"--blackduck.token={self.blackduck_token}",
            ])
            if project_name:
                cmd.append(f"--blackduck.project.name={project_name}")
        else:
            # Offline/local scan mode
            logger.warning(f"[{self.app_name}] No Blackduck server configured, running in offline mode")
            cmd.extend([
                "--stage", "blackduck",
                "--blackduck.offline.mode=true",
            ])

        cmd.extend([
            f"--blackduck.source.path={repo_path}",
            f"--blackduck.output.path={output_path}",
        ])

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=repo_path)

        logger.info(f"[{self.app_name}] Blackduck completed with exit code {result.returncode}")

        if result.stderr:
            logger.debug(f"[{self.app_name}] Blackduck stderr: {result.stderr}")

        return result.returncode

    def _parse_results(self, results_file: str, exit_code: int) -> ScanResult:
        """Parse Blackduck results file."""
        # Blackduck outputs vary by mode, handle missing file gracefully
        if not os.path.exists(results_file):
            # Try to find any JSON output
            results_dir = os.path.dirname(results_file)
            json_files = [f for f in os.listdir(results_dir) if f.endswith('.json')] if os.path.exists(results_dir) else []

            if json_files:
                results_file = os.path.join(results_dir, json_files[0])
            else:
                return ScanResult(
                    success=exit_code == 0,
                    total_issues=0,
                    severity_counters={},
                    components_scanned=0,
                    policy_violations=0,
                    execution_time_seconds=0,
                    vulnerabilities=[],
                    error_message="No results file generated" if exit_code != 0 else None
                )

        try:
            with open(results_file) as f:
                data = json.load(f)

            vulnerabilities = data.get("vulnerabilities", data.get("components", []))
            severity_counters = self._count_severities(vulnerabilities)

            return ScanResult(
                success=True,
                total_issues=len(vulnerabilities),
                severity_counters=severity_counters,
                components_scanned=data.get("componentsScanned", data.get("totalComponents", 0)),
                policy_violations=data.get("policyViolations", 0),
                execution_time_seconds=data.get("scanDuration", 0),
                vulnerabilities=vulnerabilities
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"[{self.app_name}] Failed to parse results: {e}")
            return ScanResult(
                success=exit_code == 0,
                total_issues=0,
                severity_counters={},
                components_scanned=0,
                policy_violations=0,
                execution_time_seconds=0,
                vulnerabilities=[],
                error_message=f"Failed to parse results: {e}"
            )

    def _count_severities(self, vulnerabilities: list) -> dict:
        """Count vulnerabilities by severity."""
        counters = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for vuln in vulnerabilities:
            severity = vuln.get("severity", vuln.get("vulnerabilitySeverity", "UNKNOWN")).upper()
            if severity in counters:
                counters[severity] += 1
        return counters
