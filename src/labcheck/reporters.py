from __future__ import annotations

import csv
from dataclasses import dataclass
from html import escape
import io
import json

from .demo_links import build_demo_link, github_repo_slug, render_demo_link
from .loaders import is_github_repo_url
from .models import Finding, Report


CATEGORY_HELP = {
    "environment_rebuildability": "Can a new person recreate the environment without guesswork?",
    "notebook_determinism": "Will notebooks run cleanly from top to bottom without invisible state?",
    "artifact_availability": "Are referenced inputs and generated artifacts present or clearly accounted for?",
    "portability": "Does the repo avoid machine-specific assumptions and brittle paths?",
    "onboarding_readiness": "How likely is a new contributor to succeed from the docs and structure alone?",
}

CATEGORY_SCORE_FIELDS = (
    ("Environment Rebuildability", "environment_rebuildability"),
    ("Notebook Determinism", "notebook_determinism"),
    ("Artifact Availability", "artifact_availability"),
    ("Portability", "portability"),
    ("Onboarding Readiness", "onboarding_readiness"),
)

KIND_COLUMNS = {
    "input": 0,
    "notebook": 1,
    "python": 1,
    "artifact": 2,
}

SEVERITY_RANK = {
    "high": 0,
    "medium": 1,
    "low": 2,
}

SARIF_LEVELS = {
    "high": "error",
    "medium": "warning",
    "low": "note",
}

TRIAGE_OWNER_BY_CATEGORY = {
    "environment": "environment/runtime owner",
    "environment_rebuildability": "environment/runtime owner",
    "determinism": "notebook/workflow owner",
    "notebook_determinism": "notebook/workflow owner",
    "artifacts": "data/artifact owner",
    "artifact_availability": "data/artifact owner",
    "portability": "repo portability owner",
    "onboarding": "docs/CI owner",
    "onboarding_readiness": "docs/CI owner",
}

DEFAULT_HUMAN_FINDING_LIMIT = 100

REVIEW_BOUNDARY_TEXT = (
    "This is a static, no-key first-pass audit. It does not execute the project code by default, "
    "does not upload source files to a hosted backend, and does not prove scientific validity; "
    "use it to prioritize rerun and handoff risks before deeper verification."
)

COMPLETE_OUTPUTS_NOTE = "JSON, CSV, and SARIF outputs remain complete."

OUTREACH_AUDIENCES = {
    "general": {
        "subject": "Quick reproducibility scorecard",
        "intro": (
            "to see how easily a new student, reviewer, maintainer, "
            "or engineer could rerun it from a fresh clone."
        ),
        "offer": (
            "If useful, I can send the full scorecard/audit bundle, open a small issue, "
            "or help turn the top finding into a concrete fix."
        ),
    },
    "professor": {
        "subject": "Quick lab reproducibility handoff check",
        "intro": (
            "to see how easily a new student, collaborator, or reviewer could rerun it "
            "from a fresh clone without hidden local state."
        ),
        "offer": (
            "If useful, I can send the full scorecard/audit bundle or turn the top finding "
            "into a small lab handoff checklist."
        ),
    },
    "founder": {
        "subject": "Quick ML repo onboarding and diligence check",
        "intro": (
            "to see how easily a new engineer, technical lead, or diligence reviewer could "
            "rebuild the workflow from a fresh clone."
        ),
        "offer": (
            "If useful, I can send the full scorecard/audit bundle or help convert the top "
            "finding into an onboarding-ready fix."
        ),
    },
    "maintainer": {
        "subject": "Quick contributor reproducibility check",
        "intro": (
            "to see how easily a new contributor or issue reporter could reproduce the "
            "workflow from a fresh clone."
        ),
        "offer": (
            "If useful, I can open a scoped issue or PR that addresses the top finding first."
        ),
    },
}

TARGET_FIT_AUDIENCE_ASKS = {
    "general": "If useful, I can send the scorecard or a zipped audit bundle for review.",
    "professor": "If useful, I can run this as a pre-handoff scorecard for one public lab repo.",
    "founder": "If useful, I can turn the top finding into an onboarding-ready fix.",
    "maintainer": "If useful, I can open a scoped issue for the first top risk.",
}


@dataclass(slots=True)
class RiskSummary:
    check_id: str
    title: str
    severity: str
    category: str
    count: int
    affected_files: list[str]
    first_finding: Finding


@dataclass(slots=True)
class ComposeReferenceSummary:
    compose_file: str
    check_id: str
    title: str
    severity: str
    missing_references: list[str]


COMPOSE_REFERENCE_CHECK_IDS = frozenset(
    {
        "LC005",
        "LC065",
        "LC066",
        "LC067",
        "LC068",
        "LC069",
        "LC070",
        "LC071",
        "LC072",
        "LC073",
    }
)

COMPOSE_REFERENCE_PREFIXES = (
    "Docker Compose bind source(s) ",
    "Docker Compose build context(s) ",
    "Docker Compose Dockerfile(s) ",
    "Docker Compose depends_on service(s) ",
    "Docker Compose network(s) ",
    "Docker Compose healthcheck script(s) ",
    "Docker Compose secret/config file(s) ",
    "Docker Compose service env_file(s) ",
    "Docker Compose extends file(s) ",
    "Docker Compose extends service target(s) ",
    "Docker Compose include file(s) ",
    "Docker Compose service label_file(s) ",
    "Docker Compose develop watch path(s) ",
)


def _severity_counts(report: Report) -> dict[str, int]:
    counts = {"high": 0, "medium": 0, "low": 0}
    for finding in report.findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
    return counts


def _capped_findings_note(report: Report) -> str:
    capped_count = report.summary.capped_findings_count
    if capped_count <= 0:
        return ""
    capped_checks = ", ".join(
        f"{check_id}: {count}"
        for check_id, count in sorted(report.summary.capped_checks.items())
    )
    detail = f" ({capped_checks})" if capped_checks else ""
    return (
        f"Configured finding limits omitted {_pluralize(capped_count, 'finding')}{detail}. "
        "Counts and scores are based on retained findings after caps."
    )


