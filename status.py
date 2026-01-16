from dataclasses import dataclass, field
from typing import Any


@dataclass
class Status:
    issues: list[dict[str, Any]]
    overall_status: list[dict[str, Any]]
    results: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "Status":
        return cls(
            issues=data.get("issues", []),
            overall_status=data.get("overallStatus", []),
            results=data.get("results", []),
        )

    def to_dict(self) -> dict:
        return {
            "issues": self.issues,
            "overallStatus": self.overall_status,
            "results": self.results,
        }

    def has_policy_violations(self) -> bool:
        return any(
            s.get("key") == "FAILURE_POLICY_VIOLATION"
            for s in self.overall_status
        )

    def get_policy_violations_summary(self) -> dict[str, Any] | None:
        if not self.has_policy_violations():
            return None

        summary = {
            "policies_violated": [],
            "components_with_violations": [],
            "critical_blocking": {},
            "other_violations": {},
        }

        for result in self.results:
            sub_messages = result.get("sub_messages", [])
            section = None

            for msg in sub_messages:
                msg = msg.strip()

                if msg.startswith("Critical and blocking"):
                    section = "critical_blocking"
                elif msg.startswith("Other policy violations"):
                    section = "other_violations"
                elif msg.startswith("Policies Violated:"):
                    section = "policies"
                elif msg.startswith("Components with Policy Violations:"):
                    section = "components"
                elif msg.startswith("Components with Policy Violation Warnings:"):
                    section = "warnings"
                elif msg.startswith("* ") and section in ("critical_blocking", "other_violations"):
                    parts = msg[2:].split(": ")
                    if len(parts) == 2:
                        summary[section][parts[0].strip()] = int(parts[1])
                elif section == "policies" and msg and not msg.startswith("*"):
                    summary["policies_violated"].append(msg)
                elif section == "components" and msg and not msg.startswith("*"):
                    summary["components_with_violations"].append(msg)

        return summary
