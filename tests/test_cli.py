from __future__ import annotations

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
    assert "## Top Risks" in captured.out
    assert "## Remediation Plan" in captured.out
    assert payload["summary"]["findings_count"] >= 8


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
    assert "<svg" in badge
    assert "labcheck: 44/100" in badge


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
    assert "Overall score: **44/100**" in scorecard
    assert "Not handoff-ready yet" in scorecard


def test_cli_pack_writes_shareable_audit_artifacts(tmp_path, capsys) -> None:
    output_dir = tmp_path / "audit-pack"
    exit_code = main(["pack", "examples/broken-repo", "--output-dir", str(output_dir)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Wrote labcheck audit pack" in captured.out
    assert "Overall score: 44" in captured.out
    assert "created labcheck-report.md" in captured.out
    assert (output_dir / "README.md").exists()
    assert (output_dir / "labcheck-report.md").exists()
    assert (output_dir / "labcheck-report.html").exists()
    assert (output_dir / "labcheck-report.json").exists()
    assert (output_dir / "labcheck-report.sarif").exists()
    assert (output_dir / "labcheck-badge.svg").exists()
    assert (output_dir / "labcheck-scorecard.md").exists()

    index = (output_dir / "README.md").read_text(encoding="utf-8")
    scorecard = (output_dir / "labcheck-scorecard.md").read_text(encoding="utf-8")
    payload = json.loads((output_dir / "labcheck-report.json").read_text(encoding="utf-8"))
    sarif = json.loads((output_dir / "labcheck-report.sarif").read_text(encoding="utf-8"))
    badge = (output_dir / "labcheck-badge.svg").read_text(encoding="utf-8")

    assert "labcheck Audit Pack" in index
    assert "No API key or hosted backend is required" in index
    assert payload["summary"]["target"] == "examples/broken-repo"
    assert payload["summary"]["findings_count"] == 12
    assert sarif["version"] == "2.1.0"
    assert "labcheck: 44/100" in badge
    assert "# labcheck Scorecard" in scorecard
    assert "Not handoff-ready yet" in scorecard


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
    assert "audit-pack/labcheck-scorecard.md" in names
    assert "audit-pack/labcheck-report.html" in names
    assert "audit-pack/labcheck-report.json" in names
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
    assert "labcheck found 4 finding(s) at or above high severity." in captured.err
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
    assert "score 44 is below minimum required score 80" in captured.err


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
    assert "config-path: .labcheck.toml" in workflow_path.read_text(encoding="utf-8")
    assert "disabled_checks" in config_path.read_text(encoding="utf-8")
    assert "labcheck-audit/**" in config_path.read_text(encoding="utf-8")
    assert 'max-findings: "100"' in workflow_path.read_text(encoding="utf-8")
    assert 'min-score: ""' in workflow_path.read_text(encoding="utf-8")
    assert "badge-path: labcheck-badge.svg" in workflow_path.read_text(encoding="utf-8")
    assert "labcheck-badge.svg" in workflow_path.read_text(encoding="utf-8")
    assert "scorecard-path: labcheck-scorecard.md" in workflow_path.read_text(encoding="utf-8")
    assert "labcheck-scorecard.md" in workflow_path.read_text(encoding="utf-8")


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
    assert "OK   checks registered: 17" in captured.out
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
    assert "steps.run.outputs.overall-score" in metadata
    assert "baseline-path:" in metadata
    assert "config-path:" in metadata
    assert "job-summary:" in metadata
    assert "fail-on:" in metadata
    assert "min-score:" in metadata
    assert "max-findings:" in metadata
    assert "badge-path:" in metadata
    assert "scorecard-path:" in metadata
    assert "GITHUB_STEP_SUMMARY" in metadata
    assert "LABCHECK_EXIT_CODE" in metadata
    assert "--baseline" in metadata
    assert "--config" in metadata
    assert "--json-output" in metadata
    assert "--sarif-output" in metadata
    assert "--badge-output" in metadata
    assert "--scorecard-output" in metadata
    assert "--fail-on" in metadata
    assert "--min-score" in metadata
    assert "--max-findings" in metadata
    assert "severity_counts" in metadata


def test_ci_workflow_smoke_uploads_badge_artifact() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "id: labcheck" in workflow
    assert "badge-path: labcheck-badge.svg" in workflow
    assert "labcheck-badge.svg" in workflow
    assert "scorecard-path: labcheck-scorecard.md" in workflow
    assert "labcheck-scorecard.md" in workflow
    assert "GITHUB_STEP_SUMMARY" in workflow
    assert "steps.labcheck.outputs.overall-score" in workflow


def test_action_guide_documents_review_patterns() -> None:
    guide = Path("docs/github-action.md").read_text(encoding="utf-8")
    assert "Copy-paste PR summary" in guide
    assert "GITHUB_STEP_SUMMARY" in guide
    assert "Optional sticky PR comment" in guide
    assert "pull-requests: write" in guide
    assert "actions/github-script@v7" in guide
    assert "github.rest.issues.updateComment" in guide
    assert "steps.labcheck.outputs.overall-score" in guide
    assert "steps.labcheck.outputs.findings-count" in guide
    assert "labcheck pack ." in guide
    assert "--output-dir labcheck-audit" in guide
    assert "--zip" in guide
    assert "scorecard-path: labcheck-scorecard.md" in guide
    assert "--scorecard-output labcheck-scorecard.md" in guide
    assert "labcheck-scorecard.md" in guide


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
    assert "LC009" in captured.out
    assert "LC001" in captured.out
    assert "Run `labcheck explain LC005`" in captured.out


def test_cli_explain_command_describes_check(capsys) -> None:
    exit_code = main(["explain", "LC005"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "LC005 - Referenced input artifact missing from repo" in captured.out
    assert "Default severity: high" in captured.out
    assert "Suggested fix:" in captured.out


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
    assert "labcheck: 44/100" in badge
    assert "#b91c1c" in badge


def test_cli_scorecard_command_outputs_compact_markdown(capsys) -> None:
    exit_code = main(["scorecard", "examples/broken-repo"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "# labcheck Scorecard" in captured.out
    assert "Overall score: **44/100**" in captured.out
    assert "Findings: **12**" in captured.out
    assert "Not handoff-ready yet" in captured.out
    assert "## Top Risks" in captured.out
    assert "`LC002`" in captured.out
    assert "Full Markdown report:" in captured.out
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
