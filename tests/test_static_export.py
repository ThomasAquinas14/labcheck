from __future__ import annotations

import importlib.util
from pathlib import Path
import re


def _load_builder():
    script_path = Path("scripts/build_static_site.py")
    spec = importlib.util.spec_from_file_location("build_static_site", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_static_site_export_contains_public_assets(tmp_path: Path) -> None:
    builder = _load_builder()
    output_dir = builder.build_static_site(Path.cwd(), tmp_path / "site")

    assert (output_dir / "index.html").exists()
    assert (output_dir / "demo.html").exists()
    assert (output_dir / "README.md").exists()
    assert (output_dir / "LICENSE").exists()
    assert (output_dir / "CITATION.cff").exists()
    assert (output_dir / "CONTRIBUTING.md").exists()
    assert (output_dir / "SECURITY.md").exists()
    assert (output_dir / ".nojekyll").exists()
    assert (output_dir / "docs" / "assets" / "scorecard-preview.svg").exists()
    assert (output_dir / "docs" / "sample-audits" / "broken-repo-scorecard.md").exists()
    assert (output_dir / "docs" / "sample-audits" / "broken-repo-audit.html").exists()
    assert (output_dir / "docs" / "case-studies.md").exists()
    assert (output_dir / "docs" / "github-publish-guide.md").exists()
    assert (output_dir / "docs" / "lab-adoption-guide.md").exists()
    assert (output_dir / "docs" / "launch-kit.md").exists()
    assert (output_dir / "docs" / "release-checklist.md").exists()


def test_static_site_export_rewrites_landing_links(tmp_path: Path) -> None:
    builder = _load_builder()
    output_dir = builder.build_static_site(Path.cwd(), tmp_path / "site")
    index_html = (output_dir / "index.html").read_text(encoding="utf-8")

    assert "../README.md" not in index_html
    assert "../docs/" not in index_html
    assert 'href="README.md"' in index_html
    assert 'href="docs/sample-audits/broken-repo-audit.html"' in index_html
    assert 'href="docs/sample-audits/broken-repo-scorecard.md"' in index_html

    hrefs = re.findall(r'href="([^"]+)"', index_html)
    for href in hrefs:
        if href.startswith(("http://", "https://", "#")):
            continue
        assert ".." not in href
        assert (output_dir / href).exists(), href


def test_static_site_export_rewrites_markdown_links(tmp_path: Path) -> None:
    builder = _load_builder()
    output_dir = builder.build_static_site(Path.cwd(), tmp_path / "site")

    readme = (output_dir / "README.md").read_text(encoding="utf-8")
    outreach = (output_dir / "docs" / "outreach-playbook.md").read_text(encoding="utf-8")
    deploy = (output_dir / "docs" / "public-deploy-guide.md").read_text(encoding="utf-8")

    assert "](site/index.html)" not in readme
    assert "](site/demo.html)" not in readme
    assert "](docs/assets/scorecard-preview.svg)" in readme
    assert "](index.html)" in readme
    assert "](demo.html)" in readme
    assert "](../site/index.html)" not in outreach
    assert "](../site/demo.html)" not in outreach
    assert "](../index.html)" in outreach
    assert "](../site/index.html)" not in deploy
    assert "dist/site" in deploy


def test_static_site_export_markdown_links_resolve(tmp_path: Path) -> None:
    builder = _load_builder()
    output_dir = builder.build_static_site(Path.cwd(), tmp_path / "site")

    for markdown_path in output_dir.rglob("*.md"):
        markdown = markdown_path.read_text(encoding="utf-8")
        links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", markdown)
        for link in links:
            if link.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = link.split("#", 1)[0]
            if not target:
                continue
            assert (markdown_path.parent / target).resolve().exists(), f"{markdown_path}: {link}"


def test_pages_workflow_deploys_static_export() -> None:
    workflow = Path(".github/workflows/pages.yml").read_text(encoding="utf-8")
    assert "python scripts/build_static_site.py" in workflow
    assert "actions/upload-pages-artifact" in workflow
    assert "path: dist/site" in workflow
    assert "actions/deploy-pages" in workflow
