from __future__ import annotations

from pathlib import Path
import fnmatch
import re
import sys
import tomllib


REQUIRED_FILES = [
    ".github/ISSUE_TEMPLATE/audit_request.yml",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/case_study.yml",
    ".github/ISSUE_TEMPLATE/check_proposal.yml",
    ".github/labels.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/workflows/ci.yml",
    ".github/workflows/pages.yml",
    ".gitattributes",
    ".gitignore",
    ".labcheck.toml",
    "CITATION.cff",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "README.md",
    "SECURITY.md",
    "SUPPORT.md",
    "action.yml",
    "docs/assets/scorecard-preview.svg",
    "docs/case-studies.md",
    "docs/comparison.md",
    "docs/demo-video-script.md",
    "docs/faq.md",
    "docs/first-audit.md",
    "docs/good-first-issues.md",
    "docs/github-publish-guide.md",
    "docs/github-action.md",
    "docs/install.md",
    "docs/issue-labels.md",
    "docs/lab-adoption-guide.md",
    "docs/launch-kit.md",
    "docs/launch-post-after-action.md",
    "docs/launch-week-plan.md",
    "docs/maintainer-reply-templates.md",
    "docs/outreach-playbook.md",
    "docs/outreach-tracker-template.md",
    "docs/privacy-and-safety.md",
    "docs/public-triage-board.md",
    "docs/public-deploy-guide.md",
    "docs/release-checklist.md",
    "docs/reply-derived-case-study-seed.md",
    "docs/reply-to-case-study-checklist.md",
    "docs/reproducibility-patterns.md",
    "docs/roadmap.md",
    "docs/scoring-guide.md",
    "docs/sample-audits/broken-repo-audit.html",
    "docs/sample-audits/broken-repo-audit.md",
    "docs/sample-audits/broken-repo-issue-draft.md",
    "docs/sample-audits/broken-repo-labeled-issue.md",
    "docs/sample-audits/broken-repo-outreach-note.md",
    "docs/sample-audits/broken-repo-scorecard.md",
    "docs/sample-audits/broken-repo-target-fit.md",
    "docs/sample-audits/handson-ml3-audit.md",
    "docs/sample-audits/python-data-science-handbook-audit.md",
    "examples/broken-repo.zip",
    "pyproject.toml",
    "scripts/build_sample_audits.py",
    "scripts/build_static_site.py",
    "scripts/check_compare_smoke.py",
    "scripts/check_public_urls.py",
    "scripts/check_static_export.py",
    "scripts/check_launch_hygiene.py",
    "scripts/check_publish_ready.py",
    "scripts/export_standalone_repo.py",
    "scripts/release_check.py",
    "site/demo.html",
    "site/index.html",
    "site/llms.txt",
    "site/robots.txt",
    "site/sitemap.xml",
    "src/labcheck/cli.py",
    "tests/test_publish_ready.py",
    "tests/test_static_export.py",
    "tests/test_static_site.py",
    "tests/test_standalone_export.py",
]

REQUIRED_IGNORE_PATTERNS = [
    ".env",
    ".env.*",
    "!.env.example",
    "!.env.sample",
    "!.env.template",
    "*.pem",
    ".pytest_cache/",
    "__pycache__/",
    "*.egg-info/",
    ".coverage",
    "htmlcov/",
    "build/",
    "node_modules/",
    ".venv/",
    "venv/",
    "labcheck-report.*",
    "labcheck-audit/",
    "labcheck-audit.zip",
    ".tmp-*",
    "dist/",
]

DANGEROUS_PUBLIC_PATTERNS = [
    ".env",
    ".env.*",
    "*.pem",
    "*private-key*",
    "*secret*",
]
SAFE_ENV_EXAMPLE_FILES = {
    ".env.example",
    ".env.sample",
    ".env.template",
}

