from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap


def _run_blocks(action_text: str) -> list[str]:
    """Return composite-action shell blocks without needing a YAML parser."""
    lines = action_text.splitlines()
    blocks: list[str] = []
    for index, line in enumerate(lines):
        if line.strip() != "run: |":
            continue
        base_indent = len(line) - len(line.lstrip())
        block_lines: list[str] = []
        for candidate in lines[index + 1 :]:
            if not candidate.strip():
                block_lines.append(candidate)
                continue
            indent = len(candidate) - len(candidate.lstrip())
            if indent <= base_indent:
                break
            block_lines.append(candidate)
        blocks.append("\n".join(block_lines))
    return blocks


def _embedded_output_python(action_text: str) -> str:
    for block in _run_blocks(action_text):
        lines = block.splitlines()
        for index, line in enumerate(lines):
            if 'python - "$LABCHECK_JSON_PATH" <<\'PY\'' not in line:
                continue
            script_lines: list[str] = []
            for candidate in lines[index + 1 :]:
                if candidate.strip() == "PY":
                    return textwrap.dedent("\n".join(script_lines))
                script_lines.append(candidate)
    raise AssertionError("Could not find embedded Action output Python block")


def test_composite_action_does_not_interpolate_inputs_inside_shell_blocks() -> None:
    action = Path("action.yml").read_text(encoding="utf-8")

    run_blocks = _run_blocks(action)

    assert run_blocks
    assert all("${{ inputs." not in block for block in run_blocks)
    assert 'labcheck scan "$LABCHECK_TARGET"' in action
    assert 'python - "$LABCHECK_JSON_PATH"' in action


def test_composite_action_maps_public_inputs_to_environment_variables() -> None:
    action = Path("action.yml").read_text(encoding="utf-8")

    expected_mappings = [
        "LABCHECK_TARGET: ${{ inputs.target }}",
        "LABCHECK_REPORT_FORMAT: ${{ inputs.report-format }}",
        "LABCHECK_REPORT_PATH: ${{ inputs.report-path }}",
        "LABCHECK_JSON_PATH: ${{ inputs.json-path }}",
        "LABCHECK_CSV_PATH: ${{ inputs.csv-path }}",
        "LABCHECK_SARIF_PATH: ${{ inputs.sarif-path }}",
        "LABCHECK_BADGE_PATH: ${{ inputs.badge-path }}",
        "LABCHECK_SCORECARD_PATH: ${{ inputs.scorecard-path }}",
        "LABCHECK_TARGET_FIT_PATH: ${{ inputs.target-fit-path }}",
        "LABCHECK_ISSUE_DRAFT_PATH: ${{ inputs.issue-draft-path }}",
        "LABCHECK_COMPARE_BASE_JSON_PATH: ${{ inputs.compare-base-json-path }}",
        "LABCHECK_COMPARE_PATH: ${{ inputs.compare-path }}",
        "LABCHECK_BASELINE_PATH: ${{ inputs.baseline-path }}",
        "LABCHECK_CONFIG_PATH: ${{ inputs.config-path }}",
        "LABCHECK_MAX_FINDINGS: ${{ inputs.max-findings }}",
        "LABCHECK_JOB_SUMMARY: ${{ inputs.job-summary }}",
        "LABCHECK_FAIL_ON: ${{ inputs.fail-on }}",
        "LABCHECK_MIN_SCORE: ${{ inputs.min-score }}",
    ]

    for mapping in expected_mappings:
        assert mapping in action


def test_composite_action_has_marketplace_branding() -> None:
    action = Path("action.yml").read_text(encoding="utf-8")

    assert 'branding:' in action
    assert 'icon: "search"' in action
    assert 'color: "green"' in action


