from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import zipfile

from . import __version__
from .baseline import build_baseline, filter_baselined_findings, load_baseline
from .check_catalog import CHECKS, CheckDefinition, get_check
from .compare import build_comparison, load_report_json, render_comparison_json, render_comparison_markdown
from .demo_links import DEFAULT_DEMO_URL, build_demo_link, render_demo_link
from .demo_project import write_demo_repo
from .init_project import init_project
from .loaders import is_github_repo_url
from .reporters import (
    DEFAULT_HUMAN_FINDING_LIMIT,
    OUTREACH_AUDIENCES,
    render_badge,
    render_csv,
    render_html,
    render_issue_draft,
    render_json,
    render_markdown,
    render_outreach_note,
    render_scorecard,
    render_sarif,
    render_target_fit,
    render_text,
)
from .scanner import scan_path

SEVERITY_RANK = {
    "none": 99,
    "low": 2,
    "medium": 1,
    "high": 0,
}


def _catalog_categories() -> list[str]:
    return sorted({check.category for check in CHECKS})


def _catalog_severities() -> list[str]:
    return sorted({check.default_severity for check in CHECKS}, key=lambda value: SEVERITY_RANK.get(value, 99))


def _parse_max_findings(value: str) -> int | None:
    normalized = value.strip().lower()
    if normalized == "all":
        return None
    try:
        parsed = int(normalized)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a non-negative integer or 'all'") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer or 'all'")
    return parsed


