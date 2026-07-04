from __future__ import annotations

from pathlib import Path


def test_browser_demo_supports_multi_file_local_audits() -> None:
    demo = Path("site/demo.html").read_text(encoding="utf-8")
    assert 'id="folder-input"' in demo
    assert 'id="copy-scorecard"' in demo
    assert 'id="download-scorecard"' in demo
    assert 'aria-live="polite"' in demo
    assert "function analyzeFileSet" in demo
    assert "function toScorecard" in demo
    assert 'return lines.join("\\n")' in demo
    assert "function copyScorecardToClipboard" in demo
    assert 'id="load-sample-repo"' in demo
    assert "sampleRepoFiles" in demo
    assert "built-in sample repo snapshot" in demo
    assert "labcheck-browser-scorecard.md" in demo
    assert "Scorecard copied" in demo
    assert "Copy Scorecard" in demo
    assert "Download Scorecard" in demo
    assert "Everything stays local" in demo
    assert "LC003" in demo
    assert "LC005" in demo
    assert "LC008" in demo
    assert "LC012" in demo
    assert "LC013" in demo
    assert "LC014" in demo
    assert "LC015" in demo
    assert "LC016" in demo
    assert "LC017" in demo
    assert "function hasPythonRuntimeSpec" in demo
    assert "function notebookMetadataIssue" in demo
    assert "function hasReadmeRunInstructions" in demo
    assert "function sklearnRandomStateIssues" in demo
    assert "function pandasRandomStateIssues" in demo
    assert ".python-version" in demo


def test_landing_page_links_adoption_pack() -> None:
    landing = Path("site/index.html").read_text(encoding="utf-8")
    assert "labcheck init --policy" in landing
    assert "docs/reproducibility.md" in landing
    assert "docs/lab-adoption-guide.md" in landing
    assert "scorecard-path: labcheck-scorecard.md" in landing
    assert "Seedless sklearn splits" in landing
    assert "LC016" in landing
    assert "Seedless pandas samples" in landing
    assert "LC017" in landing
    assert "downloadable scorecard/Markdown/JSON results" in landing


def test_landing_page_promotes_audit_pack_for_outreach() -> None:
    landing = Path("site/index.html").read_text(encoding="utf-8")
    assert "labcheck scorecard" in landing
    assert "labcheck-scorecard.md" in landing
    assert "labcheck pack --zip" in landing
    assert "docs/faq.md" in landing
    assert "docs/launch-kit.md" in landing
    assert "docs/launch-week-plan.md" in landing
    assert "docs/outreach-tracker-template.md" in landing
    assert "broken-repo-scorecard.md" in landing
    assert "labcheck-audit" in landing
    assert "single archive" in landing
    assert "complete audit folder" in landing


def test_public_pages_have_share_metadata() -> None:
    landing = Path("site/index.html").read_text(encoding="utf-8")
    demo = Path("site/demo.html").read_text(encoding="utf-8")

    assert '<meta name="description"' in landing
    assert 'property="og:title"' in landing
    assert 'property="og:site_name" content="labcheck"' in landing
    assert 'property="og:url" content="https://thomasaquinas14.github.io/labcheck/"' in landing
    assert 'property="og:image" content="https://thomasaquinas14.github.io/labcheck/docs/assets/scorecard-preview.svg"' in landing
    assert 'name="twitter:card" content="summary_large_image"' in landing
    assert 'name="twitter:image" content="https://thomasaquinas14.github.io/labcheck/docs/assets/scorecard-preview.svg"' in landing
    assert '<link rel="canonical" href="https://thomasaquinas14.github.io/labcheck/">' in landing
    assert 'name="theme-color"' in landing
    assert "No-key reproducibility audits" in landing
    assert '<meta name="description"' in demo
    assert 'property="og:title"' in demo
    assert 'property="og:url" content="https://thomasaquinas14.github.io/labcheck/demo.html"' in demo
    assert 'name="twitter:card" content="summary_large_image"' in demo
    assert '<link rel="canonical" href="https://thomasaquinas14.github.io/labcheck/demo.html">' in demo
    assert "Everything stays local" in demo


def test_readme_badges_reinforce_launch_positioning() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "python-3.11%2B" in readme
    assert "no_API_keys-required" in readme
    assert "local--first-reproducibility" in readme
    assert "license-MIT" in readme


def test_browser_demo_escapes_user_controlled_html() -> None:
    demo = Path("site/demo.html").read_text(encoding="utf-8")
    assert "function escapeHtml" in demo
    assert "escapeHtml(node.label)" in demo
    assert "escapeHtml(risk.file)" in demo
    assert "escapeHtml(risk.evidence)" in demo
    assert "escapeHtml(finding.file)" in demo
    assert "escapeHtml(finding.evidence)" in demo
