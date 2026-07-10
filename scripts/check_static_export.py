from __future__ import annotations

from pathlib import Path
import sys


DEFAULT_EXPORT_DIR = Path("dist/site")
LOCAL_WORKSPACE_PARTS = ("Users", "hp")
LOCAL_WINDOWS_USER_PATH = "C:" + "\\" + "\\".join(LOCAL_WORKSPACE_PARTS) + "\\"
LOCAL_POSIX_USER_PATH = "C:/" + "/".join(LOCAL_WORKSPACE_PARTS) + "/"

REQUIRED_EXPORT_FILES = [
    "index.html",
    "demo.html",
    "README.md",
    "LICENSE",
    "CITATION.cff",
    "robots.txt",
    "sitemap.xml",
    "llms.txt",
    ".nojekyll",
    "docs/privacy-and-safety.md",
    "docs/public-triage-board.md",
    "docs/maintainer-reply-templates.md",
    "docs/launch-post-after-action.md",
    "docs/public-deploy-guide.md",
    "docs/issue-labels.md",
    "docs/reply-derived-case-study-seed.md",
    "docs/reply-to-case-study-checklist.md",
    "docs/sample-audits/broken-repo-audit.html",
    "docs/sample-audits/broken-repo-scorecard.md",
    "docs/sample-audits/broken-repo-issue-draft.md",
    "docs/sample-audits/broken-repo-labeled-issue.md",
    "docs/sample-audits/broken-repo-outreach-note.md",
]

FORBIDDEN_EXPORT_TEXT = [
    LOCAL_WINDOWS_USER_PATH,
    LOCAL_POSIX_USER_PATH,
    "legacy ai",
    'href="../README.md"',
    'href="../docs/',
    'href="./demo.html"',
]


def check_static_export(export_dir: Path = DEFAULT_EXPORT_DIR) -> list[str]:
    """Return static-export problems that would make the public site unsafe or incomplete."""
    resolved_export_dir = export_dir.resolve()
    problems: list[str] = []
    if not resolved_export_dir.exists():
        return [f"static export directory does not exist: {export_dir}"]
    if not resolved_export_dir.is_dir():
        return [f"static export path is not a directory: {export_dir}"]

    for relative_path in REQUIRED_EXPORT_FILES:
        path = resolved_export_dir / relative_path
        if not path.exists():
            problems.append(f"missing required static export file: {relative_path}")

    text_files = [
        path
        for path in resolved_export_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".html", ".md", ".txt", ".xml", ".cff", ".svg"}
    ]
    for path in text_files:
        relative_path = path.relative_to(resolved_export_dir).as_posix()
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            problems.append(f"static export text file is not utf-8: {relative_path}")
            continue
        for forbidden in FORBIDDEN_EXPORT_TEXT:
            if forbidden in content:
                problems.append(f"forbidden public-export text in {relative_path}: {forbidden}")

    return problems


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) > 1:
        print("Usage: python scripts/check_static_export.py [export-dir]", file=sys.stderr)
        return 2
    export_dir = Path(args[0]) if args else DEFAULT_EXPORT_DIR
    problems = check_static_export(export_dir)
    if problems:
        print("labcheck static export check failed:", file=sys.stderr)
        for problem in problems:
            print(f"- {problem}", file=sys.stderr)
        return 1
    print(f"labcheck static export OK: {export_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
