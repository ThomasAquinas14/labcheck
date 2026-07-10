from __future__ import annotations

from pathlib import Path

from .checks import (
    check_absolute_paths,
    check_ci_workflow_has_verification_step,
    check_ci_python_runtime_conflict,
    check_ci_workflow_drift,
    check_conflicting_python_runtime,
    check_current_time_usage,
    check_missing_catboost_seed,
    check_dockerfile_missing_dependency_install,
    check_floating_docker_base_images,
    check_floating_github_action_refs,
    check_gitignored_input_artifacts,
    check_hardcoded_secrets,
    check_hidden_notebook_state,
    check_inline_system_package_installs,
    check_inline_command_missing_paths,
    check_interactive_prompts,
    check_reused_jax_prng_key,
    check_missing_notebook_execution_evidence,
    check_missing_notebook_kernel_metadata,
    check_missing_output_directories,
    check_missing_requirement_include_files,
    check_missing_dependency_setup_instructions,
    check_missing_keras_dataset_seed,
    check_missing_lightgbm_seed,
    check_missing_docker_compose_depends_on_services,
    check_missing_docker_compose_build_paths,
    check_missing_docker_compose_develop_watch_paths,
    check_missing_docker_compose_extends_targets,
    check_missing_docker_compose_healthcheck_scripts,
    check_missing_docker_compose_include_files,
    check_missing_docker_compose_resource_files,
    check_missing_docker_compose_service_env_files,
    check_missing_docker_compose_service_label_files,
    check_missing_docker_compose_service_networks,
    check_missing_docker_compose_volume_sources,
    check_missing_globbed_input_paths,
    check_missing_input_artifacts,
    check_missing_data_versioning_restore_steps,
    check_missing_local_dependency_paths,
    check_missing_manifest,
    check_markdown_local_links,
    check_missing_reuse_metadata,
    check_missing_numpy_default_rng_seed,
    check_missing_local_module_imports,
    check_notebook_inline_unpinned_installs,
    check_missing_optuna_sampler_seed,
    check_missing_pandas_random_state,
    check_missing_polars_seed,
    check_missing_python_runtime,
    check_missing_pytorch_dataloader_generator,
    check_missing_pytorch_dataloader_worker_init,
    check_missing_pytorch_random_split_generator,
    check_missing_run_instructions,
    check_mutable_remote_input_artifacts,
    check_orphan_output_artifacts,
    check_orphan_workflow_nodes,
    check_missing_seed,
    check_pytorch_deterministic_backend,
    check_python_hash_usage,
    check_remote_artifact_without_checksum,
    check_missing_sklearn_random_state,
    check_missing_tensorflow_seed,
    check_missing_xgboost_random_state,
    check_output_directory_missing_provenance,
    check_saved_notebook_errors,
    check_readme_drift,
    check_remote_download_without_timeout,
    check_set_derived_order,
    check_suspicious_execution_order,
    check_timestamped_output_paths,
    check_undeclared_common_imports,
    check_undocumented_accelerator_requirement,
    check_unpinned_dependencies,
    check_unpinned_huggingface_revisions,
    check_unpinned_vcs_dependencies,
    check_unsorted_file_discovery_order,
    check_undocumented_environment_variables,
    check_working_directory_changes,
)
from .config import (
    LabcheckConfig,
    discover_config,
    effective_finding_limits,
    effective_severity_overrides,
    is_check_disabled,
    is_excluded,
    is_finding_ignored,
)
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


def _filter_configured_findings(findings: list[Finding], config: LabcheckConfig) -> list[Finding]:
    filtered = [
        finding
        for finding in findings
        if not is_check_disabled(finding.check_id, config)
        and not is_finding_ignored(finding.check_id, finding.file_path, config)
    ]

    severity_overrides = effective_severity_overrides(config)
    if severity_overrides:
        for finding in filtered:
            override = severity_overrides.get(finding.check_id)
            if override:
                finding.severity = override

    finding_limits = effective_finding_limits(config)
    if not finding_limits:
        return filtered

    limited: list[Finding] = []
    counts: dict[str, int] = {}
    for finding in filtered:
        limit = finding_limits.get(finding.check_id)
        if limit is None:
            limited.append(finding)
            continue
        count = counts.get(finding.check_id, 0)
        if count >= limit:
            continue
        counts[finding.check_id] = count + 1
        limited.append(finding)
    return limited