def _parse_min_score(value: str) -> int:
    try:
        parsed = int(value.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer from 0 to 100") from exc
    if parsed < 0 or parsed > 100:
        raise argparse.ArgumentTypeError("must be an integer from 0 to 100")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="labcheck", description="Reproducibility auditor for research and ML repos.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Scan a folder, notebook, zip archive, or public GitHub repo URL.")
    scan_parser.add_argument("target", help="Folder, notebook, zip path, or public GitHub repo URL to scan.")
    scan_parser.add_argument("--format", choices=["text", "markdown", "json", "csv", "html", "sarif"], default="text")
    scan_parser.add_argument("--output", help="Optional output file path.")
    scan_parser.add_argument("--json-output", help="Optional machine-readable JSON output file path.")
    scan_parser.add_argument("--csv-output", help="Optional spreadsheet-friendly CSV findings output file path.")
    scan_parser.add_argument("--sarif-output", help="Optional SARIF output file path for code-scanning integrations.")
    scan_parser.add_argument("--badge-output", help="Optional static SVG score badge output path.")
    scan_parser.add_argument("--scorecard-output", help="Optional compact Markdown scorecard output path.")
    scan_parser.add_argument("--target-fit-output", help="Optional outreach target-fit Markdown output path.")
    scan_parser.add_argument("--issue-output", help="Optional maintainer-friendly issue draft Markdown output path.")
    scan_parser.add_argument("--baseline", help="Optional labcheck baseline JSON. Matching findings are ignored.")
    scan_parser.add_argument("--config", help="Optional .labcheck.toml config path.")
    scan_parser.add_argument(
        "--max-findings",
        type=_parse_max_findings,
        default=DEFAULT_HUMAN_FINDING_LIMIT,
        metavar="N|all",
        help=(
            "Cap detailed findings in text, Markdown, and HTML reports "
            f"(default: {DEFAULT_HUMAN_FINDING_LIMIT}; JSON/SARIF stay complete)."
        ),
    )
    scan_parser.add_argument(
        "--fail-on",
        choices=["none", "low", "medium", "high"],
        default="none",
        help="Exit non-zero if findings exist at or above this severity.",
    )
    scan_parser.add_argument(
        "--min-score",
        type=_parse_min_score,
        metavar="0-100",
        help="Exit non-zero if the overall reproducibility score is below this threshold.",
    )

    doctor_parser = subparsers.add_parser(
        "doctor",
        help="Check the labcheck install and target readiness before running a full scan.",
    )
    doctor_parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Folder, notebook, zip path, or public GitHub repo URL to check.",
    )
    doctor_parser.add_argument("--config", help="Optional .labcheck.toml config path to verify.")

    scorecard_parser = subparsers.add_parser(
        "scorecard",
        help="Generate a compact Markdown scorecard for PR comments, outreach, or handoff notes.",
    )
    scorecard_parser.add_argument("target", help="Folder, notebook, zip path, or public GitHub repo URL to scan.")
    scorecard_parser.add_argument("--output", help="Optional scorecard Markdown output path.")
    scorecard_parser.add_argument("--baseline", help="Optional labcheck baseline JSON. Matching findings are ignored.")
    scorecard_parser.add_argument("--config", help="Optional .labcheck.toml config path.")
    target_fit_parser = subparsers.add_parser(
        "target-fit",
        help="Score whether a repo is worth a cold outreach follow-up.",
    )
    target_fit_parser.add_argument("target", help="Folder, notebook, zip path, or public GitHub repo URL to scan.")
    target_fit_parser.add_argument("--output", help="Optional target-fit Markdown output path.")
    target_fit_parser.add_argument(
        "--audience",
        choices=sorted(OUTREACH_AUDIENCES),
        default="general",
        help="Score fit for a general, professor, founder, or maintainer audience.",
    )
    target_fit_parser.add_argument("--baseline", help="Optional labcheck baseline JSON. Matching findings are ignored.")
    target_fit_parser.add_argument("--config", help="Optional .labcheck.toml config path.")
    outreach_parser = subparsers.add_parser(
        "outreach",
        help="Generate a ready-to-edit outreach note from a labcheck audit.",
    )
    outreach_parser.add_argument("target", help="Folder, notebook, zip path, or public GitHub repo URL to scan.")
    outreach_parser.add_argument("--output", help="Optional outreach note Markdown output path.")
    outreach_parser.add_argument("--recipient", default="[Name]", help="Recipient name or placeholder.")
    outreach_parser.add_argument("--sender", default="[Your name]", help="Sender name or placeholder.")
    outreach_parser.add_argument(
        "--audience",
        choices=sorted(OUTREACH_AUDIENCES),
        default="general",
        help="Tailor the outreach note for a general, professor, founder, or maintainer audience.",
    )
    outreach_parser.add_argument("--baseline", help="Optional labcheck baseline JSON. Matching findings are ignored.")
    outreach_parser.add_argument("--config", help="Optional .labcheck.toml config path.")
    issue_parser = subparsers.add_parser(
        "issue",
        help="Generate a maintainer-friendly GitHub issue draft from a labcheck audit.",
    )
    issue_parser.add_argument("target", help="Folder, notebook, zip path, or public GitHub repo URL to scan.")
    issue_parser.add_argument("--output", help="Optional issue draft Markdown output path.")
    issue_parser.add_argument("--baseline", help="Optional labcheck baseline JSON. Matching findings are ignored.")
    issue_parser.add_argument("--config", help="Optional .labcheck.toml config path.")
    demo_link_parser = subparsers.add_parser(
        "demo-link",
        help="Generate a shareable browser-demo URL for a public GitHub repository.",
    )
    demo_link_parser.add_argument("target", help="GitHub repository as owner/repo or https://github.com/owner/repo.")
    demo_link_parser.add_argument("--base-url", default=DEFAULT_DEMO_URL, help="Browser demo URL to prefill.")
    demo_link_parser.add_argument("--auto-audit", action="store_true", help="Add audit=1 so the browser starts the bounded audit automatically.")
    demo_link_parser.add_argument(
        "--audience",
        choices=sorted(OUTREACH_AUDIENCES),
        default="general",
        help="Prefill the browser target-fit audience.",
    )
    demo_link_parser.add_argument("--format", choices=["url", "markdown", "html"], default="url", help="Output a raw URL, Markdown link, or HTML anchor.")
    demo_link_parser.add_argument("--output", help="Optional output file path.")

    checks_parser = subparsers.add_parser("checks", help="List supported checks.")
    checks_parser.add_argument(
        "--category",
        choices=_catalog_categories(),
        help="Only show checks in one category, for example determinism or artifacts.",
    )
    checks_parser.add_argument(
        "--severity",
        choices=_catalog_severities(),
        help="Only show checks with this default severity.",
    )
    checks_parser.add_argument(
        "--search",
        help="Case-insensitive search across check IDs, titles, categories, descriptions, and fixes.",
    )
    explain_parser = subparsers.add_parser("explain", help="Explain a labcheck finding code.")
    explain_parser.add_argument("check_id", help="Finding code to explain, for example LC005.")
    explain_parser.add_argument(
        "--format",
        choices=["text", "markdown", "json"],
        default="text",
        help="Output format for the explanation.",
    )
    baseline_parser = subparsers.add_parser("baseline", help="Create a labcheck baseline from the current findings.")
    baseline_parser.add_argument("target", help="Folder, notebook, zip path, or public GitHub repo URL to scan.")
    baseline_parser.add_argument("--output", default=".labcheck-baseline.json", help="Baseline output path.")
    baseline_parser.add_argument("--config", help="Optional .labcheck.toml config path.")
    compare_parser = subparsers.add_parser(
        "compare",
        help="Compare two labcheck JSON reports to show before/after reproducibility progress.",
    )
    compare_parser.add_argument("before_json", help="Earlier labcheck JSON report.")
    compare_parser.add_argument("after_json", help="Later labcheck JSON report.")
    compare_parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    compare_parser.add_argument("--output", help="Optional comparison output path.")
    badge_parser = subparsers.add_parser("badge", help="Generate a static SVG labcheck score badge.")
    badge_parser.add_argument("target", help="Folder, notebook, zip path, or public GitHub repo URL to scan.")
    badge_parser.add_argument("--output", default="labcheck-badge.svg", help="Badge SVG output path.")
    badge_parser.add_argument("--config", help="Optional .labcheck.toml config path.")
    pack_parser = subparsers.add_parser(
        "pack",
        help="Create a shareable audit folder with scorecard, target-fit, Markdown, HTML, CSV, JSON, SARIF, and badge outputs.",
    )
    pack_parser.add_argument("target", help="Folder, notebook, zip path, or public GitHub repo URL to scan.")
    pack_parser.add_argument("--output-dir", default="labcheck-audit", help="Directory for generated audit pack files.")
    pack_parser.add_argument("--zip", action="store_true", help="Also create a .zip archive beside the audit pack folder.")
    pack_parser.add_argument("--baseline", help="Optional labcheck baseline JSON. Matching findings are ignored.")
    pack_parser.add_argument("--config", help="Optional .labcheck.toml config path.")
    pack_parser.add_argument(
        "--max-findings",
        type=_parse_max_findings,
        default=DEFAULT_HUMAN_FINDING_LIMIT,
        metavar="N|all",
        help=(
            "Cap detailed findings in Markdown and HTML reports "
            f"(default: {DEFAULT_HUMAN_FINDING_LIMIT}; JSON/SARIF stay complete)."
        ),
    )
    pack_parser.add_argument(
        "--fail-on",
        choices=["none", "low", "medium", "high"],
        default="none",
        help="Exit non-zero after writing the pack if findings exist at or above this severity.",
    )
    pack_parser.add_argument(
        "--min-score",
        type=_parse_min_score,
        metavar="0-100",
        help="Exit non-zero after writing the pack if the overall reproducibility score is below this threshold.",
    )
    demo_repo_parser = subparsers.add_parser(
        "demo-repo",
        help="Create a tiny intentionally broken demo repo for first-run audits.",
    )
    demo_repo_parser.add_argument(
        "--output-dir",
        default="labcheck-demo-repo",
        help="Directory to write the demo repo into.",
    )
    demo_repo_parser.add_argument("--force", action="store_true", help="Overwrite demo files in a non-empty directory.")
    init_parser = subparsers.add_parser("init", help="Create starter labcheck config and GitHub Action workflow.")
    init_parser.add_argument("target", nargs="?", default=".", help="Existing repository directory to initialize.")
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing labcheck config/workflow files.")
    init_parser.add_argument("--no-workflow", action="store_true", help="Only create .labcheck.toml, not a CI workflow.")
    init_parser.add_argument("--policy", action="store_true", help="Also create docs/reproducibility.md with a lab/team handoff policy.")
    graph_parser = subparsers.add_parser("graph", help="Generate provenance graph JSON for a folder, zip, notebook, or public GitHub repo URL.")
    graph_parser.add_argument("target", help="Folder, notebook, zip path, or public GitHub repo URL to scan.")
    graph_parser.add_argument("--output", help="Optional output file path.")
    graph_parser.add_argument("--config", help="Optional .labcheck.toml config path.")
    subparsers.add_parser("version", help="Show version.")
    return parser