def _top_risks(report: Report, limit: int = 5) -> list[RiskSummary]:
    grouped: dict[tuple[str, str, str, str], dict[str, object]] = {}
    for finding in report.findings:
        key = (finding.check_id, finding.title, finding.severity, finding.category)
        if key not in grouped:
            grouped[key] = {
                "count": 0,
                "files": [],
                "seen_files": set(),
                "first_finding": finding,
            }
        group = grouped[key]
        group["count"] = int(group["count"]) + 1
        seen_files = group["seen_files"]
        if isinstance(seen_files, set) and finding.file_path not in seen_files:
            seen_files.add(finding.file_path)
            files = group["files"]
            if isinstance(files, list):
                files.append(finding.file_path)

    risks: list[RiskSummary] = []
    for (check_id, title, severity, category), group in grouped.items():
        first_finding = group["first_finding"]
        files = group["files"]
        if not isinstance(first_finding, Finding) or not isinstance(files, list):
            continue
        risks.append(
            RiskSummary(
                check_id=check_id,
                title=title,
                severity=severity,
                category=category,
                count=int(group["count"]),
                affected_files=list(files),
                first_finding=first_finding,
            )
        )

    return sorted(
        risks,
        key=lambda risk: (
            SEVERITY_RANK.get(risk.severity, 99),
            -risk.count,
            risk.check_id,
        ),
    )[:limit]


def _split_compose_references(raw_references: str) -> list[str]:
    return [reference.strip() for reference in raw_references.split(",") if reference.strip()]


def _compose_missing_references(evidence: str) -> list[str]:
    references: list[str] = []
    for prefix in COMPOSE_REFERENCE_PREFIXES:
        search_start = 0
        while True:
            prefix_start = evidence.find(prefix, search_start)
            if prefix_start < 0:
                break
            value_start = prefix_start + len(prefix)
            tail = evidence[value_start:]
            value_end = tail.find(" are ")
            if value_end < 0:
                search_start = value_start
                continue
            references.extend(_split_compose_references(tail[:value_end]))
            search_start = value_start + value_end
    return list(dict.fromkeys(references))


def _compose_reference_summaries(report: Report) -> list[ComposeReferenceSummary]:
    grouped: dict[tuple[str, str, str, str], list[str]] = {}
    for finding in report.findings:
        if finding.check_id not in COMPOSE_REFERENCE_CHECK_IDS:
            continue
        references = _compose_missing_references(finding.evidence)
        if not references:
            continue
        key = (finding.file_path, finding.check_id, finding.title, finding.severity)
        grouped.setdefault(key, [])
        for reference in references:
            if reference not in grouped[key]:
                grouped[key].append(reference)

    summaries = [
        ComposeReferenceSummary(
            compose_file=compose_file,
            check_id=check_id,
            title=title,
            severity=severity,
            missing_references=references,
        )
        for (compose_file, check_id, title, severity), references in grouped.items()
    ]
    return sorted(
        summaries,
        key=lambda summary: (
            summary.compose_file,
            SEVERITY_RANK.get(summary.severity, 99),
            summary.check_id,
        ),
    )


def _category_score_entries(report: Report) -> list[tuple[str, int, str]]:
    return [
        (label, int(getattr(report.scores, field_name)), CATEGORY_HELP[field_name])
        for label, field_name in CATEGORY_SCORE_FIELDS
    ]


def _scorecard_signal(report: Report, severities: dict[str, int]) -> str:
    if report.scores.overall_score >= 90 and severities["high"] == 0:
        return "Strong handoff candidate: no high-severity findings and the score is near release-ready."
    if severities["high"]:
        return (
            f"Not handoff-ready yet: fix {_pluralize(severities['high'], 'high-severity finding')} "
            "before sending this repo to a reviewer, student, or new engineer."
        )
    if report.scores.overall_score >= 75:
        return "Mostly usable, but the medium/low findings are still worth cleaning before a formal handoff."
    return "Needs reproducibility work before handoff; start with the top risks below."


def _target_fit_score(report: Report, audience: str) -> tuple[int, list[str]]:
    severities = _severity_counts(report)
    weakest_label, weakest_score, _weakest_help = min(_category_score_entries(report), key=lambda entry: entry[1])
    score = 0
    reasons: list[str] = []

    def add(points: int, reason: str) -> None:
        nonlocal score
        score += points
        reasons.append(reason)

    if report.summary.notebooks > 0:
        add(2, f"Notebook-heavy workflow: {_pluralize(report.summary.notebooks, 'notebook')} found.")
    if report.summary.python_files > 0:
        add(1, f"Code-backed workflow: {_pluralize(report.summary.python_files, 'Python file')} found.")
    if report.summary.findings_count > 0:
        add(1, f"Concrete audit hook: {_pluralize(report.summary.findings_count, 'finding')} to discuss.")
    if severities["high"] > 0:
        add(2, f"Clear handoff risk: {_pluralize(severities['high'], 'high-severity finding')}.")
    elif severities["medium"] > 0:
        add(1, f"Moderate handoff risk: {_pluralize(severities['medium'], 'medium-severity finding')}.")
    if report.scores.overall_score < 85:
        add(1, f"Visible improvement room: overall score is {report.scores.overall_score}/100.")
    if weakest_score <= 70:
        add(1, f"Narrow first angle: weakest area is {weakest_label} at {weakest_score}/100.")
    if is_github_repo_url(report.summary.target):
        add(1, "Public demo ready: target can be opened in the browser demo.")

    if audience == "professor":
        if report.summary.notebooks > 0:
            add(1, "Professor fit: notebook workflows are easy to frame as student handoff risk.")
        if report.scores.notebook_determinism < 85 or report.scores.artifact_availability < 85:
            add(1, "Professor fit: notebook or artifact score leaves room for a lab handoff checklist.")
    elif audience == "founder":
        if report.scores.environment_rebuildability < 85 or report.scores.onboarding_readiness < 85:
            add(1, "Founder fit: onboarding or rebuildability score maps to engineering ramp-up risk.")
        if severities["high"] > 0:
            add(1, "Founder fit: high-severity findings create a concrete first-fix offer.")
    elif audience == "maintainer":
        if report.summary.findings_count > 0:
            add(1, "Maintainer fit: findings can be converted into a small issue or PR.")
        if is_github_repo_url(report.summary.target):
            add(1, "Maintainer fit: public GitHub target makes the demo and issue draft easy to share.")
    elif report.summary.findings_count > 0:
        add(1, "General fit: there is a clear first follow-up instead of a vague cold message.")

    return min(score, 10), reasons


def _target_fit_recommendation(score: int) -> str:
    if score >= 8:
        return "strong outreach candidate"
    if score >= 5:
        return "promising candidate, but use a narrow ask"
    return "weak outreach candidate unless you have extra context"


