from __future__ import annotations

import ast
import re
from pathlib import Path

from .models import Finding, Graph, NotebookDocument
from .source_analysis import ReadmeReference, SourceArtifact, find_hidden_state_issues, readme_has_run_instructions
from .requirements_parser import find_python_runtime_spec, find_unpinned_dependencies

ABSOLUTE_PATH_PATTERNS = [
    re.compile(r"[A-Za-z]:(?:\\|/)[^\n\r\"']+"),
    re.compile(r"/Users/[^\\s\"']+"),
    re.compile(r"/home/[^\\s\"']+"),
    re.compile(r"/mnt/[^\\s\"']+"),
]

MANIFEST_FILES = {
    "requirements.txt",
    "pyproject.toml",
    "environment.yml",
    "Pipfile",
    "poetry.lock",
}

OUTPUT_DIRECTORY_NAMES = {
    "artifact",
    "artifacts",
    "checkpoint",
    "checkpoints",
    "figure",
    "figures",
    "model",
    "models",
    "output",
    "outputs",
    "plot",
    "plots",
    "report",
    "reports",
    "result",
    "results",
}

OUTPUT_FILE_SUFFIXES = {
    ".csv",
    ".feather",
    ".html",
    ".joblib",
    ".jpeg",
    ".jpg",
    ".json",
    ".jsonl",
    ".md",
    ".npy",
    ".npz",
    ".onnx",
    ".parquet",
    ".pdf",
    ".pickle",
    ".pkl",
    ".png",
    ".pt",
    ".pth",
    ".svg",
    ".tflite",
    ".tsv",
    ".txt",
}

SKLEARN_RANDOM_STATE_CALLS = {
    "AdaBoostClassifier",
    "AdaBoostRegressor",
    "BaggingClassifier",
    "BaggingRegressor",
    "ExtraTreesClassifier",
    "ExtraTreesRegressor",
    "GaussianMixture",
    "GradientBoostingClassifier",
    "GradientBoostingRegressor",
    "HistGradientBoostingClassifier",
    "HistGradientBoostingRegressor",
    "IsolationForest",
    "KMeans",
    "MLPClassifier",
    "MLPRegressor",
    "MiniBatchKMeans",
    "RandomForestClassifier",
    "RandomForestRegressor",
    "RandomizedSearchCV",
    "SGDClassifier",
    "SGDRegressor",
    "SpectralClustering",
    "TSNE",
}

SKLEARN_SHUFFLE_SPLIT_CALLS = {
    "GroupShuffleSplit",
    "ShuffleSplit",
    "StratifiedShuffleSplit",
}

SKLEARN_OPTIONAL_SHUFFLE_SPLIT_CALLS = {
    "KFold",
    "StratifiedKFold",
}