def _write_output(content: str, output: str | None) -> None:
    if output:
        Path(output).write_text(content, encoding="utf-8")
        return
    sys.stdout.write(content)
    if not content.endswith("\n"):
        sys.stdout.write("\n")


def _pack_explain_commands(report, limit: int = 3) -> list[str]:
    seen: set[str] = set()
    commands: list[str] = []
    findings = sorted(
        report.findings,
        key=lambda finding: (
            SEVERITY_RANK.get(finding.severity, 99),
            finding.check_id,
            finding.file_path,
        ),
    )
    for finding in findings:
        if finding.check_id in seen:
            continue
        seen.add(finding.check_id)
        commands.append(f"labcheck explain {finding.check_id}")
        if len(commands) >= limit:
            break
    return commands


def _render_pack_index(report, generated_files: list[Path]) -> str:
    lines = [
        "# labcheck Audit Pack",
        "",
        f"- Target: `{report.summary.target}`",
        f"- Overall score: **{report.scores.overall_score}**",
        f"- Findings: **{report.summary.findings_count}**",
        "",
        "## Files",
        "",
    ]
    lines.extend(f"- `{path.name}`" for path in generated_files)
    lines.extend(
        [
            "",
            "## Suggested review order",
            "",
            "1. Open `labcheck-scorecard.md` for the fastest triage summary.",
            "2. Open `labcheck-target-fit.md` before outreach to decide whether the repo has a strong enough hook.",
            "3. Open `labcheck-report.html` or `labcheck-report.md` for the full evidence trail.",
            "4. Review the top risks and remediation plan first.",
            "5. Use `labcheck-report.json` for automation or custom dashboards.",
            "6. Use `labcheck-report.csv` when a lab, founder, or reviewer wants a sortable triage sheet.",
            "7. Use `labcheck-report.sarif` for code-scanning integrations.",
            "8. Use `labcheck-badge.svg` in README files, CI artifacts, or release notes.",
            "9. Use `labcheck-outreach-note.md` as a polite, editable follow-up message.",
            "10. Use `labcheck-issue-draft.md` when opening a maintainer-friendly public issue.",
            "",
            "This pack is generated entirely locally by deterministic checks. No API key or hosted backend is required.",
        ]
    )
    explain_commands = _pack_explain_commands(report)
    if explain_commands:
        lines.extend(
            [
                "",
                "## Understand finding codes",
                "",
                "Run these commands for plain-language context on the top finding codes:",
            ]
        )
        lines.extend(f"- `{command}`" for command in explain_commands)
    return "\n".join(lines)