EXPECTED_PACKAGE_URLS = {
    "Homepage": "https://thomasaquinas14.github.io/labcheck/",
    "Documentation": "https://thomasaquinas14.github.io/labcheck/README.md",
    "Repository": "https://github.com/ThomasAquinas14/labcheck",
    "Issues": "https://github.com/ThomasAquinas14/labcheck/issues",
    "Demo": "https://thomasaquinas14.github.io/labcheck/demo.html",
    "Safety": "https://thomasaquinas14.github.io/labcheck/docs/privacy-and-safety.md",
}

REQUIRED_PACKAGE_KEYWORDS = {
    "reproducibility",
    "jupyter-notebook",
    "machine-learning",
    "research-software",
    "static-analysis",
    "github-action",
}

STALE_PUBLIC_COPY_PATTERNS = {
    "README.md": [
        ("CI usage later", "CI usage now"),
    ],
}

SAMPLE_SCORECARD_PATTERN = re.compile(
    r"Overall score: \*\*(?P<score>\d+)/100\*\*[\s\S]*?"
    r"Findings: \*\*(?P<count>\d+)\*\* \(`(?P<high>\d+)` high, `(?P<medium>\d+)` medium, `(?P<low>\d+)` low\)"
)

PUBLIC_CASE_STUDY_AUDITS = [
    "docs/sample-audits/handson-ml3-audit.md",
    "docs/sample-audits/python-data-science-handbook-audit.md",
]


