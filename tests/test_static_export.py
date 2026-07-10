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


def _load_export_checker():
    script_path = Path("scripts/check_static_export.py")
    spec = importlib.util.spec_from_file_location("check_static_export", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _markdown_without_fenced_blocks(markdown: str) -> str:
    lines: list[str] = []
    in_fence = False
    for raw_line in markdown.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            lines.append("")
            continue
        lines.append("" if in_fence else raw_line)
    return "\n".join(lines)


def test_static_site_export_contains_public_assets(tmp_path: Path) -> None:
    builder = _load_builder()
    output_dir = builder.build_static_site(Path.cwd(), tmp_path / "site")

    assert (output_dir / "index.html").exists()
    assert (output_dir / "demo.html").exists()
    assert (output_dir / "robots.txt").exists()
    assert (output_dir / "sitemap.xml").exists()
    assert (output_dir / "llms.txt").exists()
    assert (output_dir / "README.md").exists()
    assert (output_dir / "LICENSE").exists()
    assert (output_dir / "CITATION.cff").exists()
    assert (output_dir / "CODE_OF_CONDUCT.md").exists()
    assert (output_dir / "CONTRIBUTING.md").exists()
    assert (output_dir / "SECURITY.md").exists()
    assert (output_dir / "SUPPORT.md").exists()
    assert (output_dir / ".nojekyll").exists()
    assert (output_dir / "docs" / "assets" / "scorecard-preview.svg").exists()
    assert (output_dir / "docs" / "sample-audits" / "broken-repo-scorecard.md").exists()
    assert (output_dir / "docs" / "sample-audits" / "broken-repo-outreach-note.md").exists()
    assert (output_dir / "docs" / "sample-audits" / "broken-repo-issue-draft.md").exists()
    assert (output_dir / "docs" / "sample-audits" / "broken-repo-labeled-issue.md").exists()
    assert (output_dir / "docs" / "sample-audits" / "broken-repo-audit.html").exists()
    assert (output_dir / "docs" / "case-studies.md").exists()
    assert (output_dir / "docs" / "comparison.md").exists()
    assert (output_dir / "docs" / "demo-video-script.md").exists()
    assert (output_dir / "docs" / "faq.md").exists()
    assert (output_dir / "docs" / "first-audit.md").exists()
    assert (output_dir / "docs" / "good-first-issues.md").exists()
    assert (output_dir / "docs" / "github-publish-guide.md").exists()
    assert (output_dir / "docs" / "install.md").exists()
    assert (output_dir / "docs" / "issue-labels.md").exists()
    assert (output_dir / "docs" / "lab-adoption-guide.md").exists()
    assert (output_dir / "docs" / "launch-kit.md").exists()
    assert (output_dir / "docs" / "launch-post-after-action.md").exists()
    assert (output_dir / "docs" / "launch-week-plan.md").exists()
    assert (output_dir / "docs" / "maintainer-reply-templates.md").exists()
    assert (output_dir / "docs" / "outreach-tracker-template.md").exists()
    assert (output_dir / "docs" / "privacy-and-safety.md").exists()
    assert (output_dir / "docs" / "public-triage-board.md").exists()
    assert (output_dir / "docs" / "release-checklist.md").exists()
    assert (output_dir / "docs" / "reply-derived-case-study-seed.md").exists()
    assert (output_dir / "docs" / "reply-to-case-study-checklist.md").exists()
    assert (output_dir / "docs" / "reproducibility-patterns.md").exists()
    assert (output_dir / "docs" / "roadmap.md").exists()
    assert (output_dir / "docs" / "scoring-guide.md").exists()


def test_static_site_export_contains_discovery_assets(tmp_path: Path) -> None:
    builder = _load_builder()
    output_dir = builder.build_static_site(Path.cwd(), tmp_path / "site")

    robots = (output_dir / "robots.txt").read_text(encoding="utf-8")
    sitemap = (output_dir / "sitemap.xml").read_text(encoding="utf-8")
    llms = (output_dir / "llms.txt").read_text(encoding="utf-8")
    sample_scorecard = (output_dir / "docs" / "sample-audits" / "broken-repo-scorecard.md").read_text(encoding="utf-8")
    sample_audit = (output_dir / "docs" / "sample-audits" / "broken-repo-audit.md").read_text(encoding="utf-8")

    assert "User-agent: *" in robots
    assert "Sitemap: https://thomasaquinas14.github.io/labcheck/sitemap.xml" in robots
    assert "<loc>https://thomasaquinas14.github.io/labcheck/</loc>" in sitemap
    assert "<loc>https://thomasaquinas14.github.io/labcheck/demo.html</loc>" in sitemap
    assert "<loc>https://thomasaquinas14.github.io/labcheck/docs/first-audit.md</loc>" in sitemap
    assert "<loc>https://thomasaquinas14.github.io/labcheck/docs/install.md</loc>" in sitemap
    assert "<loc>https://thomasaquinas14.github.io/labcheck/docs/scoring-guide.md</loc>" in sitemap
    assert "<loc>https://thomasaquinas14.github.io/labcheck/docs/reproducibility-patterns.md</loc>" in sitemap
    assert "<loc>https://thomasaquinas14.github.io/labcheck/docs/privacy-and-safety.md</loc>" in sitemap
    assert "<loc>https://thomasaquinas14.github.io/labcheck/docs/sample-audits/broken-repo-issue-draft.md</loc>" in sitemap
    assert "<loc>https://thomasaquinas14.github.io/labcheck/docs/sample-audits/broken-repo-labeled-issue.md</loc>" in sitemap
    assert "<loc>https://thomasaquinas14.github.io/labcheck/docs/comparison.md</loc>" in sitemap
    assert "<loc>https://thomasaquinas14.github.io/labcheck/docs/lab-adoption-guide.md</loc>" in sitemap
    assert "<loc>https://thomasaquinas14.github.io/labcheck/docs/launch-kit.md</loc>" in sitemap
    assert "<loc>https://thomasaquinas14.github.io/labcheck/docs/launch-post-after-action.md</loc>" in sitemap
    assert "<loc>https://thomasaquinas14.github.io/labcheck/docs/outreach-playbook.md</loc>" in sitemap
    assert "<loc>https://thomasaquinas14.github.io/labcheck/docs/public-triage-board.md</loc>" in sitemap
    assert "<loc>https://thomasaquinas14.github.io/labcheck/docs/reply-derived-case-study-seed.md</loc>" in sitemap
    assert "<loc>https://thomasaquinas14.github.io/labcheck/docs/reply-to-case-study-checklist.md</loc>" in sitemap
    assert "<loc>https://thomasaquinas14.github.io/labcheck/docs/maintainer-reply-templates.md</loc>" in sitemap
    assert "<loc>https://thomasaquinas14.github.io/labcheck/llms.txt</loc>" in sitemap
    assert "# labcheck" in llms
    assert "No API keys are required." in llms
    assert "bounded public GitHub files client-side without tokens" in llms
    assert "prioritizing manifests, README files, CI workflows, notebooks, and Python source" in llms
    assert "Browser demo: https://thomasaquinas14.github.io/labcheck/demo.html" in llms
    assert "labcheck demo-repo" in llms
    assert "labcheck scorecard labcheck-demo-repo" in llms
    assert "labcheck demo-link https://github.com/owner/repo --format markdown --auto-audit" in llms
    assert "Install guide: https://thomasaquinas14.github.io/labcheck/docs/install.md" in llms
    assert "First audit guide: https://thomasaquinas14.github.io/labcheck/docs/first-audit.md" in llms
    assert "Reproducibility pattern gallery: https://thomasaquinas14.github.io/labcheck/docs/reproducibility-patterns.md" in llms
    assert "Scoring guide: https://thomasaquinas14.github.io/labcheck/docs/scoring-guide.md" in llms
    assert "Privacy and safety model: https://thomasaquinas14.github.io/labcheck/docs/privacy-and-safety.md" in llms
    assert "what is local-only, what calls GitHub directly, and what not to scan or publish" in llms
    assert "Sample outreach note: https://thomasaquinas14.github.io/labcheck/docs/sample-audits/broken-repo-outreach-note.md" in llms
    assert "Sample issue draft: https://thomasaquinas14.github.io/labcheck/docs/sample-audits/broken-repo-issue-draft.md" in llms
    assert "Sample labeled issue bundle: https://thomasaquinas14.github.io/labcheck/docs/sample-audits/broken-repo-labeled-issue.md" in llms
    assert "Comparison guide: https://thomasaquinas14.github.io/labcheck/docs/comparison.md" in llms
    assert "Lab adoption guide: https://thomasaquinas14.github.io/labcheck/docs/lab-adoption-guide.md" in llms
    assert "Launch kit: https://thomasaquinas14.github.io/labcheck/docs/launch-kit.md" in llms
    assert "Launch post after-action checklist: https://thomasaquinas14.github.io/labcheck/docs/launch-post-after-action.md" in llms
    assert "Outreach playbook: https://thomasaquinas14.github.io/labcheck/docs/outreach-playbook.md" in llms
    assert "Public triage board template: https://thomasaquinas14.github.io/labcheck/docs/public-triage-board.md" in llms
    assert "Reply-derived case study seed: https://thomasaquinas14.github.io/labcheck/docs/reply-derived-case-study-seed.md" in llms
    assert "Reply to case study checklist: https://thomasaquinas14.github.io/labcheck/docs/reply-to-case-study-checklist.md" in llms
    assert "Maintainer reply templates: https://thomasaquinas14.github.io/labcheck/docs/maintainer-reply-templates.md" in llms
    assert "Explain top finding: `labcheck explain LC001`" in sample_scorecard
    assert "## Review Boundary" in sample_audit
    assert "## Understand Finding Codes" in sample_audit
    assert "## Next Steps" in sample_audit


def test_static_site_export_rewrites_landing_links(tmp_path: Path) -> None:
    builder = _load_builder()
    output_dir = builder.build_static_site(Path.cwd(), tmp_path / "site")
    index_html = (output_dir / "index.html").read_text(encoding="utf-8")

    assert "../README.md" not in index_html
    assert "../docs/" not in index_html
    assert 'href="README.md"' in index_html
    assert 'href="docs/sample-audits/broken-repo-audit.html"' in index_html
    assert 'href="docs/sample-audits/broken-repo-scorecard.md"' in index_html
    assert 'href="docs/sample-audits/broken-repo-issue-draft.md"' in index_html
    assert 'href="docs/sample-audits/broken-repo-labeled-issue.md"' in index_html

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
    demo_script = (output_dir / "docs" / "demo-video-script.md").read_text(encoding="utf-8")
    deploy = (output_dir / "docs" / "public-deploy-guide.md").read_text(encoding="utf-8")
    safety = (output_dir / "docs" / "privacy-and-safety.md").read_text(encoding="utf-8")
    first_audit = (output_dir / "docs" / "first-audit.md").read_text(encoding="utf-8")
    install = (output_dir / "docs" / "install.md").read_text(encoding="utf-8")

    assert "](site/index.html)" not in readme
    assert "](site/demo.html)" not in readme
    assert "](docs/assets/scorecard-preview.svg)" in readme
    assert "](index.html)" in readme
    assert "](demo.html)" in readme
    assert "](../site/index.html)" not in outreach
    assert "](../site/demo.html)" not in outreach
    assert "](../index.html)" in outreach
    assert "75-Second Script" in demo_script
    assert "](../site/index.html)" not in deploy
    assert "dist/site" in deploy
    assert "](../site/demo.html)" not in first_audit
    assert "](../demo.html)" in first_audit
    assert "labcheck pack https://github.com/owner/repo" in first_audit
    assert "labcheck demo-link https://github.com/owner/repo --format markdown --auto-audit --audience professor --output labcheck-demo-link.md" in first_audit
    assert "include a bounded browser-demo link automatically" in first_audit
    assert "pipx install git+https://github.com/ThomasAquinas14/labcheck.git" in install
    assert "labcheck demo-repo" in install
    assert "labcheck scorecard labcheck-demo-repo" in install
    assert "labcheck demo-link https://github.com/owner/repo --audience professor --output labcheck-demo-link.txt" in install
    assert "labcheck demo-link https://github.com/owner/repo --format markdown --auto-audit --audience professor --output labcheck-demo-link.md" in install
    assert "](privacy-and-safety.md)" in deploy
    assert "The browser demo does not send selected local files" in safety
    assert "The CLI performs deterministic static analysis" in safety
    assert "Avoid adding a hosted clone queue" in safety
    issue_labels = (output_dir / "docs" / "issue-labels.md").read_text(encoding="utf-8")
    assert "severity/high" in issue_labels
    assert "gh label create" in issue_labels
    triage_board = (output_dir / "docs" / "public-triage-board.md").read_text(encoding="utf-8")
    assert "GitHub Issues are the source of truth" in triage_board
    assert "gh issue list --label" in triage_board
    reply_templates = (output_dir / "docs" / "maintainer-reply-templates.md").read_text(encoding="utf-8")
    assert "Do not keep bumping public maintainers" in reply_templates
    assert "labcheck compare before-labcheck-report.json after-labcheck-report.json" in reply_templates
    after_action = (output_dir / "docs" / "launch-post-after-action.md").read_text(encoding="utf-8")
    assert "Convert Attention Into One Public Artifact" in after_action
    assert "Do not ask strangers to star the repo as the main call to action" in after_action
    case_study_seed = (output_dir / "docs" / "reply-derived-case-study-seed.md").read_text(encoding="utf-8")
    assert "not a real external reply yet" in case_study_seed
    assert "Generated artifacts need an explicit contract" in case_study_seed
    case_study_checklist = (output_dir / "docs" / "reply-to-case-study-checklist.md").read_text(encoding="utf-8")
    assert "Only convert a reply into a case study when all of these are true" in case_study_checklist
    assert "Do not publish claims that are not visible in the report" in case_study_checklist
    labeled_issue = (output_dir / "docs" / "sample-audits" / "broken-repo-labeled-issue.md").read_text(encoding="utf-8")
    assert "gh issue create" in labeled_issue
    assert "triage/public-audit" in labeled_issue

    scoring = (output_dir / "docs" / "scoring-guide.md").read_text(encoding="utf-8")
    patterns = (output_dir / "docs" / "reproducibility-patterns.md").read_text(encoding="utf-8")
    assert "not a claim" in scoring
    assert "overall = round(category_average * 0.70 + weakest_category * 0.30)" in scoring
    assert "Hidden notebook state" in patterns
    assert "Missing input artifacts" in patterns


def test_static_site_export_markdown_links_resolve(tmp_path: Path) -> None:
    builder = _load_builder()
    output_dir = builder.build_static_site(Path.cwd(), tmp_path / "site")

    for markdown_path in output_dir.rglob("*.md"):
        markdown = markdown_path.read_text(encoding="utf-8")
        links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", _markdown_without_fenced_blocks(markdown))
        for link in links:
            if link.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = link.split("#", 1)[0]
            if not target:
                continue
            assert (markdown_path.parent / target).resolve().exists(), f"{markdown_path}: {link}"


def test_static_export_checker_accepts_fresh_export(tmp_path: Path) -> None:
    builder = _load_builder()
    checker = _load_export_checker()
    output_dir = builder.build_static_site(Path.cwd(), tmp_path / "site")

    assert checker.check_static_export(output_dir) == []


def test_static_export_checker_flags_local_workspace_leaks(tmp_path: Path) -> None:
    checker = _load_export_checker()
    export_dir = tmp_path / "site"
    required_files = checker.REQUIRED_EXPORT_FILES
    for relative_path in required_files:
        path = export_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok\n", encoding="utf-8")
    (export_dir / "index.html").write_text(
        '<a href="../README.md">bad</a>\nC:\\Users\\hp\\Desktop\\labcheck\n',
        encoding="utf-8",
    )

    problems = checker.check_static_export(export_dir)

    assert "forbidden public-export text in index.html: C:\\Users\\hp\\" in problems
    assert 'forbidden public-export text in index.html: href="../README.md"' in problems


def test_pages_workflow_deploys_static_export() -> None:
    workflow = Path(".github/workflows/pages.yml").read_text(encoding="utf-8")
    assert "python scripts/build_static_site.py" in workflow
    assert "python scripts/check_static_export.py" in workflow
    assert "actions/upload-pages-artifact" in workflow
    assert "path: dist/site" in workflow
    assert "actions/deploy-pages" in workflow