def _render_pack_manifest(report, generated_files: list[Path]) -> str:
    category_scores = [
        ("Environment rebuildability", report.scores.environment_rebuildability),
        ("Notebook determinism", report.scores.notebook_determinism),
        ("Artifact availability", report.scores.artifact_availability),
        ("Portability", report.scores.portability),
        ("Onboarding readiness", report.scores.onboarding_readiness),
    ]
    lines = [
        "# labcheck Audit Pack Manifest",
        "",
        "## Summary",
        "",
        f"- Target: `{report.summary.target}`",
        f"- Overall score: **{report.scores.overall_score}/100**",
        f"- Findings: **{report.summary.findings_count}**",
        f"- Scope: **{report.summary.notebooks}** notebook(s), **{report.summary.python_files}** Python file(s)",
        f"- labcheck version: `{__version__}`",
        "",
        "## Review Boundary",
        "",
        (
            "This is a static, no-key first-pass audit generated locally. It does not execute the project code "
            "by default, does not upload source files, and does not prove scientific validity. Treat it as a "
            "handoff/readiness signal for reproducibility, onboarding, and rerun risk."
        ),
        "",
        "## Category Scores",
        "",
    ]
    lines.extend(f"- {label}: **{score}/100**" for label, score in category_scores)
    lines.extend(
        [
            "",
            "## Artifact Map",
            "",
            "| File | Purpose |",
            "|---|---|",
        ]
    )
    purposes = {
        "README.md": "Quick index and suggested review order.",
        "MANIFEST.md": "Boundary, contents, score summary, and file map for sharing the pack.",
        "labcheck-scorecard.md": "One-screen handoff summary for PR comments, emails, or lab notes.",
        "labcheck-target-fit.md": "Private go/no-go card for professor, founder, maintainer, or general outreach.",
        "labcheck-outreach-note.md": "Respectful, ready-to-edit follow-up message.",
        "labcheck-issue-draft.md": "Maintainer-friendly issue draft with caveats.",
        "labcheck-report.md": "Full Markdown report with evidence and suggested fixes.",
        "labcheck-report.html": "Full HTML report for easier local review.",
        "labcheck-report.json": "Machine-readable report payload.",
        "labcheck-report.csv": "Spreadsheet-friendly findings table for triage and assignment.",
        "labcheck-report.sarif": "SARIF report for code-scanning integrations.",
        "labcheck-badge.svg": "Embeddable score badge.",
    }
    for path in generated_files:
        purpose = purposes.get(path.name, "Generated labcheck artifact.")
        lines.append(f"| `{path.name}` | {purpose} |")
    lines.extend(
        [
            "",
            "## Suggested Sharing Path",
            "",
            "1. Read `labcheck-target-fit.md` privately before deciding whether to send outreach.",
            "2. Send `labcheck-scorecard.md` when the recipient needs the shortest summary.",
            "3. Attach the zip or folder when they ask for the full evidence trail.",
            "4. Point maintainers to `labcheck-issue-draft.md` only after checking that the tone and scope fit.",
            "5. Use `labcheck-report.csv` for spreadsheet triage, assignment, or lab handoff tracking.",
            "6. Use `labcheck-report.json` or `labcheck-report.sarif` for automation, dashboards, or CI ingestion.",
            "",
            "Generated by `labcheck` with deterministic local checks. No API key or hosted backend was used.",
        ]
    )
    return "\n".join(lines)