def _read_gitignore(repo_root: Path) -> list[str]:
    gitignore = repo_root / ".gitignore"
    if not gitignore.exists():
        return []
    return [
        line.strip()
        for line in gitignore.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _matches_pattern(path: str, pattern: str) -> bool:
    normalized_pattern = pattern.rstrip("/")
    if pattern.endswith("/"):
        if "/" not in normalized_pattern:
            return normalized_pattern in Path(path).parts
        return path == normalized_pattern or path.startswith(f"{normalized_pattern}/")
    return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(Path(path).name, pattern)


def _is_ignored(path: str, ignore_patterns: list[str]) -> bool:
    ignored = False
    for pattern in ignore_patterns:
        if pattern.startswith("!"):
            if _matches_pattern(path, pattern[1:]):
                ignored = False
            continue
        if _matches_pattern(path, pattern):
            ignored = True
    return ignored


def _sample_scorecard_metrics(repo_root: Path) -> dict[str, str] | None:
    scorecard = repo_root / "docs" / "sample-audits" / "broken-repo-scorecard.md"
    if not scorecard.exists():
        return None
    match = SAMPLE_SCORECARD_PATTERN.search(scorecard.read_text(encoding="utf-8"))
    if not match:
        return None
    return match.groupdict()


def _check_sample_metric_copy(repo_root: Path, issues: list[str]) -> None:
    metrics = _sample_scorecard_metrics(repo_root)
    if not metrics:
        return

    expected = {
        "readme_score": f"Overall score: {metrics['score']}/100",
        "readme_findings": (
            f"Findings: {metrics['count']} "
            f"({metrics['high']} high, {metrics['medium']} medium, {metrics['low']} low)"
        ),
        "readme_triage": f"fix {metrics['high']} high-severity findings",
        "landing_score": f'<div class="score">{metrics["score"]}</div>',
        "landing_high": f"{metrics['high']} high-severity findings",
        "landing_medium": f"{metrics['medium']} medium-severity findings",
        "landing_total": f"{metrics['count']} total findings",
        "preview_score": f">{metrics['score']}</text>",
    }
    files_to_check = {
        "README.md": ["readme_score", "readme_findings", "readme_triage"],
        "site/index.html": ["landing_score", "landing_high", "landing_medium", "landing_total"],
        "docs/assets/scorecard-preview.svg": ["preview_score"],
    }
    for relative_path, expectation_keys in files_to_check.items():
        path = repo_root / relative_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for key in expectation_keys:
            if expected[key] not in text:
                issues.append(
                    f"{relative_path} sample metric copy is stale; expected to include {expected[key]!r}"
                )


def _check_package_metadata(repo_root: Path, issues: list[str]) -> None:
    pyproject = repo_root / "pyproject.toml"
    if not pyproject.exists():
        return
    try:
        project = tomllib.loads(pyproject.read_text(encoding="utf-8")).get("project", {})
    except tomllib.TOMLDecodeError as exc:
        issues.append(f"pyproject.toml is not valid TOML: {exc}")
        return

    expected_description = "No-key reproducibility audits for notebook-heavy research and ML repositories."
    if project.get("description") != expected_description:
        issues.append("pyproject.toml description does not match the public launch positioning")

    keywords = set(project.get("keywords", []))
    missing_keywords = sorted(REQUIRED_PACKAGE_KEYWORDS - keywords)
    if missing_keywords:
        issues.append(f"pyproject.toml is missing package keyword(s): {', '.join(missing_keywords)}")

    urls = project.get("urls", {})
    for label, expected_url in EXPECTED_PACKAGE_URLS.items():
        if urls.get(label) != expected_url:
            issues.append(f"pyproject.toml project.urls.{label} should be {expected_url!r}")


def _check_public_case_study_path_style(repo_root: Path, issues: list[str]) -> None:
    for relative_path in PUBLIC_CASE_STUDY_AUDITS:
        path = repo_root / relative_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if "\\" in text:
            issues.append(
                f"{relative_path} contains Windows-style path separators; use POSIX-style '/' paths in public audit snapshots"
            )


def _check_static_discovery_metadata(repo_root: Path, issues: list[str]) -> None:
    expected_pages = {
        "site/index.html": '"@type": "SoftwareApplication"',
        "site/demo.html": '"@type": "WebApplication"',
    }
    for relative_path, expected_schema_type in expected_pages.items():
        path = repo_root / relative_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if 'type="application/ld+json"' not in text:
            issues.append(f"{relative_path} is missing JSON-LD structured data")
            continue
        if expected_schema_type not in text:
            issues.append(f"{relative_path} JSON-LD is missing {expected_schema_type}")


def check_launch_hygiene(repo_root: Path) -> list[str]:
    """Return launch-readiness issues that should be fixed before publishing."""
    issues: list[str] = []
    ignore_patterns = _read_gitignore(repo_root)

    for required_file in REQUIRED_FILES:
        if not (repo_root / required_file).exists():
            issues.append(f"missing required launch file: {required_file}")

    for required_pattern in REQUIRED_IGNORE_PATTERNS:
        if required_pattern not in ignore_patterns:
            issues.append(f".gitignore is missing required pattern: {required_pattern}")

    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(repo_root).as_posix()
        if _is_ignored(relative, ignore_patterns):
            continue
        if Path(relative).name in SAFE_ENV_EXAMPLE_FILES:
            continue
        if any(_matches_pattern(relative, pattern) for pattern in DANGEROUS_PUBLIC_PATTERNS):
            issues.append(f"dangerous unignored file matches public-risk pattern: {relative}")

    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    if "docs/assets/scorecard-preview.svg" not in readme:
        issues.append("README.md does not embed the scorecard preview SVG")
    if "No paid APIs. No inference bill. No backend secret to protect." not in readme:
        issues.append("README.md does not clearly state the no-key public-hosting promise")

    for relative_path, stale_phrases in STALE_PUBLIC_COPY_PATTERNS.items():
        text = (repo_root / relative_path).read_text(encoding="utf-8")
        for stale_phrase, replacement in stale_phrases:
            if stale_phrase in text:
                issues.append(
                    f"{relative_path} contains stale public copy {stale_phrase!r}; use {replacement!r}"
                )

    _check_sample_metric_copy(repo_root, issues)
    _check_package_metadata(repo_root, issues)
    _check_public_case_study_path_style(repo_root, issues)
    _check_static_discovery_metadata(repo_root, issues)

    launch_kit = (repo_root / "docs" / "launch-kit.md").read_text(encoding="utf-8")
    for expected in ["Repository name", "Description", "Topics", "Professor Outreach", "Founder Outreach"]:
        if expected not in launch_kit:
            issues.append(f"docs/launch-kit.md is missing launch section: {expected}")

    return issues


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    issues = check_launch_hygiene(repo_root)
    if issues:
        print("labcheck launch hygiene failed:", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1
    print("labcheck launch hygiene OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
