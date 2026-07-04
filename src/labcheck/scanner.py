from __future__ import annotations

from pathlib import Path

from .checks import (
    check_absolute_paths,
    check_hidden_notebook_state,
    check_missing_notebook_execution_evidence,
    check_missing_notebook_kernel_metadata,
    check_missing_input_artifacts,
    check_missing_manifest,
    check_missing_pandas_random_state,
    check_missing_python_runtime,
    check_missing_run_instructions,
    check_orphan_output_artifacts,
    check_orphan_workflow_nodes,
    check_missing_seed,
    check_missing_sklearn_random_state,
    check_saved_notebook_errors,
    check_readme_drift,
    check_suspicious_execution_order,
    check_unpinned_dependencies,
)
from .config import LabcheckConfig, discover_config, is_check_disabled, is_excluded
from .graph import build_provenance_graph
from .loaders import prepared_target
from .models import Finding, Report, ScanSummary, ScoreCard
from .notebook_parser import parse_notebook
from .source_analysis import analyze_notebook, analyze_python_file, analyze_readme

TEXT_FILE_SUFFIXES = {
    ".ipynb",
    ".py",
    ".md",
    ".txt",
    ".toml",
    ".yml",
    ".yaml",
    ".json",
}


def _iter_files(root: Path, repo_root: Path, config: LabcheckConfig) -> list[Path]:
    if root.is_file():
        return [] if is_excluded(root, repo_root, config) else [root]
    return [path for path in root.rglob("*") if path.is_file() and not is_excluded(path, repo_root, config)]


SEVERITY_PENALTIES = {
    "high": 26,
    "medium": 14,
    "low": 6,
}

REPEATED_CHECK_WEIGHT = 0.35
MAX_REPEATED_CHECK_PENALTY = 72


def _score_category(findings: list[Finding], category: str) -> int:
    grouped: dict[str, list[Finding]] = {}
    for finding in findings:
        if finding.category != category:
            continue
        grouped.setdefault(finding.check_id, []).append(finding)

    penalty = 0.0
    for check_findings in grouped.values():
        weighted = sorted(
            (SEVERITY_PENALTIES.get(finding.severity, 8) for finding in check_findings),
            reverse=True,
        )
        if not weighted:
            continue
        check_penalty = weighted[0] + sum(value * REPEATED_CHECK_WEIGHT for value in weighted[1:])
        penalty += min(MAX_REPEATED_CHECK_PENALTY, check_penalty)

    return max(0, round(100 - penalty))


def score_findings(findings: list[Finding]) -> ScoreCard:
    environment = _score_category(findings, "environment")
    determinism = _score_category(findings, "determinism")
    artifacts = _score_category(findings, "artifacts")
    portability = _score_category(findings, "portability")
    onboarding = _score_category(findings, "onboarding")
    category_scores = [environment, determinism, artifacts, portability, onboarding]
    average_score = sum(category_scores) / len(category_scores)
    overall = round(average_score * 0.7 + min(category_scores) * 0.3)
    return ScoreCard(
        overall_score=overall,
        environment_rebuildability=environment,
        notebook_determinism=determinism,
        artifact_availability=artifacts,
        portability=portability,
        onboarding_readiness=onboarding,
    )


def _filter_disabled_checks(findings: list[Finding], config: LabcheckConfig) -> list[Finding]:
    if not config.disabled_checks:
        return findings
    return [finding for finding in findings if not is_check_disabled(finding.check_id, config)]


def scan_path(target: str, config_path: str | None = None) -> Report:
    with prepared_target(target) as (display_target, resolved_root):
        root = Path(resolved_root)
        repo_root = root if root.is_dir() else root.parent
        config = discover_config(repo_root, config_path)
        files = _iter_files(root, repo_root, config)

        notebooks = [parse_notebook(path) for path in files if path.suffix == ".ipynb"]
        python_files = [path for path in files if path.suffix == ".py"]
        text_files = [path for path in files if path.suffix.lower() in TEXT_FILE_SUFFIXES]
        notebook_artifacts = [analyze_notebook(notebook) for notebook in notebooks]
        python_artifacts = [analyze_python_file(path) for path in python_files]
        source_artifacts = notebook_artifacts + python_artifacts
        readme_references = analyze_readme(repo_root / "README.md")
        graph = build_provenance_graph(repo_root, source_artifacts)

        findings = []
        findings.extend(check_suspicious_execution_order(notebooks, repo_root))
        findings.extend(check_missing_notebook_execution_evidence(notebooks, repo_root))
        findings.extend(check_missing_notebook_kernel_metadata(notebooks, repo_root))
        findings.extend(check_hidden_notebook_state(notebooks, repo_root))
        findings.extend(check_saved_notebook_errors(notebooks, repo_root))
        findings.extend(check_missing_manifest(repo_root, notebooks, python_files))
        findings.extend(check_missing_python_runtime(repo_root, notebooks, python_files))
        findings.extend(check_unpinned_dependencies(repo_root))
        findings.extend(check_absolute_paths(repo_root, text_files))
        findings.extend(check_missing_input_artifacts(repo_root, source_artifacts))
        findings.extend(check_orphan_output_artifacts(repo_root, files, source_artifacts))
        findings.extend(check_missing_seed(repo_root, source_artifacts))
        findings.extend(check_missing_sklearn_random_state(repo_root, source_artifacts))
        findings.extend(check_missing_pandas_random_state(repo_root, source_artifacts))
        findings.extend(check_readme_drift(repo_root, readme_references))
        findings.extend(check_missing_run_instructions(repo_root, notebooks, python_files))
        findings.extend(check_orphan_workflow_nodes(repo_root, graph))
        findings = _filter_disabled_checks(findings, config)

        scores = score_findings(findings)
        summary = ScanSummary(
            target=display_target,
            notebooks=len(notebooks),
            python_files=len(python_files),
            findings_count=len(findings),
        )
        return Report(summary=summary, scores=scores, findings=findings, graph=graph)