def _write_pack(report, output_dir: str, max_findings: int | None) -> list[Path]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    files = [
        (destination / "labcheck-scorecard.md", render_scorecard(report)),
        (destination / "labcheck-target-fit.md", render_target_fit(report)),
        (destination / "labcheck-outreach-note.md", render_outreach_note(report)),
        (destination / "labcheck-report.md", render_markdown(report, max_findings=max_findings)),
        (destination / "labcheck-report.html", render_html(report, max_findings=max_findings)),
        (destination / "labcheck-report.json", render_json(report)),
        (destination / "labcheck-report.csv", render_csv(report)),
        (destination / "labcheck-report.sarif", render_sarif(report)),
        (destination / "labcheck-badge.svg", render_badge(report)),
        (destination / "labcheck-issue-draft.md", render_issue_draft(report)),
    ]
    generated_paths: list[Path] = []
    for path, content in files:
        path.write_text(content, encoding="utf-8")
        generated_paths.append(path)
    manifest_path = destination / "MANIFEST.md"
    index_path = destination / "README.md"
    manifest_path.write_text(
        _render_pack_manifest(report, generated_paths + [manifest_path, index_path]),
        encoding="utf-8",
    )
    generated_paths.append(manifest_path)
    index_path.write_text(_render_pack_index(report, generated_paths), encoding="utf-8")
    generated_paths.append(index_path)
    return generated_paths


def _write_pack_zip(output_dir: str) -> Path:
    source_dir = Path(output_dir)
    zip_path = source_dir.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                archive.write(path, Path(source_dir.name) / path.relative_to(source_dir))
    return zip_path


def _blocking_findings_count(report, fail_on: str) -> int:
    if fail_on == "none":
        return 0
    threshold = SEVERITY_RANK[fail_on]
    return sum(1 for finding in report.findings if SEVERITY_RANK.get(finding.severity, 99) <= threshold)