def _public_demo_markdown_link(target: str) -> str | None:
    if not is_github_repo_url(target) or github_repo_slug(target) is None:
        return None
    return render_demo_link(build_demo_link(target, auto_audit=True), "markdown")


def _remediation_intro(risk: RiskSummary) -> str:
    scope = f"{_pluralize(risk.count, 'finding')} across {_pluralize(len(risk.affected_files), 'file')}"
    return f"Fix {risk.check_id} first because it affects {scope}."


def _explain_commands(risks: list[RiskSummary], limit: int = 3) -> list[str]:
    seen: set[str] = set()
    commands: list[str] = []
    for risk in risks:
        if risk.check_id in seen:
            continue
        seen.add(risk.check_id)
        commands.append(f"labcheck explain {risk.check_id}")
        if len(commands) >= limit:
            break
    return commands


def _next_step_entries(
    report: Report,
    risks: list[RiskSummary],
    *,
    include_full_report: bool,
) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    if include_full_report:
        entries.append(
            ("Full Markdown report", f"labcheck scan {report.summary.target} --format markdown")
        )
    entries.extend(
        [
            ("Scorecard summary", f"labcheck scorecard {report.summary.target}"),
            (
                "Sortable triage CSV",
                f"labcheck scan {report.summary.target} --format csv --output labcheck-findings.csv",
            ),
            (
                "Shareable audit bundle",
                f"labcheck pack {report.summary.target} --output-dir labcheck-audit --zip",
            ),
        ]
    )
    if risks:
        entries.append(("Explain top finding", f"labcheck explain {risks[0].check_id}"))
    return entries


def _pluralize(count: int, singular: str, plural: str | None = None) -> str:
    return f"{count} {singular if count == 1 else plural or singular + 's'}"


def _visible_findings(report: Report, max_findings: int | None) -> tuple[list[Finding], int]:
    if max_findings is None:
        return report.findings, 0
    visible = report.findings[:max_findings]
    return visible, max(0, len(report.findings) - len(visible))


def _markdown_cell(value: str) -> str:
    return value.replace("\n", " ").replace("|", "\\|")


def _suggested_triage_owner(category: str) -> str:
    return TRIAGE_OWNER_BY_CATEGORY.get(category, "repo maintainer")


def _display_label(raw_label: str) -> str:
    normalized = raw_label.replace("\\", "/")
    return normalized.split("/")[-1]


def _render_graph_svg(report: Report) -> str:
    if not report.graph.nodes:
        return "<svg viewBox='0 0 640 140' role='img' aria-label='Empty provenance graph'></svg>"

    lanes: dict[int, list] = {0: [], 1: [], 2: []}
    for node in report.graph.nodes:
        lanes[KIND_COLUMNS.get(node.kind, 1)].append(node)

    positions: dict[str, tuple[int, int]] = {}
    column_x = {0: 120, 1: 320, 2: 520}
    for lane, nodes in lanes.items():
        for index, node in enumerate(nodes):
            positions[node.id] = (column_x[lane], 90 + index * 90)

    height = max((y for _, y in positions.values()), default=90) + 70
    edge_markup = []
    for edge in report.graph.edges:
        if edge.source not in positions or edge.target not in positions:
            continue
        x1, y1 = positions[edge.source]
        x2, y2 = positions[edge.target]
        edge_markup.append(
            f"<path d='M {x1} {y1} C {(x1 + x2) // 2} {y1}, {(x1 + x2) // 2} {y2}, {x2} {y2}' "
            f"fill='none' stroke='#0f766e' stroke-width='3' stroke-opacity='0.45' />"
        )

    node_markup = []
    for node in report.graph.nodes:
        x, y = positions[node.id]
        fill = {
            "input": "#fef3c7",
            "notebook": "#d1fae5",
            "python": "#dbeafe",
            "artifact": "#fee2e2",
        }.get(node.kind, "#e5e7eb")
        display_label = _display_label(node.label)
        node_markup.append(
            f"""
            <g>
              <rect x="{x - 80}" y="{y - 24}" width="160" height="48" rx="14" fill="{fill}" stroke="#d8cdb9" />
              <text x="{x}" y="{y - 4}" text-anchor="middle" font-size="12" font-weight="700" fill="#17202a">{escape(node.kind.upper())}</text>
              <text x="{x}" y="{y + 14}" text-anchor="middle" font-size="12" fill="#17202a">{escape(display_label)}</text>
            </g>
            """
        )

    return (
        f"<svg viewBox='0 0 640 {height}' role='img' aria-label='Provenance graph'>"
        + "".join(edge_markup)
        + "".join(node_markup)
        + "</svg>"
    )


def render_text(report: Report, max_findings: int | None = DEFAULT_HUMAN_FINDING_LIMIT) -> str:
    severities = _severity_counts(report)
    risks = _top_risks(report)
    compose_summaries = _compose_reference_summaries(report)
    visible_findings, omitted_findings = _visible_findings(report, max_findings)
    lines = [
        f"Target: {report.summary.target}",
        f"Overall Score: {report.scores.overall_score}",
        "",
        "Category Scores:",
        f"- Environment Rebuildability: {report.scores.environment_rebuildability}",
        f"- Notebook Determinism: {report.scores.notebook_determinism}",
        f"- Artifact Availability: {report.scores.artifact_availability}",
        f"- Portability: {report.scores.portability}",
        f"- Onboarding Readiness: {report.scores.onboarding_readiness}",
        "",
        f"Severity Mix: {severities['high']} high, {severities['medium']} medium, {severities['low']} low",
    ]
    capped_note = _capped_findings_note(report)
    if capped_note:
        lines.extend(["", "Configured Finding Limits:", capped_note])
    lines.extend(["", "Review Boundary:", REVIEW_BOUNDARY_TEXT, "", "Top Risks:"])
    if risks:
        for risk in risks:
            scope = f"{_pluralize(risk.count, 'finding')} across {_pluralize(len(risk.affected_files), 'file')}"
            lines.append(f"- {risk.severity.upper()} {risk.check_id} {risk.title}: {scope}")
            lines.append(f"  First evidence: {risk.first_finding.file_path} - {risk.first_finding.evidence}")
    else:
        lines.append("- No top risks")

    if compose_summaries:
        lines.extend(["", "Docker Compose Reference Summary:"])
        current_file = ""
        for summary in compose_summaries:
            if summary.compose_file != current_file:
                current_file = summary.compose_file
                lines.append(f"- {summary.compose_file}:")
            references = ", ".join(summary.missing_references)
            lines.append(f"  - {summary.check_id} {summary.title}: {references}")

    explain_commands = _explain_commands(risks)
    if explain_commands:
        lines.extend(["", "Understand Finding Codes:"])
        lines.extend(f"- {command}" for command in explain_commands)

    lines.extend(["", "Remediation Plan:"])
    if risks:
        for index, risk in enumerate(risks, start=1):
            lines.append(f"{index}. {_remediation_intro(risk)}")
            lines.append(f"   Suggested fix: {risk.first_finding.suggested_fix}")
    else:
        lines.append("- No remediation needed")

    lines.extend(["", "Next Steps:"])
    lines.extend(
        f"- {label}: {command}"
        for label, command in _next_step_entries(report, risks, include_full_report=True)
    )

    lines.extend(
        [
            "",
            f"Graph: {len(report.graph.nodes)} nodes, {len(report.graph.edges)} edges",
            "",
            f"Findings ({len(report.findings)}):",
        ]
    )
    if omitted_findings:
        lines.append(
            f"Showing first {len(visible_findings)} findings; {omitted_findings} omitted. "
            "Use --max-findings all to include every detail."
        )
    if not visible_findings:
        if omitted_findings:
            lines.append("- No detailed findings shown")
        else:
            lines.append("- No findings")
    else:
        for finding in visible_findings:
            lines.append(
                f"- {finding.severity.upper()} {finding.check_id} {finding.title} [{finding.file_path}]"
            )
            lines.append(f"  Evidence: {finding.evidence}")
    return "\n".join(lines)


