from __future__ import annotations

from pathlib import Path


def test_community_files_exist_and_document_project_constraints() -> None:
    code_of_conduct = Path("CODE_OF_CONDUCT.md").read_text(encoding="utf-8")
    contributing = Path("CONTRIBUTING.md").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")
    security = Path("SECURITY.md").read_text(encoding="utf-8")
    support = Path("SUPPORT.md").read_text(encoding="utf-8")
    citation = Path("CITATION.cff").read_text(encoding="utf-8")

    assert "Expected behavior" in code_of_conduct
    assert "Treat findings as reproducibility signals" in code_of_conduct
    assert "private datasets" in code_of_conduct
    assert "no-key" in contributing
    assert "pytest -q" in contributing
    assert "check_catalog.py" in contributing
    assert "SUPPORT.md" in contributing
    assert "Code of Conduct" in contributing
    assert "Request a public repo audit" in readme
    assert "Audit request" in readme
    assert "Support guide" in readme
    assert "Code of Conduct" in readme
    assert "no paid API calls" in security
    assert "XSS" in security
    assert "path traversal" in security
    assert "GitHub Action inputs" in security
    assert "Request an audit of a public repo" in support
    assert "Check proposal" in support
    assert "private security advisory" in support
    assert "cff-version: 1.2.0" in citation
    assert "Thomas" in citation
    assert "reproducibility auditor" in citation
    assert "repository-code" in citation


def test_github_issue_and_pr_templates_exist() -> None:
    template_dir = Path(".github/ISSUE_TEMPLATE")
    assert (template_dir / "audit_request.yml").exists()
    assert (template_dir / "bug_report.yml").exists()
    assert (template_dir / "check_proposal.yml").exists()
    assert (template_dir / "case_study.yml").exists()
    assert (template_dir / "config.yml").exists()
    assert Path(".github/PULL_REQUEST_TEMPLATE.md").exists()
    assert Path(".github/labels.yml").exists()

    check_template = (template_dir / "check_proposal.yml").read_text(encoding="utf-8")
    audit_template = (template_dir / "audit_request.yml").read_text(encoding="utf-8")
    pr_template = Path(".github/PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")
    labels = Path(".github/labels.yml").read_text(encoding="utf-8")
    assert "Public repository URL" in audit_template
    assert "no-key reproducibility review" in audit_template
    assert "heuristic reproducibility signals" in audit_template
    assert "without API keys" in check_template
    assert "No API key" in pr_template
    assert "Static demo changes escape user-controlled content" in pr_template
    assert "name: severity/high" in labels
    assert "name: category/artifacts" in labels
    assert "name: triage/public-audit" in labels


def test_outreach_docs_include_audit_request_path() -> None:
    playbook = Path("docs/outreach-playbook.md").read_text(encoding="utf-8")

    assert "Audit request issue" in playbook
    assert "public repo URL" in playbook
    assert "Audit request template for public repositories" in playbook