def _gate_report(report, fail_on: str, min_score: int | None) -> int:
    blocking_count = _blocking_findings_count(report, fail_on)
    if blocking_count:
        sys.stderr.write(f"labcheck found {blocking_count} finding(s) at or above {fail_on} severity.\n")
        return 2
    if min_score is not None and report.scores.overall_score < min_score:
        sys.stderr.write(
            f"labcheck score {report.scores.overall_score} is below minimum required score {min_score}.\n"
        )
        return 2
    return 0


def _check_matches_search(check: CheckDefinition, search: str) -> bool:
    haystack = " ".join(
        [
            check.check_id,
            check.title,
            check.default_severity,
            check.category,
            check.detects,
            check.why_it_matters,
            check.suggested_fix,
        ]
    ).lower()
    return search.lower() in haystack


def _render_checks(
    *,
    category: str | None = None,
    severity: str | None = None,
    search: str | None = None,
) -> str:
    search_term = search.strip() if search else None
    checks = [
        check
        for check in CHECKS
        if (category is None or check.category == category)
        and (severity is None or check.default_severity == severity)
        and (search_term is None or _check_matches_search(check, search_term))
    ]
    filter_labels = []
    if category:
        filter_labels.append(f"category={category}")
    if severity:
        filter_labels.append(f"severity={severity}")
    if search_term:
        filter_labels.append(f'search="{search_term}"')
    title = "Supported checks:"
    if filter_labels:
        title = f"Supported checks ({', '.join(filter_labels)}):"
    lines = [title]
    if not checks:
        lines.append("- No checks matched these filters.")
    for check in checks:
        lines.append(
            f"- {check.check_id} [{check.default_severity}/{check.category}] {check.title}"
        )
    lines.append("")
    lines.append("Browse subsets with `labcheck checks --category determinism`, `--severity high`, or `--search seed`.")
    lines.append("Run `labcheck explain LC005` for remediation details.")
    return "\n".join(lines)


def _check_explanation_payload(check: CheckDefinition) -> dict[str, str]:
    return {
        "check_id": check.check_id,
        "title": check.title,
        "default_severity": check.default_severity,
        "category": check.category,
        "detects": check.detects,
        "why_it_matters": check.why_it_matters,
        "suggested_fix": check.suggested_fix,
        "related_command": f"labcheck checks --category {check.category}",
    }


def _render_check_explanation(check_id: str, output_format: str = "text") -> str | None:
    check = get_check(check_id)
    if not check:
        return None
    if output_format == "json":
        return json.dumps(_check_explanation_payload(check), indent=2)
    if output_format == "markdown":
        return "\n".join(
            [
                f"# {check.check_id} - {check.title}",
                "",
                f"- Default severity: `{check.default_severity}`",
                f"- Category: `{check.category}`",
                "",
                "## Detects",
                check.detects,
                "",
                "## Why It Matters",
                check.why_it_matters,
                "",
                "## Suggested Fix",
                check.suggested_fix,
                "",
                "## Related Checks",
                f"Browse nearby checks with `labcheck checks --category {check.category}`.",
            ]
        )
    return "\n".join(
        [
            f"{check.check_id} - {check.title}",
            f"Default severity: {check.default_severity}",
            f"Category: {check.category}",
            f"Detects: {check.detects}",
            f"Why it matters: {check.why_it_matters}",
            f"Suggested fix: {check.suggested_fix}",
        ]
    )


def _describe_target_path(path: Path) -> str:
    resolved = path.expanduser().resolve()
    if resolved.is_dir():
        return f"{resolved} (directory)"
    if resolved.is_file():
        if resolved.suffix.lower() == ".zip":
            return f"{resolved} (zip archive)"
        return f"{resolved} (file)"
    return str(resolved)


def _doctor_default_config_path(target: str) -> Path:
    path = Path(target).expanduser()
    if path.is_dir():
        return path / ".labcheck.toml"
    if path.is_file():
        return path.parent / ".labcheck.toml"
    return Path(".labcheck.toml")