def check_suspicious_execution_order(notebooks: list[NotebookDocument], root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for notebook in notebooks:
        counts = [count for count in notebook.execution_counts if count is not None]
        if len(counts) < 3:
            continue
        monotonic = all(next_count > count for count, next_count in zip(counts, counts[1:]))
        if monotonic:
            continue
        findings.append(
            Finding(
                check_id="LC001",
                title="Suspicious notebook execution order",
                severity="high",
                category="determinism",
                file_path=_relative_posix(notebook.path, root),
                evidence=f"Execution counts are non-monotonic: {counts}",
                why_it_matters="The notebook may rely on hidden runtime state rather than a clean top-to-bottom execution path.",
                suggested_fix="Restart the kernel and run all cells before committing the notebook.",
            )
        )
    return findings


def check_missing_notebook_execution_evidence(notebooks: list[NotebookDocument], root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for notebook in notebooks:
        if notebook.code_cell_count < 2:
            continue
        if any(count is not None for count in notebook.execution_counts):
            continue
        findings.append(
            Finding(
                check_id="LC014",
                title="Notebook has no saved execution evidence",
                severity="low",
                category="determinism",
                file_path=_relative_posix(notebook.path, root),
                evidence=f"All {notebook.code_cell_count} code cells have empty execution counts.",
                why_it_matters="A cleared notebook may be intentional, but it gives reviewers no saved evidence that the notebook was rerun from a clean kernel.",
                suggested_fix="If outputs are intentionally stripped, document the rerun command or CI check; otherwise restart the kernel, run all cells, and save the notebook.",
            )
        )
    return findings


def check_missing_notebook_kernel_metadata(notebooks: list[NotebookDocument], root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for notebook in notebooks:
        if notebook.code_cell_count == 0:
            continue

        missing = []
        if not notebook.kernel_name.strip():
            missing.append("kernelspec.name")
        if not notebook.language_name.strip():
            missing.append("language_info.name")
        if not missing:
            continue

        findings.append(
            Finding(
                check_id="LC015",
                title="Notebook is missing kernel metadata",
                severity="low",
                category="environment",
                file_path=_relative_posix(notebook.path, root),
                evidence=f"Notebook metadata is missing {' and '.join(missing)}.",
                why_it_matters="A notebook handoff is harder when reviewers cannot tell which kernel and language the author intended.",
                suggested_fix="Open the notebook with the intended kernel and save it, or add kernelspec and language_info metadata before sharing.",
            )
        )
    return findings


def check_missing_manifest(root: Path, notebooks: list[NotebookDocument], python_files: list[Path]) -> list[Finding]:
    if not notebooks and not python_files:
        return []
    if any((root / name).exists() for name in MANIFEST_FILES):
        return []
    return [
        Finding(
            check_id="LC003",
            title="Missing environment manifest",
            severity="high",
            category="environment",
            file_path=".",
            evidence="Found runnable notebooks or Python files, but no dependency manifest at the repo root.",
            why_it_matters="A new user cannot reliably recreate the environment needed to run the project.",
            suggested_fix="Add requirements.txt, pyproject.toml, environment.yml, or another clear environment manifest.",
        )
    ]


def check_missing_python_runtime(root: Path, notebooks: list[NotebookDocument], python_files: list[Path]) -> list[Finding]:
    if not notebooks and not python_files:
        return []
    if find_python_runtime_spec(root):
        return []
    return [
        Finding(
            check_id="LC012",
            title="Missing Python runtime version",
            severity="medium",
            category="environment",
            file_path=".",
            evidence="Found runnable notebooks or Python files, but no Python runtime version is specified.",
            why_it_matters="A repo can have pinned packages and still fail to rebuild if users guess the wrong Python version.",
            suggested_fix="Declare the Python version with requires-python, .python-version, runtime.txt, Pipfile [requires], setup.cfg python_requires, or a Conda python= dependency.",
        )
    ]


def check_hidden_notebook_state(notebooks: list[NotebookDocument], root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for notebook in notebooks:
        issues = find_hidden_state_issues(notebook)
        if not issues:
            continue
        example_bits = [
            f"cell {issue.cell_index}: {', '.join(issue.names[:4])}"
            for issue in issues[:3]
        ]
        findings.append(
            Finding(
                check_id="LC002",
                title="Likely hidden notebook state",
                severity="high",
                category="determinism",
                file_path=_relative_posix(notebook.path, root),
                evidence=(
                    f"{len(issues)} cells reference names with no visible prior definition; "
                    f"examples: {'; '.join(example_bits)}"
                ),
                why_it_matters="The notebook may only work in the original author's live kernel rather than from a clean rerun.",
                suggested_fix="Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.",
            )
        )
    return findings


def check_saved_notebook_errors(notebooks: list[NotebookDocument], root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for notebook in notebooks:
        if not notebook.error_outputs:
            continue
        examples = [
            f"cell {error.cell_index}: {error.ename}{(': ' + error.evalue) if error.evalue else ''}"
            for error in notebook.error_outputs[:3]
        ]
        findings.append(
            Finding(
                check_id="LC011",
                title="Notebook contains saved error output",
                severity="high",
                category="determinism",
                file_path=_relative_posix(notebook.path, root),
                evidence=f"{len(notebook.error_outputs)} saved error output(s); examples: {'; '.join(examples)}",
                why_it_matters="A committed traceback is strong evidence that the notebook was not saved after a clean successful rerun.",
                suggested_fix="Fix the failing cell, restart the kernel, run all cells, and save the notebook without error outputs.",
            )
        )
    return findings


def check_unpinned_dependencies(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for dependency in find_unpinned_dependencies(root):
        findings.append(
            Finding(
                check_id="LC004",
                title="Unpinned dependency",
                severity="medium",
                category="environment",
                file_path=dependency.file_path,
                evidence=f"Dependency '{dependency.dependency}' in {dependency.file_path} does not pin a version.",
                why_it_matters="Environment rebuilds can drift over time when critical dependencies are unpinned.",
                suggested_fix="Pin this dependency to an exact or tightly bounded version.",
            )
        )
    return findings


def _is_escaped_newline_fragment(path_text: str) -> bool:
    return 3 <= len(path_text) <= 4 and path_text[1] == ":" and path_text[2:] in {"\\n", "/n"}


def _is_illustrative_or_regex_path_fragment(path_text: str) -> bool:
    return "..." in path_text or "[^" in path_text


def check_absolute_paths(root: Path, text_files: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in text_files:
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        normalized = content.replace("\\\\", "\\")
        for pattern in ABSOLUTE_PATH_PATTERNS:
            match = pattern.search(normalized)
            if not match:
                continue
            matched_path = match.group(0).rstrip("\\")
            if (
                "://" in matched_path
                or _is_escaped_newline_fragment(matched_path)
                or _is_illustrative_or_regex_path_fragment(matched_path)
            ):
                continue
            findings.append(
                Finding(
                    check_id="LC006",
                    title="Absolute machine-local path",
                    severity="medium",
                    category="portability",
                    file_path=_relative_posix(path, root),
                    evidence=f"Found path-like string '{matched_path}'.",
                    why_it_matters="Hardcoded local paths make the repo brittle on other machines and operating systems.",
                    suggested_fix="Use project-relative paths, environment variables, or documented configuration.",
                )
            )
            break
    return findings


def _is_external_or_placeholder(path_text: str) -> bool:
    lowered = path_text.lower()
    return (
        "://" in lowered
        or lowered.startswith("s3://")
        or lowered.startswith("gs://")
        or lowered.startswith("path/to/")
        or lowered.startswith("<")
    )


def _is_within_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _relative_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _candidate_repo_paths(root: Path, source_path: Path, candidate: str) -> list[Path]:
    candidate_path = Path(candidate)
    if candidate_path.is_absolute():
        return [candidate_path.resolve()]
    return [
        (root / candidate).resolve(),
        (source_path.parent / candidate).resolve(),
    ]


def _candidate_exists_in_repo(root: Path, source_path: Path, candidate: str) -> bool:
    root_resolved = root.resolve()
    for path in _candidate_repo_paths(root_resolved, source_path, candidate):
        if _is_within_root(path, root_resolved) and path.exists():
            return True
    return False


def check_missing_input_artifacts(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    for artifact in artifacts:
        for candidate in artifact.reads:
            if _is_external_or_placeholder(candidate):
                continue
            if _candidate_exists_in_repo(root, artifact.path, candidate):
                continue
            rel_path = _relative_posix(artifact.path, root)
            finding_key = (rel_path, candidate)
            if finding_key in seen:
                continue
            seen.add(finding_key)
            findings.append(
                Finding(
                    check_id="LC005",
                    title="Referenced input artifact missing from repo",
                    severity="high",
                    category="artifacts",
                    file_path=rel_path,
                    evidence=f"Reads '{candidate}', but that path is not present in the scanned repo.",
                    why_it_matters="A new user may not be able to run the workflow because required inputs are missing.",
                    suggested_fix="Commit the artifact, document how to obtain it, or make the input contract explicit.",
                )
            )
    return findings


def _repo_relative_key(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _produced_output_keys(root: Path, artifacts: list[SourceArtifact]) -> set[str]:
    root_resolved = root.resolve()
    produced: set[str] = set()
    for artifact in artifacts:
        for candidate in artifact.writes:
            if _is_external_or_placeholder(candidate):
                continue
            for path in _candidate_repo_paths(root_resolved, artifact.path, candidate):
                if _is_within_root(path, root_resolved):
                    produced.add(_repo_relative_key(path, root_resolved))
    return produced


def _is_likely_output_artifact(path: Path, root: Path) -> bool:
    try:
        relative_path = path.relative_to(root)
    except ValueError:
        return False
    parts = [part.lower() for part in relative_path.parts]
    if len(parts) < 2 or path.suffix.lower() not in OUTPUT_FILE_SUFFIXES:
        return False
    return any(part in OUTPUT_DIRECTORY_NAMES for part in parts[:-1])


def check_orphan_output_artifacts(root: Path, files: list[Path], artifacts: list[SourceArtifact]) -> list[Finding]:
    produced = _produced_output_keys(root, artifacts)
    findings: list[Finding] = []
    for path in sorted(files):
        if not _is_likely_output_artifact(path, root):
            continue
        relative_key = _repo_relative_key(path.resolve(), root.resolve())
        if relative_key in produced:
            continue
        findings.append(
            Finding(
                check_id="LC009",
                title="Committed output has no visible producer",
                severity="medium",
                category="artifacts",
                file_path=_relative_posix(path, root),
                evidence=f"'{relative_key}' looks like a generated artifact, but no scanned notebook or script visibly writes it.",
                why_it_matters="Committed results are harder to trust when the repo does not show how to regenerate them.",
                suggested_fix="Add or document the generating notebook/script, or move archival outputs behind an explicit exclusion.",
            )
        )
    return findings


def check_missing_seed(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    for artifact in artifacts:
        if not artifact.uses_randomness or artifact.seeds_randomness:
            continue
        findings.append(
            Finding(
                check_id="LC007",
                title="Randomness used without visible seeding",
                severity="medium",
                category="determinism",
                file_path=_relative_posix(artifact.path, root),
                evidence="Detected randomness-related APIs, but no obvious seed call in the same file.",
                why_it_matters="Results may drift between runs even if the code itself executes successfully.",
                suggested_fix="Set and document seeds for the randomness sources used in this workflow.",
            )
        )
    return findings


def _call_name(node: ast.AST) -> str:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


def _has_keyword(call: ast.Call, keyword_name: str) -> bool:
    return any(keyword.arg == keyword_name for keyword in call.keywords)


def _keyword_is_true(call: ast.Call, keyword_name: str) -> bool:
    for keyword in call.keywords:
        if keyword.arg != keyword_name:
            continue
        return isinstance(keyword.value, ast.Constant) and keyword.value.value is True
    return False


def _sklearn_random_state_issues(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    issues: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call_name = _call_name(node.func)
        short_name = call_name.rsplit(".", 1)[-1]
        if _has_keyword(node, "random_state"):
            continue
        if short_name == "train_test_split":
            issues.append(f"line {node.lineno}: {short_name}(...)")
        elif short_name in SKLEARN_RANDOM_STATE_CALLS:
            issues.append(f"line {node.lineno}: {short_name}(...)")
        elif short_name in SKLEARN_SHUFFLE_SPLIT_CALLS:
            issues.append(f"line {node.lineno}: {short_name}(...)")
        elif short_name in SKLEARN_OPTIONAL_SHUFFLE_SPLIT_CALLS and _keyword_is_true(node, "shuffle"):
            issues.append(f"line {node.lineno}: {short_name}(..., shuffle=True)")
    return issues


def _source_uses_pandas(source: str, tree: ast.AST) -> bool:
    if re.search(r"\bpd\.", source) or re.search(r"\bpandas\.", source):
        return True
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name == "pandas" for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom) and node.module == "pandas":
            return True
    return False


def _pandas_random_state_issues(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    if not _source_uses_pandas(source, tree):
        return []

    issues: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call_name = _call_name(node.func)
        if not call_name.endswith(".sample") or call_name == "random.sample":
            continue
        if _has_keyword(node, "random_state") or len(node.args) >= 5:
            continue
        issues.append(f"line {node.lineno}: {call_name}(...)")
    return issues


def check_missing_sklearn_random_state(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    for artifact in artifacts:
        issues = _sklearn_random_state_issues(artifact.content)
        if not issues:
            continue
        examples = "; ".join(issues[:4])
        findings.append(
            Finding(
                check_id="LC016",
                title="Scikit-learn randomness lacks random_state",
                severity="medium",
                category="determinism",
                file_path=_relative_posix(artifact.path, root),
                evidence=f"Detected sklearn calls without random_state: {examples}.",
                why_it_matters="Common sklearn splitters and randomized estimators can produce different train/test splits or model fits between runs.",
                suggested_fix="Pass a documented random_state value to train/test splits, shuffled splitters, and randomized sklearn estimators.",
            )
        )
    return findings


def check_missing_pandas_random_state(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    for artifact in artifacts:
        issues = _pandas_random_state_issues(artifact.content)
        if not issues:
            continue
        examples = "; ".join(issues[:4])
        findings.append(
            Finding(
                check_id="LC017",
                title="Pandas sampling lacks random_state",
                severity="medium",
                category="determinism",
                file_path=_relative_posix(artifact.path, root),
                evidence=f"Detected pandas sample calls without random_state: {examples}.",
                why_it_matters="Pandas sampling can produce different rows between runs, which makes notebook results and train/eval subsets drift.",
                suggested_fix="Pass a documented random_state value to pandas sample() calls used in reproducible workflows.",
            )
        )
    return findings


def check_readme_drift(root: Path, references: list[ReadmeReference]) -> list[Finding]:
    findings: list[Finding] = []
    for reference in references:
        referenced = (root / reference.referenced_path).resolve()
        if referenced.exists():
            continue
        findings.append(
            Finding(
                check_id="LC008",
                title="README command references a missing path",
                severity="medium",
                category="onboarding",
                file_path="README.md",
                evidence=f"Command '{reference.command}' points to '{reference.referenced_path}', which is not present.",
                why_it_matters="Setup instructions lose trust quickly when they point to files that do not exist.",
                suggested_fix="Update the README command or restore the missing entrypoint.",
            )
        )
    return findings


def check_missing_run_instructions(root: Path, notebooks: list[NotebookDocument], python_files: list[Path]) -> list[Finding]:
    if not notebooks and not python_files:
        return []
    if readme_has_run_instructions(root / "README.md"):
        return []
    evidence = (
        "README.md is missing."
        if not (root / "README.md").exists()
        else "README.md exists, but no clear setup or run command was found."
    )
    return [
        Finding(
            check_id="LC013",
            title="Missing setup or run instructions",
            severity="medium",
            category="onboarding",
            file_path="README.md",
            evidence=evidence,
            why_it_matters="A repo can contain runnable notebooks or scripts but still be hard to hand off if the next person does not know which command to start with.",
            suggested_fix="Add a short Quick start section with environment setup and the command or notebook needed to reproduce the main workflow.",
        )
    ]


def check_orphan_workflow_nodes(root: Path, graph: Graph) -> list[Finding]:
    if not graph.edges:
        return []

    inbound: dict[str, int] = {}
    outbound: dict[str, int] = {}
    for edge in graph.edges:
        outbound[edge.source] = outbound.get(edge.source, 0) + 1
        inbound[edge.target] = inbound.get(edge.target, 0) + 1

    findings: list[Finding] = []
    for node in graph.nodes:
        if node.kind not in {"notebook", "python"}:
            continue
        if inbound.get(node.id, 0) == 0 and outbound.get(node.id, 0) == 0:
            findings.append(
                Finding(
                    check_id="LC010",
                    title="Workflow node is disconnected from data lineage",
                    severity="low",
                    category="onboarding",
                    file_path=node.label,
                    evidence="This analysis file has no visible input or output edges in the provenance graph.",
                    why_it_matters="Disconnected workflow files are hard for new contributors to place in the actual experiment pipeline.",
                    suggested_fix="Document whether this file is archival, illustrative, or part of the real workflow, or connect it to visible inputs and outputs.",
                )
            )
    return findings
