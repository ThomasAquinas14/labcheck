from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

from .models import Finding, Report
from .scanner import score_findings

BASELINE_VERSION = 1


def finding_fingerprint(finding: Finding) -> str:
    payload = {
        "check_id": finding.check_id,
        "severity": finding.severity,
        "file_path": finding.file_path.replace("\\", "/"),
        "evidence": finding.evidence,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "v1:" + hashlib.sha256(encoded).hexdigest()


def build_baseline(report: Report) -> dict:
    return {
        "version": BASELINE_VERSION,
        "findings": [
            {
                "fingerprint": finding_fingerprint(finding),
                "check_id": finding.check_id,
                "severity": finding.severity,
                "file_path": finding.file_path,
                "title": finding.title,
            }
            for finding in report.findings
        ],
    }


def load_baseline(path: str | Path) -> set[str]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("version") != BASELINE_VERSION:
        raise ValueError(f"Unsupported labcheck baseline version: {data.get('version')}")
    findings = data.get("findings", [])
    if not isinstance(findings, list):
        raise ValueError("Invalid labcheck baseline: findings must be a list")
    fingerprints = set()
    for finding in findings:
        if not isinstance(finding, dict) or not isinstance(finding.get("fingerprint"), str):
            raise ValueError("Invalid labcheck baseline: every finding needs a fingerprint")
        fingerprints.add(finding["fingerprint"])
    return fingerprints


def filter_baselined_findings(report: Report, baseline_fingerprints: set[str]) -> Report:
    findings = [
        finding
        for finding in report.findings
        if finding_fingerprint(finding) not in baseline_fingerprints
    ]
    return Report(
        summary=replace(report.summary, findings_count=len(findings)),
        scores=score_findings(findings),
        findings=findings,
        graph=report.graph,
    )