def _render_doctor(target: str, config: str | None) -> tuple[str, int]:
    lines = ["labcheck doctor", ""]
    failures = 0

    def add(status: str, label: str, detail: str) -> None:
        lines.append(f"{status:<4} {label}: {detail}")

    add("OK", "labcheck version", __version__)

    python_version = ".".join(str(part) for part in sys.version_info[:3])
    if sys.version_info >= (3, 11):
        add("OK", "Python runtime", python_version)
    else:
        failures += 1
        add("FAIL", "Python runtime", f"{python_version}; labcheck requires Python 3.11+")

    raw_target = target.strip()
    if is_github_repo_url(raw_target):
        add("OK", "target", f"{raw_target} (public GitHub repo URL)")
    else:
        target_path = Path(raw_target).expanduser()
        if target_path.exists():
            add("OK", "target", _describe_target_path(target_path))
        else:
            failures += 1
            add("FAIL", "target", f"{target_path} does not exist")

    config_path = Path(config).expanduser() if config else _doctor_default_config_path(raw_target)
    if config_path.exists():
        add("OK", "config", str(config_path.resolve()))
    elif config:
        failures += 1
        add("FAIL", "config", f"{config_path} does not exist")
    else:
        add("WARN", "config", "no .labcheck.toml found; defaults will be used")

    if CHECKS:
        add("OK", "checks registered", str(len(CHECKS)))
    else:
        failures += 1
        add("FAIL", "checks registered", "no checks are available")

    lines.append("")
    if failures:
        lines.append("Fix the failing preflight item(s), then rerun `labcheck doctor`.")
        return "\n".join(lines), 2

    if config_path.exists():
        lines.append(f"Next: labcheck scan {target} --config {config_path}")
    else:
        lines.append(f"Next: labcheck scan {target}")
    return "\n".join(lines), 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "version":
        sys.stdout.write(f"{__version__}\n")
        return 0

    if args.command == "checks":
        _write_output(
            _render_checks(category=args.category, severity=args.severity, search=args.search),
            None,
        )
        return 0

    if args.command == "explain":
        explanation = _render_check_explanation(args.check_id, args.format)
        if explanation is None:
            sys.stderr.write(f"Unknown labcheck finding code: {args.check_id}\n")
            sys.stderr.write("Run `labcheck checks` to list supported checks.\n")
            return 2
        _write_output(explanation, None)
        return 0

    if args.command == "doctor":
        content, exit_code = _render_doctor(args.target, args.config)
        _write_output(content, None)
        return exit_code

    if args.command == "graph":
        report = scan_path(args.target, config_path=args.config)
        _write_output(render_json(report), args.output)
        return 0

    if args.command == "baseline":
        report = scan_path(args.target, config_path=args.config)
        baseline = json.dumps(build_baseline(report), indent=2)
        _write_output(baseline, args.output)
        return 0

    if args.command == "compare":
        try:
            comparison = build_comparison(
                load_report_json(args.before_json),
                load_report_json(args.after_json),
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            sys.stderr.write(f"Could not compare labcheck reports: {exc}\n")
            return 2
        content = (
            render_comparison_json(comparison)
            if args.format == "json"
            else render_comparison_markdown(comparison)
        )
        _write_output(content, args.output)
        return 0

    if args.command == "badge":
        report = scan_path(args.target, config_path=args.config)
        _write_output(render_badge(report), args.output)
        return 0

    if args.command == "scorecard":
        report = scan_path(args.target, config_path=args.config)
        if args.baseline:
            report = filter_baselined_findings(report, load_baseline(args.baseline))
        _write_output(render_scorecard(report), args.output)
        return 0

    if args.command == "target-fit":
        report = scan_path(args.target, config_path=args.config)
        if args.baseline:
            report = filter_baselined_findings(report, load_baseline(args.baseline))
        _write_output(render_target_fit(report, audience=args.audience), args.output)
        return 0

    if args.command == "outreach":
        report = scan_path(args.target, config_path=args.config)
        if args.baseline:
            report = filter_baselined_findings(report, load_baseline(args.baseline))
        _write_output(
            render_outreach_note(
                report,
                recipient=args.recipient,
                sender=args.sender,
                audience=args.audience,
            ),
            args.output,
        )
        return 0

    if args.command == "issue":
        report = scan_path(args.target, config_path=args.config)
        if args.baseline:
            report = filter_baselined_findings(report, load_baseline(args.baseline))
        _write_output(render_issue_draft(report), args.output)
        return 0

    if args.command == "demo-link":
        try:
            link = build_demo_link(args.target, args.base_url, args.auto_audit, args.audience)
        except ValueError as exc:
            sys.stderr.write(f"{exc}\n")
            return 2
        _write_output(render_demo_link(link, args.format), args.output)
        return 0

    if args.command == "demo-repo":
        output_dir = Path(args.output_dir)
        output_root = output_dir.expanduser()
        try:
            written = write_demo_repo(output_root, force=args.force)
        except FileExistsError as exc:
            sys.stderr.write(f"{exc}\n")
            return 2
        lines = [
            f"Wrote labcheck demo repo to {output_dir}",
            "",
            "Next:",
            f"  labcheck doctor {output_dir}",
            f"  labcheck scorecard {output_dir}",
            f"  labcheck scan {output_dir} --format markdown",
            "",
            "Files:",
        ]
        lines.extend(f"- {path.relative_to(output_root).as_posix()}" for path in written)
        _write_output("\n".join(lines), None)
        return 0

    if args.command == "pack":
        report = scan_path(args.target, config_path=args.config)
        if args.baseline:
            report = filter_baselined_findings(report, load_baseline(args.baseline))
        generated_paths = _write_pack(report, args.output_dir, args.max_findings)
        zip_path = _write_pack_zip(args.output_dir) if args.zip else None
        lines = [
            f"Wrote labcheck audit pack to {Path(args.output_dir)}",
            f"Overall score: {report.scores.overall_score}",
            f"Findings: {report.summary.findings_count}",
        ]
        lines.extend(f"created {path.name}" for path in generated_paths)
        if zip_path:
            lines.append(f"created {zip_path.name}")
        _write_output("\n".join(lines), None)
        return _gate_report(report, args.fail_on, args.min_score)

    if args.command == "init":
        result = init_project(
            Path(args.target),
            force=args.force,
            include_workflow=not args.no_workflow,
            include_policy=args.policy,
        )
        lines = [f"Initialized labcheck in {result.root}"]
        lines.extend(f"created {path.relative_to(result.root).as_posix()}" for path in result.created)
        lines.extend(f"skipped {path.relative_to(result.root).as_posix()} (already exists)" for path in result.skipped)
        lines.append("Next: labcheck scan . --config .labcheck.toml")
        if result.skipped and not args.force:
            lines.append("Use --force to overwrite existing labcheck files.")
        _write_output("\n".join(lines), None)
        return 0

    report = scan_path(args.target, config_path=args.config)
    if args.baseline:
        report = filter_baselined_findings(report, load_baseline(args.baseline))
    if args.format == "json":
        content = render_json(report)
    elif args.format == "csv":
        content = render_csv(report)
    elif args.format == "html":
        content = render_html(report, max_findings=args.max_findings)
    elif args.format == "markdown":
        content = render_markdown(report, max_findings=args.max_findings)
    elif args.format == "sarif":
        content = render_sarif(report)
    else:
        content = render_text(report, max_findings=args.max_findings)
    _write_output(content, args.output)
    if args.json_output:
        _write_output(render_json(report), args.json_output)
    if args.csv_output:
        _write_output(render_csv(report), args.csv_output)
    if args.sarif_output:
        _write_output(render_sarif(report), args.sarif_output)
    if args.badge_output:
        _write_output(render_badge(report), args.badge_output)
    if args.scorecard_output:
        _write_output(render_scorecard(report), args.scorecard_output)
    if args.target_fit_output:
        _write_output(render_target_fit(report), args.target_fit_output)
    if args.issue_output:
        _write_output(render_issue_draft(report), args.issue_output)

    return _gate_report(report, args.fail_on, args.min_score)


if __name__ == "__main__":
    raise SystemExit(main())
