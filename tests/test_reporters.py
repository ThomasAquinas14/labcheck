from __future__ import annotations

import csv
import io
import json

from labcheck.models import Finding, Report, ScanSummary, ScoreCard
from labcheck.reporters import (
    render_csv,
    render_html,
    render_issue_draft,
    render_markdown,
    render_outreach_note,
    render_sarif,
    render_scorecard,
    render_target_fit,
    render_text,
)


def _report(target: str) -> Report:
    return Report(
        summary=ScanSummary(target=target, notebooks=1, python_files=1, findings_count=1),
        scores=ScoreCard(
            overall_score=72,
            environment_rebuildability=80,
            notebook_determinism=65,
            artifact_availability=70,
            portability=75,
            onboarding_readiness=70,
        ),
        findings=[
            Finding(
                check_id="LC005",
                title="Referenced input artifact missing from repo",
                severity="high",
                category="artifact_availability",
                file_path="notebooks/train.ipynb",
                evidence="Reads 'data/train.csv', but that path is not present.",
                why_it_matters="A new user may not be able to run the workflow.",
                suggested_fix="Commit the artifact or document how to obtain it.",
            )
        ],
    )


def _compose_report() -> Report:
    findings = [
        Finding(
            check_id="LC005",
            title="Referenced input artifact missing from repo",
            severity="high",
            category="artifacts",
            file_path="compose.yml",
            evidence=(
                "Docker Compose bind source(s) ./data are referenced, "
                "but those paths are not present in the scanned repo."
            ),
            why_it_matters="A new user may not be able to start services.",
            suggested_fix="Commit or document the bind source.",
        ),
        Finding(
            check_id="LC069",
            title="Docker Compose service env_file references missing file",
            severity="medium",
            category="onboarding",
            file_path="compose.yml",
            evidence=(
                "Docker Compose service env_file(s) config/dev.env, .env.local "
                "are referenced, but those files are not present in the scanned repo."
            ),
            why_it_matters="A fresh clone can miss service configuration.",
            suggested_fix="Commit safe env examples or update env_file.",
        ),
        Finding(
            check_id="LC070",
            title="Docker Compose extends references missing file or service",
            severity="medium",
            category="onboarding",
            file_path="compose.dev.yml",
            evidence=(
                "Docker Compose extends file(s) compose.base.yml are referenced, "
                "but those files are not present in the scanned repo. "
                "Docker Compose extends service target(s) api->base in compose.base.yml "
                "are referenced, but those services are not defined in the target Compose file."
            ),
            why_it_matters="A fresh clone can fail when inheritance targets drift.",
            suggested_fix="Commit the base file or update extends.",
        ),
    ]
    return Report(
        summary=ScanSummary(
            target="examples/compose-drift",
            notebooks=0,
            python_files=0,
            findings_count=len(findings),
        ),
        scores=ScoreCard(
            overall_score=64,
            environment_rebuildability=65,
            notebook_determinism=100,
            artifact_availability=55,
            portability=80,
            onboarding_readiness=50,
        ),
        findings=findings,
    )


def test_human_reports_group_docker_compose_reference_findings() -> None:
    report = _compose_report()

    outputs = [
        render_text(report),
        render_markdown(report),
        render_scorecard(report),
        render_html(report),
    ]

    for output in outputs:
        assert "Docker Compose Reference Summary" in output
        assert "compose.yml" in output
        assert "compose.dev.yml" in output
        assert "LC005" in output
        assert "LC069" in output
        assert "LC070" in output
        assert "./data" in output
        assert "config/dev.env" in output
        assert ".env.local" in output
        assert "compose.base.yml" in output
        assert "api-&gt;base in compose.base.yml" in output or "api->base in compose.base.yml" in output


def test_compose_reference_summary_ignores_non_compose_lc005_findings() -> None:
    report = _report("examples/notebook-only")

    assert "Docker Compose Reference Summary" not in render_text(report)
    assert "Docker Compose Reference Summary" not in render_markdown(report)
    assert "Docker Compose Reference Summary" not in render_scorecard(report)
    assert "Docker Compose Reference Summary" not in render_html(report)


def test_public_github_outreach_note_includes_browser_demo_link() -> None:
    note = render_outreach_note(_report("https://github.com/owner/repo"))

    assert "Browser demo:" in note
    assert "[Try this repo in labcheck](https://thomasaquinas14.github.io/labcheck/demo.html?repo=owner%2Frepo&audit=1)" in note
    assert "bounded public GitHub files only" in note


def test_professor_outreach_note_uses_lab_handoff_framing() -> None:
    note = render_outreach_note(
        _report("https://github.com/owner/repo"),
        recipient="Professor Ada",
        sender="Thomas",
        audience="professor",
    )

    assert "Subject: Quick lab reproducibility handoff check" in note
    assert "Hi Professor Ada," in note
    assert "new student, collaborator, or reviewer" in note
    assert "small lab handoff checklist" in note
    assert "Best,\nThomas" in note


def test_founder_outreach_note_uses_onboarding_framing() -> None:
    note = render_outreach_note(_report("https://github.com/owner/repo"), audience="founder")

    assert "Subject: Quick ML repo onboarding and diligence check" in note
    assert "new engineer, technical lead, or diligence reviewer" in note
    assert "onboarding-ready fix" in note


