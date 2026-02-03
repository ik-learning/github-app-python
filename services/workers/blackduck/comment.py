from scan import ScanResult


class Comment:
    """Builds markdown comments and summaries for GitHub."""

    def __init__(self, app_name: str = "blackduck-worker"):
        self.app_name = app_name

    def pr_comment(self, result: ScanResult) -> str:
        """Build full PR comment with scan results."""
        status_icon = "✅" if result.total_issues == 0 else "⚠️"
        counters = result.severity_counters

        return f"""## {status_icon} Blackduck Security Scan Results

{self._severity_table(counters)}

{self._metrics_table(result)}

{self._top_vulnerabilities(result.vulnerabilities)}

---
🤖 *Scanned by {self.app_name}*
"""

    def check_run_summary(self, result: ScanResult) -> str:
        """Build summary for check run output."""
        return f"Found {result.total_issues} vulnerabilities ({result.components_scanned} components scanned)"

    def callback_message(self, result: ScanResult) -> str:
        """Build callback message for coordinator."""
        if not result.success:
            return f"Scan failed: {result.error_message}"

        return (
            f"Blackduck scan completed: {result.total_issues} vulnerabilities found "
            f"(CRITICAL={result.severity_counters.get('CRITICAL', 0)}, "
            f"HIGH={result.severity_counters.get('HIGH', 0)}, "
            f"MEDIUM={result.severity_counters.get('MEDIUM', 0)})"
        )

    def _severity_table(self, counters: dict) -> str:
        """Build severity counts table."""
        return f"""| Severity | Count |
|----------|-------|
| 🔴 CRITICAL | {counters.get('CRITICAL', 0)} |
| 🟠 HIGH | {counters.get('HIGH', 0)} |
| 🟡 MEDIUM | {counters.get('MEDIUM', 0)} |
| 🔵 LOW | {counters.get('LOW', 0)} |"""

    def _metrics_table(self, result: ScanResult) -> str:
        """Build scan metrics table."""
        return f"""| Metric | Value |
|--------|-------|
| Components Scanned | {result.components_scanned} |
| Total Vulnerabilities | {result.total_issues} |
| Policy Violations | {result.policy_violations} |
| Scan Duration | {result.execution_time_seconds:.1f}s |"""

    def _top_vulnerabilities(self, vulnerabilities: list, max_items: int = 10) -> str:
        """Build top vulnerabilities list."""
        if not vulnerabilities:
            return "✅ **No vulnerabilities found!**"

        # Sort by severity
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        sorted_vulns = sorted(
            vulnerabilities,
            key=lambda v: severity_order.get(
                v.get("severity", v.get("vulnerabilitySeverity", "LOW")).upper(), 4
            )
        )

        lines = ["### Top Vulnerabilities", ""]

        for vuln in sorted_vulns[:max_items]:
            severity = vuln.get("severity", vuln.get("vulnerabilitySeverity", "UNKNOWN")).upper()
            name = vuln.get("name", vuln.get("componentName", "Unknown"))
            version = vuln.get("version", vuln.get("componentVersion", ""))
            cve = vuln.get("cve", vuln.get("vulnerabilityId", ""))

            if version:
                name = f"{name}@{version}"

            lines.append(f"- **[{severity}]** {name}")
            if cve:
                lines.append(f"  - CVE: `{cve}`")

        if len(vulnerabilities) > max_items:
            lines.append(f"\n*...and {len(vulnerabilities) - max_items} more vulnerabilities*")

        return "\n".join(lines)
