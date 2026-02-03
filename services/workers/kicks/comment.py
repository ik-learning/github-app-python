from scan import ScanResult


class Comment:
    """Builds markdown comments and summaries for GitHub."""

    def __init__(self, app_name: str = "kics-worker"):
        self.app_name = app_name

    def pr_comment(self, result: ScanResult) -> str:
        """Build full PR comment with scan results."""
        status_icon = "✅" if result.total_issues == 0 else "⚠️"
        counters = result.severity_counters

        return f"""## {status_icon} KICS Security Scan Results

{self._severity_table(counters)}

{self._metrics_table(result)}

{self._top_issues(result.queries)}

---
🤖 *Scanned by {self.app_name}*
"""

    def check_run_summary(self, result: ScanResult) -> str:
        """Build summary for check run output."""
        return f"Found {result.total_issues} issues ({result.files_scanned} files scanned)"

    def callback_message(self, result: ScanResult) -> str:
        """Build callback message for coordinator."""
        if not result.success:
            return f"Scan failed: {result.error_message}"

        return (
            f"KICS scan completed: {result.total_issues} issues found "
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
| 🔵 LOW | {counters.get('LOW', 0)} |
| ⚪ INFO | {counters.get('INFO', 0)} |"""

    def _metrics_table(self, result: ScanResult) -> str:
        """Build scan metrics table."""
        return f"""| Metric | Value |
|--------|-------|
| Files Scanned | {result.files_scanned} |
| Files Parsed | {result.files_parsed} |
| Total Issues | {result.total_issues} |
| Queries Executed | {result.queries_total} |
| Scan Duration | {result.execution_time_seconds:.1f}s |"""

    def _top_issues(self, queries: list, max_issues: int = 10) -> str:
        """Build top issues list."""
        if not queries:
            return "✅ **No issues found!**"

        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
        sorted_queries = sorted(
            queries,
            key=lambda q: severity_order.get(q.get("severity", "INFO"), 5)
        )

        lines = ["### Top Issues", ""]
        count = 0

        for query in sorted_queries:
            if count >= max_issues:
                lines.append(f"\n*...and more issues*")
                break

            severity = query.get("severity", "INFO")
            name = query.get("query_name", "Unknown")

            for file in query.get("files", [])[:3]:
                if count >= max_issues:
                    break
                file_name = file.get("file_name", "unknown")
                line_num = file.get("line", 0)
                lines.append(f"- **[{severity}]** {name}")
                lines.append(f"  - `{file_name}:{line_num}`")
                count += 1

        return "\n".join(lines)