def test_target_fit_scores_public_professor_candidate() -> None:
    fit = render_target_fit(_report("https://github.com/owner/repo"), audience="professor")

    assert "# labcheck Target Fit" in fit
    assert "Audience: `professor`" in fit
    assert "Fit score: **10/10**" in fit
    assert "strong outreach candidate" in fit
    assert "Notebook-heavy workflow" in fit
    assert "Professor fit" in fit
    assert "Top risk: `LC005`" in fit
    assert "Browser demo: [Try this repo in labcheck]" in fit
    assert "This is a static, no-key first-pass audit" in fit
    assert "labcheck outreach https://github.com/owner/repo --audience professor" in fit


def test_target_fit_for_low_signal_clean_repo_stays_cautious() -> None:
    report = Report(
        summary=ScanSummary(target="examples/clean-notebook", notebooks=1, python_files=0, findings_count=0),
        scores=ScoreCard(
            overall_score=100,
            environment_rebuildability=100,
            notebook_determinism=100,
            artifact_availability=100,
            portability=100,
            onboarding_readiness=100,
        ),
        findings=[],
    )

    fit = render_target_fit(report)

    assert "Fit score: **2/10**" in fit
    assert "weak outreach candidate" in fit
    assert "No top risk found" in fit
    assert "Browser demo:" not in fit


def test_public_github_issue_draft_includes_browser_demo_link() -> None:
    draft = render_issue_draft(_report("https://github.com/owner/repo.git"))

    assert "Browser demo:" in draft
    assert "[Try this repo in labcheck](https://thomasaquinas14.github.io/labcheck/demo.html?repo=owner%2Frepo&audit=1)" in draft
    assert "bounded public-file snapshot" in draft


def test_local_outreach_artifacts_do_not_include_browser_demo_link() -> None:
    report = _report("examples/broken-repo")

    assert "Browser demo:" not in render_outreach_note(report)
    assert "Browser demo:" not in render_issue_draft(report)


def test_render_csv_outputs_spreadsheet_friendly_findings() -> None:
    report = _report("examples/broken-repo")
    report.findings[0].evidence = 'Reads "data/train.csv",\nthen fails.'

    rows = list(csv.DictReader(io.StringIO(render_csv(report))))

    assert rows == [
        {
            "target": "examples/broken-repo",
            "overall_score": "72",
            "status": "",
            "owner": "",
            "suggested_owner": "data/artifact owner",
            "check_id": "LC005",
            "title": "Referenced input artifact missing from repo",
            "severity": "high",
            "category": "artifact_availability",
            "file_path": "notebooks/train.ipynb",
            "evidence": 'Reads "data/train.csv",\nthen fails.',
            "why_it_matters": "A new user may not be able to run the workflow.",
            "suggested_fix": "Commit the artifact or document how to obtain it.",
        }
    ]


def test_render_sarif_preserves_finding_fields_for_code_scanning() -> None:
    report = Report(
        summary=ScanSummary(target="examples/sarif-fixture", notebooks=1, python_files=1, findings_count=3),
        scores=ScoreCard(
            overall_score=61,
            environment_rebuildability=80,
            notebook_determinism=60,
            artifact_availability=55,
            portability=70,
            onboarding_readiness=40,
        ),
        findings=[
            Finding(
                check_id="LC005",
                title="Referenced input artifact missing from repo",
                severity="high",
                category="artifacts",
                file_path=r"notebooks\train.ipynb",
                evidence="Reads 'data/train.csv', but that path is not present.",
                why_it_matters="A new user may not be able to run the workflow.",
                suggested_fix="Commit the artifact or document how to obtain it.",
            ),
            Finding(
                check_id="LC005",
                title="Referenced input artifact missing from repo",
                severity="high",
                category="artifacts",
                file_path="compose.yml",
                evidence="Docker Compose bind source(s) ./data are referenced, but those paths are not present.",
                why_it_matters="A new user may not be able to run the workflow.",
                suggested_fix="Commit the bind source or document how to obtain it.",
            ),
            Finding(
                check_id="LC021",
                title="Dependency setup step is undocumented",
                severity="medium",
                category="onboarding",
                file_path="README.md",
                evidence="Found dependency manifest(s) requirements.txt, but README.md does not show an install/setup command.",
                why_it_matters="A README can show what to run and still fail handoff if dependencies are never installed.",
                suggested_fix="Add a setup step before the run command.",
            ),
        ],
    )

    payload = json.loads(render_sarif(report))
    run = payload["runs"][0]
    rules = {rule["id"]: rule for rule in run["tool"]["driver"]["rules"]}
    results = run["results"]

    assert payload["version"] == "2.1.0"
    assert run["tool"]["driver"]["name"] == "labcheck"
    assert run["properties"] == {"target": "examples/sarif-fixture", "overall_score": 61}
    assert set(rules) == {"LC005", "LC021"}
    assert rules["LC005"]["properties"] == {"category": "artifacts", "severity": "high"}
    assert rules["LC005"]["fullDescription"]["text"] == "A new user may not be able to run the workflow."
    assert rules["LC021"]["help"]["text"] == "Add a setup step before the run command."

    assert [result["ruleId"] for result in results] == ["LC005", "LC005", "LC021"]
    assert [result["level"] for result in results] == ["error", "error", "warning"]
    assert results[0]["message"]["text"] == "Reads 'data/train.csv', but that path is not present."
    assert results[0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "notebooks/train.ipynb"
    assert results[0]["locations"][0]["physicalLocation"]["region"]["startLine"] == 1
    assert results[1]["properties"]["suggested_fix"] == "Commit the bind source or document how to obtain it."
    assert results[2]["properties"] == {
        "category": "onboarding",
        "severity": "medium",
        "title": "Dependency setup step is undocumented",
        "suggested_fix": "Add a setup step before the run command.",
    }