def test_composite_action_exposes_top_risk_outputs() -> None:
    action = Path("action.yml").read_text(encoding="utf-8")

    assert "top-risk-id:" in action
    assert "top-risk-title:" in action
    assert "top-risk-severity:" in action
    assert "top-risk-file:" in action
    assert "top-risk-count:" in action
    assert "triage-status:" in action
    assert "triage-signal:" in action
    assert "target-fit-path:" in action
    assert "steps.paths.outputs.target-fit-path" in action
    assert "issue-draft-path:" in action
    assert "steps.paths.outputs.issue-draft-path" in action
    assert "csv-path:" in action
    assert "steps.paths.outputs.csv-path" in action
    assert "compare-base-json-path:" in action
    assert "compare-path:" in action
    assert "steps.paths.outputs.compare-path" in action
    assert 'labcheck compare "$LABCHECK_COMPARE_BASE_JSON_PATH" "$LABCHECK_JSON_PATH"' in action
    assert "--target-fit-output" in action
    assert "--issue-output" in action
    assert "--csv-output" in action
    assert "grouped_risks" in action
    assert "triage_signal" in action
    assert "triage_status" in action
    assert "one_line(value)" in action


def test_composite_action_top_risk_output_script_runs(tmp_path: Path) -> None:
    action = Path("action.yml").read_text(encoding="utf-8")
    script = _embedded_output_python(action)
    report_path = tmp_path / "labcheck-report.json"
    output_path = tmp_path / "github-output.txt"
    report_path.write_text(
        json.dumps(
            {
                "scores": {
                    "overall_score": 52,
                    "environment_rebuildability": 60,
                    "notebook_determinism": 70,
                    "artifact_availability": 40,
                    "portability": 90,
                    "onboarding_readiness": 50,
                },
                "summary": {"findings_count": 3},
                "findings": [
                    {
                        "check_id": "LC050",
                        "title": "Remote artifact lacks checksum",
                        "severity": "medium",
                        "category": "artifacts",
                        "file_path": "analysis.py",
                    },
                    {
                        "check_id": "LC005",
                        "title": "Referenced input artifact missing from repo",
                        "severity": "high",
                        "category": "artifacts",
                        "file_path": "notebooks/analysis.ipynb",
                    },
                    {
                        "check_id": "LC005",
                        "title": "Referenced input artifact missing from repo",
                        "severity": "high",
                        "category": "artifacts",
                        "file_path": "scripts/train.py",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["GITHUB_OUTPUT"] = str(output_path)
    subprocess.run([sys.executable, "-c", script, str(report_path)], check=True, env=env)

    outputs = dict(
        line.split("=", 1)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if "=" in line
    )
    assert outputs["overall-score"] == "52"
    assert outputs["findings-count"] == "3"
    assert outputs["high-count"] == "2"
    assert outputs["medium-count"] == "1"
    assert outputs["triage-status"] == "blocked"
    assert outputs["triage-signal"] == (
        "Not handoff-ready yet: fix 2 high-severity findings "
        "before sending this repo to a reviewer, student, or new engineer."
    )
    assert outputs["top-risk-id"] == "LC005"
    assert outputs["top-risk-title"] == "Referenced input artifact missing from repo"
    assert outputs["top-risk-severity"] == "high"
    assert outputs["top-risk-file"] == "notebooks/analysis.ipynb"
    assert outputs["top-risk-count"] == "2"


def test_composite_action_outputs_strong_triage_signal(tmp_path: Path) -> None:
    action = Path("action.yml").read_text(encoding="utf-8")
    script = _embedded_output_python(action)
    report_path = tmp_path / "labcheck-report.json"
    output_path = tmp_path / "github-output.txt"
    report_path.write_text(
        json.dumps(
            {
                "scores": {
                    "overall_score": 96,
                    "environment_rebuildability": 100,
                    "notebook_determinism": 92,
                    "artifact_availability": 95,
                    "portability": 100,
                    "onboarding_readiness": 94,
                },
                "summary": {"findings_count": 1},
                "findings": [
                    {
                        "check_id": "LC014",
                        "title": "Notebook has no saved execution evidence",
                        "severity": "low",
                        "category": "determinism",
                        "file_path": "notebooks/demo.ipynb",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["GITHUB_OUTPUT"] = str(output_path)
    subprocess.run([sys.executable, "-c", script, str(report_path)], check=True, env=env)

    outputs = dict(
        line.split("=", 1)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if "=" in line
    )
    assert outputs["triage-status"] == "strong"
    assert outputs["triage-signal"] == "Strong handoff candidate: no high-severity findings and the score is near release-ready."