def render_markdown(report: Report, max_findings: int | None = DEFAULT_HUMAN_FINDING_LIMIT) -> str:
    severities = _severity_counts(report)
    risks = _top_risks(report)
    compose_summaries = _compose_reference_summaries(report)
    visible_findings, omitted_findings = _visible_findings(report, max_findings)
    lines = [
        "# labcheck Report",
        "",
        f"- Target: `{report.summary.target}`",
        f"- Overall Score: **{report.scores.overall_score}**",
        f"- Severity Mix: **{severities['high']} high**, **{severities['medium']} medium**, **{severities['low']} low**",
    ]
    capped_note = _capped_findings_note(report)
    if capped_note:
        lines.append(f"- Configured finding limits: {capped_note}")
    lines.extend(
        [
            "",
            "## Review Boundary",
            "",
            REVIEW_BOUNDARY_TEXT,
            "",
            "## Scores",
            "",
            "| Category | Score | What it means |",
            "|---|---:|---|",
            f"| Environment Rebuildability | {report.scores.environment_rebuildability} | {CATEGORY_HELP['environment_rebuildability']} |",
            f"| Notebook Determinism | {report.scores.notebook_determinism} | {CATEGORY_HELP['notebook_determinism']} |",
            f"| Artifact Availability | {report.scores.artifact_availability} | {CATEGORY_HELP['artifact_availability']} |",
            f"| Portability | {report.scores.portability} | {CATEGORY_HELP['portability']} |",
            f"| Onboarding Readiness | {report.scores.onboarding_readiness} | {CATEGORY_HELP['onboarding_readiness']} |",
            "",
            "## Top Risks",
            "",
        ]
    )
    if risks:
        lines.extend(
            [
                "| Risk | Severity | Scope | First evidence |",
                "|---|---|---|---|",
            ]
        )
        for risk in risks:
            scope = f"{_pluralize(risk.count, 'finding')} across {_pluralize(len(risk.affected_files), 'file')}"
            evidence = f"{risk.first_finding.file_path}: {risk.first_finding.evidence}"
            lines.append(
                f"| `{risk.check_id}` {risk.title} | `{risk.severity}` | {scope} | {_markdown_cell(evidence)} |"
            )
    else:
        lines.append("No top risks.")

    if compose_summaries:
        lines.extend(
            [
                "",
                "## Docker Compose Reference Summary",
                "",
                "| Compose file | Check | Missing references |",
                "|---|---|---|",
            ]
        )
        for summary in compose_summaries:
            references = ", ".join(f"`{_markdown_cell(reference)}`" for reference in summary.missing_references)
            lines.append(
                f"| `{_markdown_cell(summary.compose_file)}` | `{summary.check_id}` {_markdown_cell(summary.title)} | {references} |"
            )

    explain_commands = _explain_commands(risks)
    if explain_commands:
        lines.extend(
            [
                "",
                "## Understand Finding Codes",
                "",
                "Run these commands for plain-language context, why the finding matters, and the expected fix:",
                "",
            ]
        )
        lines.extend(f"- `{command}`" for command in explain_commands)

    lines.extend(
        [
            "",
            "## Remediation Plan",
            "",
        ]
    )
    if risks:
        for index, risk in enumerate(risks, start=1):
            lines.extend(
                [
                    f"{index}. **{_markdown_cell(_remediation_intro(risk))}**",
                    f"   Suggested fix: {_markdown_cell(risk.first_finding.suggested_fix)}",
                    f"   First evidence: `{_markdown_cell(risk.first_finding.file_path)}` - {_markdown_cell(risk.first_finding.evidence)}",
                    "",
                ]
            )
    else:
        lines.append("No remediation needed.")

    lines.extend(["", "## Next Steps", ""])
    lines.extend(
        f"- {label}: `{command}`"
        for label, command in _next_step_entries(report, risks, include_full_report=False)
    )

    lines.extend(
        [
            "",
            "## Provenance Graph",
            "",
            f"- Nodes: {len(report.graph.nodes)}",
            f"- Edges: {len(report.graph.edges)}",
            "",
            "| Source | Edge | Target |",
            "|---|---|---|",
        ]
    )
    if report.graph.edges:
        for edge in report.graph.edges:
            lines.append(f"| `{edge.source}` | `{edge.kind}` | `{edge.target}` |")
    else:
        lines.append("| `-` | `-` | `-` |")
    lines.extend(["", "## Findings", ""])
    if omitted_findings:
        lines.extend(
            [
                f"Showing first {len(visible_findings)} findings; {omitted_findings} omitted.",
                "",
                f"Use `--max-findings all` to include every detail in human-readable reports. {COMPLETE_OUTPUTS_NOTE}",
                "",
            ]
        )
    if not visible_findings:
        if omitted_findings:
            lines.append("No detailed findings shown.")
        else:
            lines.append("No findings.")
    else:
        for finding in visible_findings:
            lines.extend(
                [
                    f"### {finding.check_id} - {finding.title}",
                    "",
                    f"- Severity: `{finding.severity}`",
                    f"- Category: `{finding.category}`",
                    f"- File: `{finding.file_path}`",
                    f"- Evidence: {finding.evidence}",
                    f"- Why it matters: {finding.why_it_matters}",
                    f"- Suggested fix: {finding.suggested_fix}",
                    "",
                ]
            )
    return "\n".join(lines)


