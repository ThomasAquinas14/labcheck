from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import zipfile

from . import __version__
from .baseline import build_baseline, filter_baselined_findings, load_baseline
from .check_catalog import CHECKS, get_check
from .init_project import init_project
from .loaders import is_github_repo_url
from .reporters import (
    DEFAULT_HUMAN_FINDING_LIMIT,
    render_badge,
    render_html,
    render_json,
    render_markdown,
    render_scorecard,
    render_sarif,
    render_text,
)
from .scanner import scan_path

SEVERITY_RANK = {
    "none": 99,
    "low": 2,
    "medium": 1,
    "high": 0,
}


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
    scan_parser.add_argument("--format", choices=["text", "markdown", "json", "html", "sarif"], default="text")
    scan_parser.add_argument("--output", help="Optional output file path.")
    scan_parser.add_argument("--json-output", help="Optional machine-readable JSON output file path.")
    scan_parser.add_argument("--sarif-output", help="Optional SARIF output file path for code-scanning integrations.")
    scan_parser.add_argument("--badge-output", help="Optional static SVG score badge output path.")
    scan_parser.add_argument("--scorecard-output", help="Optional compact Markdown scorecard output path.")
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

    subparsers.add_parser("checks", help="List supported checks.")
    explain_parser = subparsers.add_parser("explain", help="Explain a labcheck finding code.")
    explain_parser.add_argument("check_id", help="Finding code to explain, for example LC005.")
    baseline_parser = subparsers.add_parser("baseline", help="Create a labcheck baseline from the current findings.")
    baseline_parser.add_argument("target", help="Folder, notebook, zip path, or public GitHub repo URL to scan.")
    baseline_parser.add_argument("--output", default=".labcheck-baseline.json", help="Baseline output path.")
    baseline_parser.add_argument("--config", help="Optional .labcheck.toml config path.")
    badge_parser = subparsers.add_parser("badge", help="Generate a static SVG labcheck score badge.")
    badge_parser.add_argument("target", help="Folder, notebook, zip path, or public GitHub repo URL to scan.")
    badge_parser.add_argument("--output", default="labcheck-badge.svg", help="Badge SVG output path.")
    badge_parser.add_argument("--config", help="Optional .labcheck.toml config path.")
    pack_parser = subparsers.add_parser(
        "pack",
        help="Create a shareable audit folder with scorecard, Markdown, HTML, JSON, SARIF, and badge outputs.",
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
            "2. Open `labcheck-report.html` or `labcheck-report.md` for the full evidence trail.",
            "3. Review the top risks and remediation plan first.",
            "4. Use `labcheck-report.json` for automation or custom dashboards.",
            "5. Use `labcheck-report.sarif` for code-scanning integrations.",
            "6. Use `labcheck-badge.svg` in README files, CI artifacts, or release notes.",
            "",
            "This pack is generated entirely locally by deterministic checks. No API key or hosted backend is required.",
        ]
    )
    return "\n".join(lines)


def _write_pack(report, output_dir: str, max_findings: int | None) -> list[Path]:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    files = [
        (destination / "labcheck-scorecard.md", render_scorecard(report)),
        (destination / "labcheck-report.md", render_markdown(report, max_findings=max_findings)),
        (destination / "labcheck-report.html", render_html(report, max_findings=max_findings)),
        (destination / "labcheck-report.json", render_json(report)),
        (destination / "labcheck-report.sarif", render_sarif(report)),
        (destination / "labcheck-badge.svg", render_badge(report)),
    ]
    generated_paths: list[Path] = []
    for path, content in files:
        path.write_text(content, encoding="utf-8")
        generated_paths.append(path)
    index_path = destination / "README.md"
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


def _render_checks() -> str:
    lines = ["Supported checks:"]
    for check in CHECKS:
        lines.append(
            f"- {check.check_id} [{check.default_severity}/{check.category}] {check.title}"
        )
    lines.append("")
    lines.append("Run `labcheck explain LC005` for remediation details.")
    return "\n".join(lines)


def _render_check_explanation(check_id: str) -> str | None:
    check = get_check(check_id)
    if not check:
        return None
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
        _write_output(_render_checks(), None)
        return 0

    if args.command == "explain":
        explanation = _render_check_explanation(args.check_id)
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
    if args.sarif_output:
        _write_output(render_sarif(report), args.sarif_output)
    if args.badge_output:
        _write_output(render_badge(report), args.badge_output)
    if args.scorecard_output:
        _write_output(render_scorecard(report), args.scorecard_output)

    return _gate_report(report, args.fail_on, args.min_score)


if __name__ == "__main__":
    raise SystemExit(main())
