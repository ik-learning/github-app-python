import os
import json
import logging
import subprocess
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """KICS scan result."""
    success: bool
    total_issues: int
    severity_counters: dict
    files_scanned: int
    files_parsed: int
    queries_total: int
    execution_time_seconds: float
    queries: list
    error_message: Optional[str] = None


class KicsNotFoundError(Exception):
    """Raised when KICS binary is not found."""
    pass


def check_kics_installed() -> str:
    """
    Check if KICS is installed and return version.
    Raises KicsNotFoundError if not found.
    """
    kics_binary = os.getenv("KICS_BINARY", "kics")

    try:
        result = subprocess.run(
            [kics_binary, "version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            logger.info(f"KICS found: {version}")
            return version
        else:
            raise KicsNotFoundError(f"KICS returned error: {result.stderr}")
    except FileNotFoundError:
        raise KicsNotFoundError(f"KICS binary not found at: {kics_binary}")
    except subprocess.TimeoutExpired:
        raise KicsNotFoundError("KICS version check timed out")


class Scan:
    """KICS security scanner. Only handles scanning, no Git/GitHub operations."""

    def __init__(self, app_name: str = "kics-worker"):
        self.app_name = app_name
        self.kics_binary = os.getenv("KICS_BINARY", "kics")

    def run(self, repo_path: str) -> ScanResult:
        """
        Run KICS scan on a directory.

        Args:
            repo_path: Path to the repository/directory to scan

        Returns:
            ScanResult with findings
        """
        try:
            output_path = os.path.join(repo_path, "kics-results")
            exit_code = self._execute_kics(repo_path, output_path)

            results_file = os.path.join(output_path, "results.json")
            return self._parse_results(results_file, exit_code)

        except Exception as e:
            logger.error(f"[{self.app_name}] Scan failed: {e}")
            return ScanResult(
                success=False,
                total_issues=0,
                severity_counters={},
                files_scanned=0,
                files_parsed=0,
                queries_total=0,
                execution_time_seconds=0,
                queries=[],
                error_message=str(e)
            )

    def _execute_kics(self, repo_path: str, output_path: str) -> int:
        """Execute KICS binary and return exit code."""
        os.makedirs(output_path, exist_ok=True)

        logger.info(f"[{self.app_name}] Running KICS scan on {repo_path}")

        cmd = [
            self.kics_binary, "scan",
            "--no-progress",
            "-p", repo_path,
            "-o", output_path,
            "--output-name", "results",
            "--report-formats", "json"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        logger.info(f"[{self.app_name}] KICS completed with exit code {result.returncode}")

        if result.stderr:
            logger.debug(f"[{self.app_name}] KICS stderr: {result.stderr}")

        return result.returncode

    def _parse_results(self, results_file: str, exit_code: int) -> ScanResult:
        """Parse KICS JSON results file."""
        if not os.path.exists(results_file):
            return ScanResult(
                success=exit_code == 0,
                total_issues=0,
                severity_counters={},
                files_scanned=0,
                files_parsed=0,
                queries_total=0,
                execution_time_seconds=0,
                queries=[],
                error_message="No results file generated"
            )

        with open(results_file) as f:
            data = json.load(f)

        return ScanResult(
            success=True,
            total_issues=data.get("total_counter", 0),
            severity_counters=data.get("severity_counters", {}),
            files_scanned=data.get("files_scanned", 0),
            files_parsed=data.get("files_parsed", 0),
            queries_total=data.get("queries_total", 0),
            execution_time_seconds=self._calculate_duration(data),
            queries=data.get("queries", [])
        )

    def _calculate_duration(self, data: dict) -> float:
        """Calculate scan duration from timestamps."""
        try:
            from datetime import datetime
            start = datetime.fromisoformat(data.get("start", "").replace("Z", "+00:00"))
            end = datetime.fromisoformat(data.get("end", "").replace("Z", "+00:00"))
            return (end - start).total_seconds()
        except Exception:
            return 0.0