def render_scorecard(report: Report) -> str:
    """Render a compact Markdown scorecard for PR comments, outreach, and handoff notes."""
    severities = _severity_counts(report)
    risks = _top_risks(report, limit=3)
    compose_summaries = _compose_reference_summaries(report)
    category_scores = _category_score_entries(report)
    weakest_label, weakest_score, weakest_help = min(category_scores, key=lambda entry: entry[1])
    lines = [
        "# labcheck Scorecard",
        "",
        f"- Target: `{report.summary.target}`",
        f"- Overall score: **{report.scores.overall_score}/100**",
        (
            f"- Scope: **{_pluralize(report.summary.notebooks, 'notebook')}**, "
            f"**{_pluralize(report.summary.python_files, 'Python file')}**"
        ),
        (
            f"- Findings: **{report.summary.findings_count}** "
            f"(`{severities['high']}` high, `{severities['medium']}` medium, `{severities['low']}` low)"
        ),
        f"- Weakest area: **{weakest_label}** ({weakest_score}/100) - {weakest_help}",
    ]
    capped_note = _capped_findings_note(report)
    if capped_note:
        lines.append(f"- Configured finding limits: {capped_note}")
    lines.extend(
        [
            "",
            "## Triage Signal",
            "",
            _scorecard_signal(report, severities),
            "",
            "## Review Boundary",
            "",
            REVIEW_BOUNDARY_TEXT,
            "",
            "## Top Risks",
            "",
        ]
    )
    if risks:
        lines.extend(["| Risk | Severity | Scope | First evidence |", "|---|---|---|---|"])
        for risk in risks:
            scope = f"{_pluralize(risk.count, 'finding')} across {_pluralize(len(risk.affected_files), 'file')}"
            evidence = f"{risk.first_finding.file_path}: {risk.first_finding.evidence}"
            lines.append(
                f"| `{risk.check_id}` {risk.title} | `{risk.severity}` | {scope} | {_markdown_cell(evidence)} |"
            )
    else:
        lines.append("No top risks.")

    if compose_summaries:
        lines.extend(
            [
                "",
                "## Docker Compose Reference Summary",
                "",
                "| Compose file | Check | Missing references |",
                "|---|---|---|",
            ]
        )
        for summary in compose_summaries:
            references = ", ".join(f"`{_markdown_cell(reference)}`" for reference in summary.missing_references)
            lines.append(
                f"| `{_markdown_cell(summary.compose_file)}` | `{summary.check_id}` {_markdown_cell(summary.title)} | {references} |"
            )

    lines.extend(["", "## First Fixes", ""])
    if risks:
        for index, risk in enumerate(risks, start=1):
            lines.append(f"{index}. {_markdown_cell(_remediation_intro(risk))}")
            lines.append(f"   Suggested fix: {_markdown_cell(risk.first_finding.suggested_fix)}")
    else:
        lines.append("No fixes needed before sharing.")

    lines.extend(
        [
            "",
            "## Next Steps",
            "",
        ]
    )
    lines.extend(
        f"- {label}: `{command}`"
        for label, command in _next_step_entries(report, risks, include_full_report=True)
    )
    return "\n".join(lines)


def render_target_fit(report: Report, audience: str = "general") -> str:
    """Render an outreach target-fit card from static audit evidence."""
    normalized_audience = audience if audience in OUTREACH_AUDIENCES else "general"
    severities = _severity_counts(report)
    risks = _top_risks(report, limit=1)
    score, reasons = _target_fit_score(report, normalized_audience)
    recommendation = _target_fit_recommendation(score)
    top_risk = risks[0] if risks else None
    demo_link = _public_demo_markdown_link(report.summary.target)

    lines = [
        "# labcheck Target Fit",
        "",
        f"- Target: `{report.summary.target}`",
        f"- Audience: `{normalized_audience}`",
        f"- Fit score: **{score}/10**",
        f"- Recommendation: **{recommendation}**",
        (
            f"- Findings: **{report.summary.findings_count}** "
            f"(`{severities['high']}` high, `{severities['medium']}` medium, `{severities['low']}` low)"
        ),
        f"- Overall score: **{report.scores.overall_score}/100**",
        "",
        "## Why This Target Fits",
        "",
    ]
    if reasons:
        lines.extend(f"- {reason}" for reason in reasons)
    else:
        lines.append("- No strong static outreach signal was found; prioritize warmer context before reaching out.")

    lines.extend(["", "## Best Outreach Hook", ""])
    if top_risk:
        lines.extend(
            [
                f"- Top risk: `{top_risk.check_id}` - {top_risk.title}.",
                f"- Scope: {_pluralize(top_risk.count, 'finding')} across {_pluralize(len(top_risk.affected_files), 'file')}.",
                f"- First evidence: {top_risk.first_finding.file_path}: {top_risk.first_finding.evidence}",
            ]
        )
    else:
        lines.append("- No top risk found. Lead with a positive handoff scorecard or skip cold outreach.")

    if demo_link:
        lines.extend(
            [
                "",
                "## Shareable Demo",
                "",
                f"- Browser demo: {demo_link}",
                "- Demo scope: bounded public GitHub files only; use the CLI for the full audit.",
            ]
        )

    lines.extend(
        [
            "",
            "## Suggested Ask",
            "",
            TARGET_FIT_AUDIENCE_ASKS[normalized_audience],
            "",
            "## Safe Framing",
            "",
            REVIEW_BOUNDARY_TEXT,
            "",
            "## Next Commands",
            "",
            f"- Scorecard: `labcheck scorecard {report.summary.target}`",
            (
                f"- Outreach note: `labcheck outreach {report.summary.target} "
                f"--audience {normalized_audience} --output labcheck-outreach-note.md`"
            ),
            f"- Audit bundle: `labcheck pack {report.summary.target} --output-dir labcheck-audit --zip`",
        ]
    )
    return "\n".join(lines)