def scan_path(target: str, config_path: str | None = None) -> Report:
    with prepared_target(target) as (display_target, resolved_root):
        root = Path(resolved_root)
        repo_root = root if root.is_dir() else root.parent
        config = discover_config(repo_root, config_path)
        files = _iter_files(root, repo_root, config)

        notebooks = [parse_notebook(path) for path in files if path.suffix == ".ipynb"]
        python_files = [path for path in files if path.suffix == ".py"]
        markdown_files = [path for path in files if path.suffix.lower() == ".md"]
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
        if root.is_dir():
            findings.extend(check_missing_reuse_metadata(repo_root, notebooks, python_files))
        findings.extend(check_missing_python_runtime(repo_root, notebooks, python_files))
        findings.extend(check_conflicting_python_runtime(repo_root))
        findings.extend(check_ci_python_runtime_conflict(repo_root, files))
        findings.extend(check_floating_github_action_refs(repo_root, files))
        findings.extend(check_floating_docker_base_images(repo_root, files))
        findings.extend(check_dockerfile_missing_dependency_install(repo_root, files))
        findings.extend(check_ci_workflow_has_verification_step(repo_root, files))
        findings.extend(check_unpinned_dependencies(repo_root))
        findings.extend(check_unpinned_vcs_dependencies(repo_root, source_artifacts))
        findings.extend(check_missing_requirement_include_files(repo_root))
        findings.extend(check_missing_local_dependency_paths(repo_root))
        findings.extend(check_undeclared_common_imports(repo_root, source_artifacts))
        findings.extend(check_missing_local_module_imports(repo_root, source_artifacts))
        findings.extend(check_notebook_inline_unpinned_installs(repo_root, source_artifacts))
        findings.extend(check_inline_system_package_installs(repo_root, source_artifacts))
        findings.extend(check_inline_command_missing_paths(repo_root, source_artifacts))
        findings.extend(check_undocumented_environment_variables(repo_root, files, source_artifacts))
        findings.extend(check_hardcoded_secrets(repo_root, files))
        findings.extend(check_interactive_prompts(repo_root, source_artifacts))
        findings.extend(check_working_directory_changes(repo_root, source_artifacts))
        findings.extend(check_undocumented_accelerator_requirement(repo_root, files, source_artifacts))
        findings.extend(check_absolute_paths(repo_root, text_files))
        findings.extend(check_missing_input_artifacts(repo_root, source_artifacts))
        findings.extend(check_missing_docker_compose_volume_sources(repo_root, files))
        findings.extend(check_missing_docker_compose_build_paths(repo_root, files))
        findings.extend(check_missing_docker_compose_develop_watch_paths(repo_root, files))
        findings.extend(check_missing_docker_compose_depends_on_services(repo_root, files))
        findings.extend(check_missing_docker_compose_service_networks(repo_root, files))
        findings.extend(check_missing_docker_compose_healthcheck_scripts(repo_root, files))
        findings.extend(check_missing_docker_compose_resource_files(repo_root, files))
        findings.extend(check_missing_docker_compose_service_env_files(repo_root, files))
        findings.extend(check_missing_docker_compose_extends_targets(repo_root, files))
        findings.extend(check_missing_docker_compose_include_files(repo_root, files))
        findings.extend(check_missing_docker_compose_service_label_files(repo_root, files))
        findings.extend(check_gitignored_input_artifacts(repo_root, source_artifacts))
        findings.extend(check_missing_globbed_input_paths(repo_root, source_artifacts))
        findings.extend(check_mutable_remote_input_artifacts(repo_root, source_artifacts))
        findings.extend(check_remote_download_without_timeout(repo_root, source_artifacts))
        findings.extend(check_remote_artifact_without_checksum(repo_root, source_artifacts))
        findings.extend(check_unpinned_huggingface_revisions(repo_root, source_artifacts))
        findings.extend(check_missing_data_versioning_restore_steps(repo_root, files))
        findings.extend(check_missing_output_directories(repo_root, source_artifacts))
        findings.extend(check_timestamped_output_paths(repo_root, source_artifacts))
        findings.extend(check_current_time_usage(repo_root, source_artifacts))
        findings.extend(check_orphan_output_artifacts(repo_root, files, source_artifacts))
        findings.extend(check_output_directory_missing_provenance(repo_root, files))
        findings.extend(check_unsorted_file_discovery_order(repo_root, source_artifacts))
        findings.extend(check_set_derived_order(repo_root, source_artifacts))
        findings.extend(check_python_hash_usage(repo_root, source_artifacts))
        findings.extend(check_missing_seed(repo_root, source_artifacts))
        findings.extend(check_missing_sklearn_random_state(repo_root, source_artifacts))
        findings.extend(check_missing_pandas_random_state(repo_root, source_artifacts))
        findings.extend(check_missing_numpy_default_rng_seed(repo_root, source_artifacts))
        findings.extend(check_missing_polars_seed(repo_root, source_artifacts))
        findings.extend(check_missing_tensorflow_seed(repo_root, source_artifacts))
        findings.extend(check_missing_pytorch_random_split_generator(repo_root, source_artifacts))
        findings.extend(check_missing_pytorch_dataloader_generator(repo_root, source_artifacts))
        findings.extend(check_missing_pytorch_dataloader_worker_init(repo_root, source_artifacts))
        findings.extend(check_pytorch_deterministic_backend(repo_root, source_artifacts))
        findings.extend(check_missing_xgboost_random_state(repo_root, source_artifacts))
        findings.extend(check_missing_lightgbm_seed(repo_root, source_artifacts))
        findings.extend(check_missing_catboost_seed(repo_root, source_artifacts))
        findings.extend(check_missing_keras_dataset_seed(repo_root, source_artifacts))
        findings.extend(check_missing_optuna_sampler_seed(repo_root, source_artifacts))
        findings.extend(check_reused_jax_prng_key(repo_root, source_artifacts))
        findings.extend(check_readme_drift(repo_root, readme_references))
        findings.extend(check_markdown_local_links(repo_root, markdown_files))
        findings.extend(check_ci_workflow_drift(repo_root, files))
        findings.extend(check_missing_run_instructions(repo_root, notebooks, python_files))
        findings.extend(check_missing_dependency_setup_instructions(repo_root, notebooks, python_files))
        findings.extend(check_orphan_workflow_nodes(repo_root, graph))
        findings = _filter_configured_findings(findings, config)

        scores = score_findings(findings)
        summary = ScanSummary(
            target=display_target,
            notebooks=len(notebooks),
            python_files=len(python_files),
            findings_count=len(findings),
        )
        return Report(summary=summary, scores=scores, findings=findings, graph=graph)
