from __future__ import annotations

from dataclasses import dataclass
from html import escape
import json

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

DEFAULT_HUMAN_FINDING_LIMIT = 100


@dataclass(slots=True)
class RiskSummary:
    check_id: str
    title: str
    severity: str
    category: str
    count: int
    affected_files: list[str]
    first_finding: Finding


def _severity_counts(report: Report) -> dict[str, int]:
    counts = {"high": 0, "medium": 0, "low": 0}
    for finding in report.findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
    return counts


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


def _remediation_intro(risk: RiskSummary) -> str:
    scope = f"{_pluralize(risk.count, 'finding')} across {_pluralize(len(risk.affected_files), 'file')}"
    return f"Fix {risk.check_id} first because it affects {scope}."


def _pluralize(count: int, singular: str, plural: str | None = None) -> str:
    return f"{count} {singular if count == 1 else plural or singular + 's'}"


def _visible_findings(report: Report, max_findings: int | None) -> tuple[list[Finding], int]:
    if max_findings is None:
        return report.findings, 0
    visible = report.findings[:max_findings]
    return visible, max(0, len(report.findings) - len(visible))


def _markdown_cell(value: str) -> str:
    return value.replace("\n", " ").replace("|", "\\|")


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
        "",
        "Top Risks:",
    ]
    if risks:
        for risk in risks:
            scope = f"{_pluralize(risk.count, 'finding')} across {_pluralize(len(risk.affected_files), 'file')}"
            lines.append(f"- {risk.severity.upper()} {risk.check_id} {risk.title}: {scope}")
            lines.append(f"  First evidence: {risk.first_finding.file_path} - {risk.first_finding.evidence}")
    else:
        lines.append("- No top risks")

    lines.extend(["", "Remediation Plan:"])
    if risks:
        for index, risk in enumerate(risks, start=1):
            lines.append(f"{index}. {_remediation_intro(risk)}")
            lines.append(f"   Suggested fix: {risk.first_finding.suggested_fix}")
    else:
        lines.append("- No remediation needed")

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
    visible_findings, omitted_findings = _visible_findings(report, max_findings)
    lines = [
        "# labcheck Report",
        "",
        f"- Target: `{report.summary.target}`",
        f"- Overall Score: **{report.scores.overall_score}**",
        f"- Severity Mix: **{severities['high']} high**, **{severities['medium']} medium**, **{severities['low']} low**",
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
                "Use `--max-findings all` to include every detail in human-readable reports. JSON and SARIF outputs remain complete.",
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
        "",
        "## Triage Signal",
        "",
        _scorecard_signal(report, severities),
        "",
        "## Top Risks",
        "",
    ]
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
            "## Next Step",
            "",
            f"- Full Markdown report: `labcheck scan {report.summary.target} --format markdown`",
            f"- Shareable audit bundle: `labcheck pack {report.summary.target} --output-dir labcheck-audit --zip`",
        ]
    )
    return "\n".join(lines)


def render_json(report: Report) -> str:
    return json.dumps(report.to_dict(), indent=2)


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
              Use <code>--max-findings all</code> to include every detail. JSON and SARIF outputs remain complete.
            </div>
            """
            + finding_cards
        )

    graph_rows = "".join(
        f"<tr><td>{escape(edge.source)}</td><td>{escape(edge.kind)}</td><td>{escape(edge.target)}</td></tr>"
        for edge in report.graph.edges
    ) or "<tr><td>-</td><td>-</td><td>-</td></tr>"
    graph_svg = _render_graph_svg(report)

    return f"""<!doctype html>
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

    <section class="grid">{score_markup}</section>

    <section class="panel">
      <h2>Top risks</h2>
      <div class="risk-list">{risk_markup}</div>
    </section>

    <section class="panel">
      <h2>Remediation plan</h2>
      <div class="remediation-list">{remediation_markup}</div>
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