def render_outreach_note(
    report: Report,
    recipient: str = "[Name]",
    sender: str = "[Your name]",
    audience: str = "general",
) -> str:
    """Render a respectful, ready-to-edit outreach note from a report."""
    profile = OUTREACH_AUDIENCES.get(audience, OUTREACH_AUDIENCES["general"])
    severities = _severity_counts(report)
    risks = _top_risks(report, limit=1)
    signal = _scorecard_signal(report, severities)
    top_risk = risks[0] if risks else None
    demo_link = _public_demo_markdown_link(report.summary.target)
    top_risk_line = (
        f"The first thing I would look at is `{top_risk.check_id}` ({top_risk.title}), "
        f"which appears as {_pluralize(top_risk.count, 'finding')} across "
        f"{_pluralize(len(top_risk.affected_files), 'file')}."
        if top_risk
        else "I did not find a top reproducibility risk in the scanned files."
    )
    score_context = (
        "This is not a scientific-validity judgment; it is a handoff/readiness signal based on static evidence "
        "in the repository."
    )
    lines = [
        "# labcheck Outreach Note",
        "",
        f"Subject: {profile['subject']} for `{report.summary.target}`",
        "",
        f"Hi {recipient},",
        "",
        (
            "I ran `labcheck`, a no-key static reproducibility auditor, on "
            f"`{report.summary.target}` {profile['intro']}"
        ),
        "",
        f"- Overall score: **{report.scores.overall_score}/100**",
        (
            f"- Findings: **{report.summary.findings_count}** "
            f"(`{severities['high']}` high, `{severities['medium']}` medium, `{severities['low']}` low)"
        ),
        f"- Triage signal: {signal}",
        f"- Top risk: {top_risk_line}",
    ]
    if demo_link:
        lines.extend(
            [
                f"- Browser demo: {demo_link}",
                "- Demo scope: bounded public GitHub files only; use the CLI for the full audit.",
            ]
        )
    lines.extend(
        [
            "",
            score_context,
            "",
            profile["offer"],
            "",
            f"Best,\n{sender}",
            "",
            "Generated by `labcheck` with deterministic local checks. No API key or hosted backend was used.",
        ]
    )
    return "\n".join(lines)


def render_issue_draft(report: Report) -> str:
    """Render a maintainer-friendly GitHub issue draft from a report."""
    severities = _severity_counts(report)
    risks = _top_risks(report, limit=3)
    signal = _scorecard_signal(report, severities)
    demo_link = _public_demo_markdown_link(report.summary.target)
    lines = [
        "# labcheck Issue Draft",
        "",
        f"Suggested title: Reproducibility handoff gaps in `{report.summary.target}`",
        "",
        "## Context",
        "",
        (
            "I ran `labcheck`, a no-key static reproducibility auditor, on this repository to look for "
            "fresh-clone handoff issues such as hidden notebook state, missing inputs, dependency drift, "
            "stale setup commands, and unclear generated artifacts."
        ),
        "",
        (
            "This is not a scientific-validity judgment, and `labcheck` does not execute the project code by default. "
            "Please treat this as a lightweight maintainer handoff signal; close it if the findings are expected, "
            "out of scope, or already documented elsewhere."
        ),
        "",
        "## Summary",
        "",
        f"- Target: `{report.summary.target}`",
        f"- Overall score: **{report.scores.overall_score}/100**",
        (
            f"- Findings: **{report.summary.findings_count}** "
            f"(`{severities['high']}` high, `{severities['medium']}` medium, `{severities['low']}` low)"
        ),
        f"- Triage signal: {signal}",
        "",
        "## Suggested Triage",
        "",
    ]
    if risks:
        for index, risk in enumerate(risks, start=1):
            first = risk.first_finding
            lines.extend(
                [
                    f"### {index}. `{risk.check_id}` - {risk.title}",
                    "",
                    f"- Severity: `{risk.severity}`",
                    f"- Scope: {_pluralize(risk.count, 'finding')} across {_pluralize(len(risk.affected_files), 'file')}",
                    f"- First evidence: `{first.file_path}` - {_markdown_cell(first.evidence)}",
                    f"- Why it matters: {_markdown_cell(first.why_it_matters)}",
                    f"- Suggested fix: {_markdown_cell(first.suggested_fix)}",
                    "",
                ]
            )
    else:
        lines.extend(
            [
                "No reproducibility risks were found in the scanned files.",
                "",
            ]
        )

    lines.extend(
        [
            "## Reproduce This Audit",
            "",
        ]
    )
    if demo_link:
        lines.extend(
            [
                f"- Browser demo: {demo_link}",
                "- Note: the browser demo audits a bounded public-file snapshot; use the CLI commands below for the full audit.",
                "",
            ]
        )
    lines.extend(
        [
            "```bash",
            f"labcheck scorecard {report.summary.target}",
            f"labcheck scan {report.summary.target} --format markdown",
            "```",
            "",
            "## Maintainer Notes",
            "",
            "- If a finding is real, the fastest path is usually to fix or document the first top-risk item.",
            "- If a finding is intentional, document the exception or add it to a `labcheck` baseline/config.",
            "- If this issue is too broad, split out the first top-risk item and close the rest.",
            "",
            "Generated by `labcheck` with deterministic local checks. No API key or hosted backend was used.",
        ]
    )
    return "\n".join(lines)


def render_json(report: Report) -> str:
    return json.dumps(report.to_dict(), indent=2)


