from __future__ import annotations

import json

from labcheck.compare import build_comparison, render_comparison_json, render_comparison_markdown


def _report(score: int, findings: list[dict]) -> dict:
    return {
        "summary": {
            "target": "demo",
            "notebooks": 1,
            "python_files": 1,
            "findings_count": len(findings),
        },
        "scores": {
            "overall_score": score,
            "environment_rebuildability": score,
            "notebook_determinism": score,
            "artifact_availability": score,
            "portability": score,
            "onboarding_readiness": score,
        },
        "findings": findings,
        "graph": {"nodes": [], "edges": []},
    }


def _finding(check_id: str, severity: str, file_path: str, evidence: str) -> dict:
    return {
        "check_id": check_id,
        "title": f"{check_id} title",
        "severity": severity,
        "category": "determinism",
        "file_path": file_path,
        "evidence": evidence,
        "why_it_matters": "why",
        "suggested_fix": "fix",
    }


def test_compare_reports_resolved_new_and_unchanged_findings() -> None:
    before = _report(
        40,
        [
            _finding("LC001", "high", "notebooks\\train.ipynb", "hidden state"),
            _finding("LC005", "high", "notebooks/data.ipynb", "missing data"),
        ],
    )
    after = _report(
        82,
        [
            _finding("LC001", "high", "notebooks/train.ipynb", "hidden state"),
            _finding("LC021", "medium", "README.md", "missing setup"),
        ],
    )

    comparison = build_comparison(before, after)

    assert comparison["delta"]["overall_score"] == 42
    assert comparison["delta"]["findings_count"] == 0
    assert comparison["delta"]["severity_counts"]["high"] == -1
    assert comparison["delta"]["severity_counts"]["medium"] == 1
    assert comparison["unchanged_findings_count"] == 1
    assert [finding["check_id"] for finding in comparison["resolved_findings"]] == ["LC005"]
    assert [finding["check_id"] for finding in comparison["new_findings"]] == ["LC021"]
    assert comparison["resolved_findings"][0]["file_path"] == "notebooks/data.ipynb"


def test_compare_markdown_is_shareable() -> None:
    comparison = build_comparison(
        _report(20, [_finding("LC005", "high", "notebooks/train.ipynb", "missing data")]),
        _report(95, []),
    )

    markdown = render_comparison_markdown(comparison)

    assert "# labcheck Before/After Compare" in markdown
    assert "Score change: **+75** points (20 -> 95)" in markdown
    assert "Findings change: **-1** (1 -> 0)" in markdown
    assert "## Resolved Findings" in markdown
    assert "`LC005` LC005 title" in markdown
    assert "## New Findings" in markdown
    assert "None." in markdown
    assert "No API key or hosted backend was used" in markdown


def test_compare_json_is_machine_readable() -> None:
    comparison = build_comparison(_report(50, []), _report(55, []))
    payload = json.loads(render_comparison_json(comparison))

    assert payload["delta"]["overall_score"] == 5
    assert payload["resolved_findings"] == []
    assert payload["new_findings"] == []
