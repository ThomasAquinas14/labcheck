from __future__ import annotations

from pathlib import Path
import shutil


DEFAULT_OUTPUT_DIR = Path("dist/site")

LINK_REWRITES = {
    'href="../README.md"': 'href="README.md"',
    'href="../CITATION.cff"': 'href="CITATION.cff"',
    'href="./demo.html"': 'href="demo.html"',
    'href="../docs/': 'href="docs/',
}

README_REWRITES = {
    "](site/index.html)": "](index.html)",
    "](site/demo.html)": "](demo.html)",
}

DOC_REWRITES = {
    "](../site/index.html)": "](../index.html)",
    "](../site/demo.html)": "](../demo.html)",
}

DOC_FILES = [
    "case-studies.md",
    "comparison.md",
    "demo-video-script.md",
    "faq.md",
    "first-audit.md",
    "good-first-issues.md",
    "github-publish-guide.md",
    "github-action.md",
    "install.md",
    "issue-labels.md",
    "lab-adoption-guide.md",
    "launch-kit.md",
    "launch-post-after-action.md",
    "launch-week-plan.md",
    "maintainer-reply-templates.md",
    "outreach-playbook.md",
    "outreach-tracker-template.md",
    "privacy-and-safety.md",
    "public-triage-board.md",
    "public-deploy-guide.md",
    "release-checklist.md",
    "reply-derived-case-study-seed.md",
    "reply-to-case-study-checklist.md",
    "reproducibility-patterns.md",
    "roadmap.md",
    "scoring-guide.md",
]

ROOT_STATIC_FILES = [
    "robots.txt",
    "sitemap.xml",
    "llms.txt",
]


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _rewrite_landing_links(html: str) -> str:
    rewritten = html
    for old, new in LINK_REWRITES.items():
        rewritten = rewritten.replace(old, new)
    return rewritten


def _rewrite_markdown_links(markdown: str, rewrites: dict[str, str]) -> str:
    rewritten = markdown
    for old, new in rewrites.items():
        rewritten = rewritten.replace(old, new)
    return rewritten


def build_static_site(repo_root: Path, output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    """Build a self-contained static site folder for public hosting."""
    repo_root = repo_root.resolve()
    output_dir = (repo_root / output_dir).resolve() if not output_dir.is_absolute() else output_dir.resolve()
    if output_dir == repo_root or repo_root in output_dir.parents and output_dir.name == "":
        raise ValueError("Refusing to write static site to the repository root.")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    landing_html = (repo_root / "site" / "index.html").read_text(encoding="utf-8")
    (output_dir / "index.html").write_text(_rewrite_landing_links(landing_html), encoding="utf-8")
    demo_html = (repo_root / "site" / "demo.html").read_text(encoding="utf-8")
    (output_dir / "demo.html").write_text(_rewrite_landing_links(demo_html), encoding="utf-8")
    for file_name in ROOT_STATIC_FILES:
        _copy_file(repo_root / "site" / file_name, output_dir / file_name)
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    (output_dir / "README.md").write_text(_rewrite_markdown_links(readme, README_REWRITES), encoding="utf-8")
    _copy_file(repo_root / "LICENSE", output_dir / "LICENSE")
    _copy_file(repo_root / "CITATION.cff", output_dir / "CITATION.cff")
    _copy_file(repo_root / "CONTRIBUTING.md", output_dir / "CONTRIBUTING.md")
    _copy_file(repo_root / "CODE_OF_CONDUCT.md", output_dir / "CODE_OF_CONDUCT.md")
    _copy_file(repo_root / "SECURITY.md", output_dir / "SECURITY.md")
    _copy_file(repo_root / "SUPPORT.md", output_dir / "SUPPORT.md")

    docs_output = output_dir / "docs"
    for file_name in DOC_FILES:
        markdown = (repo_root / "docs" / file_name).read_text(encoding="utf-8")
        (docs_output / file_name).parent.mkdir(parents=True, exist_ok=True)
        (docs_output / file_name).write_text(_rewrite_markdown_links(markdown, DOC_REWRITES), encoding="utf-8")
    assets_dir = repo_root / "docs" / "assets"
    if assets_dir.exists():
        shutil.copytree(assets_dir, docs_output / "assets")
    shutil.copytree(repo_root / "docs" / "sample-audits", docs_output / "sample-audits")
    (output_dir / ".nojekyll").write_text("", encoding="utf-8")
    return output_dir


def main() -> int:
    output_dir = build_static_site(Path.cwd())
    print(f"Built static site at {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