def render_csv(report: Report) -> str:
    """Render findings as a spreadsheet-friendly CSV table."""
    output = io.StringIO(newline="")
    fieldnames = [
        "target",
        "overall_score",
        "status",
        "owner",
        "suggested_owner",
        "check_id",
        "title",
        "severity",
        "category",
        "file_path",
        "evidence",
        "why_it_matters",
        "suggested_fix",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for finding in report.findings:
        writer.writerow(
            {
                "target": report.summary.target,
                "overall_score": report.scores.overall_score,
                "status": "",
                "owner": "",
                "suggested_owner": _suggested_triage_owner(finding.category),
                "check_id": finding.check_id,
                "title": finding.title,
                "severity": finding.severity,
                "category": finding.category,
                "file_path": finding.file_path,
                "evidence": finding.evidence,
                "why_it_matters": finding.why_it_matters,
                "suggested_fix": finding.suggested_fix,
            }
        )
    return output.getvalue()


def _badge_color(score: int) -> str:
    if score >= 85:
        return "#0f766e"
    if score >= 70:
        return "#a16207"
    return "#b91c1c"


def render_badge(report: Report) -> str:
    """Render a static SVG score badge suitable for README or CI artifacts."""
    score = report.scores.overall_score
    label = "labcheck"
    value = f"{score}/100"
    label_width = 70
    value_width = 58
    total_width = label_width + value_width
    color = _badge_color(score)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="20" role="img" aria-label="{label}: {value}">
  <title>{label}: {value}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#fff" stop-opacity=".7"/>
    <stop offset=".1" stop-color="#aaa" stop-opacity=".1"/>
    <stop offset=".9" stop-color="#000" stop-opacity=".3"/>
    <stop offset="1" stop-color="#000" stop-opacity=".5"/>
  </linearGradient>
  <clipPath id="r">
    <rect width="{total_width}" height="20" rx="3" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_width}" height="20" fill="#17202a"/>
    <rect x="{label_width}" width="{value_width}" height="20" fill="{color}"/>
    <rect width="{total_width}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
    <text x="{label_width / 2}" y="15" fill="#010101" fill-opacity=".3">{label}</text>
    <text x="{label_width / 2}" y="14">{label}</text>
    <text x="{label_width + value_width / 2}" y="15" fill="#010101" fill-opacity=".3">{value}</text>
    <text x="{label_width + value_width / 2}" y="14">{value}</text>
  </g>
