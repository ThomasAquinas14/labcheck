from __future__ import annotations

from pathlib import Path


def test_community_files_exist_and_document_project_constraints() -> None:
    contributing = Path("CONTRIBUTING.md").read_text(encoding="utf-8")
    security = Path("SECURITY.md").read_text(encoding="utf-8")
    citation = Path("CITATION.cff").read_text(encoding="utf-8")

    assert "no-key" in contributing
    assert "pytest -q" in contributing
    assert "check_catalog.py" in contributing
    assert "no paid API calls" in security
    assert "XSS" in security
    assert "path traversal" in security
    assert "cff-version: 1.2.0" in citation
    assert "Thomas" in citation
    assert "reproducibility auditor" in citation
    assert "repository-code" in citation


def test_github_issue_and_pr_templates_exist() -> None:
    template_dir = Path(".github/ISSUE_TEMPLATE")
    assert (template_dir / "bug_report.yml").exists()
    assert (template_dir / "check_proposal.yml").exists()
    assert (template_dir / "case_study.yml").exists()
    assert (template_dir / "config.yml").exists()
    assert Path(".github/PULL_REQUEST_TEMPLATE.md").exists()

    check_template = (template_dir / "check_proposal.yml").read_text(encoding="utf-8")
    pr_template = Path(".github/PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")
    assert "without API keys" in check_template
    assert "No API key" in pr_template
    assert "Static demo changes escape user-controlled content" in pr_template
