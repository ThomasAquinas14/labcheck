from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import zipfile

from labcheck.cli import main


def test_cli_json_output(capsys) -> None:
    exit_code = main(["scan", "examples/broken-repo", "--format", "json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["summary"]["target"] == "examples/broken-repo"
    assert payload["summary"]["findings_count"] >= 8
    assert "artifact_availability" in payload["scores"]
    assert "graph" in payload


def test_cli_compare_command_outputs_markdown(tmp_path, capsys) -> None:
    before_path = tmp_path / "before.json"
    after_path = tmp_path / "after.json"
    before_path.write_text(
        json.dumps(
            {
                "summary": {"target": "before", "findings_count": 1},
                "scores": {
                    "overall_score": 30,
                    "environment_rebuildability": 30,
                    "notebook_determinism": 30,
                    "artifact_availability": 30,
                    "portability": 30,
                    "onboarding_readiness": 30,
                },
                "findings": [
                    {
                        "check_id": "LC005",
                        "title": "Referenced input artifact missing from repo",
                        "severity": "high",
                        "category": "artifact_availability",
                        "file_path": "notebooks/train.ipynb",
                        "evidence": "Reads data/train.csv.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    after_path.write_text(
        json.dumps(
            {
                "summary": {"target": "after", "findings_count": 0},
                "scores": {
                    "overall_score": 100,
                    "environment_rebuildability": 100,
                    "notebook_determinism": 100,
                    "artifact_availability": 100,
                    "portability": 100,
                    "onboarding_readiness": 100,
                },
                "findings": [],
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(["compare", str(before_path), str(after_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "# labcheck Before/After Compare" in captured.out
    assert "Score change: **+70** points (30 -> 100)" in captured.out
    assert "Findings change: **-1** (1 -> 0)" in captured.out
    assert "Resolved findings: **1**" in captured.out


def test_cli_scan_can_write_json_sidecar(tmp_path, capsys) -> None:
    json_path = tmp_path / "labcheck-report.json"
    exit_code = main(
        [
            "scan",
            "examples/broken-repo",
            "--format",
            "markdown",
            "--json-output",
            str(json_path),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert "## Review Boundary" in captured.out
    assert "does not upload source files to a hosted backend" in captured.out
    assert "## Top Risks" in captured.out
    assert "## Understand Finding Codes" in captured.out
    assert "`labcheck explain LC001`" in captured.out
    assert "## Remediation Plan" in captured.out
    assert "## Next Steps" in captured.out
    assert "Scorecard summary: `labcheck scorecard examples/broken-repo`" in captured.out
    assert "Sortable triage CSV: `labcheck scan examples/broken-repo --format csv --output labcheck-findings.csv`" in captured.out
    assert payload["summary"]["findings_count"] >= 8


def test_cli_csv_output(capsys) -> None:
    exit_code = main(["scan", "examples/broken-repo", "--format", "csv"])
    captured = capsys.readouterr()
    rows = list(csv.DictReader(io.StringIO(captured.out)))
    assert exit_code == 0
    assert rows
    assert rows[0]["target"] == "examples/broken-repo"
    assert rows[0]["overall_score"] == "39"
    assert rows[0]["status"] == ""
    assert rows[0]["owner"] == ""
    assert rows[0]["suggested_owner"]
    assert rows[0]["check_id"].startswith("LC")
    assert rows[0]["suggested_fix"]


def test_cli_scan_can_write_csv_sidecar(tmp_path, capsys) -> None:
    csv_path = tmp_path / "labcheck-report.csv"
    exit_code = main(
        [
            "scan",
            "examples/broken-repo",
            "--format",
            "markdown",
            "--csv-output",
            str(csv_path),
        ]
    )
    captured = capsys.readouterr()
    rows = list(csv.DictReader(io.StringIO(csv_path.read_text(encoding="utf-8"))))
    assert exit_code == 0
    assert "## Top Risks" in captured.out
    assert rows
    assert rows[0]["target"] == "examples/broken-repo"
    assert rows[0]["overall_score"] == "39"
    assert rows[0]["status"] == ""
    assert rows[0]["owner"] == ""
    assert rows[0]["suggested_owner"]
    assert rows[0]["check_id"].startswith("LC")


def test_cli_sarif_output(capsys) -> None:
    exit_code = main(["scan", "examples/broken-repo", "--format", "sarif"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["version"] == "2.1.0"
    run = payload["runs"][0]
    assert run["tool"]["driver"]["name"] == "labcheck"
    assert run["results"]
    assert run["results"][0]["locations"][0]["physicalLocation"]["region"]["startLine"] == 1


def test_cli_scan_can_write_sarif_sidecar(tmp_path, capsys) -> None:
    sarif_path = tmp_path / "labcheck-report.sarif"
    exit_code = main(
        [
            "scan",
            "examples/broken-repo",
            "--format",
            "markdown",
            "--sarif-output",
            str(sarif_path),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(sarif_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert "## Top Risks" in captured.out
    assert "## Remediation Plan" in captured.out
    assert payload["runs"][0]["results"]


def test_cli_scan_can_write_badge_sidecar(tmp_path, capsys) -> None:
    badge_path = tmp_path / "labcheck-badge.svg"
    exit_code = main(
        [
            "scan",
            "examples/broken-repo",
            "--format",
            "markdown",
            "--badge-output",
            str(badge_path),
        ]
    )
    captured = capsys.readouterr()
    badge = badge_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert "## Top Risks" in captured.out
    assert "## Understand Finding Codes" in captured.out
    assert "<svg" in badge
    assert "labcheck: 39/100" in badge


def test_cli_scan_can_write_scorecard_sidecar(tmp_path, capsys) -> None:
    scorecard_path = tmp_path / "labcheck-scorecard.md"
    exit_code = main(
        [
            "scan",
            "examples/broken-repo",
            "--format",
            "markdown",
            "--scorecard-output",
            str(scorecard_path),
        ]
    )
    captured = capsys.readouterr()
    scorecard = scorecard_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert "## Top Risks" in captured.out
    assert "# labcheck Scorecard" in scorecard
    assert "Overall score: **39/100**" in scorecard
    assert "Not handoff-ready yet" in scorecard
    assert "## Review Boundary" in scorecard
    assert "does not prove scientific validity" in scorecard
    assert "Sortable triage CSV: `labcheck scan examples/broken-repo --format csv --output labcheck-findings.csv`" in scorecard
    assert "Explain top finding: `labcheck explain LC001`" in scorecard


def test_cli_scan_can_write_target_fit_sidecar(tmp_path, capsys) -> None:
    target_fit_path = tmp_path / "labcheck-target-fit.md"
    exit_code = main(
        [
            "scan",
            "examples/broken-repo",
            "--format",
            "markdown",
            "--target-fit-output",
            str(target_fit_path),
        ]
    )
    captured = capsys.readouterr()
    target_fit = target_fit_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert "## Top Risks" in captured.out
    assert "# labcheck Target Fit" in target_fit
    assert "Fit score: **9/10**" in target_fit
    assert "strong outreach candidate" in target_fit
    assert "Safe Framing" in target_fit


def test_cli_scan_can_write_issue_draft_sidecar(tmp_path, capsys) -> None:
    issue_path = tmp_path / "labcheck-issue-draft.md"
    exit_code = main(
        [
            "scan",
            "examples/broken-repo",
            "--format",
            "markdown",
            "--issue-output",
            str(issue_path),
        ]
    )
    captured = capsys.readouterr()
    issue = issue_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert "## Top Risks" in captured.out
    assert "# labcheck Issue Draft" in issue
    assert "Suggested title: Reproducibility handoff gaps in `examples/broken-repo`" in issue
    assert "Overall score: **39/100**" in issue
    assert "No API key or hosted backend was used" in issue


def test_cli_issue_generates_maintainer_friendly_draft(tmp_path, capsys) -> None:
    issue_path = tmp_path / "labcheck-issue-draft.md"
    exit_code = main(["issue", "examples/broken-repo", "--output", str(issue_path)])
    captured = capsys.readouterr()
    issue = issue_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert captured.out == ""
    assert "# labcheck Issue Draft" in issue
    assert "Suggested title: Reproducibility handoff gaps in `examples/broken-repo`" in issue
    assert "This is not a scientific-validity judgment" in issue
    assert "Please treat this as a lightweight maintainer handoff signal" in issue
    assert "Overall score: **39/100**" in issue
    assert "## Suggested Triage" in issue
    assert "`LC001`" in issue
    assert "labcheck scorecard examples/broken-repo" in issue
    assert "No API key or hosted backend was used" in issue


def test_cli_demo_link_generates_prefilled_public_demo_url(capsys) -> None:
    exit_code = main(["demo-link", "https://github.com/owner/repo"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.strip() == "https://thomasaquinas14.github.io/labcheck/demo.html?repo=owner%2Frepo"
    assert captured.err == ""


def test_cli_demo_link_accepts_slug_and_auto_audit(capsys) -> None:
    exit_code = main(["demo-link", "owner/repo", "--auto-audit"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.strip() == "https://thomasaquinas14.github.io/labcheck/demo.html?repo=owner%2Frepo&audit=1"


def test_cli_demo_link_can_prefill_target_fit_audience(capsys) -> None:
    exit_code = main(["demo-link", "owner/repo", "--auto-audit", "--audience", "founder"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.strip() == "https://thomasaquinas14.github.io/labcheck/demo.html?repo=owner%2Frepo&audit=1&audience=founder"


def test_cli_demo_link_can_render_markdown(capsys) -> None:
    exit_code = main(["demo-link", "owner/repo", "--auto-audit", "--format", "markdown"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.strip() == (
        "[Try this repo in labcheck]"
        "(https://thomasaquinas14.github.io/labcheck/demo.html?repo=owner%2Frepo&audit=1)"
    )


def test_cli_demo_link_can_render_html(capsys) -> None:
    exit_code = main(
        [
            "demo-link",
            "owner/repo",
            "--base-url",
            "https://example.com/labcheck/demo.html?utm=outreach&source=email",
            "--format",
            "html",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out.strip() == (
        '<a href="https://example.com/labcheck/demo.html?utm=outreach'
        '&amp;source=email&amp;repo=owner%2Frepo">Try this repo in labcheck</a>'
    )


def test_cli_demo_link_accepts_custom_base_url_and_output(tmp_path, capsys) -> None:
    output_path = tmp_path / "demo-link.txt"
    exit_code = main(
        [
            "demo-link",
            "github.com/owner/repo.git",
            "--base-url",
            "https://example.com/labcheck/demo.html?utm=outreach",
            "--output",
            str(output_path),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.out == ""
    assert output_path.read_text(encoding="utf-8") == "https://example.com/labcheck/demo.html?utm=outreach&repo=owner%2Frepo"


def test_cli_demo_link_rejects_non_github_targets(capsys) -> None:
    exit_code = main(["demo-link", "https://gitlab.com/owner/repo"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "demo-link target must be owner/repo or a public GitHub repository URL" in captured.err


def test_cli_demo_repo_creates_first_run_fixture(tmp_path, capsys) -> None:
    output_dir = tmp_path / "labcheck-demo-repo"
    exit_code = main(["demo-repo", "--output-dir", str(output_dir)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Wrote labcheck demo repo" in captured.out
    assert "labcheck scorecard" in captured.out
    assert (output_dir / "README.md").exists()
    assert (output_dir / "requirements.txt").exists()
    assert (output_dir / "scripts" / "train.py").exists()
    assert (output_dir / "notebooks" / "analysis.ipynb").exists()

    scorecard_exit = main(["scorecard", str(output_dir)])
    scorecard = capsys.readouterr().out
    assert scorecard_exit == 0
    assert "# labcheck Scorecard" in scorecard
    assert "Not handoff-ready yet" in scorecard
    assert "`LC005`" in scorecard


def test_cli_demo_repo_refuses_non_empty_directory_without_force(tmp_path, capsys) -> None:
    output_dir = tmp_path / "labcheck-demo-repo"
    output_dir.mkdir()
    (output_dir / "notes.txt").write_text("keep me\n", encoding="utf-8")

    exit_code = main(["demo-repo", "--output-dir", str(output_dir)])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "Output directory is not empty" in captured.err
    assert (output_dir / "notes.txt").read_text(encoding="utf-8") == "keep me\n"

    forced_exit = main(["demo-repo", "--output-dir", str(output_dir), "--force"])
    forced = capsys.readouterr()
    assert forced_exit == 0
    assert "Wrote labcheck demo repo" in forced.out
    assert (output_dir / "notes.txt").read_text(encoding="utf-8") == "keep me\n"
    assert (output_dir / "notebooks" / "analysis.ipynb").exists()


def test_cli_pack_writes_shareable_audit_artifacts(tmp_path, capsys) -> None:
    output_dir = tmp_path / "audit-pack"
    exit_code = main(["pack", "examples/broken-repo", "--output-dir", str(output_dir)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Wrote labcheck audit pack" in captured.out
    assert "Overall score: 39" in captured.out
    assert "created labcheck-report.md" in captured.out
    assert "created MANIFEST.md" in captured.out
    assert (output_dir / "README.md").exists()
    assert (output_dir / "MANIFEST.md").exists()
    assert (output_dir / "labcheck-report.md").exists()
    assert (output_dir / "labcheck-report.html").exists()
    assert (output_dir / "labcheck-report.json").exists()
    assert (output_dir / "labcheck-report.csv").exists()
    assert (output_dir / "labcheck-report.sarif").exists()
    assert (output_dir / "labcheck-badge.svg").exists()
    assert (output_dir / "labcheck-scorecard.md").exists()
    assert (output_dir / "labcheck-target-fit.md").exists()
    assert (output_dir / "labcheck-outreach-note.md").exists()
    assert (output_dir / "labcheck-issue-draft.md").exists()

    index = (output_dir / "README.md").read_text(encoding="utf-8")
    manifest = (output_dir / "MANIFEST.md").read_text(encoding="utf-8")
    scorecard = (output_dir / "labcheck-scorecard.md").read_text(encoding="utf-8")
    target_fit = (output_dir / "labcheck-target-fit.md").read_text(encoding="utf-8")
    markdown = (output_dir / "labcheck-report.md").read_text(encoding="utf-8")
    html = (output_dir / "labcheck-report.html").read_text(encoding="utf-8")
    outreach_note = (output_dir / "labcheck-outreach-note.md").read_text(encoding="utf-8")
    issue_draft = (output_dir / "labcheck-issue-draft.md").read_text(encoding="utf-8")
    payload = json.loads((output_dir / "labcheck-report.json").read_text(encoding="utf-8"))
    csv_rows = list(csv.DictReader(io.StringIO((output_dir / "labcheck-report.csv").read_text(encoding="utf-8"))))
    sarif = json.loads((output_dir / "labcheck-report.sarif").read_text(encoding="utf-8"))
    badge = (output_dir / "labcheck-badge.svg").read_text(encoding="utf-8")

    assert "labcheck Audit Pack" in index
    assert "No API key or hosted backend is required" in index
    assert "MANIFEST.md" in index
    assert "labcheck-target-fit.md" in index
    assert "labcheck-outreach-note.md" in index
    assert "labcheck-issue-draft.md" in index
    assert "Understand finding codes" in index
    assert "`labcheck explain LC001`" in index
    assert "# labcheck Audit Pack Manifest" in manifest
    assert "This is a static, no-key first-pass audit generated locally" in manifest
    assert "| `labcheck-report.json` | Machine-readable report payload. |" in manifest
    assert "| `labcheck-report.csv` | Spreadsheet-friendly findings table for triage and assignment. |" in manifest
    assert "| `labcheck-target-fit.md` | Private go/no-go card" in manifest
    assert "| `README.md` | Quick index and suggested review order. |" in manifest
    assert "Use `labcheck-report.csv` for spreadsheet triage" in manifest
    assert "No API key or hosted backend was used" in manifest
    assert payload["summary"]["target"] == "examples/broken-repo"
    assert payload["summary"]["findings_count"] == 14
    assert csv_rows
    assert csv_rows[0]["target"] == "examples/broken-repo"
    assert sarif["version"] == "2.1.0"
    assert "labcheck: 39/100" in badge
    assert "# labcheck Scorecard" in scorecard
    assert "Not handoff-ready yet" in scorecard
    assert "## Review Boundary" in scorecard
    assert "does not prove scientific validity" in scorecard
    assert "# labcheck Target Fit" in target_fit
    assert "Fit score: **9/10**" in target_fit
    assert "strong outreach candidate" in target_fit
    assert "Safe Framing" in target_fit
    assert "## Review Boundary" in markdown
    assert "## Next Steps" in markdown
    assert "Scorecard summary: `labcheck scorecard examples/broken-repo`" in markdown
    assert "Review boundary" in html
    assert "Next steps" in html
    assert "labcheck scorecard examples/broken-repo" in html
    assert "# labcheck Outreach Note" in outreach_note
    assert "This is not a scientific-validity judgment" in outreach_note
    assert "# labcheck Issue Draft" in issue_draft
    assert "Please treat this as a lightweight maintainer handoff signal" in issue_draft


def test_cli_pack_can_create_zip_archive(tmp_path, capsys) -> None:
    output_dir = tmp_path / "audit-pack"
    exit_code = main(["pack", "examples/clean-notebook", "--output-dir", str(output_dir), "--zip"])
    captured = capsys.readouterr()
    zip_path = output_dir.with_suffix(".zip")

    assert exit_code == 0
    assert zip_path.exists()
    assert f"created {zip_path.name}" in captured.out
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())

    assert "audit-pack/README.md" in names
    assert "audit-pack/MANIFEST.md" in names
    assert "audit-pack/labcheck-scorecard.md" in names
    assert "audit-pack/labcheck-target-fit.md" in names
    assert "audit-pack/labcheck-outreach-note.md" in names
    assert "audit-pack/labcheck-issue-draft.md" in names
    assert "audit-pack/labcheck-report.html" in names
    assert "audit-pack/labcheck-report.json" in names
    assert "audit-pack/labcheck-report.csv" in names
    assert "audit-pack/labcheck-report.sarif" in names
    assert "audit-pack/labcheck-badge.svg" in names


def test_cli_pack_applies_baseline_before_writing_outputs(tmp_path, capsys) -> None:
    baseline_path = tmp_path / ".labcheck-baseline.json"
    output_dir = tmp_path / "audit-pack"
    assert main(["baseline", "examples/broken-repo", "--output", str(baseline_path)]) == 0

    exit_code = main(
        [
            "pack",
            "examples/broken-repo",
            "--baseline",
            str(baseline_path),
            "--output-dir",
            str(output_dir),
            "--min-score",
            "100",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads((output_dir / "labcheck-report.json").read_text(encoding="utf-8"))

    assert exit_code == 0
    assert "Findings: 0" in captured.out
    assert payload["summary"]["findings_count"] == 0
    assert payload["scores"]["overall_score"] == 100


def test_cli_pack_writes_artifacts_before_returning_gate_failure(tmp_path, capsys) -> None:
    output_dir = tmp_path / "audit-pack"
    exit_code = main(["pack", "examples/broken-repo", "--output-dir", str(output_dir), "--fail-on", "high"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "labcheck found 5 finding(s) at or above high severity." in captured.err
    assert (output_dir / "labcheck-report.md").exists()
    assert (output_dir / "labcheck-report.json").exists()


def test_cli_fail_on_high_returns_nonzero(capsys) -> None:
    exit_code = main(["scan", "examples/broken-repo", "--fail-on", "high"])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert "at or above high severity" in captured.err


def test_cli_fail_on_high_passes_when_no_high_findings(capsys) -> None:
    exit_code = main(["scan", "examples/clean-notebook", "--fail-on", "high"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""


def test_cli_min_score_returns_nonzero_when_score_is_too_low(capsys) -> None:
    exit_code = main(["scan", "examples/broken-repo", "--min-score", "80"])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert "score 39 is below minimum required score 80" in captured.err


def test_cli_min_score_passes_when_score_meets_threshold(capsys) -> None:
    exit_code = main(["scan", "examples/clean-notebook", "--min-score", "100"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""


def test_cli_baseline_filters_known_findings_before_min_score_gate(tmp_path, capsys) -> None:
    baseline_path = tmp_path / ".labcheck-baseline.json"
    assert main(["baseline", "examples/broken-repo", "--output", str(baseline_path)]) == 0

    exit_code = main(
        [
            "scan",
            "examples/broken-repo",
            "--baseline",
            str(baseline_path),
            "--min-score",
            "100",
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""


def test_cli_baseline_command_writes_fingerprints(tmp_path, capsys) -> None:
    baseline_path = tmp_path / ".labcheck-baseline.json"
    exit_code = main(["baseline", "examples/broken-repo", "--output", str(baseline_path)])
    captured = capsys.readouterr()
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert captured.out == ""
    assert payload["version"] == 1
    assert payload["findings"]
    assert payload["findings"][0]["fingerprint"].startswith("v1:")


def test_cli_baseline_filters_known_findings_before_fail_gate(tmp_path, capsys) -> None:
    baseline_path = tmp_path / ".labcheck-baseline.json"
    report_path = tmp_path / "report.json"
    assert main(["baseline", "examples/broken-repo", "--output", str(baseline_path)]) == 0

    exit_code = main(
        [
            "scan",
            "examples/broken-repo",
            "--format",
            "json",
            "--output",
            str(report_path),
            "--baseline",
            str(baseline_path),
            "--fail-on",
            "high",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert captured.err == ""
    assert payload["summary"]["findings_count"] == 0
    assert payload["scores"]["overall_score"] == 100


def test_cli_scan_uses_config_excludes(tmp_path, capsys) -> None:
    config_path = tmp_path / "labcheck.toml"
    config_path.write_text('exclude = ["skip.py"]\n', encoding="utf-8")
    (tmp_path / "skip.py").write_text("import random\nrandom.random()\n", encoding="utf-8")

    exit_code = main(["scan", str(tmp_path), "--format", "json", "--config", str(config_path)])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["summary"]["python_files"] == 0
    assert payload["findings"] == []


def test_cli_baseline_uses_config_excludes(tmp_path, capsys) -> None:
    config_path = tmp_path / "labcheck.toml"
    baseline_path = tmp_path / ".labcheck-baseline.json"
    config_path.write_text('exclude = ["skip.py"]\n', encoding="utf-8")
    (tmp_path / "skip.py").write_text("import random\nrandom.random()\n", encoding="utf-8")

    exit_code = main(["baseline", str(tmp_path), "--config", str(config_path), "--output", str(baseline_path)])
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["findings"] == []


def test_cli_graph_uses_config_excludes(tmp_path, capsys) -> None:
    config_path = tmp_path / "labcheck.toml"
    config_path.write_text('exclude = ["skip.py"]\n', encoding="utf-8")
    (tmp_path / "skip.py").write_text("print('skip')\n", encoding="utf-8")

    exit_code = main(["graph", str(tmp_path), "--config", str(config_path)])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["summary"]["python_files"] == 0
    assert payload["graph"]["nodes"] == []


def test_cli_init_writes_config_and_workflow(tmp_path, capsys) -> None:
    exit_code = main(["init", str(tmp_path)])
    captured = capsys.readouterr()
    config_path = tmp_path / ".labcheck.toml"
    workflow_path = tmp_path / ".github" / "workflows" / "labcheck.yml"

    assert exit_code == 0
    assert config_path.exists()
    assert workflow_path.exists()
    assert "created .labcheck.toml" in captured.out
    assert "id: labcheck" in workflow_path.read_text(encoding="utf-8")
    assert "permissions:" in workflow_path.read_text(encoding="utf-8")
    assert "contents: read" in workflow_path.read_text(encoding="utf-8")
    assert "config-path: .labcheck.toml" in workflow_path.read_text(encoding="utf-8")
    assert "disabled_checks" in config_path.read_text(encoding="utf-8")
    assert "[[ignored_findings]]" in config_path.read_text(encoding="utf-8")
    assert "archive/old_experiment.py" in config_path.read_text(encoding="utf-8")
    assert "labcheck-audit/**" in config_path.read_text(encoding="utf-8")
    assert 'max-findings: "100"' in workflow_path.read_text(encoding="utf-8")
    assert 'min-score: ""' in workflow_path.read_text(encoding="utf-8")
    assert "csv-path: labcheck-report.csv" in workflow_path.read_text(encoding="utf-8")
    assert "labcheck-report.csv" in workflow_path.read_text(encoding="utf-8")
    assert "badge-path: labcheck-badge.svg" in workflow_path.read_text(encoding="utf-8")
    assert "labcheck-badge.svg" in workflow_path.read_text(encoding="utf-8")
    assert "scorecard-path: labcheck-scorecard.md" in workflow_path.read_text(encoding="utf-8")
    assert "labcheck-scorecard.md" in workflow_path.read_text(encoding="utf-8")
    assert "target-fit-path: labcheck-target-fit.md" in workflow_path.read_text(encoding="utf-8")
    assert "labcheck-target-fit.md" in workflow_path.read_text(encoding="utf-8")
    assert "issue-draft-path: labcheck-issue-draft.md" in workflow_path.read_text(encoding="utf-8")
    assert "labcheck-issue-draft.md" in workflow_path.read_text(encoding="utf-8")
    assert "if: always()" in workflow_path.read_text(encoding="utf-8")
    assert "if-no-files-found: warn" in workflow_path.read_text(encoding="utf-8")
    assert "retention-days: 14" in workflow_path.read_text(encoding="utf-8")


def test_cli_init_policy_writes_reproducibility_policy(tmp_path, capsys) -> None:
    exit_code = main(["init", str(tmp_path), "--no-workflow", "--policy"])
    captured = capsys.readouterr()
    policy_path = tmp_path / "docs" / "reproducibility.md"

    assert exit_code == 0
    assert policy_path.exists()
    assert "created docs/reproducibility.md" in captured.out
    policy = policy_path.read_text(encoding="utf-8")
    assert "Expected handoff standard" in policy
    assert "labcheck scorecard . --config .labcheck.toml" in policy
    assert "labcheck scan . --config .labcheck.toml" in policy
    assert "[[ignored_findings]]" in policy
    assert "Python runtime version" in policy
    assert "Reviewer checklist" in policy
    assert not (tmp_path / ".github" / "workflows" / "labcheck.yml").exists()


def test_cli_init_does_not_overwrite_without_force(tmp_path, capsys) -> None:
    config_path = tmp_path / ".labcheck.toml"
    config_path.write_text('exclude = ["custom/**"]\n', encoding="utf-8")

    exit_code = main(["init", str(tmp_path), "--no-workflow"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert config_path.read_text(encoding="utf-8") == 'exclude = ["custom/**"]\n'
    assert "skipped .labcheck.toml (already exists)" in captured.out


def test_cli_init_force_overwrites_existing_files(tmp_path, capsys) -> None:
    config_path = tmp_path / ".labcheck.toml"
    config_path.write_text('exclude = ["custom/**"]\n', encoding="utf-8")

    exit_code = main(["init", str(tmp_path), "--no-workflow", "--force"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "custom/**" not in config_path.read_text(encoding="utf-8")
    assert "created .labcheck.toml" in captured.out


def test_cli_init_no_workflow_only_writes_config(tmp_path, capsys) -> None:
    exit_code = main(["init", str(tmp_path), "--no-workflow"])

    assert exit_code == 0
    assert (tmp_path / ".labcheck.toml").exists()
    assert not (tmp_path / ".github" / "workflows" / "labcheck.yml").exists()


def test_cli_doctor_reports_ready_for_existing_target(tmp_path, capsys) -> None:
    config_path = tmp_path / ".labcheck.toml"
    config_path.write_text("exclude = []\n", encoding="utf-8")

    exit_code = main(["doctor", str(tmp_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "labcheck doctor" in captured.out
    assert "OK   labcheck version:" in captured.out
    assert "OK   Python runtime:" in captured.out
    assert "OK   target:" in captured.out
    assert "OK   config:" in captured.out
    assert "OK   checks registered: 77" in captured.out
    assert f"Next: labcheck scan {tmp_path} --config {config_path}" in captured.out


def test_cli_doctor_warns_when_default_config_is_missing(tmp_path, capsys) -> None:
    exit_code = main(["doctor", str(tmp_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "WARN config: no .labcheck.toml found; defaults will be used" in captured.out
    assert f"Next: labcheck scan {tmp_path}" in captured.out


def test_cli_doctor_fails_for_missing_target(tmp_path, capsys) -> None:
    missing_target = tmp_path / "missing"

    exit_code = main(["doctor", str(missing_target)])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert f"FAIL target: {missing_target} does not exist" in captured.out
    assert "Fix the failing preflight item(s)" in captured.out


def test_cli_doctor_fails_for_missing_explicit_config(tmp_path, capsys) -> None:
    missing_config = tmp_path / "missing.toml"

    exit_code = main(["doctor", str(tmp_path), "--config", str(missing_config)])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert f"FAIL config: {missing_config} does not exist" in captured.out


def test_cli_doctor_accepts_public_github_url_without_cloning(capsys) -> None:
    exit_code = main(["doctor", "https://github.com/owner/repo"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "OK   target: https://github.com/owner/repo (public GitHub repo URL)" in captured.out
    assert "Next: labcheck scan https://github.com/owner/repo" in captured.out


def test_action_metadata_exposes_ci_inputs() -> None:
    metadata = Path("action.yml").read_text(encoding="utf-8")
    assert "using: \"composite\"" in metadata
    assert "overall-score:" in metadata
    assert "environment-score:" in metadata
    assert "determinism-score:" in metadata
    assert "artifact-score:" in metadata
    assert "portability-score:" in metadata
    assert "onboarding-score:" in metadata
    assert "findings-count:" in metadata
    assert "high-count:" in metadata
    assert "medium-count:" in metadata
    assert "low-count:" in metadata
    assert "triage-status:" in metadata
    assert "triage-signal:" in metadata
    assert "top-risk-id:" in metadata
    assert "top-risk-title:" in metadata
    assert "top-risk-count:" in metadata
    assert "steps.run.outputs.overall-score" in metadata
    assert "steps.run.outputs.triage-signal" in metadata
    assert "steps.run.outputs.top-risk-id" in metadata
    assert "baseline-path:" in metadata
    assert "config-path:" in metadata
    assert "job-summary:" in metadata
    assert "fail-on:" in metadata
    assert "min-score:" in metadata
    assert "max-findings:" in metadata
    assert "csv-path:" in metadata
    assert "badge-path:" in metadata
    assert "scorecard-path:" in metadata
    assert "target-fit-path:" in metadata
    assert "issue-draft-path:" in metadata
    assert "compare-base-json-path:" in metadata
    assert "compare-path:" in metadata
    assert "GITHUB_STEP_SUMMARY" in metadata
    assert "LABCHECK_EXIT_CODE" in metadata
    assert "LABCHECK_COMPARE_EXIT_CODE" in metadata
    assert "--baseline" in metadata
    assert "--config" in metadata
    assert "--json-output" in metadata
    assert "--csv-output" in metadata
    assert "--sarif-output" in metadata
    assert "--badge-output" in metadata
    assert "--scorecard-output" in metadata
    assert "--target-fit-output" in metadata
    assert "--issue-output" in metadata
    assert "labcheck compare" in metadata
    assert "--fail-on" in metadata
    assert "--min-score" in metadata
    assert "--max-findings" in metadata
    assert "severity_counts" in metadata


def test_ci_workflow_smoke_uploads_badge_artifact() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "id: labcheck" in workflow
    assert "csv-path: labcheck-report.csv" in workflow
    assert "labcheck-report.csv" in workflow
    assert "badge-path: labcheck-badge.svg" in workflow
    assert "labcheck-badge.svg" in workflow
    assert "scorecard-path: labcheck-scorecard.md" in workflow
    assert "labcheck-scorecard.md" in workflow
    assert "target-fit-path: labcheck-target-fit.md" in workflow
    assert "labcheck-target-fit.md" in workflow
    assert "issue-draft-path: labcheck-issue-draft.md" in workflow
    assert "labcheck-issue-draft.md" in workflow
    assert "compare-base-json-path: previous-labcheck-report.json" in workflow
    assert "compare-path: labcheck-compare.md" in workflow
    assert "labcheck-compare.md" in workflow
    assert "GITHUB_STEP_SUMMARY" in workflow
    assert "if-no-files-found: warn" in workflow
    assert "retention-days: 14" in workflow
    assert "steps.labcheck.outputs.overall-score" in workflow
    assert "steps.labcheck.outputs.triage-signal" in workflow
    assert "steps.labcheck.outputs.top-risk-id" in workflow


def test_action_guide_documents_review_patterns() -> None:
    guide = Path("docs/github-action.md").read_text(encoding="utf-8")
    assert "Copy-paste PR summary" in guide
    assert "GITHUB_STEP_SUMMARY" in guide
    assert "Optional sticky PR comment" in guide
    assert "contents: read" in guide
    assert "does not need repository secrets or write permissions" in guide
    assert "pull-requests: write" in guide
    assert "if-no-files-found: warn" in guide
    assert "retention-days: 14" in guide
    assert "actions/github-script@v7" in guide
    assert "github.rest.issues.updateComment" in guide
    assert "steps.labcheck.outputs.overall-score" in guide
    assert "steps.labcheck.outputs.findings-count" in guide
    assert "steps.labcheck.outputs.triage-signal" in guide
    assert "steps.labcheck.outputs.top-risk-id" in guide
    assert "triage-status" in guide
    assert "triage-signal" in guide
    assert "Triage" in guide
    assert "Top risk" in guide
    assert "labcheck pack ." in guide
    assert "--output-dir labcheck-audit" in guide
    assert "--zip" in guide
    assert "csv-path: labcheck-report.csv" in guide
    assert "labcheck-report.csv" in guide
    assert "scorecard-path: labcheck-scorecard.md" in guide
    assert "--scorecard-output labcheck-scorecard.md" in guide
    assert "labcheck-scorecard.md" in guide
    assert "target-fit-path: labcheck-target-fit.md" in guide
    assert "--target-fit-output labcheck-target-fit.md" in guide
    assert "labcheck-target-fit.md" in guide
    assert "issue-draft-path: labcheck-issue-draft.md" in guide
    assert "--issue-output labcheck-issue-draft.md" in guide
    assert "labcheck-issue-draft.md" in guide
    assert "Before/After Compare In CI" in guide
    assert "compare-base-json-path: previous-labcheck-report.json" in guide
    assert "compare-path: labcheck-compare.md" in guide
    assert "score deltas, severity deltas, resolved findings, and new findings" in guide


def test_cli_checks_command(capsys) -> None:
    exit_code = main(["checks"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "LC002" in captured.out
    assert "LC010" in captured.out
    assert "LC011" in captured.out
    assert "LC012" in captured.out
    assert "LC013" in captured.out
    assert "LC014" in captured.out
    assert "LC015" in captured.out
    assert "LC016" in captured.out
    assert "LC017" in captured.out
    assert "LC018" in captured.out
    assert "LC019" in captured.out
    assert "LC020" in captured.out
    assert "LC021" in captured.out
    assert "LC022" in captured.out
    assert "LC023" in captured.out
    assert "LC024" in captured.out
    assert "LC025" in captured.out
    assert "LC026" in captured.out
    assert "LC027" in captured.out
    assert "LC028" in captured.out
    assert "LC029" in captured.out
    assert "LC030" in captured.out
    assert "LC031" in captured.out
    assert "LC032" in captured.out
    assert "LC033" in captured.out
    assert "LC034" in captured.out
    assert "LC035" in captured.out
    assert "LC036" in captured.out
    assert "LC037" in captured.out
    assert "LC038" in captured.out
    assert "LC039" in captured.out
    assert "LC040" in captured.out
    assert "LC041" in captured.out
    assert "LC042" in captured.out
    assert "LC043" in captured.out
    assert "LC044" in captured.out
    assert "LC045" in captured.out
    assert "LC046" in captured.out
    assert "LC047" in captured.out
    assert "LC048" in captured.out
    assert "LC049" in captured.out
    assert "LC050" in captured.out
    assert "LC051" in captured.out
    assert "LC052" in captured.out
    assert "LC053" in captured.out
    assert "LC054" in captured.out
    assert "LC055" in captured.out
    assert "LC056" in captured.out
    assert "LC057" in captured.out
    assert "LC058" in captured.out
    assert "LC059" in captured.out
    assert "LC060" in captured.out
    assert "LC061" in captured.out
    assert "LC062" in captured.out
    assert "LC063" in captured.out
    assert "LC064" in captured.out
    assert "LC065" in captured.out
    assert "LC066" in captured.out
    assert "LC067" in captured.out
    assert "LC068" in captured.out
    assert "LC069" in captured.out
    assert "LC070" in captured.out
    assert "LC071" in captured.out
    assert "LC072" in captured.out
    assert "LC073" in captured.out
    assert "LC074" in captured.out
    assert "LC075" in captured.out
    assert "LC076" in captured.out
    assert "LC077" in captured.out
    assert "LC009" in captured.out
    assert "LC001" in captured.out
    assert "labcheck checks --category determinism" in captured.out
    assert "Run `labcheck explain LC005`" in captured.out


def test_cli_checks_command_filters_by_category(capsys) -> None:
    exit_code = main(["checks", "--category", "determinism"])
    captured = capsys.readouterr()
    check_rows = [line for line in captured.out.splitlines() if line.startswith("- LC")]
    assert exit_code == 0
    assert "Supported checks (category=determinism):" in captured.out
    assert "LC001" in captured.out
    assert "LC061" in captured.out
    assert "LC074" in captured.out
    assert "LC075" in captured.out
    assert "LC076" in captured.out
    assert not any("LC003" in row for row in check_rows)
    assert not any("LC005" in row for row in check_rows)

    artifacts_exit = main(["checks", "--category", "artifacts"])
    artifacts = capsys.readouterr()
    assert artifacts_exit == 0
    assert "LC077" in artifacts.out

    onboarding_exit = main(["checks", "--category", "onboarding"])
    onboarding = capsys.readouterr()
    onboarding_rows = [line for line in onboarding.out.splitlines() if line.startswith("- LC")]
    assert onboarding_exit == 0
    assert "LC062" in onboarding.out
    assert "LC063" in onboarding.out
    assert "LC064" in onboarding.out
    assert "LC065" in onboarding.out
    assert "LC066" in onboarding.out
    assert "LC067" in onboarding.out
    assert "LC068" in onboarding.out
    assert "LC069" in onboarding.out
    assert "LC070" in onboarding.out
    assert "LC071" in onboarding.out
    assert "LC072" in onboarding.out
    assert "LC073" in onboarding.out
    assert any("Markdown link references a missing local file" in row for row in onboarding_rows)
    assert any("Missing reuse license metadata" in row for row in onboarding_rows)
    assert any("Missing citation metadata" in row for row in onboarding_rows)
    assert any("Docker Compose dependency references missing service" in row for row in onboarding_rows)
    assert any("Docker Compose service references missing network" in row for row in onboarding_rows)
    assert any("Docker Compose healthcheck references missing script" in row for row in onboarding_rows)
    assert any("Docker Compose secret/config references missing file" in row for row in onboarding_rows)
    assert any("Docker Compose service env_file references missing file" in row for row in onboarding_rows)
    assert any("Docker Compose extends references missing file or service" in row for row in onboarding_rows)
    assert any("Docker Compose include references missing file" in row for row in onboarding_rows)
    assert any("Docker Compose service label_file references missing file" in row for row in onboarding_rows)
    assert any("Docker Compose develop watch references missing path" in row for row in onboarding_rows)


def test_cli_checks_command_filters_by_severity(capsys) -> None:
    exit_code = main(["checks", "--severity", "high"])
    captured = capsys.readouterr()
    check_rows = [line for line in captured.out.splitlines() if line.startswith("- LC")]
    assert exit_code == 0
    assert "Supported checks (severity=high):" in captured.out
    assert "LC005" in captured.out
    assert "LC054" in captured.out
    assert not any("LC004" in row for row in check_rows)


def test_cli_checks_command_searches_catalog_text(capsys) -> None:
    exit_code = main(["checks", "--search", "seed"])
    captured = capsys.readouterr()
    check_rows = [line for line in captured.out.splitlines() if line.startswith("- LC")]
    assert exit_code == 0
    assert 'Supported checks (search="seed"):' in captured.out
    assert "LC007" in captured.out
    assert "LC060" in captured.out
    assert "LC061" in captured.out
    assert not any("LC005" in row for row in check_rows)


def test_cli_checks_command_reports_empty_filter(capsys) -> None:
    exit_code = main(["checks", "--category", "artifacts", "--search", "prng"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert 'Supported checks (category=artifacts, search="prng"):' in captured.out
    assert "No checks matched these filters" in captured.out


def test_cli_explain_command_describes_check(capsys) -> None:
    exit_code = main(["explain", "LC005"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "LC005 - Referenced input artifact missing from repo" in captured.out
    assert "Default severity: high" in captured.out
    assert "Suggested fix:" in captured.out


def test_cli_explain_command_can_render_markdown(capsys) -> None:
    exit_code = main(["explain", "LC005", "--format", "markdown"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "# LC005 - Referenced input artifact missing from repo" in captured.out
    assert "- Default severity: `high`" in captured.out
    assert "## Detects" in captured.out
    assert "## Suggested Fix" in captured.out
    assert "labcheck checks --category artifacts" in captured.out


def test_cli_explain_command_can_render_json(capsys) -> None:
    exit_code = main(["explain", "LC005", "--format", "json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["check_id"] == "LC005"
    assert payload["title"] == "Referenced input artifact missing from repo"
    assert payload["default_severity"] == "high"
    assert payload["category"] == "artifacts"
    assert payload["related_command"] == "labcheck checks --category artifacts"


def test_cli_explain_command_accepts_lowercase_code(capsys) -> None:
    exit_code = main(["explain", "lc009"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "LC009 - Committed output has no visible producer" in captured.out


def test_cli_explain_command_rejects_unknown_code(capsys) -> None:
    exit_code = main(["explain", "LC999"])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "Unknown labcheck finding code: LC999" in captured.err
    assert "labcheck checks" in captured.err


def test_cli_markdown_output_includes_top_risks(capsys) -> None:
    exit_code = main(["scan", "examples/broken-repo", "--format", "markdown"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "## Top Risks" in captured.out
    assert "## Remediation Plan" in captured.out
    assert "LC002" in captured.out


def test_cli_markdown_output_can_cap_detailed_findings(capsys) -> None:
    exit_code = main(["scan", "examples/broken-repo", "--format", "markdown", "--max-findings", "2"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Showing first 2 findings;" in captured.out
    assert "Use `--max-findings all`" in captured.out
    assert captured.out.count("### ") == 2


def test_cli_markdown_output_can_hide_detailed_findings(capsys) -> None:
    exit_code = main(["scan", "examples/broken-repo", "--format", "markdown", "--max-findings", "0"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Showing first 0 findings;" in captured.out
    assert "No detailed findings shown." in captured.out
    assert "No findings." not in captured.out


def test_cli_markdown_output_can_show_all_findings(capsys) -> None:
    exit_code = main(["scan", "examples/broken-repo", "--format", "markdown", "--max-findings", "all"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "omitted" not in captured.out
    assert "LC010 - Workflow node is disconnected from data lineage" in captured.out
    assert "LC011 - Notebook contains saved error output" in captured.out


def test_cli_json_output_ignores_human_finding_cap(capsys) -> None:
    exit_code = main(["scan", "examples/broken-repo", "--format", "json", "--max-findings", "1"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["summary"]["findings_count"] == len(payload["findings"])
    assert len(payload["findings"]) > 1


def test_cli_badge_command_writes_svg(tmp_path, capsys) -> None:
    badge_path = tmp_path / "badge.svg"
    exit_code = main(["badge", "examples/broken-repo", "--output", str(badge_path)])
    captured = capsys.readouterr()
    badge = badge_path.read_text(encoding="utf-8")
    assert exit_code == 0
    assert captured.out == ""
    assert badge.startswith("<svg")
    assert "labcheck: 39/100" in badge
    assert "#b91c1c" in badge


def test_cli_scorecard_command_outputs_compact_markdown(capsys) -> None:
    exit_code = main(["scorecard", "examples/broken-repo"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "# labcheck Scorecard" in captured.out
    assert "Overall score: **39/100**" in captured.out
    assert "Findings: **14**" in captured.out
    assert "Not handoff-ready yet" in captured.out
    assert "## Review Boundary" in captured.out
    assert "does not prove scientific validity" in captured.out
    assert "## Top Risks" in captured.out
    assert "`LC002`" in captured.out
    assert "Full Markdown report:" in captured.out
    assert "Sortable triage CSV:" in captured.out
    assert "Shareable audit bundle:" in captured.out


def test_cli_scorecard_can_write_output_file(tmp_path, capsys) -> None:
    output_path = tmp_path / "scorecard.md"

    exit_code = main(["scorecard", "examples/clean-notebook", "--output", str(output_path)])
    captured = capsys.readouterr()
    scorecard = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert captured.out == ""
    assert "# labcheck Scorecard" in scorecard
    assert "Overall score: **100/100**" in scorecard
    assert "Strong handoff candidate" in scorecard
    assert "## Review Boundary" in scorecard
    assert "does not prove scientific validity" in scorecard
    assert "No top risks." in scorecard


def test_cli_scorecard_applies_baseline(tmp_path, capsys) -> None:
    baseline_path = tmp_path / ".labcheck-baseline.json"
    assert main(["baseline", "examples/broken-repo", "--output", str(baseline_path)]) == 0

    exit_code = main(["scorecard", "examples/broken-repo", "--baseline", str(baseline_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Findings: **0**" in captured.out
    assert "Strong handoff candidate" in captured.out
    assert "No top risks." in captured.out


def test_cli_target_fit_command_outputs_outreach_score(capsys) -> None:
    exit_code = main(["target-fit", "examples/broken-repo", "--audience", "founder"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "# labcheck Target Fit" in captured.out
    assert "Audience: `founder`" in captured.out
    assert "Fit score: **10/10**" in captured.out
    assert "strong outreach candidate" in captured.out
    assert "Founder fit" in captured.out
    assert "Top risk:" in captured.out
    assert "This is a static, no-key first-pass audit" in captured.out
    assert "labcheck outreach examples/broken-repo --audience founder" in captured.out


def test_cli_target_fit_can_write_output_file(tmp_path, capsys) -> None:
    output_path = tmp_path / "labcheck-target-fit.md"

    exit_code = main(["target-fit", "examples/clean-notebook", "--output", str(output_path)])
    captured = capsys.readouterr()
    fit = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert captured.out == ""
    assert "# labcheck Target Fit" in fit
    assert "Fit score: **2/10**" in fit
    assert "weak outreach candidate" in fit


def test_cli_outreach_command_outputs_ready_to_edit_note(capsys) -> None:
    exit_code = main(
        [
            "outreach",
            "examples/broken-repo",
            "--recipient",
            "Dr. Ada",
            "--sender",
            "Thomas",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "# labcheck Outreach Note" in captured.out
    assert "Hi Dr. Ada," in captured.out
    assert "Overall score: **39/100**" in captured.out
    assert "Top risk:" in captured.out
    assert "This is not a scientific-validity judgment" in captured.out
    assert "Best,\nThomas" in captured.out
    assert "Browser demo:" not in captured.out


def test_cli_outreach_command_accepts_audience(capsys) -> None:
    exit_code = main(
        [
            "outreach",
            "examples/broken-repo",
            "--audience",
            "founder",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Subject: Quick ML repo onboarding and diligence check" in captured.out
    assert "new engineer, technical lead, or diligence reviewer" in captured.out
    assert "onboarding-ready fix" in captured.out


def test_cli_outreach_can_write_output_file(tmp_path, capsys) -> None:
    output_path = tmp_path / "labcheck-outreach-note.md"

    exit_code = main(["outreach", "examples/clean-notebook", "--output", str(output_path)])
    captured = capsys.readouterr()
    note = output_path.read_text(encoding="utf-8")

    assert exit_code == 0
    assert captured.out == ""
    assert "# labcheck Outreach Note" in note
    assert "Overall score: **100/100**" in note
    assert "I did not find a top reproducibility risk" in note


def test_cli_graph_command(capsys) -> None:
    exit_code = main(["graph", "examples/broken-repo"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert len(payload["graph"]["nodes"]) >= 4


def test_cli_html_output(capsys) -> None:
    exit_code = main(["scan", "examples/broken-repo", "--format", "html"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "<html" in captured.out
    assert "labcheck Report" in captured.out
    assert "Top risks" in captured.out
    assert "Remediation plan" in captured.out
    assert "<svg" in captured.out
