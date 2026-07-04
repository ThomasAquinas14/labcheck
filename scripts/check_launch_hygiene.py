from __future__ import annotations

from pathlib import Path
import fnmatch
import sys


REQUIRED_FILES = [
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/case_study.yml",
    ".github/ISSUE_TEMPLATE/check_proposal.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/workflows/ci.yml",
    ".github/workflows/pages.yml",
    ".gitignore",
    ".labcheck.toml",
    "CITATION.cff",
    "CONTRIBUTING.md",
    "LICENSE",
    "README.md",
    "SECURITY.md",
    "action.yml",
    "docs/assets/scorecard-preview.svg",
    "docs/case-studies.md",
    "docs/github-action.md",
    "docs/lab-adoption-guide.md",
    "docs/launch-kit.md",
    "docs/outreach-playbook.md",
    "docs/public-deploy-guide.md",
    "docs/release-checklist.md",
    "docs/sample-audits/broken-repo-audit.html",
    "docs/sample-audits/broken-repo-audit.md",
    "docs/sample-audits/broken-repo-scorecard.md",
    "examples/broken-repo.zip",
    "pyproject.toml",
    "scripts/build_sample_audits.py",
    "scripts/build_static_site.py",
    "scripts/check_launch_hygiene.py",
    "scripts/export_standalone_repo.py",
    "scripts/release_check.py",
    "site/demo.html",
    "site/index.html",
    "src/labcheck/cli.py",
    "tests/test_static_export.py",
    "tests/test_static_site.py",
    "tests/test_standalone_export.py",
]

REQUIRED_IGNORE_PATTERNS = [
    ".env",
    ".env.*",
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


def _read_gitignore(repo_root: Path) -> set[str]:
    gitignore = repo_root / ".gitignore"
    if not gitignore.exists():
        return set()
    return {
        line.strip()
        for line in gitignore.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def _matches_pattern(path: str, pattern: str) -> bool:
    normalized_pattern = pattern.rstrip("/")
    if pattern.endswith("/"):
        if "/" not in normalized_pattern:
            return normalized_pattern in Path(path).parts
        return path == normalized_pattern or path.startswith(f"{normalized_pattern}/")
    return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(Path(path).name, pattern)


def _is_ignored(path: str, ignore_patterns: set[str]) -> bool:
    return any(_matches_pattern(path, pattern) for pattern in ignore_patterns)


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
        if any(_matches_pattern(relative, pattern) for pattern in DANGEROUS_PUBLIC_PATTERNS):
            issues.append(f"dangerous unignored file matches public-risk pattern: {relative}")

    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    if "docs/assets/scorecard-preview.svg" not in readme:
        issues.append("README.md does not embed the scorecard preview SVG")
    if "No paid APIs. No inference bill. No backend secret to protect." not in readme:
        issues.append("README.md does not clearly state the no-key public-hosting promise")

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
