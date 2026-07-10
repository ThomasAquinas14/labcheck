from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any


SEVERITY_ORDER = ("high", "medium", "low")
SCORE_FIELDS = (
    ("Environment Rebuildability", "environment_rebuildability"),
    ("Notebook Determinism", "notebook_determinism"),
    ("Artifact Availability", "artifact_availability"),
    ("Portability", "portability"),
    ("Onboarding Readiness", "onboarding_readiness"),
)


def load_report_json(path: str | Path) -> dict[str, Any]:
    """Load and validate the subset of labcheck JSON needed for comparison."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("labcheck report JSON must be an object")
    if not isinstance(payload.get("summary"), dict):
        raise ValueError("labcheck report JSON is missing summary")
    if not isinstance(payload.get("scores"), dict):
        raise ValueError("labcheck report JSON is missing scores")
    if not isinstance(payload.get("findings"), list):
        raise ValueError("labcheck report JSON is missing findings")
    return payload


def build_comparison(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic before/after comparison from two labcheck JSON reports."""
    before_findings = [_finding_summary(finding) for finding in before.get("findings", []) if isinstance(finding, dict)]
    after_findings = [_finding_summary(finding) for finding in after.get("findings", []) if isinstance(finding, dict)]
    before_by_key = {_finding_key(finding): finding for finding in before_findings}
    after_by_key = {_finding_key(finding): finding for finding in after_findings}
    resolved_keys = sorted(set(before_by_key) - set(after_by_key), key=lambda key: _finding_sort_key(before_by_key[key]))
    new_keys = sorted(set(after_by_key) - set(before_by_key), key=lambda key: _finding_sort_key(after_by_key[key]))

    before_summary = _report_summary(before)
    after_summary = _report_summary(after)
    return {
        "before": before_summary,
        "after": after_summary,
        "delta": {
            "overall_score": after_summary["overall_score"] - before_summary["overall_score"],
            "findings_count": after_summary["findings_count"] - before_summary["findings_count"],
            "severity_counts": {
                severity: after_summary["severity_counts"][severity] - before_summary["severity_counts"][severity]
                for severity in SEVERITY_ORDER
            },
        },
        "category_scores": [
            {
                "category": label,
                "before": _int_score(before.get("scores", {}), field_name),
                "after": _int_score(after.get("scores", {}), field_name),
                "delta": _int_score(after.get("scores", {}), field_name)
                - _int_score(before.get("scores", {}), field_name),
            }
            for label, field_name in SCORE_FIELDS
        ],
        "resolved_findings": [deepcopy(before_by_key[key]) for key in resolved_keys],
        "new_findings": [deepcopy(after_by_key[key]) for key in new_keys],
        "unchanged_findings_count": len(set(before_by_key) & set(after_by_key)),
    }


def render_comparison_markdown(comparison: dict[str, Any], max_findings: int = 10) -> str:
    """Render a shareable before/after improvement note."""
    before = comparison["before"]
    after = comparison["after"]
    delta = comparison["delta"]
    lines = [
        "# labcheck Before/After Compare",
        "",
        f"- Before target: `{before['target']}`",
        f"- After target: `{after['target']}`",
        f"- Score change: **{_signed(delta['overall_score'])}** points ({before['overall_score']} -> {after['overall_score']})",
        f"- Findings change: **{_signed(delta['findings_count'])}** ({before['findings_count']} -> {after['findings_count']})",
        f"- Resolved findings: **{len(comparison['resolved_findings'])}**",
        f"- New findings: **{len(comparison['new_findings'])}**",
        "",
        "## Severity Delta",
        "",
        "| Severity | Before | After | Delta |",
        "|---|---:|---:|---:|",
    ]
    for severity in SEVERITY_ORDER:
        before_count = before["severity_counts"][severity]
        after_count = after["severity_counts"][severity]
        lines.append(f"| {severity.title()} | {before_count} | {after_count} | {_signed(after_count - before_count)} |")

    lines.extend(
        [
            "",
            "## Category Scores",
            "",
            "| Category | Before | After | Delta |",
            "|---|---:|---:|---:|",
        ]
    )
    for entry in comparison["category_scores"]:
        lines.append(f"| {entry['category']} | {entry['before']} | {entry['after']} | {_signed(entry['delta'])} |")

    _append_finding_section(lines, "Resolved Findings", comparison["resolved_findings"], max_findings)
    _append_finding_section(lines, "New Findings", comparison["new_findings"], max_findings)
    lines.extend(
        [
            "",
            "## Next Step",
            "",
            "- If this improvement is intentional, regenerate or shrink the baseline so the repo ratchets cleaner over time.",
            "- If new findings appeared, inspect them before sharing the updated scorecard.",
            "",
            "Generated locally by `labcheck compare`. No API key or hosted backend was used.",
        ]
    )
    return "\n".join(lines)


def render_comparison_json(comparison: dict[str, Any]) -> str:
    """Render machine-readable comparison JSON."""
    return json.dumps(comparison, indent=2)


def _report_summary(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary", {})
    scores = report.get("scores", {})
    findings = [finding for finding in report.get("findings", []) if isinstance(finding, dict)]
    return {
        "target": str(summary.get("target", "")),
        "overall_score": _int_score(scores, "overall_score"),
        "findings_count": len(findings),
        "severity_counts": _severity_counts(findings),
    }


def _finding_summary(finding: dict[str, Any]) -> dict[str, str]:
    return {
        "check_id": str(finding.get("check_id", "")),
        "title": str(finding.get("title", "")),
        "severity": str(finding.get("severity", "")),
        "category": str(finding.get("category", "")),
        "file_path": str(finding.get("file_path", "")).replace("\\", "/"),
        "evidence": str(finding.get("evidence", "")),
    }


def _finding_key(finding: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        finding["check_id"],
        finding["severity"],
        finding["file_path"].replace("\\", "/"),
        finding["evidence"],
    )


def _finding_sort_key(finding: dict[str, str]) -> tuple[int, str, str, str]:
    severity_rank = {"high": 0, "medium": 1, "low": 2}
    return (
        severity_rank.get(finding["severity"], 99),
        finding["check_id"],
        finding["file_path"],
        finding["evidence"],
    )


def _severity_counts(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts = {severity: 0 for severity in SEVERITY_ORDER}
    for finding in findings:
        severity = str(finding.get("severity", ""))
        if severity in counts:
            counts[severity] += 1
    return counts


def _int_score(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key, 0)
    return value if isinstance(value, int) else 0


def _signed(value: int) -> str:
    return f"+{value}" if value > 0 else str(value)


def _append_finding_section(
    lines: list[str],
    heading: str,
    findings: list[dict[str, str]],
    max_findings: int,
) -> None:
    lines.extend(["", f"## {heading}", ""])
    if not findings:
        lines.append("None.")
        return
    visible = findings[:max_findings]
    for finding in visible:
        lines.append(
            f"- `{finding['check_id']}` {finding['title']} "
            f"({finding['severity']}) in `{finding['file_path']}`: {finding['evidence']}"
        )
    omitted = len(findings) - len(visible)
    if omitted:
        lines.append(f"- ... {omitted} more not shown")