</svg>
"""


def _sarif_uri(file_path: str) -> str:
    normalized = file_path.replace("\\", "/")
    return normalized if normalized else "."


def render_sarif(report: Report) -> str:
    rules: dict[str, dict] = {}
    results = []
    for finding in report.findings:
        if finding.check_id not in rules:
            rules[finding.check_id] = {
                "id": finding.check_id,
                "name": finding.title,
                "shortDescription": {"text": finding.title},
                "fullDescription": {"text": finding.why_it_matters},
                "help": {"text": finding.suggested_fix},
                "properties": {
                    "category": finding.category,
                    "severity": finding.severity,
                },
            }
        results.append(
            {
                "ruleId": finding.check_id,
                "level": SARIF_LEVELS.get(finding.severity, "warning"),
                "message": {"text": finding.evidence},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": _sarif_uri(finding.file_path)},
                            "region": {"startLine": 1},
                        }
                    }
                ],
                "properties": {
                    "category": finding.category,
                    "severity": finding.severity,
                    "title": finding.title,
                    "suggested_fix": finding.suggested_fix,
                },
            }
        )

    payload = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "labcheck",
                        "informationUri": "https://github.com/ThomasAquinas14/labcheck",
                        "rules": list(rules.values()),
                    }
                },
                "results": results,
                "properties": {
                    "target": report.summary.target,
                    "overall_score": report.scores.overall_score,
                },
            }
        ],
    }
    return json.dumps(payload, indent=2)


def render_html(report: Report, max_findings: int | None = DEFAULT_HUMAN_FINDING_LIMIT) -> str:
    severities = _severity_counts(report)
    risks = _top_risks(report)
    compose_summaries = _compose_reference_summaries(report)
    visible_findings, omitted_findings = _visible_findings(report, max_findings)
    score_cards = [
        ("Environment Rebuildability", report.scores.environment_rebuildability, CATEGORY_HELP["environment_rebuildability"]),
        ("Notebook Determinism", report.scores.notebook_determinism, CATEGORY_HELP["notebook_determinism"]),
        ("Artifact Availability", report.scores.artifact_availability, CATEGORY_HELP["artifact_availability"]),
        ("Portability", report.scores.portability, CATEGORY_HELP["portability"]),
        ("Onboarding Readiness", report.scores.onboarding_readiness, CATEGORY_HELP["onboarding_readiness"]),
    ]

    score_markup = "".join(
        f"""
        <div class="score-card">
          <div class="score">{score}</div>
          <div class="score-title">{escape(title)}</div>
          <p>{escape(help_text)}</p>
        </div>
        """
        for title, score, help_text in score_cards
    )

    risk_markup = "".join(
        f"""
        <article class="risk-item severity-{escape(risk.severity)}">
          <div class="finding-head">
            <span class="badge">{escape(risk.severity.upper())}</span>
            <strong>{escape(risk.check_id)} - {escape(risk.title)}</strong>
          </div>
          <p class="file">{escape(_pluralize(risk.count, "finding"))} across {escape(_pluralize(len(risk.affected_files), "file"))}</p>
          <p><strong>First evidence:</strong> {escape(risk.first_finding.file_path)} - {escape(risk.first_finding.evidence)}</p>
          <p><strong>Suggested fix:</strong> {escape(risk.first_finding.suggested_fix)}</p>
        </article>
        """
        for risk in risks
    ) or "<p>No top risks.</p>"

    compose_items = "".join(
        f"""
        <tr>
          <td><code>{escape(summary.compose_file)}</code></td>
          <td><code>{escape(summary.check_id)}</code> {escape(summary.title)}</td>
          <td>{", ".join(f"<code>{escape(reference)}</code>" for reference in summary.missing_references)}</td>
        </tr>
        """
        for summary in compose_summaries
    )
    compose_summary_section = (
        f"""
    <section class="panel">
      <h2>Docker Compose Reference Summary</h2>
      <p>Grouped view of Compose checks that reference missing local files, directories, services, or networks.</p>
      <table>
        <thead><tr><th>Compose file</th><th>Check</th><th>Missing references</th></tr></thead>
        <tbody>{compose_items}</tbody>
      </table>
    </section>
        """
        if compose_summaries
        else ""
    )

    remediation_markup = "".join(
        f"""
        <article class="remediation-item severity-{escape(risk.severity)}">
          <div class="finding-head">
            <span class="step">{index}</span>
            <strong>{escape(_remediation_intro(risk))}</strong>
          </div>
          <p><strong>Suggested fix:</strong> {escape(risk.first_finding.suggested_fix)}</p>
          <p class="file">{escape(risk.first_finding.file_path)} - {escape(risk.first_finding.evidence)}</p>
        </article>
        """
        for index, risk in enumerate(risks, start=1)
    ) or "<p>No remediation needed.</p>"

    next_steps_markup = "".join(
        f"<li><strong>{escape(label)}:</strong> <code>{escape(command)}</code></li>"
        for label, command in _next_step_entries(report, risks, include_full_report=False)
    )

    empty_finding_message = "<p>No detailed findings shown.</p>" if omitted_findings else "<p>No findings.</p>"
    finding_cards = "".join(
        f"""
        <article class="finding severity-{escape(finding.severity)}">
          <div class="finding-head">
            <span class="badge">{escape(finding.severity.upper())}</span>
            <strong>{escape(finding.check_id)} - {escape(finding.title)}</strong>
          </div>
          <p class="file">{escape(finding.file_path)}</p>
          <p><strong>Evidence:</strong> {escape(finding.evidence)}</p>
          <p><strong>Why it matters:</strong> {escape(finding.why_it_matters)}</p>
          <p><strong>Suggested fix:</strong> {escape(finding.suggested_fix)}</p>
        </article>
        """
        for finding in visible_findings
    ) or empty_finding_message

    if omitted_findings:
        finding_cards = (
            f"""
            <div class="truncation-note">
              Showing first {len(visible_findings)} findings; {omitted_findings} omitted.
              Use <code>--max-findings all</code> to include every detail. {escape(COMPLETE_OUTPUTS_NOTE)}
            </div>
            """
            + finding_cards
        )

    graph_rows = "".join(
        f"<tr><td>{escape(edge.source)}</td><td>{escape(edge.kind)}</td><td>{escape(edge.target)}</td></tr>"
        for edge in report.graph.edges
    ) or "<tr><td>-</td><td>-</td><td>-</td></tr>"
    graph_svg = _render_graph_svg(report)

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>labcheck Report</title>
  <style>
    :root {{
      --bg: #f5f1e8;
      --ink: #17202a;
      --card: #fffdf8;
      --border: #d8cdb9;
      --accent: #0f766e;
      --warn: #b45309;
      --danger: #b91c1c;
    }}
    body {{ font-family: Georgia, 'Times New Roman', serif; background: linear-gradient(180deg, #f4efe6, #fbfaf7); color: var(--ink); margin: 0; }}
    main {{ max-width: 1100px; margin: 0 auto; padding: 40px 20px 64px; }}
    .hero, .panel, .finding {{ background: var(--card); border: 1px solid var(--border); border-radius: 18px; box-shadow: 0 10px 30px rgba(23,32,42,0.06); }}
    .hero {{ padding: 28px; margin-bottom: 24px; }}
    h1, h2 {{ margin: 0 0 12px; }}
    .overall {{ font-size: 52px; font-weight: 700; color: var(--accent); }}
    .meta {{ display: flex; gap: 18px; flex-wrap: wrap; margin-top: 16px; }}
    .meta span {{ background: #efe7d7; border-radius: 999px; padding: 8px 14px; font-size: 14px; }}
    .grid {{ display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); margin: 24px 0; }}
    .score-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 16px; padding: 18px; }}
    .score {{ font-size: 34px; font-weight: 700; color: var(--accent); }}
    .score-title {{ font-weight: 700; margin-top: 8px; }}
    .panel {{ padding: 22px; margin-top: 24px; }}
    .risk-list {{ display: grid; gap: 14px; margin-top: 14px; }}
    .risk-item {{ border-top: 1px solid var(--border); padding: 14px 0; }}
    .risk-item:first-child {{ border-top: 0; padding-top: 0; }}
    .remediation-list {{ counter-reset: fix-order; display: grid; gap: 14px; margin-top: 14px; }}
    .remediation-item {{ border: 1px solid var(--border); border-radius: 16px; padding: 16px; background: #fcfaf5; }}
    .step {{ display: inline-grid; place-items: center; width: 30px; height: 30px; border-radius: 999px; background: var(--accent); color: white; font-weight: 700; }}
    .finding-list {{ display: grid; gap: 14px; }}
    .finding {{ padding: 18px; }}
    .truncation-note {{ border: 1px dashed var(--border); border-radius: 16px; padding: 14px; background: #f8f4ec; color: #5b6470; }}
    .finding-head {{ display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }}
    .badge {{ border-radius: 999px; padding: 4px 10px; font-size: 12px; font-weight: 700; background: #efe7d7; }}
    .severity-high .badge {{ background: #fee2e2; color: var(--danger); }}
    .severity-medium .badge {{ background: #fef3c7; color: var(--warn); }}
    .file {{ color: #5b6470; font-family: Consolas, monospace; }}
    code {{ background: #efe7d7; border-radius: 6px; font-family: Consolas, monospace; padding: 2px 5px; }}
    .next-steps {{ margin: 0; padding-left: 22px; }}
    .next-steps li {{ margin: 8px 0; }}
    .graph-shell {{ background: linear-gradient(180deg, #fcfaf5, #f3ecdf); border: 1px solid var(--border); border-radius: 18px; padding: 14px; overflow: auto; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-top: 1px solid var(--border); text-align: left; padding: 12px 8px; }}
    th {{ border-top: 0; }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <p>labcheck reproducibility audit</p>
      <h1>{escape(report.summary.target)}</h1>
      <div class="overall">{report.scores.overall_score}</div>
      <div class="meta">
        <span>{severities['high']} high</span>
        <span>{severities['medium']} medium</span>
        <span>{len(report.graph.nodes)} graph nodes</span>
        <span>{len(report.graph.edges)} graph edges</span>
      </div>
    </section>

    <section class="panel">
      <h2>Review boundary</h2>
      <p>{escape(REVIEW_BOUNDARY_TEXT)}</p>
    </section>

    <section class="grid">{score_markup}</section>

    <section class="panel">
      <h2>Top risks</h2>
      <div class="risk-list">{risk_markup}</div>
    </section>{compose_summary_section}

    <section class="panel">
      <h2>Remediation plan</h2>
      <div class="remediation-list">{remediation_markup}</div>
    </section>

    <section class="panel">
      <h2>Next steps</h2>
      <ul class="next-steps">{next_steps_markup}</ul>
    </section>

    <section class="panel">
      <h2>Provenance graph</h2>
      <div class="graph-shell">{graph_svg}</div>
    </section>

    <section class="panel">
      <h2>Provenance edges</h2>
      <table>
        <thead><tr><th>Source</th><th>Edge</th><th>Target</th></tr></thead>
        <tbody>{graph_rows}</tbody>
      </table>
    </section>

    <section class="panel">
      <h2>Findings</h2>
      <div class="finding-list">{finding_cards}</div>
    </section>
  </main>
</body>
</html>
"""
    return "\n".join(line.rstrip() for line in html.splitlines()) + "\n"
