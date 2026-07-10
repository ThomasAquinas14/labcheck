from __future__ import annotations

import ast
import configparser
import fnmatch
import json
import re
import shlex
import sys
import tomllib
from pathlib import Path
from urllib.parse import unquote, urlparse

from .models import Finding, Graph, NotebookDocument
from .source_analysis import (
    ReadmeReference,
    SourceArtifact,
    find_hidden_state_issues,
    readme_has_dependency_setup_instructions,
    readme_has_run_instructions,
)
from .requirements_parser import (
    PythonRuntimeSpec,
    find_declared_dependency_names,
    find_missing_local_dependency_paths,
    find_missing_requirement_includes,
    find_python_runtime_spec,
    find_python_runtime_specs,
    find_unpinned_dependencies,
    find_unpinned_vcs_dependencies,
    vcs_dependency_issue_reason,
)

ABSOLUTE_PATH_PATTERNS = [
    re.compile(r"[A-Za-z]:(?:\\|/)[^\n\r\"']+"),
    re.compile(r"/Users/[^\s\"']+"),
    re.compile(r"/home/[^\s\"']+"),
    re.compile(r"/mnt/[^\s\"']+"),
    re.compile(r"/content/[^\s\"']+"),
    re.compile(r"/kaggle/[^\s\"']+"),
]

MARKDOWN_INLINE_LINK_PATTERN = re.compile(r"!?\[[^\]\n]*\]\(\s*([^)\s]+)(?:\s+['\"][^)]*['\"])?\s*\)")

MANIFEST_FILES = {
    "requirements.txt",
    "pyproject.toml",
    "environment.yml",
    "environment.yaml",
    "Pipfile",
    "poetry.lock",
}

LICENSE_FILE_NAMES = {
    "copying",
    "copying.md",
    "copying.txt",
    "licence",
    "licence.md",
    "licence.txt",
    "license",
    "license.md",
    "license.txt",
    "unlicense",
}

CITATION_FILE_NAMES = {
    ".zenodo.json",
    "citation",
    "citation.cff",
    "citation.md",
    "codemeta.json",
}

DATA_VERSIONING_ROOT_MARKERS = {
    ".dvcignore",
    "dvc.lock",
    "dvc.yaml",
}

DVC_YAML_NAMES = (
    "dvc.yaml",
    "dvc.yml",
)

DVC_RESTORE_COMMAND_PATTERN = re.compile(
    r"\b(?:(?:uv|poetry|pipenv|pdm|hatch|rye)\s+run\s+|python(?:3)?\s+-m\s+)?"
    r"dvc\s+(?:pull|repro|checkout)\b",
    re.IGNORECASE,
)

GIT_LFS_RESTORE_COMMAND_PATTERN = re.compile(
    r"\b(?:git\s+lfs|git-lfs)\s+(?:install|pull|fetch|checkout)\b",
    re.IGNORECASE,
)

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

INPUT_DIRECTORY_NAMES = {
    "annotation",
    "annotations",
    "audio",
    "corpora",
    "corpus",
    "data",
    "dataset",
    "datasets",
    "features",
    "image",
    "images",
    "img",
    "input",
    "inputs",
    "label",
    "labels",
    "raw",
    "sample",
    "samples",
    "text",
    "texts",
    "video",
    "videos",
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

MAKEFILE_NAMES = (
    "Makefile",
    "makefile",
    "GNUmakefile",
)
JUSTFILE_NAMES = (
    "justfile",
    "Justfile",
    ".justfile",
)
TASKFILE_NAMES = (
    "Taskfile.yml",
    "Taskfile.yaml",
    "Taskfile.dist.yml",
    "Taskfile.dist.yaml",
)
DOCKER_COMPOSE_FILE_NAMES = (
    "compose.yaml",
    "compose.yml",
    "docker-compose.yaml",
    "docker-compose.yml",
)
DOCKER_COMPOSE_HEALTHCHECK_SCRIPT_SUFFIXES = (
    ".bash",
    ".cjs",
    ".js",
    ".mjs",
    ".php",
    ".pl",
    ".ps1",
    ".py",
    ".rb",
    ".sh",
)
DOCKER_COMPOSE_HEALTHCHECK_LOCAL_DIRS = {
    "bin",
    "ci",
    "docker",
    "hack",
    "scripts",
    "tools",
}
NOXFILE_NAMES = (
    "noxfile.py",
)
RAKEFILE_NAMES = (
    "Rakefile",
    "rakefile",
    "rakefile.rb",
)
TOX_INI_CONFIG_NAMES = (
    "tox.ini",
    "setup.cfg",
)
SNAKEFILE_NAMES = (
    "Snakefile",
    "snakefile",
    "workflow/Snakefile",
)
NEXTFLOW_CONFIG_NAMES = (
    "nextflow.config",
    "conf/base.config",
)

MAKE_TARGET_PATTERN = re.compile(r"^([A-Za-z0-9_./%-][A-Za-z0-9_./% -]*)\s*:(?!=)")
PYTHON_MINOR_PATTERN = re.compile(r"(?<!\d)(\d+)\.(\d+)(?:\.\d+)?")
RANGE_RUNTIME_MARKERS = (">=", "<=", ">", "<", "~=", "^", "!=", "*", ",")
WORKFLOW_COMMAND_PREFIX_PATTERN = re.compile(
    r"\b(?:uv\s+run\s+)?(?:python3?|pip3?|bash|sh|make|npm|pnpm|yarn)\b"
)
WORKFLOW_PYTHON_VERSION_PATTERN = re.compile(r"\bpython-version\s*:\s*([^\n#]+)")
WORKFLOW_VALIDATION_NAME_PATTERN = re.compile(
    r"(^|[^a-z0-9])(ci|test|tests|check|checks|verify|verification|reproduce|repro|audit|quality)([^a-z0-9]|$)",
    re.IGNORECASE,
)
WORKFLOW_SETUP_PATTERN = re.compile(
    r"\b(?:"
    r"actions/setup-python|"
    r"pip\s+install|"
    r"python(?:3)?\s+-m\s+pip\s+install|"
    r"uv\s+(?:sync|pip\s+install)|"
    r"poetry\s+install|"
    r"pipenv\s+install|"
    r"conda\s+env\s+create|"
    r"conda\s+install|"
    r"mamba\s+env\s+create|"
    r"micromamba\s+env\s+create|"
    r"npm\s+(?:install|ci)|"
    r"pnpm\s+install|"
    r"yarn\s+install"
    r")\b",
    re.IGNORECASE,
)
WORKFLOW_VERIFICATION_PATTERN = re.compile(
    r"\b(?:"
    r"pytest|"
    r"unittest|"
    r"nox|"
    r"tox|"
    r"coverage\s+run|"
    r"ruff\s+check|"
    r"mypy|"
    r"pyright|"
    r"pre-commit\s+run|"
    r"python(?:3)?\s+scripts/check_[A-Za-z0-9_.-]+\.py|"
    r"jupyter\s+nbconvert\b[^#\n]*--execute|"
    r"papermill|"
    r"labcheck\s+(?:scan|scorecard|pack)|"
    r"make\s+(?:test|tests|check|ci|verify|reproduce|repro)|"
    r"npm\s+(?:test|run\s+(?:test|tests|check|ci|verify|reproduce|repro))|"
    r"pnpm\s+(?:test|run\s+(?:test|tests|check|ci|verify|reproduce|repro))|"
    r"yarn\s+(?:test|run\s+(?:test|tests|check|ci|verify|reproduce|repro)|(?:check|ci|verify|reproduce|repro))"
    r")\b",
    re.IGNORECASE,
)
FLOATING_DOCKER_TAGS = {
    "latest",
    "main",
    "master",
    "dev",
    "develop",
    "development",
    "edge",
    "nightly",
    "stable",
    "rolling",
    "snapshot",
    "current",
    "head",
    "canary",
}
FLOATING_GITHUB_ACTION_REFS = {
    "latest",
    "main",
    "master",
    "dev",
    "develop",
    "development",
    "edge",
    "nightly",
    "stable",
    "rolling",
    "snapshot",
    "current",
    "head",
    "canary",
}
INSTALL_TOKEN_VALUE_OPTIONS = {
    "-c",
    "--constraint",
    "-r",
    "--requirement",
    "--index-url",
    "--extra-index-url",
    "-f",
    "--find-links",
    "--trusted-host",
    "-t",
    "--target",
    "--prefix",
    "--root",
    "--src",
    "--python",
    "--upgrade-strategy",
    "-n",
    "--name",
    "-p",
    "--prefix",
}
INSTALL_FLAG_OPTIONS = {
    "-q",
    "--quiet",
    "-u",
    "--upgrade",
    "--user",
    "--no-deps",
    "--pre",
    "-y",
    "--yes",
}
INSTALL_PIN_MARKERS = ("==", "===", ">=", "<=", "~=", "!=")
INLINE_INSTALL_COMMANDS = {
    ("pip", "install"),
    ("pip3", "install"),
    ("python", "-m", "pip", "install"),
    ("python3", "-m", "pip", "install"),
    ("uv", "pip", "install"),
    ("conda", "install"),
    ("mamba", "install"),
    ("micromamba", "install"),
}
SYSTEM_INSTALL_COMMANDS = {
    ("apk", "add"),
    ("apt", "install"),
    ("apt-fast", "install"),
    ("apt-get", "install"),
    ("brew", "install"),
    ("dnf", "install"),
    ("pacman", "-S"),
    ("pacman", "--sync"),
    ("yum", "install"),
    ("zypper", "install"),
}
SYSTEM_INSTALL_FLAG_OPTIONS = {
    "-q",
    "-qq",
    "-s",
    "-y",
    "--allow-downgrades",
    "--allow-unauthenticated",
    "--best",
    "--clean",
    "--needed",
    "--no-cache",
    "--no-install-recommends",
    "--noconfirm",
    "--quiet",
    "--refresh",
    "--update",
    "--yes",
}
SYSTEM_INSTALL_VALUE_OPTIONS = {
    "-c",
    "-o",
    "--config",
    "--option",
    "--root",
}
MOVING_REF_NAMES = {"head", "main", "master", "develop", "dev", "trunk"}
CHECKSUM_CONTEXT_PATTERN = re.compile(r"\b(?:sha256|sha512|md5|checksum|hash)\b", re.IGNORECASE)
ACCELERATOR_DOCUMENTATION_PATTERN = re.compile(
    r"\b(?:gpu|cuda|cudnn|nvidia|accelerator|mps|tpu|cpu fallback|runs on cpu|cpu-only)\b",
    re.IGNORECASE,
)
ACCELERATOR_USAGE_PATTERNS = (
    re.compile(r"\.cuda\s*\(", re.IGNORECASE),
    re.compile(r"\btorch\.cuda\.", re.IGNORECASE),
    re.compile(r"\btorch\.device\s*\(\s*['\"]cuda(?::\d+)?['\"]", re.IGNORECASE),
    re.compile(r"\.to\s*\(\s*(?:device\s*=\s*)?['\"]cuda(?::\d+)?['\"]", re.IGNORECASE),
    re.compile(r"\bdevice\s*=\s*['\"]cuda(?::\d+)?['\"]", re.IGNORECASE),
    re.compile(r"\b(?:tf|tensorflow)\.config\.(?:list_physical_devices|set_visible_devices)\s*\(\s*['\"]GPU['\"]", re.IGNORECASE),
    re.compile(r"^\s*(?:import|from)\s+(?:cupy|cudf|cuml|cugraph|rapids)\b", re.IGNORECASE),
)
REMOTE_TIMEOUT_REQUIRED_CALLS = {
    "requests.delete",
    "requests.get",
    "requests.head",
    "requests.options",
    "requests.patch",
    "requests.post",
    "requests.put",
    "requests.request",
    "urllib.request.urlopen",
    "urllib.request.urlretrieve",
    "wget.download",
    "gdown.download",
}
SHELL_REMOTE_DOWNLOAD_PATTERN = re.compile(r"^\s*[!%]?\s*(?:curl|wget)\b.*https?://", re.IGNORECASE)
SHELL_TIMEOUT_OPTION_PATTERN = re.compile(
    r"(?:\btimeout\b|(?:^|\s)(?:--timeout|--connect-timeout|--max-time|-T)(?:[=\s]|$))",
    re.IGNORECASE,
)
DOCKER_PYTHON_CONTEXT_PATTERN = re.compile(
    r"^\s*FROM\s+(?:--platform=\S+\s+)?(?:\S+/)?python:|\b(?:python|pip|uv|poetry|pipenv|conda|mamba|micromamba)\b",
    re.IGNORECASE | re.MULTILINE,
)
DOCKER_DEPENDENCY_INSTALL_PATTERN = re.compile(
    r"\b(?:(?:python3?|pip3?)\s+(?:-m\s+)?pip\s+install|pip3?\s+install)\b"
    r".*(?:\s-r\s|\s--requirement(?:=|\s)|requirements?[^\s]*\.txt|\s(?:-e\s+)?\.)(?:\s|$)"
    r"|\buv\s+(?:sync|pip\s+(?:install|sync))\b"
    r"|\bpoetry\s+install\b"
    r"|\bpipenv\s+install\b"
    r"|\b(?:conda|mamba|micromamba)\s+env\s+create\b",
    re.IGNORECASE,
)
ENV_EXAMPLE_FILENAMES = {
    ".env.example",
    ".env.sample",
    ".env.template",
    "example.env",
    "sample.env",
}
SECRET_SCAN_SUFFIXES = {
    ".cfg",
    ".conf",
    ".ini",
    ".ipynb",
    ".js",
    ".json",
    ".jsx",
    ".key",
    ".pem",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
}
SECRET_SCAN_FILENAMES = {
    ".env",
    ".env.development",
    ".env.local",
    ".env.production",
    ".env.test",
    "config",
    "secrets",
}
SECRET_ASSIGNMENT_PATTERNS = (
    re.compile(
        r"""(?ix)
        ["']?(?P<name>[A-Za-z_][A-Za-z0-9_.-]{1,80})["']?
        \s*:\s*[^=\n]{1,80}=\s*
        (?P<quote>["']?)(?P<value>[^"'\s#,\]}]+)
        """
    ),
    re.compile(
        r"""(?ix)
        ["']?(?P<name>[A-Za-z_][A-Za-z0-9_.-]{1,80})["']?
        \s*(?:=|:)\s*
        (?P<quote>["']?)(?P<value>[^"'\s#,\]}]+)
        """
    ),
)
KNOWN_SECRET_VALUE_PATTERNS = (
    re.compile(r"sk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"glpat-[A-Za-z0-9_-]{20,}"),
    re.compile(r"hf_[A-Za-z0-9]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"SG\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}"),
)
PRIVATE_KEY_BLOCK_PATTERN = re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----")
PLACEHOLDER_SECRET_VALUES = {
    "changeme",
    "change-me",
    "change_me",
    "dummy",
    "example",
    "fake",
    "none",
    "null",
    "placeholder",
    "replace-me",
    "replace_me",
    "sample",
    "secret",
    "test",
    "todo",
    "your-api-key",
    "your_api_key",
    "your-token",
    "your_token",
}
STANDARD_ENV_PREFIXES = (
    "GITHUB_",
    "RUNNER_",
    "ACTIONS_",
)
STANDARD_ENV_VARS = {
    "CI",
    "COLORTERM",
    "COMSPEC",
    "HOME",
    "HOMEDRIVE",
    "HOMEPATH",
    "LANG",
    "PATH",
    "PATHEXT",
    "PWD",
    "SHELL",
    "TEMP",
    "TMP",
    "TMPDIR",
    "USER",
    "USERNAME",
    "USERPROFILE",
    "VIRTUAL_ENV",
}

COMMON_IMPORT_DEPENDENCIES = {
    "bs4": "beautifulsoup4",
    "catboost": "catboost",
    "cv2": "opencv-python",
    "datasets": "datasets",
    "dotenv": "python-dotenv",
    "dvc": "dvc",
    "duckdb": "duckdb",
    "gdown": "gdown",
    "httpx": "httpx",
    "joblib": "joblib",
    "keras": "keras",
    "lightgbm": "lightgbm",
    "matplotlib": "matplotlib",
    "mlflow": "mlflow",
    "nltk": "nltk",
    "numpy": "numpy",
    "pandas": "pandas",
    "PIL": "pillow",
    "plotly": "plotly",
    "polars": "polars",
    "pyarrow": "pyarrow",
    "requests": "requests",
    "scipy": "scipy",
    "seaborn": "seaborn",
    "skimage": "scikit-image",
    "sklearn": "scikit-learn",
    "spacy": "spacy",
    "statsmodels": "statsmodels",
    "tensorflow": "tensorflow",
    "torch": "torch",
    "transformers": "transformers",
    "wget": "wget",
    "xgboost": "xgboost",
    "yaml": "pyyaml",
}
LOCAL_HELPER_IMPORT_NAMES = {
    "analysis",
    "clean",
    "cleaning",
    "common",
    "config",
    "constants",
    "data",
    "dataset",
    "evaluate",
    "evaluation",
    "experiment",
    "features",
    "helpers",
    "io_utils",
    "lib",
    "metrics",
    "model",
    "models",
    "pipeline",
    "pipelines",
    "plotting",
    "preprocess",
    "preprocessing",
    "src",
    "train",
    "training",
    "utils",
    "visualization",
    "visualize",
}
SUPPORTED_DEPENDENCY_MANIFEST_FILES = {
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-test.txt",
    "pyproject.toml",
    "environment.yml",
    "environment.yaml",
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


def _exact_python_minor(spec: str) -> tuple[int, int] | None:
    normalized = spec.strip().lower()
    if any(marker in normalized for marker in RANGE_RUNTIME_MARKERS):
        return None
    match = PYTHON_MINOR_PATTERN.search(normalized)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def check_conflicting_python_runtime(root: Path) -> list[Finding]:
    specs = find_python_runtime_specs(root)
    exact_specs: dict[tuple[int, int], list[PythonRuntimeSpec]] = {}
    for runtime_spec in specs:
        minor_version = _exact_python_minor(runtime_spec.spec)
        if minor_version is None:
            continue
        exact_specs.setdefault(minor_version, []).append(runtime_spec)

    if len(exact_specs) <= 1:
        return []

    details = []
    for minor_version, version_specs in sorted(exact_specs.items()):
        locations = ", ".join(f"{spec.file_path} declares {spec.spec}" for spec in version_specs)
        details.append(f"Python {minor_version[0]}.{minor_version[1]} ({locations})")

    return [
        Finding(
            check_id="LC019",
            title="Conflicting Python runtime declarations",
            severity="medium",
            category="environment",
            file_path=".",
            evidence=f"Exact Python runtime declarations disagree: {'; '.join(details)}.",
            why_it_matters="A repo can document a runtime and still fail handoff if different setup files ask for different Python versions.",
            suggested_fix="Align .python-version, runtime.txt, pyproject.toml, Pipfile, Conda files, setup.cfg, and Dockerfile variants to the same Python minor version, or document why multiple runtimes are intentional.",
        )
    ]


def _project_exact_python_minor(root: Path) -> tuple[int, int] | None:
    exact_minors = {
        minor
        for spec in find_python_runtime_specs(root)
        if (minor := _exact_python_minor(spec.spec)) is not None
    }
    if len(exact_minors) != 1:
        return None
    return next(iter(exact_minors))


def _workflow_python_versions(content: str) -> list[str]:
    versions: list[str] = []
    for match in WORKFLOW_PYTHON_VERSION_PATTERN.finditer(content):
        value = match.group(1).strip().strip("'\"")
        if "${{" in value:
            continue
        versions.extend(
            version_match.group(0)
            for version_match in re.finditer(r"(?<!\d)\d+\.\d+(?:\.\d+)?", value)
        )
    return versions


def check_ci_python_runtime_conflict(root: Path, files: list[Path]) -> list[Finding]:
    project_minor = _project_exact_python_minor(root)
    if project_minor is None:
        return []

    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    expected = f"{project_minor[0]}.{project_minor[1]}"
    for path in _workflow_files(root, files):
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel_path = _relative_posix(path, root)
        for version in _workflow_python_versions(content):
            workflow_minor = _exact_python_minor(version)
            if workflow_minor is None or workflow_minor == project_minor:
                continue
            actual = f"{workflow_minor[0]}.{workflow_minor[1]}"
            key = (rel_path, actual)
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                Finding(
                    check_id="LC026",
                    title="CI Python version conflicts with project runtime",
                    severity="medium",
                    category="environment",
                    file_path=rel_path,
                    evidence=f"Workflow uses Python {actual}, but project runtime declarations use Python {expected}.",
                    why_it_matters="CI is often the reproducibility proof reviewers trust first; a different Python minor can make installs, notebooks, or tests fail in CI while local setup appears correct.",
                    suggested_fix="Align GitHub Actions python-version with the declared project runtime, or document why CI intentionally tests a different Python version.",
                )
            )
    return findings


def _workflow_uses_references(content: str) -> list[tuple[int, str]]:
    references: list[tuple[int, str]] = []
    for line_number, raw_line in enumerate(content.splitlines(), start=1):
        match = re.match(r"^\s*(?:-\s*)?uses:\s*([^#\n]+)", raw_line)
        if not match:
            continue
        reference = match.group(1).strip().strip("'\"")
        if reference:
            references.append((line_number, reference))
    return references


def _floating_github_action_reason(reference: str) -> str | None:
    lowered = reference.lower()
    if (
        not lowered
        or lowered.startswith(("./", "../", "docker://"))
        or "${{" in lowered
        or "$" in lowered
    ):
        return None
    if "@" not in reference:
        return "does not specify an action ref"

    ref = reference.rsplit("@", 1)[1].strip().lower()
    if not ref:
        return "does not specify an action ref"
    if re.fullmatch(r"[0-9a-f]{40}", ref):
        return None
    if ref in FLOATING_GITHUB_ACTION_REFS or ref.rsplit("/", 1)[-1] in FLOATING_GITHUB_ACTION_REFS:
        return f"uses the moving '{ref}' ref"
    return None


def check_floating_github_action_refs(root: Path, files: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    for path in _workflow_files(root, files):
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel_path = _relative_posix(path, root)
        for line_number, reference in _workflow_uses_references(content):
            reason = _floating_github_action_reason(reference)
            if reason is None:
                continue
            key = (rel_path, reference)
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                Finding(
                    check_id="LC030",
                    title="Floating GitHub Action reference",
                    severity="medium",
                    category="onboarding",
                    file_path=rel_path,
                    evidence=f"Line {line_number}: uses: {reference} {reason}.",
                    why_it_matters="A passing workflow can stop being a reliable reproducibility signal if a referenced action changes after the repo is handed off.",
                    suggested_fix="Pin the action to a stable version tag or full commit SHA, for example actions/checkout@v4 or owner/action@<40-character-sha>.",
                )
            )
    return findings


def _is_dockerfile(path: Path) -> bool:
    name = path.name.lower()
    return name == "dockerfile" or name.startswith("dockerfile.") or name.endswith(".dockerfile")


def _dockerfile_tokens(line: str) -> list[str]:
    try:
        return shlex.split(line, comments=True, posix=True)
    except ValueError:
        return line.split()


def _docker_from_instruction(tokens: list[str]) -> tuple[str, str | None] | None:
    if not tokens or tokens[0].lower() != "from":
        return None

    image_index = 1
    while image_index < len(tokens) and tokens[image_index].startswith("--"):
        # Dockerfile FROM currently uses --platform=..., but tolerate split option values.
        image_index += 1 if "=" in tokens[image_index] else 2
    if image_index >= len(tokens):
        return None

    image = tokens[image_index]
    alias: str | None = None
    for index in range(image_index + 1, len(tokens) - 1):
        if tokens[index].lower() == "as":
            alias = tokens[index + 1].lower()
            break
    return image, alias


def _docker_image_tag(image: str) -> str | None:
    image_without_digest = image.split("@", 1)[0]
    last_segment = image_without_digest.rsplit("/", 1)[-1]
    if ":" not in last_segment:
        return None
    return last_segment.rsplit(":", 1)[1].lower()


def _floating_docker_reason(image: str, known_stage_aliases: set[str]) -> str | None:
    lowered = image.lower()
    if lowered == "scratch" or lowered in known_stage_aliases:
        return None
    if "@" in image or "$" in image or "{" in image:
        return None

    tag = _docker_image_tag(image)
    if tag is None:
        return "does not specify a tag, so Docker will pull the moving default tag"
    if tag in FLOATING_DOCKER_TAGS:
        return f"uses the moving '{tag}' tag"
    return None


def check_floating_docker_base_images(root: Path, files: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in files:
        if not _is_dockerfile(path):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        stage_aliases: set[str] = set()
        rel_path = _relative_posix(path, root)
        for line_number, raw_line in enumerate(content.splitlines(), start=1):
            tokens = _dockerfile_tokens(raw_line.strip())
            instruction = _docker_from_instruction(tokens)
            if instruction is None:
                continue
            image, alias = instruction
            reason = _floating_docker_reason(image, stage_aliases)
            if reason is not None:
                findings.append(
                    Finding(
                        check_id="LC029",
                        title="Floating Docker base image tag",
                        severity="medium",
                        category="environment",
                        file_path=rel_path,
                        evidence=f"Line {line_number}: FROM {image} {reason}.",
                        why_it_matters="A Dockerfile can look reproducible while rebuilding against a different base image days or months later.",
                        suggested_fix="Pin the base image to a stable version tag or digest, for example python:3.11-slim or python:3.11-slim@sha256:<digest>.",
                    )
                )
            if alias:
                stage_aliases.add(alias)
    return findings


def _dependency_manifest_paths(root: Path, files: list[Path]) -> list[str]:
    root_resolved = root.resolve()
    manifests: list[str] = []
    for path in files:
        try:
            relative = path.resolve().relative_to(root_resolved).as_posix()
        except ValueError:
            continue
        name = path.name.lower()
        normalized = relative.lower()
        if name in SUPPORTED_DEPENDENCY_MANIFEST_FILES:
            manifests.append(relative)
        elif name.endswith(".txt") and "requirements" in name:
            manifests.append(relative)
        elif normalized.startswith("requirements/") and name.endswith(".txt"):
            manifests.append(relative)
    return sorted(set(manifests))


def _dockerfile_logical_lines(content: str) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    pending: list[str] = []
    start_line = 1
    for line_number, raw_line in enumerate(content.splitlines(), start=1):
        stripped = raw_line.rstrip()
        if not pending:
            start_line = line_number
        continued = stripped.endswith("\\")
        pending.append(stripped.removesuffix("\\").strip())
        if continued:
            continue
        lines.append((start_line, " ".join(part for part in pending if part)))
        pending = []
    if pending:
        lines.append((start_line, " ".join(part for part in pending if part)))
    return lines


def _dockerfile_has_dependency_install(content: str) -> bool:
    return any(DOCKER_DEPENDENCY_INSTALL_PATTERN.search(line) for _, line in _dockerfile_logical_lines(content))


def check_dockerfile_missing_dependency_install(root: Path, files: list[Path]) -> list[Finding]:
    manifests = _dependency_manifest_paths(root, files)
    if not manifests:
        return []

    findings: list[Finding] = []
    manifest_preview = ", ".join(manifests[:4])
    for path in files:
        if not _is_dockerfile(path):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if not DOCKER_PYTHON_CONTEXT_PATTERN.search(content):
            continue
        if _dockerfile_has_dependency_install(content):
            continue
        findings.append(
            Finding(
                check_id="LC049",
                title="Dockerfile skips dependency manifest",
                severity="medium",
                category="environment",
                file_path=_relative_posix(path, root),
                evidence=f"Dockerfile appears to build a Python environment, but no dependency install step was found for manifest(s): {manifest_preview}.",
                why_it_matters="A Dockerfile can create false reproducibility confidence if it copies the repo but never installs the dependencies declared for notebooks or scripts.",
                suggested_fix="Add a Docker build step such as RUN python -m pip install -r requirements.txt, RUN pip install ., uv sync, poetry install, or conda env create -f environment.yml.",
            )
        )
    return findings


def _readme_text(root: Path) -> str:
    try:
        return (root / "README.md").read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _repo_data_versioning_markers(root: Path, files: list[Path]) -> dict[str, list[str]]:
    root_resolved = root.resolve()
    markers: dict[str, list[str]] = {"dvc": [], "git-lfs": []}

    for path in files:
        try:
            relative = path.resolve().relative_to(root_resolved).as_posix()
        except ValueError:
            continue
        name = path.name
        if name in DATA_VERSIONING_ROOT_MARKERS or name.endswith(".dvc"):
            markers["dvc"].append(relative)
        elif name == ".gitattributes":
            try:
                content = path.read_text(encoding="utf-8").lower()
            except UnicodeDecodeError:
                continue
            if "filter=lfs" in content or "filter lfs" in content:
                markers["git-lfs"].append(relative)

    return {tool: sorted(paths) for tool, paths in markers.items() if paths}


def _text_contains_restore_command(text: str, tool: str) -> bool:
    pattern = DVC_RESTORE_COMMAND_PATTERN if tool == "dvc" else GIT_LFS_RESTORE_COMMAND_PATTERN
    return pattern.search(text) is not None


def _readme_make_targets(readme: str) -> set[str]:
    targets: set[str] = set()
    for match in re.finditer(r"\bmake(?:\s+-[^\s`]+)*\s+([A-Za-z0-9_.:-]+)\b", readme, re.IGNORECASE):
        targets.add(match.group(1))
    return targets


def _readme_package_scripts(readme: str) -> set[str]:
    scripts: set[str] = set()
    for match in re.finditer(r"\b(?:npm|pnpm)\s+run\s+([A-Za-z0-9_.:-]+)\b", readme, re.IGNORECASE):
        scripts.add(match.group(1))
    for match in re.finditer(r"\byarn\s+(?:run\s+)?([A-Za-z0-9_.:-]+)\b", readme, re.IGNORECASE):
        script = match.group(1)
        if script not in {"add", "cache", "config", "install", "remove", "upgrade"}:
            scripts.add(script)
    return scripts


def _readme_shell_script_paths(readme: str) -> set[str]:
    paths: set[str] = set()
    for match in re.finditer(r"\b(?:bash|sh)\s+([A-Za-z0-9_./\\-]+\.sh)\b", readme, re.IGNORECASE):
        paths.add(match.group(1))
    for match in re.finditer(r"(?:^|[\s`])(\.?/?(?:scripts|bin)/[A-Za-z0-9_./\\-]+\.sh)\b", readme, re.IGNORECASE):
        paths.add(match.group(1))
    return paths


def _repo_script_text(root: Path, script_path: str) -> str:
    normalized = script_path.replace("\\", "/").strip()
    if (
        not normalized
        or normalized.startswith(("$", "${", "~", "/", "<"))
        or "://" in normalized
    ):
        return ""
    candidate = (root / normalized).resolve()
    root_resolved = root.resolve()
    if not _is_within_root(candidate, root_resolved) or not candidate.is_file():
        return ""
    try:
        return candidate.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def _readme_documents_restore_steps(root: Path, readme: str, tool: str) -> bool:
    if _text_contains_restore_command(readme, tool):
        return True

    makefile = _find_makefile(root)
    if makefile is not None:
        recipes = _makefile_target_recipes(makefile)
        for target in _readme_make_targets(readme):
            if _text_contains_restore_command(recipes.get(target, ""), tool):
                return True

    package_scripts = _package_json_script_commands(root)
    for script_name in _readme_package_scripts(readme):
        if _text_contains_restore_command(package_scripts.get(script_name, ""), tool):
            return True

    for script_path in _readme_shell_script_paths(readme):
        if _text_contains_restore_command(_repo_script_text(root, script_path), tool):
            return True

    return False


def check_missing_data_versioning_restore_steps(root: Path, files: list[Path]) -> list[Finding]:
    markers = _repo_data_versioning_markers(root, files)
    if not markers:
        return []

    readme = _readme_text(root)
    undocumented = {
        tool: paths
        for tool, paths in markers.items()
        if not _readme_documents_restore_steps(root, readme, tool)
    }
    if not undocumented:
        return []

    tool_labels = {
        "dvc": "DVC",
        "git-lfs": "Git LFS",
    }
    detected = "; ".join(
        f"{tool_labels[tool]} metadata ({', '.join(paths[:3])}{', ...' if len(paths) > 3 else ''})"
        for tool, paths in sorted(undocumented.items())
    )
    restore_examples = []
    if "dvc" in undocumented:
        restore_examples.append("dvc pull")
    if "git-lfs" in undocumented:
        restore_examples.append("git lfs pull")
    restore_text = "`, `".join(restore_examples)
    return [
        Finding(
            check_id="LC018",
            title="Data versioning restore steps are undocumented",
            severity="low",
            category="artifacts",
            file_path="README.md" if (root / "README.md").exists() else ".",
            evidence=f"Detected {detected}, but README.md does not document restore steps.",
            why_it_matters="Data versioning metadata is useful, but a new reviewer still needs to know the exact command that restores required data or large artifacts.",
            suggested_fix=f"Add a short data restore step such as `{restore_text}` before the main reproduction command.",
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


def check_unpinned_vcs_dependencies(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    for dependency in find_unpinned_vcs_dependencies(root):
        findings.append(
            Finding(
                check_id="LC043",
                title="VCS dependency uses moving ref",
                severity="medium",
                category="environment",
                file_path=dependency.file_path,
                evidence=(
                    f"{dependency.file_path} references VCS dependency {dependency.dependency}, "
                    f"which {dependency.reason}."
                ),
                why_it_matters="Git, Mercurial, SVN, and Bazaar dependency refs can drift when they point at branches or omit a ref entirely.",
                suggested_fix="Pin VCS dependencies to an immutable commit SHA or release tag, and avoid branch refs such as main or master.",
            )
        )

    for artifact in artifacts:
        if artifact.kind != "notebook":
            continue
        issues: list[str] = []
        for line_number, line in enumerate(artifact.content.splitlines(), start=1):
            command = _inline_install_args(_shell_tokens(line))
            if not command:
                continue
            manager, args = command
            for arg in args:
                lowered = arg.lower()
                if not lowered.startswith(("git+", "hg+", "svn+", "bzr+")):
                    continue
                reason = vcs_dependency_issue_reason(arg)
                if reason:
                    issues.append(f"line {line_number}: {manager} installs {arg} ({reason})")
        if not issues:
            continue
        findings.append(
            Finding(
                check_id="LC043",
                title="VCS dependency uses moving ref",
                severity="medium",
                category="environment",
                file_path=_relative_posix(artifact.path, root),
                evidence=f"Detected inline VCS installs with missing or moving refs: {'; '.join(issues[:4])}.",
                why_it_matters="Inline notebook installs from mutable VCS refs can pull different code each time the notebook is rerun.",
                suggested_fix="Move the dependency into a manifest and pin it to an immutable commit SHA or release tag.",
            )
        )
    return findings


def check_missing_requirement_include_files(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for missing_include in find_missing_requirement_includes(root):
        findings.append(
            Finding(
                check_id="LC023",
                title="Requirement include file is missing",
                severity="high",
                category="environment",
                file_path=missing_include.file_path,
                evidence=(
                    f"{missing_include.file_path} uses {missing_include.directive} "
                    f"{missing_include.referenced_path}, but that file is not present in the repo."
                ),
                why_it_matters="Environment setup can fail immediately when a requirements, constraints, or Conda pip include points to a missing file.",
                suggested_fix="Commit the referenced requirements/constraints file, fix the include path, or remove the stale include.",
            )
        )
    return findings


def check_missing_local_dependency_paths(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for missing_dependency in find_missing_local_dependency_paths(root):
        findings.append(
            Finding(
                check_id="LC027",
                title="Local dependency path is missing",
                severity="high",
                category="environment",
                file_path=missing_dependency.file_path,
                evidence=(
                    f"{missing_dependency.file_path} references local dependency path "
                    f"{missing_dependency.referenced_path}, but that path is not present in the scanned repo."
                ),
                why_it_matters="Environment setup can fail immediately when editable, file, wheelhouse, or path dependencies point outside the shared repo.",
                suggested_fix="Commit the local dependency path, publish the dependency as a normal package, or update the manifest to a path that exists in the repo.",
            )
        )
    return findings


def _notebook_source_for_ast(source: str) -> str:
    lines: list[str] = []
    for index, raw_line in enumerate(source.splitlines()):
        stripped = raw_line.lstrip()
        if index == 0 and stripped.startswith("%%"):
            continue
        if stripped.startswith(("%", "!", "?")):
            continue
        lines.append(raw_line)
    return "\n".join(lines)


def _literal_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _is_os_environ(node: ast.AST) -> bool:
    return isinstance(node, ast.Attribute) and node.attr == "environ" and isinstance(node.value, ast.Name) and node.value.id == "os"


def _is_environ_name(node: ast.AST) -> bool:
    return isinstance(node, ast.Name) and node.id == "environ"


def _is_getenv_call(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr == "getenv" and isinstance(func.value, ast.Name) and func.value.id == "os"
    return isinstance(func, ast.Name) and func.id == "getenv"


def _environment_variable_reads(source: str, *, notebook: bool = False) -> list[tuple[int, str]]:
    parse_source = _notebook_source_for_ast(source) if notebook else source
    try:
        tree = ast.parse(parse_source)
    except SyntaxError:
        return []

    reads: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and (_is_os_environ(node.value) or _is_environ_name(node.value)):
            variable = _literal_string(node.slice)
            if variable:
                reads.append((node.lineno, variable))
            continue
        if not isinstance(node, ast.Call):
            continue
        if _is_getenv_call(node) and node.args:
            variable = _literal_string(node.args[0])
            if variable:
                reads.append((node.lineno, variable))
            continue
        if isinstance(node.func, ast.Attribute) and node.func.attr == "get" and (
            _is_os_environ(node.func.value) or _is_environ_name(node.func.value)
        ):
            if node.args:
                variable = _literal_string(node.args[0])
                if variable:
                    reads.append((node.lineno, variable))
    return reads


def _is_project_env_var(variable: str) -> bool:
    normalized = variable.strip()
    if not normalized or normalized in STANDARD_ENV_VARS:
        return False
    return not any(normalized.startswith(prefix) for prefix in STANDARD_ENV_PREFIXES)


def _env_documentation_text(root: Path, files: list[Path]) -> str:
    doc_parts: list[str] = []
    readme = root / "README.md"
    if readme.exists():
        try:
            doc_parts.append(readme.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            pass

    root_resolved = root.resolve()
    for path in files:
        try:
            relative = path.resolve().relative_to(root_resolved).as_posix()
        except ValueError:
            continue
        name = path.name.lower()
        if name not in ENV_EXAMPLE_FILENAMES and not relative.lower().startswith("docs/"):
            continue
        try:
            doc_parts.append(path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            continue
    return "\n".join(doc_parts)


def _project_documentation_text(root: Path, files: list[Path]) -> str:
    doc_parts: list[str] = []
    root_resolved = root.resolve()
    for candidate in (root / "README.md", root / "docs"):
        if candidate.is_file():
            try:
                doc_parts.append(candidate.read_text(encoding="utf-8"))
            except UnicodeDecodeError:
                continue
        elif candidate.is_dir():
            for path in sorted(candidate.rglob("*.md")):
                try:
                    doc_parts.append(path.read_text(encoding="utf-8"))
                except UnicodeDecodeError:
                    continue

    for path in files:
        try:
            relative = path.resolve().relative_to(root_resolved).as_posix()
        except ValueError:
            continue
        if relative.lower().startswith("docs/") or path.name.lower() in {"README.md", "readme.md"}:
            try:
                doc_parts.append(path.read_text(encoding="utf-8"))
            except UnicodeDecodeError:
                continue
    return "\n".join(doc_parts)


def _env_var_documented(variable: str, documentation: str) -> bool:
    return re.search(rf"(?<![A-Za-z0-9_]){re.escape(variable)}(?![A-Za-z0-9_])", documentation) is not None


def check_undocumented_environment_variables(root: Path, files: list[Path], artifacts: list[SourceArtifact]) -> list[Finding]:
    documentation = _env_documentation_text(root, files)
    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()

    for artifact in artifacts:
        reads = _environment_variable_reads(artifact.content, notebook=artifact.kind == "notebook")
        undocumented = [
            (line_number, variable)
            for line_number, variable in reads
            if _is_project_env_var(variable) and not _env_var_documented(variable, documentation)
        ]
        if not undocumented:
            continue

        rel_path = _relative_posix(artifact.path, root)
        examples: list[str] = []
        for line_number, variable in undocumented:
            key = (rel_path, variable)
            if key in seen:
                continue
            seen.add(key)
            examples.append(f"line {line_number}: {variable}")
        if not examples:
            continue
        findings.append(
            Finding(
                check_id="LC024",
                title="Environment variable is undocumented",
                severity="medium",
                category="onboarding",
                file_path=rel_path,
                evidence=f"Reads environment variable(s) with no README or .env.example documentation: {'; '.join(examples[:4])}.",
                why_it_matters="A repo can install correctly but still fail handoff when required environment variables are only known to the original author.",
                suggested_fix="Document the required variables in README.md or add a committed .env.example with safe placeholder values.",
            )
        )
    return findings


def _is_secret_scan_file(path: Path) -> bool:
    name = path.name.lower()
    if name in SECRET_SCAN_FILENAMES or name in ENV_EXAMPLE_FILENAMES or name.startswith(".env."):
        return True
    return path.suffix.lower() in SECRET_SCAN_SUFFIXES


def _secret_name_is_sensitive(name: str) -> bool:
    normalized = name.strip().lower().replace("-", "_").replace(".", "_")
    if not normalized:
        return False
    parts = [part for part in normalized.split("_") if part]
    joined = "_".join(parts)
    if any(fragment in joined for fragment in ("api_key", "access_key", "client_secret", "private_key", "auth_token")):
        return True
    return any(part in {"secret", "token", "password", "passwd", "pwd"} for part in parts)


def _normalize_secret_value(value: str) -> str:
    return value.strip().strip("\"'").rstrip(",;")


def _secret_value_is_placeholder(value: str) -> bool:
    normalized = _normalize_secret_value(value).strip().lower()
    if not normalized:
        return True
    if normalized.startswith(("$", "${", "<", "{{")):
        return True
    if normalized in PLACEHOLDER_SECRET_VALUES:
        return True
    return any(marker in normalized for marker in ("placeholder", "replace_me", "changeme", "your_", "your-", "example", "dummy", "fake"))


def _known_secret_value(value: str) -> bool:
    normalized = _normalize_secret_value(value)
    return any(pattern.fullmatch(normalized) for pattern in KNOWN_SECRET_VALUE_PATTERNS)


def _looks_like_secret_value(name: str, value: str) -> bool:
    normalized = _normalize_secret_value(value)
    if not _secret_name_is_sensitive(name) or _secret_value_is_placeholder(normalized):
        return False
    if _known_secret_value(normalized):
        return True
    if normalized.startswith(("http://", "https://", "file:")) or "/" in normalized or "\\" in normalized:
        return False
    if len(normalized) < 24:
        return False
    has_letter = any(char.isalpha() for char in normalized)
    has_digit = any(char.isdigit() for char in normalized)
    has_symbol = any(not char.isalnum() for char in normalized)
    return has_letter and (has_digit or has_symbol)


def _mask_secret_value(value: str) -> str:
    normalized = _normalize_secret_value(value)
    if len(normalized) <= 8:
        return "<redacted>"
    return f"{normalized[:4]}...{normalized[-4:]}"


def _secret_assignment_matches(line: str) -> list[tuple[str, str]]:
    matches: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for pattern in SECRET_ASSIGNMENT_PATTERNS:
        for match in pattern.finditer(line):
            name = match.group("name")
            value = match.group("value")
            key = (name, value)
            if key in seen:
                continue
            seen.add(key)
            if _looks_like_secret_value(name, value):
                matches.append((name, value))
    return matches


def check_hardcoded_secrets(root: Path, files: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[tuple[str, int, str]] = set()

    for path in files:
        if not _is_secret_scan_file(path):
            continue
        try:
            if path.stat().st_size > 1_000_000:
                continue
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        rel_path = _relative_posix(path, root)
        for line_number, line in enumerate(content.splitlines(), start=1):
            if PRIVATE_KEY_BLOCK_PATTERN.search(line):
                key = (rel_path, line_number, "private-key")
                if key in seen:
                    continue
                seen.add(key)
                findings.append(
                    Finding(
                        check_id="LC054",
                        title="Hardcoded secret-looking value",
                        severity="high",
                        category="onboarding",
                        file_path=rel_path,
                        evidence=f"line {line_number}: contains a private key block marker.",
                        why_it_matters="Publishing committed credentials or private keys can expose paid APIs, infrastructure, or private data when the repo is shared publicly.",
                        suggested_fix="Remove the secret from git history, rotate it, and load credentials from documented environment variables or a local .env file that is not committed.",
                    )
                )
                continue

            for name, value in _secret_assignment_matches(line):
                key = (rel_path, line_number, name)
                if key in seen:
                    continue
                seen.add(key)
                findings.append(
                    Finding(
                        check_id="LC054",
                        title="Hardcoded secret-looking value",
                        severity="high",
                        category="onboarding",
                        file_path=rel_path,
                        evidence=f"line {line_number}: {name} is assigned a secret-looking value ({_mask_secret_value(value)}).",
                        why_it_matters="Publishing committed credentials or private keys can expose paid APIs, infrastructure, or private data when the repo is shared publicly.",
                        suggested_fix="Remove the secret from git history, rotate it, and load credentials from documented environment variables or a local .env file that is not committed.",
                    )
                )
    return findings


def _target_names(target: ast.AST) -> set[str]:
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        names: set[str] = set()
        for element in target.elts:
            names.update(_target_names(element))
        return names
    return set()


def _shadowed_builtin_prompt_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == "input":
            names.add("input")
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if "input" in _target_names(target):
                    names.add("input")
        elif isinstance(node, ast.AnnAssign) and "input" in _target_names(node.target):
            names.add("input")
        elif isinstance(node, ast.ImportFrom) and node.module not in {None, "builtins"}:
            for alias in node.names:
                if (alias.asname or alias.name) == "input":
                    names.add("input")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if (alias.asname or alias.name.split(".", 1)[0]) == "input":
                    names.add("input")
    return names


def _interactive_prompt_issues(source: str, *, notebook: bool = False) -> list[str]:
    parse_source = _notebook_source_for_ast(source) if notebook else source
    try:
        tree = ast.parse(parse_source)
    except SyntaxError:
        return []

    shadowed_names = _shadowed_builtin_prompt_names(tree)
    getpass_aliases = _import_aliases(tree, "getpass")
    direct_getpass_names = _direct_import_names(tree, "getpass", {"getpass"})

    issues: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call_name = _call_name(node.func)
        if call_name == "input" and "input" not in shadowed_names:
            issues.append(f"line {node.lineno}: input(...)")
            continue
        if isinstance(node.func, ast.Name) and node.func.id in direct_getpass_names:
            issues.append(f"line {node.lineno}: {node.func.id}(...)")
            continue
        if any(call_name == f"{alias}.getpass" for alias in getpass_aliases):
            issues.append(f"line {node.lineno}: {call_name}(...)")
    return issues


def check_interactive_prompts(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    for artifact in artifacts:
        issues = _interactive_prompt_issues(artifact.content, notebook=artifact.kind == "notebook")
        if not issues:
            continue
        examples = "; ".join(issues[:4])
        findings.append(
            Finding(
                check_id="LC041",
                title="Interactive prompt blocks unattended rerun",
                severity="medium",
                category="onboarding",
                file_path=_relative_posix(artifact.path, root),
                evidence=f"Detected interactive prompt calls: {examples}.",
                why_it_matters="Notebooks and scripts that stop for terminal input cannot be rerun reliably in CI, batch jobs, or by reviewers following a README.",
                suggested_fix="Replace prompts with documented CLI arguments, config files, environment variables, or safe defaults for non-interactive reruns.",
            )
        )
    return findings


def _notebook_cd_magic_issues(source: str) -> list[str]:
    issues: list[str] = []
    for line_number, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("%cd"):
            issues.append(f"line {line_number}: {stripped[:120]}")
    return issues


def _working_directory_change_issues(source: str, *, notebook: bool = False) -> list[str]:
    parse_source = _notebook_source_for_ast(source) if notebook else source
    try:
        tree = ast.parse(parse_source)
    except SyntaxError:
        return _notebook_cd_magic_issues(source) if notebook else []

    os_aliases = _import_aliases(tree, "os")
    direct_chdir_names = _direct_import_names(tree, "os", {"chdir"})
    issues = _notebook_cd_magic_issues(source) if notebook else []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call_name = _call_name(node.func)
        if isinstance(node.func, ast.Name) and node.func.id in direct_chdir_names:
            issues.append(f"line {node.lineno}: {node.func.id}(...)")
            continue
        if any(call_name == f"{alias}.chdir" for alias in os_aliases):
            issues.append(f"line {node.lineno}: {call_name}(...)")
            continue
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "run_line_magic"
            and node.args
            and _literal_string(node.args[0]) == "cd"
        ):
            issues.append(f"line {node.lineno}: run_line_magic('cd', ...)")

    return list(dict.fromkeys(issues))


def check_working_directory_changes(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    for artifact in artifacts:
        issues = _working_directory_change_issues(artifact.content, notebook=artifact.kind == "notebook")
        if not issues:
            continue
        findings.append(
            Finding(
                check_id="LC051",
                title="Working directory changes during rerun",
                severity="medium",
                category="portability",
                file_path=_relative_posix(artifact.path, root),
                evidence=f"Detected persistent working-directory changes: {'; '.join(issues[:4])}.",
                why_it_matters="Changing the process working directory makes paths depend on cell order, launch location, or hidden session state, so fresh clones can read or write the wrong files.",
                suggested_fix="Keep paths repo-relative with pathlib.Path variables, pass base directories explicitly, or document the required run directory instead of mutating cwd.",
            )
        )
    return findings


def _script_reference_from_command_tokens(tokens: list[str]) -> str | None:
    if not tokens:
        return None
    command = tokens[0].lower()
    if command == "run":
        for token in tokens[1:]:
            if token.startswith("-"):
                continue
            if Path(token).suffix.lower() in {".py", ".ipynb"}:
                return token
        return None
    if command in {"python", "python3"}:
        if len(tokens) >= 2 and tokens[1] == "-m":
            return None
        for token in tokens[1:]:
            if token.startswith("-"):
                continue
            if Path(token).suffix.lower() == ".py":
                return token
        return None
    if command in {"bash", "sh"}:
        for token in tokens[1:]:
            if token.startswith("-"):
                continue
            if Path(token).suffix.lower() == ".sh":
                return token
    return None


def _is_checkable_local_script_reference(reference: str) -> bool:
    if not reference or _is_external_or_placeholder(reference):
        return False
    if reference.startswith(("$", "${", "~", "<")):
        return False
    return not Path(reference).is_absolute()


def _starts_shell_cell_magic(stripped_line: str) -> bool:
    tokens = stripped_line.split()
    if not tokens:
        return False
    if tokens[0] in {"%%bash", "%%sh"}:
        return True
    return len(tokens) >= 2 and tokens[0] == "%%script" and tokens[1] in {"bash", "sh"}


def _shell_or_magic_script_command_issues(root: Path, artifact: SourceArtifact) -> list[str]:
    issues: list[str] = []
    in_shell_cell = False
    for line_number, line in enumerate(artifact.content.splitlines(), start=1):
        stripped = line.strip()
        if _starts_shell_cell_magic(stripped):
            in_shell_cell = True
            continue
        if in_shell_cell and not stripped:
            in_shell_cell = False
            continue
        if in_shell_cell and stripped.startswith("%%"):
            in_shell_cell = _starts_shell_cell_magic(stripped)
            continue
        if not in_shell_cell and not stripped.startswith(("!", "%run")):
            continue
        reference = _script_reference_from_command_tokens(_shell_tokens(stripped))
        if (
            reference
            and _is_checkable_local_script_reference(reference)
            and not _candidate_exists_in_repo(root, artifact.path, reference)
        ):
            issues.append(f"line {line_number}: command references missing script '{reference}'")
    return issues


def _ast_command_tokens(node: ast.AST) -> list[str] | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return _shell_tokens(node.value)
    if isinstance(node, (ast.List, ast.Tuple)):
        tokens: list[str] = []
        for element in node.elts:
            literal = _literal_string(element)
            if literal is None:
                return None
            tokens.append(literal)
        return tokens
    return None


def _subprocess_call_names(tree: ast.AST) -> set[str]:
    subprocess_aliases = _import_aliases(tree, "subprocess")
    direct_names = _direct_import_names(tree, "subprocess", {"call", "check_call", "check_output", "Popen", "run"})
    names = {f"{alias}.{name}" for alias in subprocess_aliases for name in {"call", "check_call", "check_output", "Popen", "run"}}
    names.update(direct_names)
    return names


def _python_inline_script_command_issues(root: Path, artifact: SourceArtifact) -> list[str]:
    parse_source = _notebook_source_for_ast(artifact.content) if artifact.kind == "notebook" else artifact.content
    try:
        tree = ast.parse(parse_source)
    except SyntaxError:
        return []

    os_aliases = _import_aliases(tree, "os")
    direct_system_names = _direct_import_names(tree, "os", {"system"})
    subprocess_call_names = _subprocess_call_names(tree)
    issues: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        call_name = _call_name(node.func)
        tokens: list[str] | None = None
        if call_name in subprocess_call_names:
            tokens = _ast_command_tokens(node.args[0])
        elif isinstance(node.func, ast.Name) and node.func.id in direct_system_names:
            tokens = _ast_command_tokens(node.args[0])
        elif any(call_name == f"{alias}.system" for alias in os_aliases):
            tokens = _ast_command_tokens(node.args[0])
        if not tokens:
            continue
        reference = _script_reference_from_command_tokens(tokens)
        if (
            reference
            and _is_checkable_local_script_reference(reference)
            and not _candidate_exists_in_repo(root, artifact.path, reference)
        ):
            issues.append(f"line {getattr(node, 'lineno', 1)}: command references missing script '{reference}'")

    return issues


def check_inline_command_missing_paths(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    for artifact in artifacts:
        issues = list(
            dict.fromkeys(
                _shell_or_magic_script_command_issues(root, artifact)
                + _python_inline_script_command_issues(root, artifact)
            )
        )
        if not issues:
            continue
        findings.append(
            Finding(
                check_id="LC052",
                title="Inline command references a missing script",
                severity="medium",
                category="onboarding",
                file_path=_relative_posix(artifact.path, root),
                evidence=f"Detected inline commands that invoke missing local scripts: {'; '.join(issues[:4])}.",
                why_it_matters="Notebooks and scripts often hide setup or preprocessing in shell commands; fresh reruns fail when those invoked local scripts were not shared.",
                suggested_fix="Commit the referenced script, update the command to an existing entrypoint, or move the step into documented README/CI instructions.",
            )
        )
    return findings


def _accelerator_usage_issues(source: str) -> list[str]:
    issues: list[str] = []
    seen: set[str] = set()
    for line_number, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        for pattern in ACCELERATOR_USAGE_PATTERNS:
            if not pattern.search(stripped):
                continue
            issue = f"line {line_number}: {stripped[:120]}"
            if issue not in seen:
                seen.add(issue)
                issues.append(issue)
            break
    return issues


def check_undocumented_accelerator_requirement(
    root: Path,
    files: list[Path],
    artifacts: list[SourceArtifact],
) -> list[Finding]:
    documentation = _project_documentation_text(root, files)
    if ACCELERATOR_DOCUMENTATION_PATTERN.search(documentation):
        return []

    findings: list[Finding] = []
    for artifact in artifacts:
        issues = _accelerator_usage_issues(artifact.content)
        if not issues:
            continue
        findings.append(
            Finding(
                check_id="LC046",
                title="Accelerator requirement is undocumented",
                severity="medium",
                category="onboarding",
                file_path=_relative_posix(artifact.path, root),
                evidence=f"Detected GPU/CUDA-specific code with no matching README/docs note: {'; '.join(issues[:4])}.",
                why_it_matters="A repo can install successfully and still fail for reviewers if it silently assumes GPU, CUDA, or accelerator hardware.",
                suggested_fix="Document the required accelerator stack, tested CUDA/GPU setup, or CPU fallback in README.md or docs.",
            )
        )
    return findings


def _shell_tokens(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return []
    stripped = stripped.removeprefix("$").strip()
    if stripped.startswith(("!", "%")):
        stripped = stripped[1:].strip()
    try:
        return shlex.split(stripped, comments=True, posix=True)
    except ValueError:
        return stripped.split()


def _inline_install_args(tokens: list[str]) -> tuple[str, list[str]] | None:
    lowered = [token.lower() for token in tokens]
    for command in sorted(INLINE_INSTALL_COMMANDS, key=len, reverse=True):
        prefix = list(command)
        if lowered[: len(prefix)] == prefix:
            manager = " ".join(tokens[: len(prefix)])
            return manager, tokens[len(prefix) :]
    return None


def _is_pinned_install_token(token: str) -> bool:
    return any(marker in token for marker in INSTALL_PIN_MARKERS) or re.search(r"(?<![<>=!~])=[0-9]", token) is not None


def _is_install_package_token(token: str) -> bool:
    lowered = token.lower()
    if not token or token in {"&&", ";", "|"}:
        return False
    if lowered.startswith(("-", "http://", "https://", "git+", "file:")):
        return False
    if lowered in {"pip", "python", "python3"}:
        return False
    if token.startswith((".", "/", "~")):
        return False
    if "/" in token or "\\" in token:
        return False
    return True


def _unpinned_install_packages(args: list[str]) -> list[str]:
    packages: list[str] = []
    skip_next = False

    for index, token in enumerate(args):
        lowered = token.lower()
        if token in {"&&", ";", "|"}:
            break
        if skip_next:
            skip_next = False
            continue
        if index + 1 < len(args) and args[index + 1] == "@":
            continue
        if token == "@":
            skip_next = True
            continue
        if lowered in INSTALL_TOKEN_VALUE_OPTIONS:
            skip_next = True
            continue
        if lowered in INSTALL_FLAG_OPTIONS:
            continue
        if lowered in {"-e", "--editable"}:
            skip_next = True
            continue
        if lowered.startswith("--") and "=" in lowered:
            continue
        if not _is_install_package_token(token):
            continue
        if _is_pinned_install_token(token):
            continue
        packages.append(token)

    return packages


def _inline_unpinned_install_issues(source: str) -> list[str]:
    issues: list[str] = []
    for line_number, line in enumerate(source.splitlines(), start=1):
        command = _inline_install_args(_shell_tokens(line))
        if not command:
            continue
        manager, args = command
        packages = _unpinned_install_packages(args)
        if packages:
            issues.append(f"line {line_number}: {manager} installs {', '.join(packages[:4])}")
    return issues


def check_notebook_inline_unpinned_installs(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    for artifact in artifacts:
        if artifact.kind != "notebook":
            continue
        issues = _inline_unpinned_install_issues(artifact.content)
        if not issues:
            continue
        findings.append(
            Finding(
                check_id="LC020",
                title="Notebook installs unpinned packages inline",
                severity="medium",
                category="environment",
                file_path=_relative_posix(artifact.path, root),
                evidence=f"Detected inline install commands without package pins: {'; '.join(issues[:4])}.",
                why_it_matters="Inline notebook installs can silently drift over time even when the notebook itself is committed.",
                suggested_fix="Move dependencies into requirements.txt, pyproject.toml, or environment.yml, or pin inline notebook installs to exact or bounded versions.",
            )
        )
    return findings


def _normalize_system_install_tokens(tokens: list[str]) -> list[str]:
    normalized = list(tokens)
    while normalized and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", normalized[0]):
        normalized.pop(0)
    if normalized and normalized[0].lower() == "sudo":
        normalized.pop(0)
    return normalized


def _inline_system_install_args(tokens: list[str]) -> tuple[str, list[str]] | None:
    normalized = _normalize_system_install_tokens(tokens)
    lowered = [token.lower() for token in normalized]
    for command in sorted(SYSTEM_INSTALL_COMMANDS, key=len, reverse=True):
        prefix = list(command)
        if lowered[: len(prefix)] == prefix:
            manager = " ".join(normalized[: len(prefix)])
            return manager, normalized[len(prefix) :]
    return None


def _system_package_tokens(args: list[str]) -> list[str]:
    packages: list[str] = []
    skip_next = False
    for token in args:
        lowered = token.lower()
        if token in {"&&", ";", "|"}:
            break
        if skip_next:
            skip_next = False
            continue
        if lowered in SYSTEM_INSTALL_VALUE_OPTIONS:
            skip_next = True
            continue
        if lowered in SYSTEM_INSTALL_FLAG_OPTIONS or lowered.startswith("--") and "=" in lowered:
            continue
        if lowered.startswith("-"):
            continue
        packages.append(token)
    return packages


def _inline_system_install_issues(source: str) -> list[str]:
    issues: list[str] = []
    for line_number, raw_line in enumerate(source.splitlines(), start=1):
        for segment in re.split(r"\s*(?:&&|;|\|)\s*", raw_line):
            command = _inline_system_install_args(_shell_tokens(segment))
            if not command:
                continue
            manager, args = command
            packages = _system_package_tokens(args)
            if not packages:
                continue
            issues.append(f"line {line_number}: {manager} installs {', '.join(packages[:4])}")
    return issues


def check_inline_system_package_installs(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    for artifact in artifacts:
        issues = _inline_system_install_issues(artifact.content)
        if not issues:
            continue
        findings.append(
            Finding(
                check_id="LC048",
                title="System package install is inline",
                severity="medium",
                category="environment",
                file_path=_relative_posix(artifact.path, root),
                evidence=f"Detected inline OS package install commands: {'; '.join(issues[:4])}.",
                why_it_matters="Python dependency files can look complete while notebooks or scripts still need apt, brew, apk, yum, or other machine-level packages that reviewers do not know to install.",
                suggested_fix="Move OS package setup into Dockerfile, devcontainer, README setup steps, or a reproducible environment script instead of hiding it in notebook cells.",
            )
        )
    return findings


def _normalize_package_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower().strip()


def _has_supported_dependency_manifest(root: Path) -> bool:
    if any((root / name).exists() for name in SUPPORTED_DEPENDENCY_MANIFEST_FILES):
        return True
    return any(root.glob("*requirements*.txt")) or any(root.glob("requirements/*.txt"))


def _imported_top_level_modules(source: str, *, notebook: bool = False) -> set[str]:
    ast_source = _notebook_source_for_ast(source) if notebook else source
    try:
        tree = ast.parse(ast_source)
    except SyntaxError:
        modules: set[str] = set()
        for line in ast_source.splitlines():
            stripped = line.strip()
            import_match = re.match(r"import\s+([A-Za-z_][A-Za-z0-9_]*)", stripped)
            from_match = re.match(r"from\s+([A-Za-z_][A-Za-z0-9_]*)\b", stripped)
            if import_match:
                modules.add(import_match.group(1))
            if from_match:
                modules.add(from_match.group(1))
        return modules

    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module.split(".", 1)[0])
    return modules


def _imported_module_references(source: str, *, notebook: bool = False) -> list[tuple[int, str]]:
    ast_source = _notebook_source_for_ast(source) if notebook else source
    try:
        tree = ast.parse(ast_source)
    except SyntaxError:
        references: list[tuple[int, str]] = []
        for line_number, line in enumerate(ast_source.splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith(("%", "!", "?")):
                continue
            import_match = re.match(r"import\s+([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)", stripped)
            from_match = re.match(r"from\s+([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\s+import\b", stripped)
            if import_match:
                references.append((line_number, import_match.group(1)))
            if from_match:
                references.append((line_number, from_match.group(1)))
        return references

    references: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            references.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            references.append((node.lineno, node.module))
    return references


def check_undeclared_common_imports(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    if not _has_supported_dependency_manifest(root):
        return []

    declared = find_declared_dependency_names(root)
    findings: list[Finding] = []
    for artifact in artifacts:
        imported_modules = _imported_top_level_modules(artifact.content, notebook=artifact.kind == "notebook")
        missing_packages = sorted(
            {
                package
                for module, package in COMMON_IMPORT_DEPENDENCIES.items()
                if module in imported_modules and _normalize_package_name(package) not in declared
            }
        )
        if not missing_packages:
            continue
        findings.append(
            Finding(
                check_id="LC028",
                title="Imported dependency is not declared",
                severity="medium",
                category="environment",
                file_path=_relative_posix(artifact.path, root),
                evidence=(
                    "Imports common third-party package(s) with no matching dependency declaration: "
                    f"{', '.join(missing_packages[:8])}."
                ),
                why_it_matters="A repo can have a dependency manifest and still fail first-run setup when imported packages are missing from it.",
                suggested_fix="Add the missing package(s) to requirements.txt, pyproject.toml, or environment.yml, or document why they are provided by another setup layer.",
            )
        )
    return findings


def _is_stdlib_module(module_name: str) -> bool:
    top_level = module_name.split(".", 1)[0]
    return top_level in sys.stdlib_module_names or top_level in {"__future__"}


def _looks_like_local_helper_import(module_name: str) -> bool:
    parts = module_name.split(".")
    return any(part in LOCAL_HELPER_IMPORT_NAMES for part in parts[:2])


def _declared_or_common_dependency(module_name: str, declared: set[str]) -> bool:
    top_level = module_name.split(".", 1)[0]
    if top_level in COMMON_IMPORT_DEPENDENCIES:
        return True
    normalized = _normalize_package_name(top_level)
    return normalized in declared


def check_missing_local_module_imports(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    declared = find_declared_dependency_names(root) if _has_supported_dependency_manifest(root) else set()
    findings: list[Finding] = []
    for artifact in artifacts:
        missing: list[str] = []
        seen: set[str] = set()
        for line_number, module_name in _imported_module_references(
            artifact.content,
            notebook=artifact.kind == "notebook",
        ):
            top_level = module_name.split(".", 1)[0]
            if module_name in seen:
                continue
            seen.add(module_name)
            if (
                top_level == artifact.path.stem
                or _is_stdlib_module(module_name)
                or _declared_or_common_dependency(module_name, declared)
                or not _looks_like_local_helper_import(module_name)
                or _python_module_exists(root, module_name)
                or _python_module_exists(root, top_level)
            ):
                continue
            missing.append(f"line {line_number}: {module_name}")
        if not missing:
            continue
        findings.append(
            Finding(
                check_id="LC045",
                title="Local helper module import is missing",
                severity="medium",
                category="onboarding",
                file_path=_relative_posix(artifact.path, root),
                evidence=f"Imports project-local-looking module(s) that are not present in the repo: {'; '.join(missing[:6])}.",
                why_it_matters="Fresh clones fail quickly when notebooks or scripts import private helper modules that were never committed or packaged.",
                suggested_fix="Commit the helper module/package, add it as a declared dependency, or update the import to match the files that are actually shared.",
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


def _markdown_local_link_target(raw_target: str) -> str | None:
    target = raw_target.strip().strip("<>").strip()
    if not target or target.startswith("#") or target.startswith("//"):
        return None
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return None
    path = unquote(parsed.path or "").replace("\\", "/")
    path = path.lstrip("/")
    if not path:
        return None
    if path.startswith(("path/to/", "<")):
        return None
    return path


def _markdown_without_fenced_blocks(content: str) -> str:
    lines: list[str] = []
    in_fence = False
    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            lines.append("")
            continue
        lines.append("" if in_fence else raw_line)
    return "\n".join(lines)


def check_markdown_local_links(root: Path, markdown_files: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in markdown_files:
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        visible_markdown = _markdown_without_fenced_blocks(content)
        seen: set[str] = set()
        for match in MARKDOWN_INLINE_LINK_PATTERN.finditer(visible_markdown):
            target = _markdown_local_link_target(match.group(1))
            if target is None or target in seen:
                continue
            seen.add(target)
            if _candidate_exists_in_repo(root, path, target):
                continue
            findings.append(
                Finding(
                    check_id="LC062",
                    title="Markdown link references a missing local file",
                    severity="medium",
                    category="onboarding",
                    file_path=_relative_posix(path.resolve(), root.resolve()),
                    evidence=f"Markdown link target '{target}' is not present in the scanned repo.",
                    why_it_matters="README and docs links are part of the handoff path; dead local links send reviewers, students, and maintainers to missing notebooks, data, images, or policy pages.",
                    suggested_fix="Update the Markdown link, restore the missing file, or replace the link with explicit instructions for obtaining the artifact.",
                )
            )
    return findings


def _root_file_names(root: Path) -> set[str]:
    if not root.exists() or not root.is_dir():
        return set()
    return {path.name.lower() for path in root.iterdir() if path.is_file()}


def _read_optional_text(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def _has_license_metadata(root: Path) -> bool:
    names = _root_file_names(root)
    if names & LICENSE_FILE_NAMES:
        return True
    readme = _read_optional_text(root / "README.md")
    if re.search(r"(?im)^#{1,4}\s+licen[cs]e\b", readme) or re.search(
        r"\blicen[cs]ed under\b", readme, re.IGNORECASE
    ):
        return True
    pyproject = _read_optional_text(root / "pyproject.toml")
    return bool(re.search(r"(?im)^\s*licen[cs]e\s*=", pyproject) or "license-files" in pyproject.lower())


def _has_citation_metadata(root: Path) -> bool:
    names = _root_file_names(root)
    if names & CITATION_FILE_NAMES:
        return True
    readme = _read_optional_text(root / "README.md")
    return bool(
        re.search(r"(?im)^#{1,4}\s+(?:citation|citing|how to cite|cite this)\b", readme)
        or re.search(r"\b(?:please cite|how to cite|doi:|https://doi\.org/)", readme, re.IGNORECASE)
    )


def _looks_research_like(root: Path, notebooks: list[NotebookDocument], python_files: list[Path]) -> bool:
    if notebooks:
        return True
    if not python_files:
        return False
    readme = _read_optional_text(root / "README.md").lower()
    return any(
        marker in readme
        for marker in (
            "arxiv",
            "benchmark",
            "citation",
            "cite",
            "dataset",
            "doi",
            "experiment",
            "model",
            "notebook",
            "paper",
            "research",
            "reproduce",
            "reproducibility",
        )
    )


def check_missing_reuse_metadata(root: Path, notebooks: list[NotebookDocument], python_files: list[Path]) -> list[Finding]:
    if not root.is_dir() or not (notebooks or python_files):
        return []

    findings: list[Finding] = []
    if not _has_license_metadata(root):
        findings.append(
            Finding(
                check_id="LC063",
                title="Missing reuse license metadata",
                severity="low",
                category="onboarding",
                file_path=".",
                evidence="No top-level LICENSE/COPYING file, pyproject license field, or README license section was found.",
                why_it_matters="Professors, founders, students, and maintainers cannot safely reuse or evaluate a public repo if the permitted reuse terms are unclear.",
                suggested_fix="Add a top-level LICENSE file, declare the license in pyproject.toml, and mention the license from the README.",
            )
        )

    if _looks_research_like(root, notebooks, python_files) and not _has_citation_metadata(root):
        findings.append(
            Finding(
                check_id="LC064",
                title="Missing citation metadata",
                severity="low",
                category="onboarding",
                file_path=".",
                evidence="No CITATION.cff, codemeta.json, .zenodo.json, or README citation section was found.",
                why_it_matters="Research and notebook-heavy repos are easier to share when downstream users know exactly how to credit the project.",
                suggested_fix="Add CITATION.cff or a README citation section with the preferred citation, DOI, paper, or repository reference.",
            )
        )
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


def _gitignore_entries(root: Path) -> list[tuple[str, bool, bool]]:
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return []

    entries: list[tuple[str, bool, bool]] = []
    try:
        lines = gitignore.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return []

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        negated = line.startswith("!")
        if negated:
            line = line[1:].strip()
        line = line.replace("\\", "/")
        anchored = line.startswith("/")
        line = line.lstrip("/")
        directory_only = line.endswith("/")
        line = line.rstrip("/")
        if line:
            entries.append((line, negated, anchored or "/" in line or line.startswith("**/")))
            if directory_only and not line.endswith("/**"):
                entries.append((f"{line}/**", negated, True))
    return entries


def _gitignore_pattern_matches(pattern: str, anchored: bool, rel_path: str) -> bool:
    path = rel_path.strip("/")
    if not path:
        return False
    if anchored or "/" in pattern:
        return fnmatch.fnmatchcase(path, pattern)
    parts = path.split("/")
    return any(fnmatch.fnmatchcase(part, pattern) for part in parts)


def _gitignore_status(entries: list[tuple[str, bool, bool]], rel_path: str) -> tuple[bool, str]:
    ignored = False
    matched_pattern = ""
    for pattern, negated, anchored in entries:
        if not _gitignore_pattern_matches(pattern, anchored, rel_path):
            continue
        ignored = not negated
        matched_pattern = f"!{pattern}" if negated else pattern
    return ignored, matched_pattern


def _repo_parent_keys(rel_path: str) -> list[str]:
    parts = [part for part in rel_path.strip("/").split("/") if part]
    return ["/".join(parts[:index]) for index in range(1, len(parts))]


def _gitignored_match(root: Path, source_path: Path, candidate: str) -> tuple[str, str] | None:
    entries = _gitignore_entries(root)
    if not entries or _is_external_or_placeholder(candidate):
        return None

    root_resolved = root.resolve()
    for path in _candidate_repo_paths(root_resolved, source_path, candidate):
        if not _is_within_root(path, root_resolved) or not path.exists():
            continue
        try:
            rel_path = _repo_relative_key(path, root_resolved)
        except ValueError:
            continue
        ignored, matched_pattern = _gitignore_status(entries, rel_path)
        if not ignored:
            # Git cannot re-include a file below an ignored parent directory unless
            # the parent directory itself is also unignored.
            for parent_key in _repo_parent_keys(rel_path):
                parent_ignored, parent_pattern = _gitignore_status(entries, parent_key)
                if parent_ignored:
                    ignored = True
                    matched_pattern = parent_pattern
                    break
        if ignored:
            return rel_path, matched_pattern
    return None


def _is_likely_nested_output_write(candidate: str) -> bool:
    candidate_path = Path(candidate)
    if candidate_path.is_absolute() or not candidate_path.suffix:
        return False
    parts = [part.lower() for part in candidate_path.parts]
    if len(parts) < 2 or candidate_path.suffix.lower() not in OUTPUT_FILE_SUFFIXES:
        return False
    return any(part in OUTPUT_DIRECTORY_NAMES for part in parts[:-1])


def _literal_path_value(node: ast.AST, assignments: dict[str, str]) -> str | None:
    literal = _literal_string(node)
    if literal is not None:
        return literal
    if isinstance(node, ast.Name):
        return assignments.get(node.id)
    if isinstance(node, ast.Call) and _call_name(node.func) in {"Path", "pathlib.Path"} and node.args:
        return _literal_path_value(node.args[0], assignments)
    return None


def _created_directory_literals(source: str, *, notebook: bool = False) -> set[str]:
    parse_source = _notebook_source_for_ast(source) if notebook else source
    created: set[str] = set()
    assignments: dict[str, str] = {}
    try:
        tree = ast.parse(parse_source)
    except SyntaxError:
        tree = None

    if tree is not None:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            value = _literal_path_value(node.value, assignments)
            if not value:
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments[target.id] = value

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            call_name = _call_name(node.func)
            directory: str | None = None
            if call_name in {"os.makedirs", "os.mkdir", "makedirs", "mkdir"} and node.args:
                directory = _literal_path_value(node.args[0], assignments)
            elif isinstance(node.func, ast.Attribute) and node.func.attr == "mkdir":
                directory = _literal_path_value(node.func.value, assignments)
            if directory:
                created.add(directory)

    mkdir_pattern = re.compile(r"(?m)^\s*[!%]?\s*mkdir\s+(?:-[A-Za-z]*p[A-Za-z]*\s+)?['\"]?([^'\"\s;&|]+)")
    created.update(match.group(1) for match in mkdir_pattern.finditer(source))
    return created


def _import_aliases(tree: ast.AST, module_name: str) -> set[str]:
    aliases: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Import):
            continue
        for alias in node.names:
            if alias.name == module_name:
                aliases.add(alias.asname or module_name)
    return aliases


def _direct_import_names(tree: ast.AST, module_name: str, imported_names: set[str]) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.module != module_name:
            continue
        for alias in node.names:
            if alias.name in imported_names:
                names.add(alias.asname or alias.name)
    return names


def _path_constructor_literal(
    node: ast.AST,
    assignments: dict[str, str],
    path_names: set[str],
    pathlib_aliases: set[str],
) -> str | None:
    if not isinstance(node, ast.Call) or not node.args:
        return None
    call_name = _call_name(node.func)
    if isinstance(node.func, ast.Name) and node.func.id in path_names:
        return _literal_path_value(node.args[0], assignments)
    if any(call_name == f"{alias}.Path" for alias in pathlib_aliases):
        return _literal_path_value(node.args[0], assignments)
    return None


def _glob_base_candidate(pattern: str) -> str:
    normalized = pattern.replace("\\", "/").strip()
    parts = [part for part in normalized.split("/") if part and part != "."]
    base_parts: list[str] = []
    for part in parts:
        if any(token in part for token in ("*", "?", "[", "]", "{", "}")):
            break
        base_parts.append(part)
    return "/".join(base_parts)


def _is_likely_input_path(candidate: str) -> bool:
    parts = [part.lower() for part in candidate.replace("\\", "/").split("/") if part and part != "."]
    return any(part in INPUT_DIRECTORY_NAMES for part in parts)


def _candidate_directory_exists(root: Path, source_path: Path, candidate: str) -> bool:
    root_resolved = root.resolve()
    for path in _candidate_repo_paths(root_resolved, source_path, candidate):
        if _is_within_root(path, root_resolved) and path.exists() and path.is_dir():
            return True
    return False


def _literal_assignments(tree: ast.AST) -> dict[str, str]:
    assignments: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        value = _literal_path_value(node.value, assignments)
        if not value:
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                assignments[target.id] = value
    return assignments


def _file_discovery_import_context(
    tree: ast.AST,
) -> tuple[set[str], set[str], set[str], set[str], set[str], set[str]]:
    glob_aliases = _import_aliases(tree, "glob") or {"glob"}
    glob_direct_names = _direct_import_names(tree, "glob", {"glob", "iglob"})
    os_aliases = _import_aliases(tree, "os") or {"os"}
    os_direct_names = _direct_import_names(tree, "os", {"listdir", "scandir"})
    path_names = _direct_import_names(tree, "pathlib", {"Path"}) or {"Path"}
    pathlib_aliases = _import_aliases(tree, "pathlib") or {"pathlib"}
    return glob_aliases, glob_direct_names, os_aliases, os_direct_names, path_names, pathlib_aliases


def _file_discovery_call_candidate(
    node: ast.Call,
    assignments: dict[str, str],
    glob_aliases: set[str],
    glob_direct_names: set[str],
    os_aliases: set[str],
    os_direct_names: set[str],
    path_names: set[str],
    pathlib_aliases: set[str],
) -> tuple[str, str] | None:
    call_name = _call_name(node.func)
    candidate: str | None = None
    display: str | None = None

    if any(call_name in {f"{alias}.glob", f"{alias}.iglob"} for alias in glob_aliases) or (
        isinstance(node.func, ast.Name) and node.func.id in glob_direct_names
    ):
        if node.args:
            candidate = _literal_path_value(node.args[0], assignments)
            display = candidate
    elif any(call_name in {f"{alias}.listdir", f"{alias}.scandir"} for alias in os_aliases) or (
        isinstance(node.func, ast.Name) and node.func.id in os_direct_names
    ):
        if node.args:
            candidate = _literal_path_value(node.args[0], assignments)
            display = candidate
    elif isinstance(node.func, ast.Attribute) and node.func.attr in {"glob", "rglob", "iterdir"}:
        base = _path_constructor_literal(node.func.value, assignments, path_names, pathlib_aliases)
        if base and node.func.attr in {"glob", "rglob"} and node.args:
            pattern = _literal_path_value(node.args[0], assignments)
            if pattern:
                candidate = "/".join(part for part in (base, pattern) if part)
                display = candidate
        elif base and node.func.attr == "iterdir":
            candidate = base
            display = candidate

    if not candidate or not display or _is_external_or_placeholder(candidate):
        return None
    base_candidate = _glob_base_candidate(candidate)
    if not base_candidate or not _is_likely_input_path(base_candidate):
        return None
    return display, base_candidate


def _globbed_input_issues(source: str, *, notebook: bool = False) -> list[tuple[int, str, str]]:
    parse_source = _notebook_source_for_ast(source) if notebook else source
    try:
        tree = ast.parse(parse_source)
    except SyntaxError:
        return []

    assignments = _literal_assignments(tree)
    discovery_context = _file_discovery_import_context(tree)
    issues: list[tuple[int, str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        candidate = _file_discovery_call_candidate(node, assignments, *discovery_context)
        if candidate is None:
            continue
        display, base_candidate = candidate
        issues.append((getattr(node, "lineno", 1), display, base_candidate))
    return issues


def _ast_parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    return {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}


def _has_sorted_ancestor(node: ast.AST, parent_map: dict[ast.AST, ast.AST]) -> bool:
    current = node
    while current in parent_map:
        current = parent_map[current]
        if isinstance(current, ast.Call) and _call_name(current.func) == "sorted":
            return True
    return False


def _in_place_sorted_name_lines(tree: ast.AST) -> dict[str, list[int]]:
    sorted_names: dict[str, list[int]] = {}

    def record(name: str, line: int) -> None:
        sorted_names.setdefault(name, []).append(line)

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "sort"
            and isinstance(node.func.value, ast.Name)
        ):
            record(node.func.value.id, getattr(node, "lineno", 0))
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Call)
            and _call_name(node.value.func) == "sorted"
            and node.value.args
            and isinstance(node.value.args[0], ast.Name)
            and node.value.args[0].id in _assignment_target_names(node)
        ):
            record(node.value.args[0].id, getattr(node, "lineno", 0))
    return sorted_names


def _discovery_assignment_targets(node: ast.AST, parent_map: dict[ast.AST, ast.AST]) -> set[str]:
    current = node
    while current in parent_map:
        current = parent_map[current]
        if isinstance(current, ast.Assign):
            return _assignment_target_names(current)
        if isinstance(current, ast.AnnAssign) and isinstance(current.target, ast.Name):
            return {current.target.id}
    return set()


def _unsorted_file_discovery_issues(source: str, *, notebook: bool = False) -> list[tuple[int, str, str]]:
    parse_source = _notebook_source_for_ast(source) if notebook else source
    try:
        tree = ast.parse(parse_source)
    except SyntaxError:
        return []

    assignments = _literal_assignments(tree)
    discovery_context = _file_discovery_import_context(tree)
    parent_map = _ast_parent_map(tree)
    sorted_name_lines = _in_place_sorted_name_lines(tree)

    issues: list[tuple[int, str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        candidate = _file_discovery_call_candidate(node, assignments, *discovery_context)
        if candidate is None:
            continue
        if _has_sorted_ancestor(node, parent_map):
            continue
        target_names = _discovery_assignment_targets(node, parent_map)
        discovery_line = getattr(node, "lineno", 0)
        if target_names and any(
            sort_line >= discovery_line
            for target_name in target_names
            for sort_line in sorted_name_lines.get(target_name, [])
        ):
            continue
        display, base_candidate = candidate
        issues.append((getattr(node, "lineno", 1), display, base_candidate))
    return issues


def _repo_directory_keys(root: Path, source_path: Path, candidate: str) -> set[str]:
    root_resolved = root.resolve()
    keys: set[str] = set()
    for path in _candidate_repo_paths(root_resolved, source_path, candidate):
        if not _is_within_root(path, root_resolved):
            continue
        try:
            key = _repo_relative_key(path, root_resolved)
        except ValueError:
            continue
        if key:
            keys.add(key)
    return keys


def _write_parent_directory_keys(root: Path, source_path: Path, candidate: str) -> set[str]:
    root_resolved = root.resolve()
    keys: set[str] = set()
    for path in _candidate_repo_paths(root_resolved, source_path, candidate):
        if not _is_within_root(path, root_resolved):
            continue
        parent = path.parent
        if parent == root_resolved:
            continue
        try:
            keys.add(_repo_relative_key(parent, root_resolved))
        except ValueError:
            continue
    return keys


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


def check_gitignored_input_artifacts(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()

    for artifact in artifacts:
        rel_path = _relative_posix(artifact.path, root)
        candidates: list[tuple[str, str]] = [(candidate, "Reads") for candidate in artifact.reads]
        candidates.extend(
            (base_candidate, "Discovers")
            for _line, _display, base_candidate in _globbed_input_issues(
                artifact.content,
                notebook=artifact.kind == "notebook",
            )
        )
        for candidate, action in candidates:
            match = _gitignored_match(root, artifact.path, candidate)
            if match is None:
                continue
            ignored_path, pattern = match
            finding_key = (rel_path, ignored_path)
            if finding_key in seen:
                continue
            seen.add(finding_key)
            findings.append(
                Finding(
                    check_id="LC053",
                    title="Referenced input is ignored by git",
                    severity="high",
                    category="artifacts",
                    file_path=rel_path,
                    evidence=(
                        f"{action} '{candidate}', which resolves to '{ignored_path}', "
                        f"but that path is covered by .gitignore pattern '{pattern}'."
                    ),
                    why_it_matters="The workflow may pass on the author's machine while a clean public clone is missing the ignored input artifact.",
                    suggested_fix="Commit a small fixture, move the input outside ignored paths, document a restore/download step, or unignore the parent directory and specific safe file with ! exceptions.",
                )
            )
    return findings


def check_missing_globbed_input_paths(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[tuple[str, str, str]] = set()
    for artifact in artifacts:
        for _line, display, base_candidate in _globbed_input_issues(
            artifact.content,
            notebook=artifact.kind == "notebook",
        ):
            if _candidate_directory_exists(root, artifact.path, base_candidate):
                continue
            rel_path = _relative_posix(artifact.path, root)
            finding_key = (rel_path, display, base_candidate)
            if finding_key in seen:
                continue
            seen.add(finding_key)
            findings.append(
                Finding(
                    check_id="LC036",
                    title="Globbed input path is missing",
                    severity="high",
                    category="artifacts",
                    file_path=rel_path,
                    evidence=f"Uses glob/listdir input '{display}', but base path '{base_candidate}' is not present in the scanned repo.",
                    why_it_matters="Fresh clones often fail or silently process zero files when a workflow discovers inputs through glob/listdir calls whose data directory was never shared.",
                    suggested_fix="Commit the input directory or a small fixture, document the restore/download step, or make the input contract explicit before running the workflow.",
                )
            )
    return findings


def check_unsorted_file_discovery_order(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[tuple[str, str, str]] = set()
    for artifact in artifacts:
        for _line, display, base_candidate in _unsorted_file_discovery_issues(
            artifact.content,
            notebook=artifact.kind == "notebook",
        ):
            if not _candidate_directory_exists(root, artifact.path, base_candidate):
                continue
            rel_path = _relative_posix(artifact.path, root)
            finding_key = (rel_path, display, base_candidate)
            if finding_key in seen:
                continue
            seen.add(finding_key)
            findings.append(
                Finding(
                    check_id="LC038",
                    title="Unsorted file discovery order",
                    severity="medium",
                    category="determinism",
                    file_path=rel_path,
                    evidence=f"Discovers input files with '{display}' without an obvious sorted(...) or .sort().",
                    why_it_matters="Filesystem and glob iteration order can vary across platforms, filesystems, and runs, which can silently reshuffle rows, batches, or train/eval inputs.",
                    suggested_fix="Wrap file discovery in sorted(...), or sort the collected paths before iterating, concatenating, or splitting the data.",
                )
            )
    return findings


def _current_time_imports(tree: ast.AST) -> dict[str, set[str]]:
    return {
        "datetime_modules": _import_aliases(tree, "datetime") or {"datetime"},
        "datetime_names": _direct_import_names(tree, "datetime", {"datetime"}),
        "date_names": _direct_import_names(tree, "datetime", {"date"}),
        "time_modules": _import_aliases(tree, "time") or {"time"},
        "time_functions": _direct_import_names(tree, "time", {"time", "time_ns"}),
        "pandas_modules": _import_aliases(tree, "pandas"),
        "timestamp_names": _direct_import_names(tree, "pandas", {"Timestamp"}),
    }


def _is_current_time_call(call: ast.Call, imports: dict[str, set[str]]) -> bool:
    call_name = _call_name(call.func)
    if any(call_name in {f"{alias}.datetime.now", f"{alias}.datetime.utcnow"} for alias in imports["datetime_modules"]):
        return True
    if any(call_name == f"{alias}.date.today" for alias in imports["datetime_modules"]):
        return True
    if any(call_name in {f"{name}.now", f"{name}.utcnow"} for name in imports["datetime_names"]):
        return True
    if any(call_name == f"{name}.today" for name in imports["date_names"]):
        return True
    if any(call_name in {f"{alias}.time", f"{alias}.time_ns"} for alias in imports["time_modules"]):
        return True
    if isinstance(call.func, ast.Name) and call.func.id in imports["time_functions"]:
        return True
    if any(
        call_name in {f"{alias}.Timestamp.now", f"{alias}.Timestamp.utcnow", f"{alias}.Timestamp.today"}
        for alias in imports["pandas_modules"]
    ):
        return True
    return any(call_name in {f"{name}.now", f"{name}.utcnow", f"{name}.today"} for name in imports["timestamp_names"])


def _path_template_from_expr(node: ast.AST, assignments: dict[str, str]) -> str | None:
    literal = _literal_string(node)
    if literal is not None:
        return literal
    if isinstance(node, ast.Name):
        return assignments.get(node.id)
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                parts.append("{}")
        return "".join(parts)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _path_template_from_expr(node.left, assignments)
        right = _path_template_from_expr(node.right, assignments)
        if left is not None and right is not None:
            return left + right
    if isinstance(node, ast.Call) and _call_name(node.func) in {"Path", "pathlib.Path"} and node.args:
        return _path_template_from_expr(node.args[0], assignments)
    return None


def _expr_uses_current_time(node: ast.AST, time_names: set[str], imports: dict[str, set[str]]) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and child.id in time_names:
            return True
        if isinstance(child, ast.Call) and _is_current_time_call(child, imports):
            return True
    return False


def _assignment_target_names(node: ast.Assign) -> set[str]:
    names: set[str] = set()
    for target in node.targets:
        if isinstance(target, ast.Name):
            names.add(target.id)
    return names


def _expr_name_refs(node: ast.AST) -> set[str]:
    return {child.id for child in ast.walk(node) if isinstance(child, ast.Name)}


def _timestamp_context(tree: ast.AST) -> tuple[dict[str, str], set[str], dict[str, set[str]]]:
    imports = _current_time_imports(tree)
    assignments: dict[str, str] = {}
    time_names: set[str] = set()
    assign_nodes = sorted(
        (node for node in ast.walk(tree) if isinstance(node, ast.Assign)),
        key=lambda node: getattr(node, "lineno", 0),
    )

    for _ in range(4):
        changed = False
        for node in assign_nodes:
            target_names = _assignment_target_names(node)
            if not target_names:
                continue
            value_refs = _expr_name_refs(node.value)
            template = None if target_names & value_refs else _path_template_from_expr(node.value, assignments)
            if template is not None:
                for name in target_names:
                    if assignments.get(name) != template:
                        assignments[name] = template
                        changed = True
            if _expr_uses_current_time(node.value, time_names, imports):
                for name in target_names:
                    if name not in time_names:
                        time_names.add(name)
                        changed = True
        if not changed:
            break
    return assignments, time_names, imports


def _write_path_expr_from_call(call: ast.Call) -> ast.AST | None:
    call_name = _call_name(call.func)
    short_name = call_name.rsplit(".", 1)[-1]
    if short_name in {"to_csv", "to_parquet", "to_json", "to_excel", "to_feather", "to_pickle", "savefig"}:
        for keyword_name in ("path_or_buf", "path", "fname"):
            for keyword in call.keywords:
                if keyword.arg == keyword_name:
                    return keyword.value
        return call.args[0] if call.args else None
    if call_name == "open":
        mode: str | None = None
        if len(call.args) >= 2:
            mode = _literal_string(call.args[1])
        for keyword in call.keywords:
            if keyword.arg == "mode":
                mode = _literal_string(keyword.value)
        if mode and any(flag in mode for flag in ("w", "a", "x")):
            return call.args[0] if call.args else None
    if call_name in {"torch.save", "joblib.dump", "pickle.dump"} and len(call.args) >= 2:
        return call.args[1]
    if call_name in {"np.save", "numpy.save", "np.savez", "numpy.savez", "np.savez_compressed", "numpy.savez_compressed"} and call.args:
        return call.args[0]
    if isinstance(call.func, ast.Attribute) and call.func.attr in {"write_text", "write_bytes"}:
        return call.func.value
    return None


def _timestamped_output_issues(source: str, *, notebook: bool = False) -> list[tuple[int, str]]:
    parse_source = _notebook_source_for_ast(source) if notebook else source
    try:
        tree = ast.parse(parse_source)
    except SyntaxError:
        return []

    assignments, time_names, imports = _timestamp_context(tree)
    issues: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        path_expr = _write_path_expr_from_call(node)
        if path_expr is None or not _expr_uses_current_time(path_expr, time_names, imports):
            continue
        template = _path_template_from_expr(path_expr, assignments)
        if not template or not _is_likely_nested_output_write(template):
            continue
        issues.append((getattr(node, "lineno", 1), template))
    return issues


def check_timestamped_output_paths(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    for artifact in artifacts:
        for _line, template in _timestamped_output_issues(artifact.content, notebook=artifact.kind == "notebook"):
            rel_path = _relative_posix(artifact.path, root)
            finding_key = (rel_path, template)
            if finding_key in seen:
                continue
            seen.add(finding_key)
            findings.append(
                Finding(
                    check_id="LC037",
                    title="Timestamped output path is unstable",
                    severity="medium",
                    category="artifacts",
                    file_path=rel_path,
                    evidence=f"Writes timestamp-derived output path '{template}'.",
                    why_it_matters="Timestamped artifact names make reruns harder to compare, cache, document, or verify because the expected output path changes every run.",
                    suggested_fix="Use a stable output filename for reproducible artifacts, or make the run id an explicit documented parameter and write metadata separately.",
                )
            )
    return findings


def _current_time_call_label(call: ast.Call) -> str:
    return _call_name(call.func) or "current-time call"


def _assignment_parent(node: ast.AST, parent_map: dict[ast.AST, ast.AST]) -> ast.Assign | None:
    current = node
    while current in parent_map:
        current = parent_map[current]
        if isinstance(current, ast.Assign):
            return current
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return None
    return None


def _is_observability_time_context(node: ast.AST, parent_map: dict[ast.AST, ast.AST]) -> bool:
    current = node
    while current in parent_map:
        parent = parent_map[current]
        if isinstance(parent, ast.Call):
            outer_name = _call_name(parent.func)
            short_name = outer_name.rsplit(".", 1)[-1]
            if short_name == "print" or short_name in {"debug", "info", "warning", "warn", "error", "exception", "critical"}:
                return True
        if isinstance(parent, ast.Expr):
            return True
        current = parent
    return False


def _timestamped_output_time_context(
    tree: ast.AST,
    assignments: dict[str, str],
    time_names: set[str],
    imports: dict[str, set[str]],
) -> tuple[set[ast.Call], set[str]]:
    output_calls: set[ast.Call] = set()
    output_time_names: set[str] = set()
    assign_nodes = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)]

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        path_expr = _write_path_expr_from_call(node)
        if path_expr is None or not _expr_uses_current_time(path_expr, time_names, imports):
            continue
        template = _path_template_from_expr(path_expr, assignments)
        if not template or not _is_likely_nested_output_write(template):
            continue
        output_calls.update(child for child in ast.walk(path_expr) if isinstance(child, ast.Call) and _is_current_time_call(child, imports))
        output_time_names.update(_expr_name_refs(path_expr) & time_names)

    for _ in range(4):
        changed = False
        for node in assign_nodes:
            target_names = _assignment_target_names(node)
            if not target_names or not (target_names & output_time_names):
                continue
            refs = _expr_name_refs(node.value) & time_names
            before = len(output_time_names)
            output_time_names.update(refs)
            if len(output_time_names) != before:
                changed = True
        if not changed:
            break
    return output_calls, output_time_names


def _current_time_usage_issues(source: str, *, notebook: bool = False) -> list[tuple[int, str]]:
    parse_source = _notebook_source_for_ast(source) if notebook else source
    try:
        tree = ast.parse(parse_source)
    except SyntaxError:
        return []

    assignments, time_names, imports = _timestamp_context(tree)
    parent_map = _ast_parent_map(tree)
    output_calls, output_time_names = _timestamped_output_time_context(tree, assignments, time_names, imports)
    issues: list[tuple[int, str]] = []
    seen_lines: set[int] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_current_time_call(node, imports):
            continue
        if node in output_calls or _is_observability_time_context(node, parent_map):
            continue
        assignment = _assignment_parent(node, parent_map)
        if assignment is not None and _assignment_target_names(assignment) & output_time_names:
            continue
        line_number = getattr(node, "lineno", 1)
        if line_number in seen_lines:
            continue
        seen_lines.add(line_number)
        issues.append((line_number, _current_time_call_label(node)))
    return issues


def check_current_time_usage(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[tuple[str, int, str]] = set()
    for artifact in artifacts:
        rel_path = _relative_posix(artifact.path, root)
        for line_number, label in _current_time_usage_issues(artifact.content, notebook=artifact.kind == "notebook"):
            finding_key = (rel_path, line_number, label)
            if finding_key in seen:
                continue
            seen.add(finding_key)
            findings.append(
                Finding(
                    check_id="LC055",
                    title="Current time used in workflow logic",
                    severity="medium",
                    category="determinism",
                    file_path=rel_path,
                    evidence=f"line {line_number}: uses {label}(), so reruns can depend on the wall clock.",
                    why_it_matters="Clock-dependent filters, cutoffs, seeds, or labels can make the same repo produce different results on a different day or machine.",
                    suggested_fix="Pass the run date/time as an explicit parameter, pin it in config, or persist it as metadata instead of reading the wall clock inside the workflow.",
                )
            )
    return findings


def check_missing_output_directories(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    root_resolved = root.resolve()
    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    for artifact in artifacts:
        created_dirs: set[str] = set()
        for directory in _created_directory_literals(artifact.content, notebook=artifact.kind == "notebook"):
            if _is_external_or_placeholder(directory):
                continue
            created_dirs.update(_repo_directory_keys(root_resolved, artifact.path, directory))

        for candidate in artifact.writes:
            if _is_external_or_placeholder(candidate) or not _is_likely_nested_output_write(candidate):
                continue
            parent_keys = _write_parent_directory_keys(root_resolved, artifact.path, candidate)
            if not parent_keys:
                continue
            if any((root_resolved / parent_key).exists() for parent_key in parent_keys):
                continue
            if any(parent_key in created_dirs for parent_key in parent_keys):
                continue
            rel_path = _relative_posix(artifact.path, root)
            finding_key = (rel_path, candidate)
            if finding_key in seen:
                continue
            seen.add(finding_key)
            parent_list = ", ".join(sorted(parent_keys))
            findings.append(
                Finding(
                    check_id="LC035",
                    title="Output directory is not created",
                    severity="high",
                    category="artifacts",
                    file_path=rel_path,
                    evidence=f"Writes '{candidate}' under missing output directory {parent_list}.",
                    why_it_matters="A fresh clone can fail at save time even after setup succeeds if generated artifact directories are only present on the author's machine.",
                    suggested_fix="Create the directory before writing with mkdir(parents=True, exist_ok=True), commit a placeholder such as .gitkeep, or document the output setup step.",
                )
            )
    return findings


def _is_remote_url(path_text: str) -> bool:
    lowered = path_text.lower()
    return lowered.startswith(("http://", "https://"))


def _url_path_parts(url: str) -> list[str]:
    return [part for part in urlparse(url).path.split("/") if part]


def _is_mutable_remote_url(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path_parts = _url_path_parts(url)
    lowered = url.lower()

    if "latest" in lowered:
        return True

    if host == "raw.githubusercontent.com" and len(path_parts) >= 3:
        ref = path_parts[2]
        return ref.lower() in MOVING_REF_NAMES

    if host == "github.com" and len(path_parts) >= 5 and path_parts[2].lower() in {"raw", "blob"}:
        ref = path_parts[3]
        return ref.lower() in MOVING_REF_NAMES

    if host.endswith("github.io"):
        return True

    return False


def _has_checksum_context(source: str, url: str) -> bool:
    if CHECKSUM_CONTEXT_PATTERN.search(source):
        return True
    parsed = urlparse(url)
    return bool(CHECKSUM_CONTEXT_PATTERN.search(parsed.query))


def _remote_url_argument(call: ast.Call) -> str | None:
    for arg in call.args:
        value = _literal_string(arg)
        if value and _is_remote_url(value):
            return value
    return None


def _call_has_explicit_timeout(call: ast.Call, call_name: str) -> bool:
    if _has_keyword(call, "timeout"):
        return True
    if call_name == "urllib.request.urlopen" and len(call.args) >= 3:
        return True
    return False


def _remote_download_timeout_issues(source: str, *, notebook: bool = False) -> list[str]:
    issues: list[str] = []
    seen: set[str] = set()
    parse_source = _notebook_source_for_ast(source) if notebook else source
    try:
        tree = ast.parse(parse_source)
    except SyntaxError:
        tree = None

    if tree is not None:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            call_name = _call_name(node.func)
            if call_name not in REMOTE_TIMEOUT_REQUIRED_CALLS:
                continue
            url = _remote_url_argument(node)
            if not url:
                continue
            if _call_has_explicit_timeout(node, call_name):
                continue
            issue = f"line {node.lineno}: {call_name}('{url[:96]}')"
            if issue not in seen:
                seen.add(issue)
                issues.append(issue)

    for line_number, raw_line in enumerate(source.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not SHELL_REMOTE_DOWNLOAD_PATTERN.search(stripped):
            continue
        if SHELL_TIMEOUT_OPTION_PATTERN.search(stripped):
            continue
        issue = f"line {line_number}: {stripped[:120]}"
        if issue not in seen:
            seen.add(issue)
            issues.append(issue)

    return issues


def check_remote_download_without_timeout(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    for artifact in artifacts:
        issues = _remote_download_timeout_issues(artifact.content, notebook=artifact.kind == "notebook")
        if not issues:
            continue
        findings.append(
            Finding(
                check_id="LC047",
                title="Remote download has no timeout",
                severity="medium",
                category="artifacts",
                file_path=_relative_posix(artifact.path, root),
                evidence=f"Detected remote download/read calls without explicit timeouts: {'; '.join(issues[:4])}.",
                why_it_matters="Fresh-clone reruns, CI jobs, and reviewer handoffs can hang indefinitely when remote downloads have no timeout or bounded failure mode.",
                suggested_fix="Add an explicit timeout to network calls, or replace the live download with a documented cached/snapshotted artifact.",
            )
        )
    return findings


def check_remote_artifact_without_checksum(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    for artifact in artifacts:
        for candidate in artifact.reads:
            if not _is_remote_url(candidate):
                continue
            if _is_mutable_remote_url(candidate):
                continue
            if _has_checksum_context(artifact.content, candidate):
                continue
            rel_path = _relative_posix(artifact.path, root)
            finding_key = (rel_path, candidate)
            if finding_key in seen:
                continue
            seen.add(finding_key)
            findings.append(
                Finding(
                    check_id="LC050",
                    title="Remote artifact lacks checksum",
                    severity="medium",
                    category="artifacts",
                    file_path=rel_path,
                    evidence=f"Reads remote artifact '{candidate}' without visible checksum or hash verification.",
                    why_it_matters="Stable-looking remote URLs can still be replaced, corrupted, or mirrored differently, so reruns need an integrity check to prove the bytes are the same.",
                    suggested_fix="Publish a SHA256/SHA512 checksum with the artifact and verify it after download, or pin the artifact through a content-addressed archive such as a DOI/release asset with documented hash.",
                )
            )
    return findings


def check_mutable_remote_input_artifacts(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    for artifact in artifacts:
        for candidate in artifact.reads:
            if not _is_remote_url(candidate):
                continue
            if not _is_mutable_remote_url(candidate):
                continue
            if _has_checksum_context(artifact.content, candidate):
                continue
            rel_path = _relative_posix(artifact.path, root)
            finding_key = (rel_path, candidate)
            if finding_key in seen:
                continue
            seen.add(finding_key)
            findings.append(
                Finding(
                    check_id="LC022",
                    title="Mutable remote input data URL",
                    severity="medium",
                    category="artifacts",
                    file_path=rel_path,
                    evidence=f"Reads mutable remote input '{candidate}'.",
                    why_it_matters="Remote data can change or disappear even when the repo code is unchanged, making old results hard to reproduce.",
                    suggested_fix="Pin the URL to a release, tag, commit, DOI/archive snapshot, or document a checksum for the downloaded artifact.",
                )
            )
    return findings


HF_LOCAL_PATH_PREFIXES = (".", "..", "/", "~", "$", "<")
HF_LOCAL_PATH_ROOTS = {
    "artifact",
    "artifacts",
    "checkpoint",
    "checkpoints",
    "data",
    "dataset",
    "datasets",
    "model",
    "models",
    "output",
    "outputs",
    "result",
    "results",
    "run",
    "runs",
}
HF_DATASET_BUILDER_NAMES = {
    "arrow",
    "audiofolder",
    "csv",
    "imagefolder",
    "json",
    "parquet",
    "text",
    "webdataset",
}


def _keyword_non_none(call: ast.Call, keyword_name: str) -> bool:
    for keyword in call.keywords:
        if keyword.arg != keyword_name:
            continue
        return not (isinstance(keyword.value, ast.Constant) and keyword.value.value is None)
    return False


def _literal_first_arg(call: ast.Call) -> str | None:
    if not call.args:
        return None
    return _literal_string(call.args[0])


def _is_probably_local_hf_reference(reference: str) -> bool:
    normalized = reference.replace("\\", "/").strip()
    lowered = normalized.lower()
    if not normalized or "://" in lowered:
        return True
    if normalized.startswith(HF_LOCAL_PATH_PREFIXES) or re.match(r"^[A-Za-z]:/", normalized):
        return True
    parts = [part for part in lowered.split("/") if part]
    if not parts:
        return True
    if parts[0] in HF_LOCAL_PATH_ROOTS:
        return True
    return len(parts) == 1 and parts[0] in HF_LOCAL_PATH_ROOTS


def _huggingface_imports(tree: ast.AST) -> dict[str, set[str]]:
    imports = {
        "datasets_aliases": set(),
        "load_dataset_names": set(),
        "transformers_aliases": set(),
        "transformer_class_names": set(),
        "pipeline_names": set(),
        "hub_aliases": set(),
        "hub_download_names": set(),
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local_name = alias.asname or alias.name.split(".", 1)[0]
                if alias.name == "datasets":
                    imports["datasets_aliases"].add(local_name)
                elif alias.name == "transformers":
                    imports["transformers_aliases"].add(local_name)
                elif alias.name == "huggingface_hub":
                    imports["hub_aliases"].add(local_name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "datasets":
                for alias in node.names:
                    if alias.name == "load_dataset":
                        imports["load_dataset_names"].add(alias.asname or alias.name)
            elif module == "transformers":
                for alias in node.names:
                    if alias.name == "pipeline":
                        imports["pipeline_names"].add(alias.asname or alias.name)
                    else:
                        imports["transformer_class_names"].add(alias.asname or alias.name)
            elif module == "huggingface_hub":
                for alias in node.names:
                    if alias.name in {"hf_hub_download", "snapshot_download"}:
                        imports["hub_download_names"].add(alias.asname or alias.name)
    return imports


def _is_hf_load_dataset_call(call_name: str, imports: dict[str, set[str]]) -> bool:
    return call_name in imports["load_dataset_names"] or any(
        call_name == f"{alias}.load_dataset" for alias in imports["datasets_aliases"]
    )


def _is_hf_from_pretrained_call(call_name: str, imports: dict[str, set[str]]) -> bool:
    if any(call_name == f"{name}.from_pretrained" for name in imports["transformer_class_names"]):
        return True
    return any(
        call_name.startswith(f"{alias}.") and call_name.endswith(".from_pretrained")
        for alias in imports["transformers_aliases"]
    )


def _is_hf_hub_download_call(call_name: str, imports: dict[str, set[str]]) -> bool:
    if call_name in imports["hub_download_names"]:
        return True
    return any(
        call_name in {f"{alias}.hf_hub_download", f"{alias}.snapshot_download"}
        for alias in imports["hub_aliases"]
    )


def _is_hf_pipeline_call(call_name: str, imports: dict[str, set[str]]) -> bool:
    return call_name in imports["pipeline_names"] or any(
        call_name == f"{alias}.pipeline" for alias in imports["transformers_aliases"]
    )


def _hf_pipeline_model_reference(call: ast.Call) -> str | None:
    for keyword in call.keywords:
        if keyword.arg == "model":
            return _literal_string(keyword.value)
    return None


def _huggingface_revision_issues(source: str, *, notebook: bool = False) -> list[str]:
    parse_source = _notebook_source_for_ast(source) if notebook else source
    try:
        tree = ast.parse(parse_source)
    except SyntaxError:
        return []

    imports = _huggingface_imports(tree)
    issues: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call_name = _call_name(node.func)
        reference: str | None = None

        if _is_hf_load_dataset_call(call_name, imports):
            reference = _literal_first_arg(node)
            if reference and reference.lower() in HF_DATASET_BUILDER_NAMES:
                continue
        elif _is_hf_from_pretrained_call(call_name, imports):
            reference = _literal_first_arg(node)
        elif _is_hf_hub_download_call(call_name, imports):
            reference = _literal_first_arg(node)
        elif _is_hf_pipeline_call(call_name, imports):
            reference = _hf_pipeline_model_reference(node)
        else:
            continue

        if not reference or _is_probably_local_hf_reference(reference):
            continue
        if _keyword_non_none(node, "revision"):
            continue
        issues.append(f"line {node.lineno}: {call_name}('{reference}', ...)")
    return issues


def check_unpinned_huggingface_revisions(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    for artifact in artifacts:
        issues = _huggingface_revision_issues(artifact.content, notebook=artifact.kind == "notebook")
        if not issues:
            continue
        examples = "; ".join(issues[:4])
        findings.append(
            Finding(
                check_id="LC042",
                title="Hugging Face artifact revision is unpinned",
                severity="medium",
                category="artifacts",
                file_path=_relative_posix(artifact.path, root),
                evidence=f"Detected Hugging Face model/data calls without revision pins: {examples}.",
                why_it_matters="Hub datasets, models, and files can move when branches or defaults change, so an old report may rerun against different artifacts.",
                suggested_fix="Pin Hugging Face calls with revision=<commit-or-tag> and document when the model or dataset revision should be updated.",
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


def _node_preview(node: ast.AST) -> str:
    try:
        preview = ast.unparse(node)
    except Exception:
        return type(node).__name__
    return preview if len(preview) <= 96 else f"{preview[:93]}..."


def _shadowed_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets: list[ast.AST]
            if isinstance(node, ast.Assign):
                targets = list(node.targets)
            else:
                targets = [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
    return names


def _is_builtin_set_call(node: ast.AST, shadowed: set[str]) -> bool:
    return isinstance(node, ast.Call) and _call_name(node.func) == "set" and "set" not in shadowed


def _set_order_issue_label(node: ast.AST) -> str:
    preview = _node_preview(node)
    return preview.replace("\n", " ")


def _set_order_issues(source: str, *, notebook: bool = False) -> list[tuple[int, str]]:
    parse_source = _notebook_source_for_ast(source) if notebook else source
    try:
        tree = ast.parse(parse_source)
    except SyntaxError:
        return []

    shadowed = _shadowed_names(tree)
    issues: list[tuple[int, str]] = []
    seen: set[tuple[int, str]] = set()

    def add_issue(line_number: int, label: str) -> None:
        key = (line_number, label)
        if key in seen:
            return
        seen.add(key)
        issues.append(key)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_name = _call_name(node.func)
            short_name = call_name.rsplit(".", 1)[-1]
            first_arg = node.args[0] if node.args else None
            if short_name in {"list", "tuple"} and first_arg is not None and _is_builtin_set_call(first_arg, shadowed):
                add_issue(getattr(node, "lineno", 1), _set_order_issue_label(node))
            elif short_name in {"DataFrame", "Series"} and first_arg is not None and _is_builtin_set_call(first_arg, shadowed):
                add_issue(getattr(node, "lineno", 1), _set_order_issue_label(node))
            elif short_name == "join" and first_arg is not None and _is_builtin_set_call(first_arg, shadowed):
                add_issue(getattr(node, "lineno", 1), _set_order_issue_label(node))
        elif isinstance(node, ast.For) and _is_builtin_set_call(node.iter, shadowed):
            add_issue(getattr(node, "lineno", 1), f"for ... in {_set_order_issue_label(node.iter)}")
        elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            for generator in node.generators:
                if _is_builtin_set_call(generator.iter, shadowed):
                    add_issue(getattr(node, "lineno", 1), _set_order_issue_label(node))
                    break
    return issues


def _enclosing_function_name(node: ast.AST, parent_map: dict[ast.AST, ast.AST]) -> str:
    current = node
    while current in parent_map:
        current = parent_map[current]
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return current.name
    return ""


def _python_hash_issues(source: str, *, notebook: bool = False) -> list[tuple[int, str]]:
    parse_source = _notebook_source_for_ast(source) if notebook else source
    try:
        tree = ast.parse(parse_source)
    except SyntaxError:
        return []

    shadowed = _shadowed_names(tree)
    if "hash" in shadowed:
        return []

    parent_map = _ast_parent_map(tree)
    issues: list[tuple[int, str]] = []
    seen: set[tuple[int, str]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _call_name(node.func) != "hash":
            continue
        if _enclosing_function_name(node, parent_map) == "__hash__":
            continue
        label = _node_preview(node).replace("\n", " ")
        key = (getattr(node, "lineno", 1), label)
        if key in seen:
            continue
        seen.add(key)
        issues.append(key)
    return issues


def check_python_hash_usage(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[tuple[str, int, str]] = set()
    for artifact in artifacts:
        rel_path = _relative_posix(artifact.path, root)
        for line_number, label in _python_hash_issues(artifact.content, notebook=artifact.kind == "notebook"):
            finding_key = (rel_path, line_number, label)
            if finding_key in seen:
                continue
            seen.add(finding_key)
            findings.append(
                Finding(
                    check_id="LC057",
                    title="Python hash() is not stable across runs",
                    severity="medium",
                    category="determinism",
                    file_path=rel_path,
                    evidence=f"line {line_number}: uses built-in {label}, which can vary across Python processes.",
                    why_it_matters="Python's built-in hash() is randomized for strings and many objects, so hash-based splits, IDs, seeds, cache keys, or ordering can drift between reruns.",
                    suggested_fix="Use a stable digest such as hashlib.sha256(...).hexdigest(), or pin an explicit deterministic mapping for split IDs, seeds, and artifact names.",
                )
            )
    return findings


def check_set_derived_order(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[tuple[str, int, str]] = set()
    for artifact in artifacts:
        rel_path = _relative_posix(artifact.path, root)
        for line_number, label in _set_order_issues(artifact.content, notebook=artifact.kind == "notebook"):
            finding_key = (rel_path, line_number, label)
            if finding_key in seen:
                continue
            seen.add(finding_key)
            findings.append(
                Finding(
                    check_id="LC056",
                    title="Set-derived order is unstable",
                    severity="medium",
                    category="determinism",
                    file_path=rel_path,
                    evidence=f"line {line_number}: uses unordered set-derived data as an ordered sequence: {label}.",
                    why_it_matters="Python set iteration order can vary across processes because hash randomization changes, so rows, labels, reports, or train/eval inputs can silently reorder.",
                    suggested_fix="Use sorted(set(...)) when order matters, or preserve first-seen order with dict.fromkeys(...) before converting to a list.",
                )
            )
    return findings


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


def _numpy_random_imports(tree: ast.AST) -> tuple[set[str], set[str], set[str]]:
    numpy_aliases: set[str] = set()
    random_aliases: set[str] = set()
    direct_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "numpy":
                    numpy_aliases.add(alias.asname or "numpy")
                elif alias.name == "numpy.random":
                    random_aliases.add(alias.asname or "random")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "numpy":
                for alias in node.names:
                    if alias.name == "random":
                        random_aliases.add(alias.asname or alias.name)
            elif module == "numpy.random":
                for alias in node.names:
                    if alias.name == "default_rng":
                        direct_names.add(alias.asname or alias.name)
    return numpy_aliases, random_aliases, direct_names


def _call_has_explicit_seed(call: ast.Call) -> bool:
    if call.args:
        return not (isinstance(call.args[0], ast.Constant) and call.args[0].value is None)
    for keyword in call.keywords:
        if keyword.arg != "seed":
            continue
        return not (isinstance(keyword.value, ast.Constant) and keyword.value.value is None)
    return False


def _numpy_default_rng_issues(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    numpy_aliases, random_aliases, direct_names = _numpy_random_imports(tree)
    if not numpy_aliases and not random_aliases and not direct_names:
        return []

    issues: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call_name = _call_name(node.func)
        is_default_rng = (
            call_name in direct_names
            or any(call_name == f"{alias}.default_rng" for alias in random_aliases)
            or any(call_name == f"{alias}.random.default_rng" for alias in numpy_aliases)
        )
        if not is_default_rng:
            continue
        if _call_has_explicit_seed(node):
            continue
        issues.append(f"line {node.lineno}: {call_name}(...)")
    return issues


def _pytorch_random_split_imports(tree: ast.AST) -> tuple[set[str], set[str], set[str]]:
    torch_aliases = {"torch"}
    data_aliases: set[str] = set()
    direct_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_name = alias.name
                local_name = alias.asname or imported_name.split(".", 1)[0]
                if imported_name == "torch":
                    torch_aliases.add(local_name)
                elif imported_name == "torch.utils.data":
                    if alias.asname:
                        data_aliases.add(alias.asname)
                    else:
                        torch_aliases.add("torch")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "torch.utils.data":
                for alias in node.names:
                    if alias.name == "random_split":
                        direct_names.add(alias.asname or alias.name)
            elif module == "torch.utils":
                for alias in node.names:
                    if alias.name == "data":
                        data_aliases.add(alias.asname or alias.name)
    return torch_aliases, data_aliases, direct_names


def _pytorch_dataloader_imports(tree: ast.AST) -> tuple[set[str], set[str], set[str], set[str]]:
    torch_aliases: set[str] = set()
    utils_aliases: set[str] = set()
    data_aliases: set[str] = set()
    direct_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_name = alias.name
                local_name = alias.asname or imported_name.split(".", 1)[0]
                if imported_name == "torch":
                    torch_aliases.add(local_name)
                elif imported_name == "torch.utils":
                    if alias.asname:
                        utils_aliases.add(alias.asname)
                    else:
                        torch_aliases.add("torch")
                elif imported_name == "torch.utils.data":
                    if alias.asname:
                        data_aliases.add(alias.asname)
                    else:
                        torch_aliases.add("torch")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "torch.utils.data":
                for alias in node.names:
                    if alias.name == "DataLoader":
                        direct_names.add(alias.asname or alias.name)
            elif module == "torch.utils":
                for alias in node.names:
                    if alias.name == "data":
                        data_aliases.add(alias.asname or alias.name)
    return torch_aliases, utils_aliases, data_aliases, direct_names


def _pytorch_backend_imports(tree: ast.AST) -> tuple[set[str], set[str], set[str], set[str]]:
    torch_aliases = {"torch"}
    backend_aliases: set[str] = set()
    cudnn_aliases: set[str] = set()
    deterministic_algorithm_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_name = alias.name
                local_name = alias.asname or imported_name.split(".", 1)[0]
                if imported_name == "torch":
                    torch_aliases.add(local_name)
                elif imported_name == "torch.backends":
                    if alias.asname:
                        backend_aliases.add(alias.asname)
                    else:
                        torch_aliases.add("torch")
                elif imported_name == "torch.backends.cudnn":
                    if alias.asname:
                        cudnn_aliases.add(alias.asname)
                    else:
                        torch_aliases.add("torch")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "torch.backends":
                for alias in node.names:
                    if alias.name == "cudnn":
                        cudnn_aliases.add(alias.asname or alias.name)
            elif module == "torch":
                for alias in node.names:
                    if alias.name == "backends":
                        backend_aliases.add(alias.asname or alias.name)
                    elif alias.name == "use_deterministic_algorithms":
                        deterministic_algorithm_names.add(alias.asname or alias.name)
    return torch_aliases, backend_aliases, cudnn_aliases, deterministic_algorithm_names


def _literal_bool(node: ast.AST) -> bool | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, bool):
        return node.value
    return None


def _pytorch_deterministic_backend_issues(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    torch_aliases, backend_aliases, cudnn_aliases, deterministic_algorithm_names = _pytorch_backend_imports(tree)
    issues: list[str] = []
    seen: set[str] = set()

    def add_issue(line_number: int, label: str) -> None:
        issue = f"line {line_number}: {label}"
        if issue not in seen:
            seen.add(issue)
            issues.append(issue)

    def is_benchmark_target(target_name: str) -> bool:
        return (
            any(target_name == f"{alias}.backends.cudnn.benchmark" for alias in torch_aliases)
            or any(target_name == f"{alias}.cudnn.benchmark" for alias in backend_aliases)
            or any(target_name == f"{alias}.benchmark" for alias in cudnn_aliases)
        )

    def is_deterministic_target(target_name: str) -> bool:
        return (
            any(target_name == f"{alias}.backends.cudnn.deterministic" for alias in torch_aliases)
            or any(target_name == f"{alias}.cudnn.deterministic" for alias in backend_aliases)
            or any(target_name == f"{alias}.deterministic" for alias in cudnn_aliases)
        )

    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = _literal_bool(node.value)
            for target in targets:
                target_name = _call_name(target)
                if value is True and is_benchmark_target(target_name):
                    add_issue(getattr(node, "lineno", 1), f"{target_name} = True")
                elif value is False and is_deterministic_target(target_name):
                    add_issue(getattr(node, "lineno", 1), f"{target_name} = False")
        elif isinstance(node, ast.Call):
            call_name = _call_name(node.func)
            is_use_deterministic_algorithms = any(
                call_name == f"{alias}.use_deterministic_algorithms" for alias in torch_aliases
            ) or call_name in deterministic_algorithm_names
            if not is_use_deterministic_algorithms:
                continue
            mode_is_false = bool(node.args and _literal_bool(node.args[0]) is False) or any(
                keyword.arg == "mode" and _literal_bool(keyword.value) is False for keyword in node.keywords
            )
            if not mode_is_false:
                continue
            add_issue(node.lineno, f"{call_name}(False)")
    return issues


def _call_has_true_keyword(call: ast.Call, keyword_name: str) -> bool:
    for keyword in call.keywords:
        if keyword.arg != keyword_name:
            continue
        return isinstance(keyword.value, ast.Constant) and keyword.value.value is True
    return False


def _dataloader_shuffle_is_true(call: ast.Call) -> bool:
    if _call_has_true_keyword(call, "shuffle"):
        return True
    return len(call.args) >= 3 and isinstance(call.args[2], ast.Constant) and call.args[2].value is True


def _keyword_value(call: ast.Call, keyword_name: str) -> ast.AST | None:
    for keyword in call.keywords:
        if keyword.arg == keyword_name:
            return keyword.value
    return None


def _is_positive_int_literal(node: ast.AST | None) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, int)
        and not isinstance(node.value, bool)
        and node.value > 0
    )


def _is_none_literal(node: ast.AST | None) -> bool:
    return isinstance(node, ast.Constant) and node.value is None


def _dataloader_has_worker_init_fn(call: ast.Call) -> bool:
    keyword_value = _keyword_value(call, "worker_init_fn")
    if keyword_value is not None:
        return not _is_none_literal(keyword_value)
    return len(call.args) >= 11 and not _is_none_literal(call.args[10])


def _dataloader_uses_workers(call: ast.Call) -> bool:
    if _is_positive_int_literal(_keyword_value(call, "num_workers")):
        return True
    if len(call.args) >= 6 and _is_positive_int_literal(call.args[5]):
        return True
    return _call_has_true_keyword(call, "persistent_workers")


def _pytorch_dataloader_generator_issues(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    torch_aliases, utils_aliases, data_aliases, direct_names = _pytorch_dataloader_imports(tree)
    if not torch_aliases and not utils_aliases and not data_aliases and not direct_names:
        return []

    issues: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call_name = _call_name(node.func)
        is_dataloader = (
            call_name in direct_names
            or any(call_name == f"{alias}.DataLoader" for alias in data_aliases)
            or any(call_name == f"{alias}.data.DataLoader" for alias in utils_aliases)
            or any(call_name == f"{alias}.utils.data.DataLoader" for alias in torch_aliases)
        )
        if not is_dataloader:
            continue
        if not _dataloader_shuffle_is_true(node):
            continue
        if _has_keyword(node, "generator") or _has_keyword(node, "sampler") or _has_keyword(node, "batch_sampler"):
            continue
        issues.append(f"line {node.lineno}: {call_name}(..., shuffle=True)")
    return issues


def _pytorch_dataloader_worker_seed_issues(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    torch_aliases, utils_aliases, data_aliases, direct_names = _pytorch_dataloader_imports(tree)
    if not torch_aliases and not utils_aliases and not data_aliases and not direct_names:
        return []

    issues: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call_name = _call_name(node.func)
        is_dataloader = (
            call_name in direct_names
            or any(call_name == f"{alias}.DataLoader" for alias in data_aliases)
            or any(call_name == f"{alias}.data.DataLoader" for alias in utils_aliases)
            or any(call_name == f"{alias}.utils.data.DataLoader" for alias in torch_aliases)
        )
        if not is_dataloader:
            continue
        if not _dataloader_uses_workers(node):
            continue
        if _dataloader_has_worker_init_fn(node):
            continue
        issues.append(f"line {node.lineno}: {call_name}(..., num_workers>0)")
    return issues


def _pytorch_random_split_issues(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    torch_aliases, data_aliases, direct_names = _pytorch_random_split_imports(tree)
    issues: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call_name = _call_name(node.func)
        is_random_split = (
            call_name in direct_names
            or any(call_name == f"{alias}.random_split" for alias in data_aliases)
            or any(call_name == f"{alias}.utils.data.random_split" for alias in torch_aliases)
        )
        if not is_random_split:
            continue
        if _has_keyword(node, "generator") or len(node.args) >= 3:
            continue
        issues.append(f"line {node.lineno}: {call_name}(...)")
    return issues


TENSORFLOW_RANDOM_CALLS = {
    "categorical",
    "gamma",
    "normal",
    "poisson",
    "shuffle",
    "truncated_normal",
    "uniform",
}

XGBOOST_ESTIMATOR_CALLS = {
    "XGBClassifier",
    "XGBRanker",
    "XGBRegressor",
    "XGBRFClassifier",
    "XGBRFRegressor",
}

OPTUNA_SAMPLER_CALLS = {
    "CmaEsSampler",
    "NSGAIISampler",
    "NSGAIIISampler",
    "QMCSampler",
    "RandomSampler",
    "TPESampler",
}

JAX_RANDOM_DRAW_CALLS = {
    "bernoulli",
    "beta",
    "categorical",
    "choice",
    "exponential",
    "gamma",
    "gumbel",
    "laplace",
    "logistic",
    "multivariate_normal",
    "normal",
    "permutation",
    "poisson",
    "randint",
    "truncated_normal",
    "uniform",
}

POLARS_RANDOM_SOURCE_CALLS = {
    "DataFrame",
    "LazyFrame",
    "Series",
    "all",
    "arange",
    "col",
    "first",
    "int_range",
    "last",
    "read_csv",
    "read_json",
    "read_ndjson",
    "read_parquet",
    "scan_csv",
    "scan_ndjson",
    "scan_parquet",
}


def _assigned_target_names(target: ast.AST) -> set[str]:
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        names: set[str] = set()
        for element in target.elts:
            names.update(_assigned_target_names(element))
        return names
    return set()


def _call_has_non_none_keyword(call: ast.Call, keyword_name: str) -> bool:
    value = _keyword_value(call, keyword_name)
    return value is not None and not _is_none_literal(value)


def _optuna_imports(tree: ast.AST, source: str) -> tuple[set[str], set[str], set[str], set[str]]:
    optuna_aliases: set[str] = set()
    sampler_module_aliases: set[str] = set()
    create_study_names: set[str] = set()
    sampler_names: set[str] = set()
    if re.search(r"\boptuna\.", source):
        optuna_aliases.add("optuna")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_name = alias.name
                local_name = alias.asname or imported_name.split(".", 1)[0]
                if imported_name == "optuna":
                    optuna_aliases.add(local_name)
                elif imported_name == "optuna.samplers":
                    if alias.asname:
                        sampler_module_aliases.add(alias.asname)
                    else:
                        optuna_aliases.add("optuna")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "optuna":
                for alias in node.names:
                    if alias.name == "create_study":
                        create_study_names.add(alias.asname or alias.name)
                    elif alias.name == "samplers":
                        sampler_module_aliases.add(alias.asname or alias.name)
            elif module == "optuna.samplers":
                for alias in node.names:
                    if alias.name in OPTUNA_SAMPLER_CALLS:
                        sampler_names.add(alias.asname or alias.name)
    return optuna_aliases, sampler_module_aliases, create_study_names, sampler_names


def _is_optuna_create_study_call(
    call_name: str,
    optuna_aliases: set[str],
    create_study_names: set[str],
) -> bool:
    return call_name in create_study_names or any(call_name == f"{alias}.create_study" for alias in optuna_aliases)


def _is_optuna_sampler_call(
    call_name: str,
    optuna_aliases: set[str],
    sampler_module_aliases: set[str],
    sampler_names: set[str],
) -> bool:
    short_name = call_name.rsplit(".", 1)[-1]
    return (
        call_name in sampler_names
        or any(call_name == f"{alias}.{short_name}" for alias in sampler_module_aliases)
        or any(call_name == f"{alias}.samplers.{short_name}" for alias in optuna_aliases)
    ) and short_name in OPTUNA_SAMPLER_CALLS


def _optuna_sampler_call_lacks_seed(
    node: ast.AST,
    optuna_aliases: set[str],
    sampler_module_aliases: set[str],
    sampler_names: set[str],
) -> bool:
    return (
        isinstance(node, ast.Call)
        and _is_optuna_sampler_call(_call_name(node.func), optuna_aliases, sampler_module_aliases, sampler_names)
        and not _call_has_non_none_keyword(node, "seed")
    )


def _assignment_target_names(node: ast.Assign | ast.AnnAssign) -> set[str]:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    names: set[str] = set()
    for target in targets:
        if isinstance(target, ast.Name):
            names.add(target.id)
    return names


def _optuna_sampler_seed_issues(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    optuna_aliases, sampler_module_aliases, create_study_names, sampler_names = _optuna_imports(tree, source)
    if not optuna_aliases and not sampler_module_aliases and not create_study_names and not sampler_names:
        return []

    issues: list[str] = []
    seen: set[str] = set()
    unseeded_sampler_vars: set[str] = set()

    def add_issue(line_number: int, label: str) -> None:
        issue = f"line {line_number}: {label}"
        if issue not in seen:
            seen.add(issue)
            issues.append(issue)

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        if not _optuna_sampler_call_lacks_seed(
            node.value,
            optuna_aliases,
            sampler_module_aliases,
            sampler_names,
        ):
            continue
        unseeded_sampler_vars.update(_assignment_target_names(node))
        add_issue(getattr(node, "lineno", 1), f"{_call_name(node.value.func)}(...) without seed")

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call_name = _call_name(node.func)
        if _is_optuna_create_study_call(call_name, optuna_aliases, create_study_names):
            sampler_value = _keyword_value(node, "sampler")
            if sampler_value is None or _is_none_literal(sampler_value):
                add_issue(node.lineno, f"{call_name}(...) without sampler")
            elif _optuna_sampler_call_lacks_seed(
                sampler_value,
                optuna_aliases,
                sampler_module_aliases,
                sampler_names,
            ):
                add_issue(node.lineno, f"{call_name}(sampler=... without seed)")
            elif isinstance(sampler_value, ast.Name) and sampler_value.id in unseeded_sampler_vars:
                add_issue(node.lineno, f"{call_name}(sampler={sampler_value.id}) uses unseeded sampler")
        elif _optuna_sampler_call_lacks_seed(node, optuna_aliases, sampler_module_aliases, sampler_names):
            add_issue(node.lineno, f"{call_name}(...) without seed")
    return issues


def _jax_random_imports(tree: ast.AST, source: str) -> tuple[set[str], set[str], set[str], set[str], set[str]]:
    jax_aliases: set[str] = set()
    random_aliases: set[str] = set()
    prng_key_names: set[str] = set()
    split_names: set[str] = set()
    random_draw_names: set[str] = set()
    if re.search(r"\bjax\.random\.", source):
        jax_aliases.add("jax")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_name = alias.name
                local_name = alias.asname or imported_name.split(".", 1)[0]
                if imported_name == "jax":
                    jax_aliases.add(local_name)
                elif imported_name == "jax.random":
                    if alias.asname:
                        random_aliases.add(alias.asname)
                    else:
                        jax_aliases.add("jax")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "jax":
                for alias in node.names:
                    if alias.name == "random":
                        random_aliases.add(alias.asname or alias.name)
            elif module == "jax.random":
                for alias in node.names:
                    local_name = alias.asname or alias.name
                    if alias.name == "PRNGKey":
                        prng_key_names.add(local_name)
                    elif alias.name == "split":
                        split_names.add(local_name)
                    elif alias.name in JAX_RANDOM_DRAW_CALLS:
                        random_draw_names.add(local_name)
    return jax_aliases, random_aliases, prng_key_names, split_names, random_draw_names


def _is_jax_prng_key_call(
    call_name: str,
    jax_aliases: set[str],
    random_aliases: set[str],
    prng_key_names: set[str],
) -> bool:
    return (
        call_name in prng_key_names
        or any(call_name == f"{alias}.PRNGKey" for alias in random_aliases)
        or any(call_name == f"{alias}.random.PRNGKey" for alias in jax_aliases)
    )


def _is_jax_split_call(
    call_name: str,
    jax_aliases: set[str],
    random_aliases: set[str],
    split_names: set[str],
) -> bool:
    return (
        call_name in split_names
        or any(call_name == f"{alias}.split" for alias in random_aliases)
        or any(call_name == f"{alias}.random.split" for alias in jax_aliases)
    )


def _is_jax_random_draw_call(
    call_name: str,
    jax_aliases: set[str],
    random_aliases: set[str],
    random_draw_names: set[str],
) -> bool:
    short_name = call_name.rsplit(".", 1)[-1]
    return (
        call_name in random_draw_names
        or any(call_name == f"{alias}.{short_name}" for alias in random_aliases)
        or any(call_name == f"{alias}.random.{short_name}" for alias in jax_aliases)
    ) and short_name in JAX_RANDOM_DRAW_CALLS


def _jax_reused_prng_key_issues(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    jax_aliases, random_aliases, prng_key_names, split_names, random_draw_names = _jax_random_imports(tree, source)
    if not jax_aliases and not random_aliases and not prng_key_names and not random_draw_names:
        return []

    reset_lines: dict[str, list[int]] = {}
    key_usage: dict[str, list[tuple[int, str]]] = {}

    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            target_names: set[str] = set()
            for target in targets:
                target_names.update(_assigned_target_names(target))
            if isinstance(node.value, ast.Call):
                call_name = _call_name(node.value.func)
                if _is_jax_prng_key_call(call_name, jax_aliases, random_aliases, prng_key_names) or _is_jax_split_call(
                    call_name,
                    jax_aliases,
                    random_aliases,
                    split_names,
                ):
                    for name in target_names:
                        reset_lines.setdefault(name, []).append(getattr(node, "lineno", 1))

        if isinstance(node, ast.Call):
            call_name = _call_name(node.func)
            if not _is_jax_random_draw_call(call_name, jax_aliases, random_aliases, random_draw_names):
                continue
            if not node.args or not isinstance(node.args[0], ast.Name):
                continue
            key_name = node.args[0].id
            if key_name not in reset_lines:
                continue
            key_usage.setdefault(key_name, []).append((node.lineno, call_name))

    issues: list[str] = []
    for key_name, uses in sorted(key_usage.items()):
        ordered_uses = sorted(uses)
        resets = sorted(reset_lines.get(key_name, []))
        for previous, current in zip(ordered_uses, ordered_uses[1:]):
            previous_line = previous[0]
            current_line, current_call = current
            was_reset_between = any(previous_line < reset_line < current_line for reset_line in resets)
            if was_reset_between:
                continue
            issues.append(f"line {current_line}: {current_call} reuses PRNG key '{key_name}'")
            break
    return issues


def _tensorflow_imports(tree: ast.AST) -> tuple[set[str], set[str], set[str]]:
    tensorflow_aliases: set[str] = set()
    random_aliases: set[str] = set()
    keras_aliases: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "tensorflow":
                    tensorflow_aliases.add(alias.asname or "tensorflow")
                elif alias.name == "tensorflow.random":
                    random_aliases.add(alias.asname or "random")
                elif alias.name == "tensorflow.keras":
                    keras_aliases.add(alias.asname or "keras")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "tensorflow":
                for alias in node.names:
                    if alias.name == "random":
                        random_aliases.add(alias.asname or alias.name)
                    elif alias.name == "keras":
                        keras_aliases.add(alias.asname or alias.name)
            elif module == "tensorflow.random":
                for alias in node.names:
                    if alias.name in TENSORFLOW_RANDOM_CALLS:
                        random_aliases.add(alias.asname or alias.name)
            elif module == "tensorflow.keras":
                for alias in node.names:
                    if alias.name == "utils":
                        keras_aliases.add(alias.asname or "keras")
    return tensorflow_aliases, random_aliases, keras_aliases


def _tensorflow_call_kind(
    call_name: str,
    tensorflow_aliases: set[str],
    random_aliases: set[str],
    keras_aliases: set[str],
) -> str | None:
    for alias in tensorflow_aliases:
        if call_name == f"{alias}.random.set_seed" or call_name == f"{alias}.keras.utils.set_random_seed":
            return "seed"
        prefix = f"{alias}.random."
        if call_name.startswith(prefix):
            method_name = call_name[len(prefix) :]
            if method_name in TENSORFLOW_RANDOM_CALLS:
                return "random"
    for alias in random_aliases:
        if call_name == f"{alias}.set_seed":
            return "seed"
        prefix = f"{alias}."
        if call_name.startswith(prefix):
            method_name = call_name[len(prefix) :]
            if method_name in TENSORFLOW_RANDOM_CALLS:
                return "random"
        if call_name == alias and alias in TENSORFLOW_RANDOM_CALLS:
            return "random"
    for alias in keras_aliases:
        if call_name == f"{alias}.utils.set_random_seed":
            return "seed"
    if call_name == "keras.utils.set_random_seed":
        return "seed"
    return None


def _tensorflow_random_seed_issues(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    tensorflow_aliases, random_aliases, keras_aliases = _tensorflow_imports(tree)
    if not tensorflow_aliases and not random_aliases and not keras_aliases:
        return []

    issues: list[str] = []
    has_seed = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call_name = _call_name(node.func)
        kind = _tensorflow_call_kind(call_name, tensorflow_aliases, random_aliases, keras_aliases)
        if kind == "seed":
            has_seed = True
        elif kind == "random":
            issues.append(f"line {node.lineno}: {call_name}(...)")
    if has_seed:
        return []
    return issues


def _xgboost_imports(tree: ast.AST) -> tuple[set[str], set[str]]:
    module_aliases: set[str] = set()
    direct_estimator_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in {"xgboost", "xgboost.sklearn"}:
                    module_aliases.add(alias.asname or alias.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module in {"xgboost", "xgboost.sklearn"}:
                for alias in node.names:
                    if alias.name in XGBOOST_ESTIMATOR_CALLS:
                        direct_estimator_names.add(alias.asname or alias.name)
                    elif alias.name == "sklearn":
                        module_aliases.add(alias.asname or alias.name)
    return module_aliases, direct_estimator_names


def _xgboost_random_state_issues(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    module_aliases, direct_estimator_names = _xgboost_imports(tree)
    if not module_aliases and not direct_estimator_names:
        return []

    issues: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call_name = _call_name(node.func)
        is_estimator = (
            call_name in direct_estimator_names
            or any(
                call_name == f"{alias}.{estimator_name}"
                for alias in module_aliases
                for estimator_name in XGBOOST_ESTIMATOR_CALLS
            )
        )
        if not is_estimator:
            continue
        if _has_keyword(node, "random_state") or _has_keyword(node, "seed"):
            continue
        issues.append(f"line {node.lineno}: {call_name}(...)")
    return issues


def _polars_imports(tree: ast.AST) -> tuple[set[str], set[str]]:
    module_aliases: set[str] = set()
    direct_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "polars":
                    module_aliases.add(alias.asname or "polars")
        elif isinstance(node, ast.ImportFrom) and node.module == "polars":
            for alias in node.names:
                if alias.name in POLARS_RANDOM_SOURCE_CALLS:
                    direct_names.add(alias.asname or alias.name)
    return module_aliases, direct_names


def _is_polars_source_call(node: ast.AST, module_aliases: set[str], direct_names: set[str]) -> bool:
    if not isinstance(node, ast.Call):
        return False
    call_name = _call_name(node.func)
    if call_name in direct_names:
        return True
    return any(
        call_name == f"{alias}.{source_name}"
        for alias in module_aliases
        for source_name in POLARS_RANDOM_SOURCE_CALLS
    )


def _polars_method_display(node: ast.Call) -> str:
    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Call):
        source_name = _call_name(node.func.value.func)
        if source_name:
            return f"{source_name}(...).{node.func.attr}"
    return _call_name(node.func)


def _polars_seed_issues(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    module_aliases, direct_names = _polars_imports(tree)
    if not module_aliases and not direct_names:
        return []

    issues: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in {"sample", "shuffle"}:
            continue
        if not _is_polars_source_call(node.func.value, module_aliases, direct_names):
            continue
        if _has_keyword(node, "seed"):
            continue
        if node.func.attr == "sample" and len(node.args) >= 5:
            continue
        if node.func.attr == "shuffle" and node.args:
            continue
        issues.append(f"line {node.lineno}: {_polars_method_display(node)}(...)")
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


def check_missing_numpy_default_rng_seed(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    for artifact in artifacts:
        issues = _numpy_default_rng_issues(artifact.content)
        if not issues:
            continue
        examples = "; ".join(issues[:4])
        findings.append(
            Finding(
                check_id="LC039",
                title="NumPy default_rng lacks seed",
                severity="medium",
                category="determinism",
                file_path=_relative_posix(artifact.path, root),
                evidence=f"Detected NumPy default_rng calls without an explicit seed: {examples}.",
                why_it_matters="NumPy Generator streams created without a seed can produce different samples, permutations, and synthetic data between runs even when legacy np.random.seed(...) is present.",
                suggested_fix="Pass a documented seed to np.random.default_rng(seed) and reuse that Generator throughout the workflow.",
            )
        )
    return findings


def check_missing_tensorflow_seed(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    for artifact in artifacts:
        issues = _tensorflow_random_seed_issues(artifact.content)
        if not issues:
            continue
        examples = "; ".join(issues[:4])
        findings.append(
            Finding(
                check_id="LC032",
                title="TensorFlow randomness lacks set_seed",
                severity="medium",
                category="determinism",
                file_path=_relative_posix(artifact.path, root),
                evidence=f"Detected TensorFlow random calls without set_seed: {examples}.",
                why_it_matters="TensorFlow random tensors, shuffles, and initializers can drift between runs unless the workflow sets a visible TensorFlow seed.",
                suggested_fix="Call tf.random.set_seed(...) or tf.keras.utils.set_random_seed(...) near the start of the workflow and document the seed value.",
            )
        )
    return findings


def check_missing_xgboost_random_state(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    for artifact in artifacts:
        issues = _xgboost_random_state_issues(artifact.content)
        if not issues:
            continue
        examples = "; ".join(issues[:4])
        findings.append(
            Finding(
                check_id="LC033",
                title="XGBoost estimator lacks random_state",
                severity="medium",
                category="determinism",
                file_path=_relative_posix(artifact.path, root),
                evidence=f"Detected XGBoost estimators without random_state or seed: {examples}.",
                why_it_matters="XGBoost estimators can produce drifting model fits when sampling, parallelism, or stochastic boosters are used without a documented seed.",
                suggested_fix="Pass a documented random_state=... or seed=... value to XGBoost estimators used in reproducible workflows.",
            )
        )
    return findings


def check_missing_optuna_sampler_seed(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    for artifact in artifacts:
        issues = _optuna_sampler_seed_issues(artifact.content)
        if not issues:
            continue
        examples = "; ".join(issues[:4])
        findings.append(
            Finding(
                check_id="LC060",
                title="Optuna study lacks seeded sampler",
                severity="medium",
                category="determinism",
                file_path=_relative_posix(artifact.path, root),
                evidence=f"Detected Optuna study/sampler calls without a fixed sampler seed: {examples}.",
                why_it_matters="Optuna's default and unseeded samplers can suggest different trial sequences between reruns, so the reported best hyperparameters may drift even when model training is seeded.",
                suggested_fix="Create an explicit sampler such as optuna.samplers.TPESampler(seed=42) or RandomSampler(seed=42), then pass it to optuna.create_study(sampler=sampler).",
            )
        )
    return findings


def check_reused_jax_prng_key(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    for artifact in artifacts:
        issues = _jax_reused_prng_key_issues(artifact.content)
        if not issues:
            continue
        examples = "; ".join(issues[:4])
        findings.append(
            Finding(
                check_id="LC061",
                title="JAX PRNG key is reused",
                severity="medium",
                category="determinism",
                file_path=_relative_posix(artifact.path, root),
                evidence=f"Detected repeated JAX random draws with the same PRNG key and no visible split: {examples}.",
                why_it_matters="JAX PRNG keys are immutable; reusing the same key can repeat or correlate random draws, so experiments may look seeded while stochastic inputs are not actually independent.",
                suggested_fix="Split keys before each random draw with key, subkey = jax.random.split(key), then pass each subkey to exactly one stochastic operation.",
            )
        )
    return findings


def check_missing_polars_seed(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    for artifact in artifacts:
        issues = _polars_seed_issues(artifact.content)
        if not issues:
            continue
        examples = "; ".join(issues[:4])
        findings.append(
            Finding(
                check_id="LC034",
                title="Polars sampling lacks seed",
                severity="medium",
                category="determinism",
                file_path=_relative_posix(artifact.path, root),
                evidence=f"Detected Polars sample/shuffle calls without seed: {examples}.",
                why_it_matters="Polars sampling and expression shuffles can select different rows or orders between runs unless a visible seed is provided.",
                suggested_fix="Pass a documented seed=... value to Polars sample() or shuffle() calls used in reproducible workflows.",
            )
        )
    return findings


def check_missing_pytorch_random_split_generator(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    for artifact in artifacts:
        issues = _pytorch_random_split_issues(artifact.content)
        if not issues:
            continue
        examples = "; ".join(issues[:4])
        findings.append(
            Finding(
                check_id="LC031",
                title="PyTorch random_split lacks generator",
                severity="medium",
                category="determinism",
                file_path=_relative_posix(artifact.path, root),
                evidence=f"Detected PyTorch random_split calls without generator: {examples}.",
                why_it_matters="PyTorch random_split can assign examples to different train/validation partitions between runs unless it receives a seeded generator.",
                suggested_fix="Pass a documented torch.Generator().manual_seed(...) via generator= when calling random_split.",
            )
        )
    return findings


def check_missing_pytorch_dataloader_generator(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    for artifact in artifacts:
        issues = _pytorch_dataloader_generator_issues(artifact.content)
        if not issues:
            continue
        examples = "; ".join(issues[:4])
        findings.append(
            Finding(
                check_id="LC040",
                title="PyTorch DataLoader shuffle lacks generator",
                severity="medium",
                category="determinism",
                file_path=_relative_posix(artifact.path, root),
                evidence=f"Detected PyTorch DataLoader shuffle without generator: {examples}.",
                why_it_matters="DataLoader shuffle order can drift between runs unless it receives a seeded torch.Generator, which changes batch composition and model training trajectories.",
                suggested_fix="Create a documented torch.Generator().manual_seed(...) and pass it as generator= when constructing shuffled DataLoaders.",
            )
        )
    return findings


def check_pytorch_deterministic_backend(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    for artifact in artifacts:
        issues = _pytorch_deterministic_backend_issues(artifact.content)
        if not issues:
            continue
        examples = "; ".join(issues[:4])
        findings.append(
            Finding(
                check_id="LC058",
                title="PyTorch deterministic backend is disabled",
                severity="medium",
                category="determinism",
                file_path=_relative_posix(artifact.path, root),
                evidence=f"Detected PyTorch backend settings that allow nondeterministic kernels: {examples}.",
                why_it_matters="CuDNN benchmark mode and disabled deterministic algorithms can pick nondeterministic kernels, so seeded training can still drift across reruns or hardware.",
                suggested_fix="Use torch.backends.cudnn.benchmark = False, torch.backends.cudnn.deterministic = True, and torch.use_deterministic_algorithms(True) when reproducibility matters; document any intentional performance tradeoff.",
            )
        )
    return findings


def check_missing_pytorch_dataloader_worker_init(root: Path, artifacts: list[SourceArtifact]) -> list[Finding]:
    findings: list[Finding] = []
    for artifact in artifacts:
        issues = _pytorch_dataloader_worker_seed_issues(artifact.content)
        if not issues:
            continue
        examples = "; ".join(issues[:4])
        findings.append(
            Finding(
                check_id="LC059",
                title="PyTorch DataLoader workers lack seed init",
                severity="medium",
                category="determinism",
                file_path=_relative_posix(artifact.path, root),
                evidence=f"Detected multi-worker PyTorch DataLoader calls without worker_init_fn: {examples}.",
                why_it_matters="PyTorch worker processes can run dataset transforms that use Python, NumPy, or library randomness; without a visible worker_init_fn, seeded training can still drift across reruns.",
                suggested_fix="Define a worker_init_fn that derives per-worker seeds from torch.initial_seed(), seeds random and numpy.random, and pass it to every DataLoader with num_workers > 0.",
            )
        )
    return findings


def _find_makefile(root: Path) -> Path | None:
    for name in MAKEFILE_NAMES:
        candidate = root / name
        if candidate.exists():
            return candidate
    return None


def _makefile_targets(makefile: Path) -> set[str]:
    try:
        content = makefile.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return set()

    targets: set[str] = set()
    for raw_line in content.splitlines():
        if not raw_line or raw_line.startswith(("\t", " ")):
            continue
        line = raw_line.split("#", 1)[0].rstrip()
        if not line or "=" in line.split(":", 1)[0]:
            continue
        match = MAKE_TARGET_PATTERN.match(line)
        if not match:
            continue
        for target in match.group(1).split():
            if target and not target.startswith("."):
                targets.add(target)
    return targets


def _makefile_target_recipes(makefile: Path) -> dict[str, str]:
    try:
        content = makefile.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {}

    recipes: dict[str, list[str]] = {}
    current_targets: list[str] = []
    for raw_line in content.splitlines():
        if raw_line.startswith(("\t", " ")):
            if current_targets and raw_line.strip():
                for target in current_targets:
                    recipes.setdefault(target, []).append(raw_line.strip())
            continue

        line = raw_line.split("#", 1)[0].rstrip()
        current_targets = []
        if not line or "=" in line.split(":", 1)[0]:
            continue
        match = MAKE_TARGET_PATTERN.match(line)
        if not match:
            continue
        current_targets = [
            target
            for target in match.group(1).split()
            if target and not target.startswith(".")
        ]

    return {target: "\n".join(lines) for target, lines in recipes.items()}


def _find_justfile(root: Path) -> Path | None:
    for name in JUSTFILE_NAMES:
        candidate = root / name
        if candidate.exists():
            return candidate
    return None


def _just_recipes(root: Path) -> set[str] | None:
    justfile = _find_justfile(root)
    if justfile is None:
        return None
    try:
        content = justfile.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return set()

    recipes: set[str] = set()
    for raw_line in content.splitlines():
        if not raw_line or raw_line.startswith((" ", "\t", "#", "[")):
            continue
        line = raw_line.split("#", 1)[0].rstrip()
        alias_match = re.match(r"^alias\s+([A-Za-z0-9_.-]+)\s*:=", line)
        if alias_match:
            recipes.add(alias_match.group(1))
            continue
        if line.startswith(("alias ", "export ", "set ")):
            continue
        recipe_match = re.match(r"^([A-Za-z0-9_.-]+)(?:\s+[^:#]+)*\s*:(?!=)", line)
        if recipe_match:
            recipes.add(recipe_match.group(1))
    return recipes


def _doit_tasks(root: Path) -> set[str] | None:
    dodo = root / "dodo.py"
    if not dodo.exists():
        return None
    try:
        tree = ast.parse(dodo.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return set()
    tasks: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("task_"):
            task_name = node.name.removeprefix("task_")
            if task_name:
                tasks.add(task_name)
    return tasks


def _find_taskfile(root: Path) -> Path | None:
    for name in TASKFILE_NAMES:
        candidate = root / name
        if candidate.exists():
            return candidate
    return None


def _taskfile_tasks(root: Path) -> set[str] | None:
    taskfile = _find_taskfile(root)
    if taskfile is None:
        return None
    try:
        content = taskfile.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return set()

    tasks: set[str] = set()
    in_tasks = False
    tasks_indent = 0
    task_entry_indent: int | None = None
    for raw_line in content.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        tasks_match = re.match(r"^(?P<indent>\s*)tasks\s*:\s*(?:#.*)?$", raw_line)
        if tasks_match:
            in_tasks = True
            tasks_indent = len(tasks_match.group("indent").expandtabs(2))
            task_entry_indent = None
            continue
        indent = len(raw_line[: len(raw_line) - len(raw_line.lstrip(" \t"))].expandtabs(2))
        if in_tasks and indent <= tasks_indent:
            break
        if not in_tasks:
            continue
        if task_entry_indent is None:
            task_entry_indent = indent
        if indent != task_entry_indent:
            continue
        match = re.match(r"^\s+([A-Za-z0-9_.:-]+)\s*:", raw_line)
        if match:
            tasks.add(match.group(1))
    return tasks


def _invoke_tasks(root: Path) -> set[str] | None:
    tasks_file = root / "tasks.py"
    if not tasks_file.exists():
        return None
    try:
        tree = ast.parse(tasks_file.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return set()

    tasks: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            is_task, configured_name = _is_invoke_task_decorator(decorator)
            if is_task:
                tasks.add((configured_name or node.name).replace("_", "-"))
                break
    return tasks


def _python_module_exists(root: Path, module_name: str) -> bool:
    module_parts = module_name.split(".")
    search_roots = (root, root / "src")

    for search_root in search_roots:
        module_path = search_root.joinpath(*module_parts)
        if module_path.with_suffix(".py").exists():
            return True
        if (module_path / "__init__.py").exists() or (module_path / "__main__.py").exists():
            return True
    return False


def _package_json_scripts(root: Path) -> set[str]:
    return set(_package_json_script_commands(root))


def _package_json_script_commands(root: Path) -> dict[str, str]:
    package_json = root / "package.json"
    if not package_json.exists():
        return {}
    try:
        payload = json.loads(package_json.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    scripts = payload.get("scripts")
    if not isinstance(scripts, dict):
        return {}
    return {
        str(name): str(command)
        for name, command in scripts.items()
        if isinstance(command, str)
    }


def _read_toml(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError):
        return {}


def _table_keys(value: object) -> set[str]:
    if not isinstance(value, dict):
        return set()
    return {str(name) for name in value}


def _pixi_tasks(root: Path) -> set[str] | None:
    tasks: set[str] = set()
    found_manifest = False

    pyproject = _read_toml(root / "pyproject.toml")
    if pyproject is not None:
        found_manifest = True
        tool = pyproject.get("tool", {}) if isinstance(pyproject, dict) else {}
        pixi = tool.get("pixi", {}) if isinstance(tool, dict) else {}
        if isinstance(pixi, dict):
            tasks.update(_table_keys(pixi.get("tasks")))

    pixi_manifest = _read_toml(root / "pixi.toml")
    if pixi_manifest is not None:
        found_manifest = True
        tasks.update(_table_keys(pixi_manifest.get("tasks")))

    return tasks if found_manifest else None


def _hatch_tasks_from_envs(envs: object) -> set[str]:
    tasks: set[str] = set()
    if not isinstance(envs, dict):
        return tasks
    for env_name, env_config in envs.items():
        if not isinstance(env_name, str) or not isinstance(env_config, dict):
            continue
        for script_name in _table_keys(env_config.get("scripts")):
            if env_name == "default":
                tasks.add(script_name)
            tasks.add(f"{env_name}:{script_name}")
    return tasks


def _hatch_tasks(root: Path) -> set[str] | None:
    tasks: set[str] = set()
    found_manifest = False

    pyproject = _read_toml(root / "pyproject.toml")
    if pyproject is not None:
        found_manifest = True
        tool = pyproject.get("tool", {}) if isinstance(pyproject, dict) else {}
        hatch = tool.get("hatch", {}) if isinstance(tool, dict) else {}
        if isinstance(hatch, dict):
            tasks.update(_hatch_tasks_from_envs(hatch.get("envs")))

    hatch_manifest = _read_toml(root / "hatch.toml")
    if hatch_manifest is not None:
        found_manifest = True
        tasks.update(_hatch_tasks_from_envs(hatch_manifest.get("envs")))

    return tasks if found_manifest else None


def _pdm_scripts(root: Path) -> set[str] | None:
    pyproject = _read_toml(root / "pyproject.toml")
    if pyproject is None:
        return None
    tool = pyproject.get("tool", {}) if isinstance(pyproject, dict) else {}
    pdm = tool.get("pdm", {}) if isinstance(tool, dict) else {}
    if not isinstance(pdm, dict):
        return set()
    return _table_keys(pdm.get("scripts"))


def _taskipy_tasks(root: Path) -> set[str] | None:
    pyproject = _read_toml(root / "pyproject.toml")
    if pyproject is None:
        return None
    tool = pyproject.get("tool", {}) if isinstance(pyproject, dict) else {}
    taskipy = tool.get("taskipy", {}) if isinstance(tool, dict) else {}
    if not isinstance(taskipy, dict):
        return set()
    return _table_keys(taskipy.get("tasks"))


def _find_noxfile(root: Path) -> Path | None:
    for name in NOXFILE_NAMES:
        candidate = root / name
        if candidate.exists():
            return candidate
    return None


def _call_keyword_string(node: ast.Call, name: str) -> str | None:
    for keyword in node.keywords:
        if keyword.arg == name and isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
            return keyword.value.value
    return None


def _is_invoke_task_decorator(node: ast.AST) -> tuple[bool, str | None]:
    if isinstance(node, ast.Name):
        return node.id == "task", None
    if isinstance(node, ast.Attribute):
        return node.attr == "task", None
    if isinstance(node, ast.Call):
        is_task, _ = _is_invoke_task_decorator(node.func)
        if is_task:
            return True, _call_keyword_string(node, "name")
    return False, None


def _is_nox_session_decorator(node: ast.AST) -> tuple[bool, str | None]:
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return node.value.id == "nox" and node.attr == "session", None
    if isinstance(node, ast.Call):
        is_session, _ = _is_nox_session_decorator(node.func)
        if is_session:
            return True, _call_keyword_string(node, "name")
    return False, None


def _nox_sessions(root: Path) -> set[str] | None:
    noxfile = _find_noxfile(root)
    if noxfile is None:
        return None
    try:
        tree = ast.parse(noxfile.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return set()

    sessions: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            is_session, configured_name = _is_nox_session_decorator(decorator)
            if is_session:
                sessions.add(configured_name or node.name)
                break
    return sessions


def _split_tox_env_names(value: object) -> set[str]:
    raw_names: list[str] = []
    if isinstance(value, list):
        for item in value:
            raw_names.extend(_split_tox_env_names(item))
        return set(raw_names)
    if not isinstance(value, str):
        return set()

    for raw_line in value.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        raw_names.extend(_split_tox_env_line(line))

    expanded: set[str] = set()
    for name in raw_names:
        expanded.update(_expand_tox_factor_name(name))
    return expanded


def _split_tox_env_line(line: str) -> list[str]:
    names: list[str] = []
    current: list[str] = []
    brace_depth = 0
    for char in line:
        if char == "{":
            brace_depth += 1
        elif char == "}" and brace_depth:
            brace_depth -= 1

        if brace_depth == 0 and (char == "," or char.isspace()):
            name = "".join(current).strip()
            if name:
                names.append(name)
            current = []
            continue
        current.append(char)

    name = "".join(current).strip()
    if name:
        names.append(name)
    return names


def _expand_tox_factor_name(name: str) -> set[str]:
    match = re.search(r"\{([^{}]+)\}", name)
    if not match:
        return {name}

    expanded: set[str] = set()
    prefix = name[: match.start()]
    suffix = name[match.end() :]
    for option in match.group(1).split(","):
        expanded.update(_expand_tox_factor_name(f"{prefix}{option.strip()}{suffix}"))
    return expanded


def _tox_envs_from_ini(path: Path, tox_section: str) -> tuple[set[str], bool] | None:
    if not path.exists():
        return None
    parser = configparser.RawConfigParser()
    try:
        parser.read_string(path.read_text(encoding="utf-8-sig"))
    except (configparser.Error, UnicodeDecodeError):
        return set(), False

    envs: set[str] = set()
    if parser.has_section(tox_section):
        for option_name in ("envlist", "env_list"):
            if parser.has_option(tox_section, option_name):
                envs.update(_split_tox_env_names(parser.get(tox_section, option_name)))

    has_generic_testenv = parser.has_section("testenv")
    for section in parser.sections():
        if section.startswith("testenv:"):
            envs.update(_split_tox_env_names(section.removeprefix("testenv:")))
    return envs, has_generic_testenv


def _tox_envs(root: Path) -> tuple[set[str], bool] | None:
    envs: set[str] = set()
    has_generic_testenv = False
    found_config = False

    for name in TOX_INI_CONFIG_NAMES:
        config = _tox_envs_from_ini(root / name, "tox:tox" if name == "setup.cfg" else "tox")
        if config is None:
            continue
        found_config = True
        config_envs, config_has_generic = config
        envs.update(config_envs)
        has_generic_testenv = has_generic_testenv or config_has_generic

    pyproject = _read_toml(root / "pyproject.toml")
    if pyproject is not None:
        tool = pyproject.get("tool", {}) if isinstance(pyproject, dict) else {}
        tox = tool.get("tox", {}) if isinstance(tool, dict) else {}
        if isinstance(tox, dict):
            found_config = True
            envs.update(_split_tox_env_names(tox.get("env_list")))
            env_table = tox.get("env")
            if isinstance(env_table, dict):
                envs.update(str(name) for name in env_table)

    return (envs, has_generic_testenv) if found_config else None


def _find_rakefiles(root: Path) -> list[Path]:
    rakefiles = [root / name for name in RAKEFILE_NAMES if (root / name).exists()]
    task_dir = root / "lib" / "tasks"
    if task_dir.exists():
        rakefiles.extend(sorted(task_dir.glob("*.rake")))
    return rakefiles


def _rake_task_name(line: str) -> str | None:
    for pattern in (
        r"^task\s+:([A-Za-z0-9_]+)\b",
        r"^task\s+['\"]([A-Za-z0-9_:-]+)['\"]",
        r"^task\s+([A-Za-z0-9_:-]+)\s*:",
    ):
        match = re.match(pattern, line)
        if match:
            return match.group(1)
    return None


def _rake_tasks(root: Path) -> set[str] | None:
    rakefiles = _find_rakefiles(root)
    if not rakefiles:
        return None

    tasks: set[str] = set()
    for rakefile in rakefiles:
        try:
            content = rakefile.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        namespace_stack: list[tuple[str, int]] = []
        for raw_line in content.splitlines():
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            indent = len(raw_line) - len(raw_line.lstrip(" \t"))
            if stripped == "end":
                while namespace_stack and namespace_stack[-1][1] >= indent:
                    namespace_stack.pop()
                continue

            namespace_match = re.match(
                r"^namespace\s+(?::([A-Za-z0-9_]+)|['\"]([A-Za-z0-9_:-]+)['\"])\s+do\b",
                stripped,
            )
            if namespace_match:
                namespace_stack.append((namespace_match.group(1) or namespace_match.group(2), indent))
                continue

            task_name = _rake_task_name(stripped)
            if task_name:
                namespace_prefix = [name for name, _ in namespace_stack]
                tasks.add(":".join([*namespace_prefix, task_name]))
    return tasks


def _find_snakefiles(root: Path) -> list[Path]:
    snakefiles = [root / name for name in SNAKEFILE_NAMES if (root / name).exists()]
    workflow_dir = root / "workflow"
    if workflow_dir.exists():
        snakefiles.extend(sorted((workflow_dir / "rules").glob("*.smk")))
        snakefiles.extend(sorted(workflow_dir.glob("*.smk")))
    return sorted(set(snakefiles))


def _quoted_strings(content: str) -> set[str]:
    return {
        match.group(1) or match.group(2) or match.group(3)
        for match in re.finditer(r"""['"]([^'"]+)['"]|'''([^']+)'''|\"\"\"([^\"]+)\"\"\"""", content)
        if match.group(1) or match.group(2) or match.group(3)
    }


def _snakemake_targets(root: Path) -> set[str] | None:
    snakefiles = _find_snakefiles(root)
    if not snakefiles:
        return None

    targets: set[str] = set()
    for snakefile in snakefiles:
        try:
            content = snakefile.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        in_output = False
        output_indent = 0
        for raw_line in content.splitlines():
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            rule_match = re.match(r"^\s*rule\s+([A-Za-z_][A-Za-z0-9_]*)\s*:", raw_line)
            if rule_match:
                targets.add(rule_match.group(1))
                in_output = False
                continue

            indent = len(raw_line) - len(raw_line.lstrip(" \t"))
            output_match = re.match(r"^(\s*)output\s*:\s*(.*)$", raw_line)
            if output_match:
                in_output = True
                output_indent = len(output_match.group(1))
                targets.update(_quoted_strings(output_match.group(2)))
                continue

            if in_output and indent > output_indent:
                targets.update(_quoted_strings(raw_line))
                continue
            if in_output and indent <= output_indent:
                in_output = False
    return targets


def _nextflow_profiles(root: Path) -> set[str] | None:
    config_files = [root / name for name in NEXTFLOW_CONFIG_NAMES if (root / name).exists()]
    config_dir = root / "conf"
    if config_dir.exists():
        config_files.extend(sorted(config_dir.glob("*.config")))
    if not config_files:
        return None

    profiles: set[str] = set()
    for config_file in sorted(set(config_files)):
        try:
            content = config_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        in_profiles = False
        profiles_depth = 0
        for raw_line in content.splitlines():
            line = raw_line.split("//", 1)[0].strip()
            if not line or line.startswith("#"):
                continue
            if not in_profiles and re.match(r"^profiles\s*\{", line):
                in_profiles = True
                profiles_depth = line.count("{") - line.count("}")
                continue
            if not in_profiles:
                continue

            match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*\{", line)
            if match and profiles_depth == 1:
                profiles.add(match.group(1))
            profiles_depth += line.count("{") - line.count("}")
            if profiles_depth <= 0:
                in_profiles = False
    return profiles


def _nextflow_names(root: Path) -> set[str]:
    names: set[str] = set()
    nextflow_files = sorted(root.glob("*.nf"))
    workflow_dir = root / "workflow"
    if workflow_dir.exists():
        nextflow_files.extend(sorted(workflow_dir.rglob("*.nf")))

    for path in sorted(set(nextflow_files)):
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for match in re.finditer(r"^\s*(?:process|workflow)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{", content, re.MULTILINE):
            names.add(match.group(1))
    return names


def _is_probably_local_nextflow_pipeline(reference: str) -> bool:
    normalized = reference.replace("\\", "/").strip()
    if not normalized or normalized.startswith(("$", "${{", "~", "/", "<")) or "://" in normalized:
        return False
    if re.match(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/.*)?$", normalized):
        return False
    return True


def _dvc_stage_names(root: Path) -> set[str] | None:
    dvc_file = next((root / name for name in DVC_YAML_NAMES if (root / name).exists()), None)
    if dvc_file is None:
        return None

    try:
        content = dvc_file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return set()

    stages: set[str] = set()
    in_stages = False
    stages_indent = 0
    stage_indent: int | None = None
    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" \t"))
        if not in_stages:
            if re.match(r"^stages\s*:\s*(?:#.*)?$", stripped):
                in_stages = True
                stages_indent = indent
            continue

        if indent <= stages_indent:
            break
        if stage_indent is None:
            stage_indent = indent
        if indent != stage_indent:
            continue

        match = re.match(r"^\s*(?:['\"]([^'\"]+)['\"]|([A-Za-z0-9_.-]+))\s*:", raw_line)
        if match:
            stages.add(match.group(1) or match.group(2))
    return stages


def _dvc_target_exists(root: Path, target: str, stages: set[str] | None) -> bool:
    normalized = target.replace("\\", "/").strip()
    if not normalized or normalized.startswith(("$", "${{", "~", "/", "<")) or "://" in normalized:
        return True
    if stages is not None and normalized in stages:
        return True
    if ":" in normalized:
        file_part, stage_part = normalized.split(":", 1)
        if file_part in DVC_YAML_NAMES and stages is not None and stage_part in stages:
            return True
    if _path_exists_at_root(root, normalized):
        return True

    metadata_path = normalized if normalized.endswith(".dvc") else f"{normalized}.dvc"
    return _path_exists_at_root(root, metadata_path)


def _kedro_pipeline_registry_files(root: Path) -> list[Path]:
    return [
        path
        for path in root.rglob("pipeline_registry.py")
        if ".venv" not in path.parts and "site-packages" not in path.parts
    ]


def _kedro_pipeline_names_from_registry(path: Path) -> set[str]:
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return set()

    names: set[str] = set()
    try:
        tree = ast.parse(content)
    except SyntaxError:
        tree = None

    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for key in node.keys:
                    if isinstance(key, ast.Constant) and isinstance(key.value, str):
                        names.add(key.value)
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)
            ):
                names.add(node.slice.value)

    for match in re.finditer(r"pipelines\[['\"]([A-Za-z0-9_.:-]+)['\"]\]\s*=", content):
        names.add(match.group(1))
    for match in re.finditer(r"['\"]([A-Za-z0-9_.:-]+)['\"]\s*:", content):
        names.add(match.group(1))
    names.discard("__default__")
    return names


def _kedro_pipeline_names_from_directories(root: Path) -> set[str]:
    names: set[str] = set()
    for pipelines_dir in root.rglob("pipelines"):
        if not pipelines_dir.is_dir() or ".venv" in pipelines_dir.parts or "site-packages" in pipelines_dir.parts:
            continue
        for child in pipelines_dir.iterdir():
            if not child.is_dir() or child.name.startswith((".", "_")):
                continue
            if (child / "pipeline.py").exists() or (child / "__init__.py").exists():
                names.add(child.name)
    return names


def _kedro_pipeline_names(root: Path) -> set[str] | None:
    registry_files = _kedro_pipeline_registry_files(root)
    directory_names = _kedro_pipeline_names_from_directories(root)
    if not registry_files and not directory_names:
        return None

    names = set(directory_names)
    for registry_file in registry_files:
        names.update(_kedro_pipeline_names_from_registry(registry_file))
    return names


def _flow_decorator_name(decorator: ast.AST) -> str | None:
    if isinstance(decorator, ast.Name) and decorator.id == "flow":
        return ""
    if isinstance(decorator, ast.Attribute) and decorator.attr == "flow":
        return ""
    if isinstance(decorator, ast.Call):
        base = _flow_decorator_name(decorator.func)
        if base is None:
            return None
        for keyword in decorator.keywords:
            if keyword.arg == "name" and isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
                return keyword.value.value
        return ""
    return None


def _prefect_flow_aliases(name: str) -> set[str]:
    aliases = {name}
    if "_" in name:
        aliases.add(name.replace("_", "-"))
    return aliases


def _prefect_flow_names_from_python(path: Path) -> set[str]:
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return set()

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return set()

    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            decorator_name = _flow_decorator_name(decorator)
            if decorator_name is None:
                continue
            names.update(_prefect_flow_aliases(decorator_name or node.name))
    return names


def _prefect_flow_names_from_yaml(root: Path) -> set[str]:
    names: set[str] = set()
    for config_name in ("prefect.yaml", "prefect.yml"):
        config = root / config_name
        if not config.exists():
            continue
        try:
            content = config.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for match in re.finditer(r"entrypoint\s*:\s*[^:\n#]+:([A-Za-z_][A-Za-z0-9_]*)", content):
            names.update(_prefect_flow_aliases(match.group(1)))
    return names


def _prefect_flow_names(root: Path) -> set[str] | None:
    names = _prefect_flow_names_from_yaml(root)
    found_prefect_file = False
    for path in root.rglob("*.py"):
        if ".venv" in path.parts or "site-packages" in path.parts:
            continue
        path_names = _prefect_flow_names_from_python(path)
        if path_names:
            found_prefect_file = True
            names.update(path_names)

    if not names and not found_prefect_file:
        return None
    return names


def _dbt_selector_names(root: Path) -> set[str]:
    names: set[str] = set()
    for config_name in ("selectors.yml", "selectors.yaml"):
        config = root / config_name
        if not config.exists():
            continue
        try:
            content = config.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for match in re.finditer(r"(?m)^\s*-\s*name\s*:\s*['\"]?([A-Za-z0-9_.:-]+)['\"]?", content):
            names.add(match.group(1))
    return names


def _dbt_model_names(root: Path) -> tuple[set[str], set[str], set[str]] | None:
    model_names: set[str] = set()
    model_paths: set[str] = set()
    selector_names = _dbt_selector_names(root)
    has_dbt_structure = selector_names or (root / "dbt_project.yml").exists() or (root / "dbt_project.yaml").exists()

    for path in root.rglob("*.sql"):
        relative_parts = path.relative_to(root).parts
        lowered_parts = {part.lower() for part in relative_parts}
        if {".venv", "site-packages", "target", "dbt_packages", "logs"} & lowered_parts:
            continue
        normalized = path.relative_to(root).as_posix()
        if "models" not in lowered_parts and "snapshots" not in lowered_parts and "analyses" not in lowered_parts:
            continue
        has_dbt_structure = True
        model_names.add(path.stem)
        model_paths.add(normalized)
        model_paths.add(normalized.removesuffix(".sql"))

    if not has_dbt_structure:
        return None
    return model_names, model_paths, selector_names


def _dbt_selector_reference_exists(root: Path, selector: str, model_names: set[str], model_paths: set[str], selector_names: set[str]) -> bool:
    normalized = selector.strip().lstrip("@+").rstrip("+")
    if not normalized or any(marker in normalized for marker in ("*", "?", "[", "]", "{", "}", "$")):
        return True

    if ":" in normalized:
        method, target = normalized.split(":", 1)
        target = target.strip().lstrip("@+").rstrip("+")
        if method == "selector":
            return target in selector_names
        if method in {"file", "path"}:
            candidate = target.removesuffix(".sql")
            return (
                _path_exists_at_root(root, target)
                or _path_exists_at_root(root, f"models/{target}")
                or candidate in model_paths
                or f"models/{candidate}" in model_paths
            )
        return True

    if normalized in model_names or normalized in model_paths:
        return True
    if "/" in normalized or normalized.endswith(".sql"):
        candidate = normalized.removesuffix(".sql")
        return (
            _path_exists_at_root(root, normalized)
            or _path_exists_at_root(root, f"{normalized}.sql")
            or _path_exists_at_root(root, f"models/{normalized}")
            or _path_exists_at_root(root, f"models/{normalized}.sql")
            or candidate in model_paths
            or f"models/{candidate}" in model_paths
        )

    if "." in normalized:
        parts = normalized.split(".")
        if parts[-1] in model_names:
            return True
        dotted_path = "/".join(parts)
        return _path_exists_at_root(root, dotted_path) or _path_exists_at_root(root, f"models/{dotted_path}")

    return False


def _gx_checkpoint_names(root: Path) -> set[str] | None:
    names: set[str] = set()
    checkpoint_dirs = [
        root / "great_expectations" / "checkpoints",
        root / "gx" / "checkpoints",
    ]
    existing_dirs = [checkpoint_dir for checkpoint_dir in checkpoint_dirs if checkpoint_dir.exists()]
    if not existing_dirs:
        return None

    for checkpoint_dir in existing_dirs:
        for path in checkpoint_dir.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".yml", ".yaml", ".json"}:
                continue
            names.add(path.stem)
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for match in re.finditer(r"(?m)^\s*name\s*:\s*['\"]?([A-Za-z0-9_.:-]+)['\"]?", content):
                names.add(match.group(1))
            for match in re.finditer(r'"name"\s*:\s*"([A-Za-z0-9_.:-]+)"', content):
                names.add(match.group(1))
    return names


def _ploomber_spec_task_names(path: Path, root: Path, seen: set[Path]) -> set[str]:
    try:
        resolved = path.resolve()
    except OSError:
        return set()
    if resolved in seen or not path.exists():
        return set()
    seen.add(resolved)

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return set()

    names: set[str] = set()
    in_tasks = False
    tasks_indent = 0
    in_imports = False
    imports_indent = 0
    for raw_line in content.splitlines():
        line_without_comment = raw_line.split("#", 1)[0].rstrip()
        stripped = line_without_comment.strip()
        if not stripped:
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" \t"))

        if re.match(r"^tasks\s*:\s*$", stripped):
            in_tasks = True
            tasks_indent = indent
            in_imports = False
            continue
        if in_tasks and indent <= tasks_indent:
            in_tasks = False

        import_match = re.match(r"^import_tasks_from\s*:\s*(.+)$", stripped)
        if import_match:
            in_imports = False
            imports_value = import_match.group(1).strip().strip("'\"")
            if imports_value and imports_value not in {"|", ">"} and not imports_value.startswith("["):
                names.update(_ploomber_spec_task_names(root / imports_value, root, seen))
            continue
        if re.match(r"^import_tasks_from\s*:\s*$", stripped):
            in_imports = True
            imports_indent = indent
            continue
        if in_imports and indent <= imports_indent:
            in_imports = False
        if in_imports:
            import_item = re.match(r"^-\s*['\"]?([^'\"]+)['\"]?$", stripped)
            if import_item:
                names.update(_ploomber_spec_task_names(root / import_item.group(1), root, seen))
            continue

        if not in_tasks:
            continue
        name_match = re.match(r"^name\s*:\s*['\"]?([A-Za-z0-9_.:-]+)['\"]?\s*$", stripped)
        if name_match:
            names.add(name_match.group(1))
            continue
        source_match = re.match(r"^(?:-\s*)?source\s*:\s*['\"]?([^'\"]+)['\"]?\s*$", stripped)
        if source_match:
            source = source_match.group(1).strip()
            if source and not source.startswith(("$", "${", "~", "<")) and "://" not in source:
                suffix = Path(source.replace("\\", "/")).suffix
                if suffix:
                    names.add(Path(source.replace("\\", "/")).stem)
    return names


def _ploomber_task_names(root: Path) -> set[str] | None:
    spec_files = [root / "pipeline.yaml", root / "pipeline.yml"]
    existing_specs = [path for path in spec_files if path.exists()]
    if not existing_specs:
        return None

    names: set[str] = set()
    seen: set[Path] = set()
    for spec in existing_specs:
        names.update(_ploomber_spec_task_names(spec, root, seen))
    return names


def _is_luigi_task_base(base: ast.AST) -> bool:
    if isinstance(base, ast.Name):
        return base.id in {"Task", "WrapperTask", "ExternalTask"}
    if isinstance(base, ast.Attribute):
        return base.attr in {"Task", "WrapperTask", "ExternalTask"}
    if isinstance(base, ast.Subscript):
        return _is_luigi_task_base(base.value)
    return False


def _luigi_task_namespace(node: ast.ClassDef) -> str:
    for statement in node.body:
        if not isinstance(statement, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "task_namespace" for target in statement.targets):
            continue
        if isinstance(statement.value, ast.Constant) and isinstance(statement.value.value, str):
            return statement.value.value
    return ""


def _luigi_task_classes_from_python(path: Path) -> set[str]:
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return set()

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return set()

    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if not any(_is_luigi_task_base(base) for base in node.bases):
            continue
        names.add(node.name)
        namespace = _luigi_task_namespace(node)
        if namespace:
            names.add(f"{namespace}.{node.name}")
    return names


def _luigi_module_files(root: Path, module: str) -> list[Path]:
    if not module:
        return []
    module_path = Path(*module.split("."))
    candidates = [
        root / f"{module_path.as_posix()}.py",
        root / module_path / "__init__.py",
        root / "src" / f"{module_path.as_posix()}.py",
        root / "src" / module_path / "__init__.py",
    ]
    return [path for path in candidates if path.exists()]


def _luigi_task_names(root: Path, module: str = "") -> set[str] | None:
    names: set[str] = set()
    files = _luigi_module_files(root, module) if module else [
        path
        for path in root.rglob("*.py")
        if ".venv" not in path.parts and "site-packages" not in path.parts
    ]
    if module and not files:
        return None

    found_luigi_names = False
    for path in files:
        path_names = _luigi_task_classes_from_python(path)
        if path_names:
            found_luigi_names = True
            names.update(path_names)

    if not found_luigi_names:
        return None
    return names


def _luigi_task_exists(target: str, names: set[str]) -> bool:
    return target in names or target.split(".")[-1] in names


def _meltano_config_files(root: Path) -> list[Path]:
    return [path for path in (root / "meltano.yml", root / "meltano.yaml") if path.exists()]


def _meltano_job_names_from_config(path: Path) -> set[str]:
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return set()

    names: set[str] = set()
    in_jobs = False
    jobs_indent = 0
    for raw_line in content.splitlines():
        line_without_comment = raw_line.split("#", 1)[0].rstrip()
        stripped = line_without_comment.strip()
        if not stripped:
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" \t"))

        if re.match(r"^jobs\s*:\s*$", stripped):
            in_jobs = True
            jobs_indent = indent
            continue
        if in_jobs and indent <= jobs_indent:
            in_jobs = False
        if not in_jobs:
            continue

        name_match = re.match(r"^(?:-\s*)?name\s*:\s*['\"]?([A-Za-z0-9_.-]+)['\"]?\s*$", stripped)
        if name_match:
            names.add(name_match.group(1))
    return names


def _meltano_job_names(root: Path) -> set[str] | None:
    configs = _meltano_config_files(root)
    if not configs:
        return None

    names: set[str] = set()
    for config in configs:
        names.update(_meltano_job_names_from_config(config))
    return names


def _is_flyte_target_decorator(decorator: ast.AST) -> bool:
    if isinstance(decorator, ast.Name):
        return decorator.id in {"task", "workflow", "dynamic", "eager", "eager_task"}
    if isinstance(decorator, ast.Attribute):
        return decorator.attr in {"task", "workflow", "dynamic", "eager", "eager_task"}
    if isinstance(decorator, ast.Call):
        return _is_flyte_target_decorator(decorator.func)
    return False


def _flyte_targets_from_script(path: Path) -> set[str] | None:
    if not path.exists():
        return None
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return set()

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return set()

    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if any(_is_flyte_target_decorator(decorator) for decorator in node.decorator_list):
            names.add(node.name)
    return names


def _flyte_target_exists(target: str, names: set[str]) -> bool:
    return target in names or target.split(".")[-1] in names


def _argo_workflow_entrypoint_and_templates(path: Path) -> tuple[str, set[str]] | None:
    if not path.exists():
        return None
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return "", set()

    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            return "", set()
        spec = payload.get("spec", {}) if isinstance(payload, dict) else {}
        if not isinstance(spec, dict):
            return "", set()
        entrypoint = spec.get("entrypoint", "")
        templates = spec.get("templates", [])
        names = {
            str(template.get("name"))
            for template in templates
            if isinstance(template, dict) and template.get("name")
        }
        return str(entrypoint) if entrypoint else "", names

    entrypoint = ""
    names: set[str] = set()
    in_templates = False
    templates_indent = 0
    for raw_line in content.splitlines():
        line_without_comment = raw_line.split("#", 1)[0].rstrip()
        stripped = line_without_comment.strip()
        if not stripped:
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" \t"))

        entrypoint_match = re.match(r"^entrypoint\s*:\s*['\"]?([A-Za-z0-9_.:-]+)['\"]?\s*$", stripped)
        if entrypoint_match and not entrypoint:
            entrypoint = entrypoint_match.group(1)

        if re.match(r"^templates\s*:\s*$", stripped):
            in_templates = True
            templates_indent = indent
            continue
        if in_templates and indent <= templates_indent:
            in_templates = False
        if not in_templates:
            continue

        name_match = re.match(r"^-\s*name\s*:\s*['\"]?([A-Za-z0-9_.:-]+)['\"]?\s*$", stripped)
        if name_match:
            names.add(name_match.group(1))
    return entrypoint, names


def _tekton_resource_from_json(path: Path) -> tuple[str, str] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    kind = payload.get("kind", "")
    metadata = payload.get("metadata", {})
    name = metadata.get("name", "") if isinstance(metadata, dict) else ""
    if kind in {"Pipeline", "Task"} and name:
        return str(kind).lower(), str(name)
    return None


def _tekton_resources_from_yaml(path: Path) -> set[tuple[str, str]]:
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return set()

    resources: set[tuple[str, str]] = set()
    for document in re.split(r"(?m)^---\s*$", content):
        kind_match = re.search(r"(?m)^\s*kind\s*:\s*(Pipeline|Task)\s*$", document)
        if not kind_match:
            continue
        metadata_match = re.search(
            r"(?ms)^\s*metadata\s*:\s*(?:\n\s+[^\n]*)*?^\s+name\s*:\s*['\"]?([A-Za-z0-9_.-]+)['\"]?\s*$",
            document,
        )
        if metadata_match:
            resources.add((kind_match.group(1).lower(), metadata_match.group(1)))
    return resources


def _tekton_resources_from_file(path: Path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    if path.suffix.lower() == ".json":
        resource = _tekton_resource_from_json(path)
        return {resource} if resource is not None else set()
    return _tekton_resources_from_yaml(path)


def _tekton_resource_names(root: Path) -> dict[str, set[str]] | None:
    names = {"pipeline": set(), "task": set()}
    found_manifest = False
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".yml", ".yaml", ".json"}:
            continue
        if any(part in {".venv", "site-packages", "node_modules"} for part in path.parts):
            continue
        resources = _tekton_resources_from_file(path)
        if resources:
            found_manifest = True
        for kind, name in resources:
            if kind in names:
                names[kind].add(name)
    if not found_manifest:
        return None
    return names


def _dagger_cli_name_variants(name: str) -> set[str]:
    camel_split = re.sub(r"(.)([A-Z][a-z]+)", r"\1-\2", name)
    kebab = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", camel_split).replace("_", "-").lower()
    return {name, name.lower(), name.replace("_", "-"), kebab}


def _dagger_python_functions(content: str) -> set[str]:
    names: set[str] = set()
    pending_function = False
    for line in content.splitlines():
        stripped = line.strip()
        if re.match(r"@(?:dagger\.)?function(?:\(|$)", stripped):
            pending_function = True
            continue
        if not pending_function:
            continue
        if not stripped or stripped.startswith("@"):
            continue
        match = re.match(r"(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", stripped)
        if match:
            names.update(_dagger_cli_name_variants(match.group(1)))
        pending_function = False
    return names


def _dagger_typescript_functions(content: str) -> set[str]:
    names: set[str] = set()
    pending_function = False
    for line in content.splitlines():
        stripped = line.strip()
        if re.match(r"@func(?:\(|$)", stripped):
            pending_function = True
            continue
        if not pending_function:
            continue
        if not stripped or stripped.startswith("@"):
            continue
        match = re.match(r"(?:public\s+|private\s+|protected\s+)?(?:async\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\(", stripped)
        if match:
            names.update(_dagger_cli_name_variants(match.group(1)))
        pending_function = False
    return names


def _dagger_go_functions(content: str) -> set[str]:
    names: set[str] = set()
    for match in re.finditer(r"func\s+\([^)]*\)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", content):
        names.update(_dagger_cli_name_variants(match.group(1)))
    return names


def _dagger_java_functions(content: str) -> set[str]:
    names: set[str] = set()
    pending_function = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("@Function"):
            pending_function = True
            continue
        if not pending_function:
            continue
        if not stripped or stripped.startswith("@"):
            continue
        match = re.search(
            r"(?:public|private|protected)?\s*(?:static\s+)?[A-Za-z0-9_<>, ?.\[\]]+\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
            stripped,
        )
        if match:
            names.update(_dagger_cli_name_variants(match.group(1)))
        pending_function = False
    return names


def _dagger_php_functions(content: str) -> set[str]:
    names: set[str] = set()
    pending_function = False
    for line in content.splitlines():
        stripped = line.strip()
        if "DaggerFunction" in stripped:
            pending_function = True
            continue
        if not pending_function:
            continue
        if not stripped or stripped.startswith("#["):
            continue
        match = re.search(r"function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", stripped)
        if match:
            names.update(_dagger_cli_name_variants(match.group(1)))
        pending_function = False
    return names


def _dagger_source_root(module_root: Path, dagger_json: Path) -> Path:
    try:
        payload = json.loads(dagger_json.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return module_root
    source = payload.get("source") if isinstance(payload, dict) else None
    if not isinstance(source, str):
        return module_root
    normalized = source.replace("\\", "/").strip().strip("'\"")
    if (
        not normalized
        or normalized.startswith(("$", "${", "~", "/", "<", "-"))
        or "://" in normalized
        or ".." in Path(normalized).parts
    ):
        return module_root
    return module_root / normalized


def _dagger_function_names(root: Path, module: str) -> set[str] | None:
    module_root = root / module if module else root
    dagger_json = module_root / "dagger.json"
    if not dagger_json.exists():
        return None

    source_root = _dagger_source_root(module_root, dagger_json)
    if source_root.is_file():
        source_files = [source_root]
    elif source_root.exists():
        source_files = [path for path in source_root.rglob("*") if path.is_file()]
    else:
        source_files = []

    names: set[str] = set()
    excluded_parts = {".dagger", ".venv", "node_modules", "vendor", "target", "__pycache__"}
    for path in source_files:
        if any(part in excluded_parts for part in path.parts) or path.name.startswith("dagger.gen."):
            continue
        suffix = path.suffix.lower()
        if suffix not in {".py", ".go", ".ts", ".tsx", ".java", ".php"}:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if suffix == ".py":
            names.update(_dagger_python_functions(content))
        elif suffix == ".go":
            names.update(_dagger_go_functions(content))
        elif suffix in {".ts", ".tsx"}:
            names.update(_dagger_typescript_functions(content))
        elif suffix == ".java":
            names.update(_dagger_java_functions(content))
        elif suffix == ".php":
            names.update(_dagger_php_functions(content))
    return names


def _bazel_build_file_for_package(root: Path, package: str) -> Path | None:
    package_dir = root / package if package else root
    for name in ("BUILD.bazel", "BUILD"):
        candidate = package_dir / name
        if candidate.exists():
            return candidate
    return None


def _bazel_rule_names(build_file: Path) -> set[str]:
    try:
        content = build_file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return set()
    return set(re.findall(r"\bname\s*=\s*[\"']([^\"']+)[\"']", content))


def _bazel_has_any_build_file(root: Path, package: str = "") -> bool:
    search_root = root / package if package else root
    if not search_root.exists():
        return False
    for path in search_root.rglob("*"):
        if not path.is_file() or path.name not in {"BUILD", "BUILD.bazel"}:
            continue
        if any(part in {".git", ".venv", "node_modules", "bazel-bin", "bazel-out", "bazel-testlogs"} for part in path.parts):
            continue
        return True
    return False


def _bazel_package_name(package: str) -> str:
    if not package:
        return ""
    return Path(package).name


def _bazel_target_exists(root: Path, target: str) -> bool:
    if target == "//...":
        return _bazel_has_any_build_file(root)
    if target.endswith("/...") and target.startswith("//"):
        package = target[2:-4].strip("/")
        return _bazel_has_any_build_file(root, package)

    package = ""
    target_name = ""
    if target.startswith("//"):
        label = target[2:]
        if ":" in label:
            package, target_name = label.split(":", 1)
        else:
            package = label.strip("/")
            target_name = _bazel_package_name(package)
    elif target.startswith(":"):
        target_name = target[1:]
    else:
        return True

    build_file = _bazel_build_file_for_package(root, package)
    if build_file is None:
        return False
    if target_name in {"", "all", "*", "__pkg__", "__subpackages__"}:
        return True
    rule_names = _bazel_rule_names(build_file)
    if not rule_names:
        return True
    return target_name in rule_names


def _pants_build_file_for_package(root: Path, package: str) -> Path | None:
    package_dir = root / package if package else root
    if not package_dir.exists():
        return None
    candidates = [
        path for path in package_dir.iterdir()
        if path.is_file() and (path.name == "BUILD" or (path.name.startswith("BUILD.") and path.name != "BUILD.bazel"))
    ]
    return candidates[0] if candidates else None


def _pants_rule_names(build_file: Path) -> set[str]:
    try:
        content = build_file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return set()
    return set(re.findall(r"\bname\s*=\s*[\"']([^\"']+)[\"']", content))


def _pants_has_any_build_file(root: Path, package: str = "") -> bool:
    search_root = root / package if package else root
    if not search_root.exists():
        return False
    excluded = {".git", ".venv", "node_modules", "dist", "__pycache__"}
    for path in search_root.rglob("*"):
        if not path.is_file() or not (path.name == "BUILD" or path.name.startswith("BUILD.")):
            continue
        if path.name == "BUILD.bazel" or any(part in excluded for part in path.parts):
            continue
        return True
    return False


def _pants_spec_exists(root: Path, spec: str) -> bool:
    normalized = spec.removeprefix("//")
    if normalized == "::":
        return _pants_has_any_build_file(root)
    if normalized.endswith("::"):
        package = normalized[:-2].strip("/")
        return _pants_has_any_build_file(root, package)

    generated_base = normalized.split("#", 1)[0]
    if generated_base.endswith(":"):
        generated_base = generated_base[:-1]

    package = ""
    target_name = ""
    if ":" in generated_base:
        package, target_name = generated_base.split(":", 1)
    elif Path(generated_base).suffix:
        return (root / generated_base).is_file()
    else:
        package = generated_base.strip("/")
        target_name = Path(package).name

    if Path(package).suffix:
        file_path = root / package
        if not file_path.is_file():
            return False
        if not target_name:
            return True
        package = str(Path(package).parent).replace("\\", "/")

    build_file = _pants_build_file_for_package(root, package)
    if build_file is None:
        return False
    if target_name in {"", "*", "__pkg__", "__subpackages__"}:
        return True
    names = _pants_rule_names(build_file)
    if not names:
        return True
    return target_name in names


def _split_local_nix_installable(installable: str) -> tuple[str, str] | None:
    target = installable.strip().strip("'\"")
    if not target:
        return None
    target = target.removeprefix("path:")
    path_part, _separator, attr = target.partition("#")
    if not path_part:
        path_part = "."
    if path_part in {".", "./"}:
        flake_dir = "."
    elif path_part.startswith("./"):
        flake_dir = path_part[2:].rstrip("/") or "."
    else:
        return None
    if ".." in Path(flake_dir).parts:
        return None
    return flake_dir, attr


def _nix_flake_file(root: Path, flake_dir: str) -> Path:
    if flake_dir == ".":
        return root / "flake.nix"
    return root / flake_dir / "flake.nix"


def _nix_strip_comments(text: str) -> str:
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def _nix_block_names(text: str, output_name: str) -> set[str]:
    names: set[str] = set()
    system_ref = r'(?:\$\{[^}]+\}|"[^"]+"|[A-Za-z0-9_+.-]+)'
    block_pattern = re.compile(
        rf"\b{re.escape(output_name)}\s*(?:\.\s*{system_ref})?\s*=\s*(?:rec\s*)?\{{(?P<body>.*?)^\s*\}};",
        re.DOTALL | re.MULTILINE,
    )
    for block in block_pattern.finditer(text):
        body = block.group("body")
        for match in re.finditer(r'^\s*"?([A-Za-z0-9_+.-]+)"?\s*=', body, re.MULTILINE):
            names.add(match.group(1))
    return names


def _nix_output_names(text: str, output_name: str) -> set[str]:
    content = _nix_strip_comments(text)
    names = _nix_block_names(content, output_name)
    system_ref = r'(?:\$\{[^}]+\}|"[^"]+"|[A-Za-z0-9_+.-]+)'
    for match in re.finditer(
        rf"\b{re.escape(output_name)}\s*\.\s*{system_ref}\s*\.\s*\"?([A-Za-z0-9_+.-]+)\"?\s*=",
        content,
    ):
        names.add(match.group(1))
    for match in re.finditer(rf"\b{re.escape(output_name)}\s*\.\s*\"?([A-Za-z0-9_+.-]+)\"?\s*=", content):
        names.add(match.group(1))
    if output_name == "packages" and re.search(r"\bdefaultPackage\s*\.", content):
        names.add("default")
    if output_name == "apps" and re.search(r"\bdefaultApp\s*\.", content):
        names.add("default")
    return names


def _nix_explicit_attr_path_exists(text: str, attr: str) -> bool:
    if not attr or not re.fullmatch(r"[A-Za-z0-9_.+-]+", attr):
        return False
    attr_pattern = r"\s*\.\s*".join(re.escape(part) for part in attr.split("."))
    return re.search(rf"\b{attr_pattern}\s*=", _nix_strip_comments(text)) is not None


def _nix_installable_exists(root: Path, nix_command: str, installable: str) -> bool:
    parsed = _split_local_nix_installable(installable)
    if parsed is None:
        return True
    flake_dir, attr = parsed
    flake_file = _nix_flake_file(root, flake_dir)
    if not flake_file.exists():
        return False
    if nix_command == "flake check":
        return True

    try:
        flake_text = flake_file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False

    attr_name = attr or "default"
    if "." in attr_name and _nix_explicit_attr_path_exists(flake_text, attr_name):
        return True

    package_names = _nix_output_names(flake_text, "packages") | _nix_output_names(flake_text, "legacyPackages")
    if nix_command == "build":
        return attr_name in package_names
    if nix_command == "run":
        app_names = _nix_output_names(flake_text, "apps")
        return attr_name in app_names or attr_name in package_names
    return True


def _docker_compose_default_files(root: Path, project_dir: str = "") -> list[Path]:
    normalized = project_dir.replace("\\", "/").rstrip("/") if project_dir else ""
    base = root if not normalized or normalized in {".", "./"} else root / normalized
    return [
        base / name
        for name in DOCKER_COMPOSE_FILE_NAMES
        if (base / name).exists()
    ]


def _is_docker_compose_file(path: Path) -> bool:
    return path.name.lower() in DOCKER_COMPOSE_FILE_NAMES


def _docker_compose_project_dir_exists(root: Path, project_dir: str) -> bool:
    normalized = project_dir.replace("\\", "/").rstrip("/") or "."
    path = root if normalized in {".", "./"} else root / normalized
    return path.is_dir()


def _docker_compose_files_for_reference(root: Path, reference: ReadmeReference) -> tuple[list[Path], list[str]]:
    if reference.docker_compose_files:
        files = [root / compose_file for compose_file in reference.docker_compose_files]
        missing = [
            compose_file
            for compose_file, path in zip(reference.docker_compose_files, files, strict=True)
            if not path.exists()
        ]
        return files, missing
    project_dir = reference.docker_compose_project_dirs[0] if reference.docker_compose_project_dirs else ""
    files = _docker_compose_default_files(root, project_dir)
    if not files:
        default_name = "compose.yaml" if not project_dir else f"{project_dir.rstrip('/')}/compose.yaml"
        return [], [default_name]
    return files, []


def _docker_compose_env_file_exists(root: Path, env_file: str) -> bool:
    normalized = env_file.replace("\\", "/").rstrip("/")
    return bool(normalized) and (root / normalized).is_file()


def _docker_compose_service_names_from_text(text: str) -> set[str]:
    services: set[str] = set()
    services_indent: int | None = None
    service_indent: int | None = None
    for raw_line in text.splitlines():
        without_comment = raw_line.split("#", 1)[0].rstrip()
        if not without_comment.strip():
            continue
        indent = len(without_comment) - len(without_comment.lstrip(" "))
        if services_indent is None:
            if re.match(r"^\s*services\s*:\s*$", without_comment):
                services_indent = indent
            continue
        if indent <= services_indent:
            break
        if service_indent is not None and indent != service_indent:
            continue
        match = re.match(r'^\s*["\']?([A-Za-z0-9][A-Za-z0-9_.-]*)["\']?\s*:', without_comment)
        if match:
            service_indent = indent
            services.add(match.group(1))
    return services


def _docker_compose_service_names(paths: list[Path]) -> set[str]:
    services: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        try:
            services.update(_docker_compose_service_names_from_text(path.read_text(encoding="utf-8")))
        except UnicodeDecodeError:
            continue
    return services


def _docker_compose_profile_value(value: str) -> str:
    return value.strip().strip("'\"")


def _docker_compose_profile_names_from_text(text: str) -> set[str]:
    profiles: set[str] = set()
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        without_comment = lines[index].split("#", 1)[0].rstrip()
        if not without_comment.strip():
            index += 1
            continue
        indent = len(without_comment) - len(without_comment.lstrip(" "))
        inline_match = re.match(r"^\s*profiles\s*:\s*\[(.*)\]\s*$", without_comment)
        if inline_match:
            for raw_profile in inline_match.group(1).split(","):
                profile = _docker_compose_profile_value(raw_profile)
                if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", profile):
                    profiles.add(profile)
            index += 1
            continue
        scalar_match = re.match(r"^\s*profiles\s*:\s*['\"]?([A-Za-z0-9][A-Za-z0-9_.-]*)['\"]?\s*$", without_comment)
        if scalar_match:
            profiles.add(scalar_match.group(1))
            index += 1
            continue
        if not re.match(r"^\s*profiles\s*:\s*$", without_comment):
            index += 1
            continue

        index += 1
        while index < len(lines):
            nested = lines[index].split("#", 1)[0].rstrip()
            if not nested.strip():
                index += 1
                continue
            nested_indent = len(nested) - len(nested.lstrip(" "))
            if nested_indent <= indent:
                break
            item_match = re.match(r"^\s*-\s*['\"]?([A-Za-z0-9][A-Za-z0-9_.-]*)['\"]?\s*$", nested)
            if item_match:
                profiles.add(item_match.group(1))
            index += 1
    return profiles


def _docker_compose_profile_names(paths: list[Path]) -> set[str]:
    profiles: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        try:
            profiles.update(_docker_compose_profile_names_from_text(path.read_text(encoding="utf-8")))
        except UnicodeDecodeError:
            continue
    return profiles


def _docker_compose_scalar_value(value: str) -> str:
    return value.strip().strip("'\"")


def _is_docker_compose_service_reference(value: str) -> bool:
    service = _docker_compose_scalar_value(value)
    return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", service))


def _docker_compose_inline_list_values(value: str) -> list[str]:
    inline_value = value.strip()
    if not (inline_value.startswith("[") and inline_value.endswith("]")):
        return []
    values: list[str] = []
    for raw_value in inline_value[1:-1].split(","):
        service = _docker_compose_scalar_value(raw_value)
        if _is_docker_compose_service_reference(service):
            values.append(service)
    return values


def _docker_compose_inline_sequence_values(value: str) -> list[str]:
    inline_value = value.strip()
    if not (inline_value.startswith("[") and inline_value.endswith("]")):
        return []
    values: list[str] = []
    current = []
    quote = ""
    escaped = False
    for char in inline_value[1:-1]:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == "\\" and quote:
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = ""
            else:
                current.append(char)
            continue
        if char in {"'", '"'}:
            quote = char
            continue
        if char == ",":
            value_part = _docker_compose_scalar_value("".join(current))
            if value_part:
                values.append(value_part)
            current = []
            continue
        current.append(char)
    value_part = _docker_compose_scalar_value("".join(current))
    if value_part:
        values.append(value_part)
    return values


def _docker_compose_shell_tokens(command: str) -> list[str]:
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return command.split()


def _docker_compose_healthcheck_script_reference(value: str) -> str:
    candidate = _docker_compose_scalar_value(value).strip(";,()")
    if not candidate or candidate.startswith(("$", "${", "~", "<", "-", "&", "|")):
        return ""
    if "://" in candidate or candidate.startswith(("http:", "https:", "tcp:", "unix:")):
        return ""
    normalized = candidate.replace("\\", "/").rstrip("/")
    if not normalized or Path(normalized).is_absolute() or re.match(r"^[A-Za-z]:/", normalized):
        return ""
    suffix_match = normalized.endswith(DOCKER_COMPOSE_HEALTHCHECK_SCRIPT_SUFFIXES)
    if normalized.startswith(("./", "../")):
        return normalized if "/" in normalized else ""
    first_part = normalized.split("/", 1)[0]
    if "/" in normalized and (suffix_match or first_part in DOCKER_COMPOSE_HEALTHCHECK_LOCAL_DIRS):
        return normalized
    return ""


def _docker_compose_healthcheck_scripts_from_tokens(tokens: list[str]) -> list[str]:
    scripts: list[str] = []
    if not tokens:
        return scripts
    command_tokens = tokens[1:] if tokens[0] in {"CMD", "CMD-SHELL", "NONE"} else tokens
    if tokens[0] == "NONE":
        return scripts
    if tokens[0] == "CMD-SHELL":
        command_tokens = _docker_compose_shell_tokens(" ".join(command_tokens))
    for token in command_tokens:
        script = _docker_compose_healthcheck_script_reference(token)
        if script:
            scripts.append(script)
    return scripts


def _docker_compose_healthcheck_scripts_from_value(value: str) -> list[str]:
    raw_value = _docker_compose_scalar_value(value)
    if not raw_value or raw_value == "NONE":
        return []
    inline_values = _docker_compose_inline_sequence_values(raw_value)
    if inline_values:
        return _docker_compose_healthcheck_scripts_from_tokens(inline_values)
    tokens = _docker_compose_shell_tokens(raw_value)
    return _docker_compose_healthcheck_scripts_from_tokens(tokens)


def _docker_compose_healthcheck_script_references_from_text(text: str) -> list[str]:
    scripts: list[str] = []
    lines = text.splitlines()
    index = 0

    while index < len(lines):
        without_comment = lines[index].split("#", 1)[0].rstrip()
        if not without_comment.strip():
            index += 1
            continue
        indent = len(without_comment) - len(without_comment.lstrip(" "))
        if not re.match(r"^\s*healthcheck\s*:\s*$", without_comment):
            index += 1
            continue

        healthcheck_indent = indent
        index += 1
        while index < len(lines):
            nested = lines[index].split("#", 1)[0].rstrip()
            if not nested.strip():
                index += 1
                continue
            nested_indent = len(nested) - len(nested.lstrip(" "))
            if nested_indent <= healthcheck_indent:
                break
            test_match = re.match(r"^\s*test\s*:\s*(.*?)\s*$", nested)
            if not test_match:
                index += 1
                continue
            value = test_match.group(1).strip()
            if value:
                scripts.extend(_docker_compose_healthcheck_scripts_from_value(value))
                index += 1
                continue

            test_indent = nested_indent
            test_tokens: list[str] = []
            index += 1
            while index < len(lines):
                token_line = lines[index].split("#", 1)[0].rstrip()
                if not token_line.strip():
                    index += 1
                    continue
                token_indent = len(token_line) - len(token_line.lstrip(" "))
                if token_indent <= test_indent:
                    break
                item_match = re.match(r"^\s*-\s*(.*?)\s*$", token_line)
                if item_match:
                    test_item = _docker_compose_scalar_value(item_match.group(1))
                    if test_item:
                        test_tokens.append(test_item)
                index += 1
            scripts.extend(_docker_compose_healthcheck_scripts_from_tokens(test_tokens))

    return list(dict.fromkeys(scripts))


def _docker_compose_depends_on_services_from_text(text: str) -> set[str]:
    dependencies: set[str] = set()
    lines = text.splitlines()
    services_indent: int | None = None
    service_indent: int | None = None
    current_service = ""
    index = 0

    while index < len(lines):
        without_comment = lines[index].split("#", 1)[0].rstrip()
        if not without_comment.strip():
            index += 1
            continue
        indent = len(without_comment) - len(without_comment.lstrip(" "))

        if services_indent is None:
            if re.match(r"^\s*services\s*:\s*$", without_comment):
                services_indent = indent
            index += 1
            continue
        if indent <= services_indent:
            break

        service_match = re.match(r'^\s*["\']?([A-Za-z0-9][A-Za-z0-9_.-]*)["\']?\s*:', without_comment)
        if service_match and (service_indent is None or indent == service_indent):
            service_indent = indent
            current_service = service_match.group(1)
            index += 1
            continue
        if not current_service or service_indent is None or indent <= service_indent:
            index += 1
            continue

        depends_match = re.match(r"^\s*depends_on\s*:\s*(.*?)\s*$", without_comment)
        if not depends_match:
            index += 1
            continue

        value = depends_match.group(1).strip()
        if value:
            if value.startswith("["):
                dependencies.update(_docker_compose_inline_list_values(value))
            index += 1
            continue

        depends_indent = indent
        item_indent: int | None = None
        index += 1
        while index < len(lines):
            nested = lines[index].split("#", 1)[0].rstrip()
            if not nested.strip():
                index += 1
                continue
            nested_indent = len(nested) - len(nested.lstrip(" "))
            if nested_indent <= depends_indent:
                break
            list_match = re.match(r"^\s*-\s*['\"]?([A-Za-z0-9][A-Za-z0-9_.-]*)['\"]?\s*$", nested)
            if list_match:
                dependencies.add(list_match.group(1))
                index += 1
                continue
            field_match = re.match(r'^\s*["\']?([A-Za-z0-9][A-Za-z0-9_.-]*)["\']?\s*:', nested)
            if field_match:
                if item_indent is None:
                    item_indent = nested_indent
                if nested_indent == item_indent:
                    dependencies.add(field_match.group(1))
            index += 1

    return dependencies


def _docker_compose_root_indent(lines: list[str]) -> int:
    indents: list[int] = []
    for raw_line in lines:
        without_comment = raw_line.split("#", 1)[0].rstrip()
        if not without_comment.strip():
            continue
        match = re.match(r"^\s*[A-Za-z_][A-Za-z0-9_-]*\s*:", without_comment)
        if match:
            indents.append(len(without_comment) - len(without_comment.lstrip(" ")))
    return min(indents) if indents else 0


def _docker_compose_top_level_network_names_from_text(text: str) -> set[str]:
    networks: set[str] = set()
    lines = text.splitlines()
    root_indent = _docker_compose_root_indent(lines)
    index = 0

    while index < len(lines):
        without_comment = lines[index].split("#", 1)[0].rstrip()
        if not without_comment.strip():
            index += 1
            continue
        indent = len(without_comment) - len(without_comment.lstrip(" "))
        if indent != root_indent or not re.match(r"^\s*networks\s*:\s*$", without_comment):
            index += 1
            continue

        networks_indent = indent
        network_indent: int | None = None
        index += 1
        while index < len(lines):
            nested = lines[index].split("#", 1)[0].rstrip()
            if not nested.strip():
                index += 1
                continue
            nested_indent = len(nested) - len(nested.lstrip(" "))
            if nested_indent <= networks_indent:
                break
            match = re.match(r'^\s*["\']?([A-Za-z0-9][A-Za-z0-9_.-]*)["\']?\s*:', nested)
            if match:
                if network_indent is None:
                    network_indent = nested_indent
                if nested_indent == network_indent:
                    networks.add(match.group(1))
            index += 1

    return networks


def _docker_compose_service_networks_from_text(text: str) -> set[str]:
    references: set[str] = set()
    lines = text.splitlines()
    services_indent: int | None = None
    service_indent: int | None = None
    current_service = ""
    index = 0

    while index < len(lines):
        without_comment = lines[index].split("#", 1)[0].rstrip()
        if not without_comment.strip():
            index += 1
            continue
        indent = len(without_comment) - len(without_comment.lstrip(" "))

        if services_indent is None:
            if re.match(r"^\s*services\s*:\s*$", without_comment):
                services_indent = indent
            index += 1
            continue
        if indent <= services_indent:
            break

        service_match = re.match(r'^\s*["\']?([A-Za-z0-9][A-Za-z0-9_.-]*)["\']?\s*:', without_comment)
        if service_match and (service_indent is None or indent == service_indent):
            service_indent = indent
            current_service = service_match.group(1)
            index += 1
            continue
        if not current_service or service_indent is None or indent <= service_indent:
            index += 1
            continue

        networks_match = re.match(r"^\s*networks\s*:\s*(.*?)\s*$", without_comment)
        if not networks_match:
            index += 1
            continue

        value = networks_match.group(1).strip()
        if value:
            references.update(_docker_compose_inline_list_values(value))
            index += 1
            continue

        networks_indent = indent
        item_indent: int | None = None
        index += 1
        while index < len(lines):
            nested = lines[index].split("#", 1)[0].rstrip()
            if not nested.strip():
                index += 1
                continue
            nested_indent = len(nested) - len(nested.lstrip(" "))
            if nested_indent <= networks_indent:
                break
            list_match = re.match(r"^\s*-\s*['\"]?([A-Za-z0-9][A-Za-z0-9_.-]*)['\"]?\s*$", nested)
            if list_match:
                if item_indent is None:
                    item_indent = nested_indent
                if nested_indent == item_indent:
                    references.add(list_match.group(1))
                index += 1
                continue
            field_match = re.match(r'^\s*["\']?([A-Za-z0-9][A-Za-z0-9_.-]*)["\']?\s*:', nested)
            if field_match:
                if item_indent is None:
                    item_indent = nested_indent
                if nested_indent == item_indent:
                    references.add(field_match.group(1))
            index += 1

    return references


def check_missing_docker_compose_depends_on_services(root: Path, files: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in files:
        if not _is_docker_compose_file(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        service_names = _docker_compose_service_names_from_text(text)
        dependencies = _docker_compose_depends_on_services_from_text(text)
        missing_services = sorted(dependency for dependency in dependencies if dependency not in service_names)
        if not missing_services:
            continue
        findings.append(
            Finding(
                check_id="LC065",
                title="Docker Compose dependency references missing service",
                severity="medium",
                category="onboarding",
                file_path=_relative_posix(path, root),
                evidence=(
                    f"Docker Compose depends_on service(s) {', '.join(missing_services)} "
                    "are referenced, but this Compose file does not define them."
                ),
                why_it_matters="A fresh clone can fail at service startup when Compose dependency wiring points at stale or renamed services.",
                suggested_fix="Add the missing service definition or update depends_on to reference an existing service in the Compose file.",
            )
        )
    return findings


def check_missing_docker_compose_service_networks(root: Path, files: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in files:
        if not _is_docker_compose_file(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        defined_networks = _docker_compose_top_level_network_names_from_text(text)
        referenced_networks = _docker_compose_service_networks_from_text(text)
        missing_networks = sorted(
            network
            for network in referenced_networks
            if network != "default" and network not in defined_networks
        )
        if not missing_networks:
            continue
        findings.append(
            Finding(
                check_id="LC066",
                title="Docker Compose service references missing network",
                severity="medium",
                category="onboarding",
                file_path=_relative_posix(path, root),
                evidence=(
                    f"Docker Compose network(s) {', '.join(missing_networks)} "
                    "are referenced by services, but this Compose file does not define them."
                ),
                why_it_matters="A fresh clone can fail at service startup when Compose network wiring points at stale or renamed networks.",
                suggested_fix="Add the missing top-level network definition, remove the stale service network reference, or use the implicit default network.",
            )
        )
    return findings


def _is_local_docker_compose_bind_source(value: str) -> bool:
    source = _docker_compose_scalar_value(value)
    if not source or source.startswith(("$", "${", "~", "<", "-")):
        return False
    if "://" in source or source.startswith(("git@", "github.com/", "gitlab.com/")):
        return False
    normalized = source.replace("\\", "/").rstrip("/") or "."
    if Path(normalized).is_absolute() or re.match(r"^[A-Za-z]:/", normalized):
        return False
    return normalized in {".", "./"} or normalized.startswith(("./", "../"))


def _is_local_docker_compose_path(value: str) -> bool:
    path = _docker_compose_scalar_value(value)
    if not path or path.startswith(("$", "${", "~", "<", "-")):
        return False
    if "://" in path or path.startswith(("git@", "github.com/", "gitlab.com/")):
        return False
    normalized = path.replace("\\", "/").rstrip("/") or "."
    if normalized.startswith("/") or Path(normalized).is_absolute() or re.match(r"^[A-Za-z]:/", normalized):
        return False
    return True


def _docker_compose_short_volume_source(value: str) -> str:
    volume = _docker_compose_scalar_value(value)
    if not volume:
        return ""
    return volume.split(":", 1)[0].strip()


def _docker_compose_bind_sources_from_text(text: str) -> list[str]:
    sources: list[str] = []
    in_volumes = False
    volumes_indent = 0
    item_indent: int | None = None
    item_type = ""
    item_source = ""

    def flush_item() -> None:
        nonlocal item_type, item_source, item_indent
        if item_type == "bind" and _is_local_docker_compose_bind_source(item_source):
            sources.append(_docker_compose_scalar_value(item_source))
        item_type = ""
        item_source = ""
        item_indent = None

    for raw_line in text.splitlines():
        without_comment = raw_line.split("#", 1)[0].rstrip()
        if not without_comment.strip():
            continue
        indent = len(without_comment) - len(without_comment.lstrip(" "))

        if in_volumes and indent <= volumes_indent:
            flush_item()
            in_volumes = False

        if not in_volumes:
            if re.match(r"^\s*volumes\s*:\s*$", without_comment):
                in_volumes = True
                volumes_indent = indent
            continue

        list_match = re.match(r"^\s*-\s*(.*?)\s*$", without_comment)
        if list_match:
            flush_item()
            item_indent = indent
            value = list_match.group(1).strip()
            field_match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*?)\s*$", value)
            if field_match:
                field, field_value = field_match.groups()
                if field == "type":
                    item_type = _docker_compose_scalar_value(field_value)
                elif field == "source":
                    item_source = _docker_compose_scalar_value(field_value)
                continue

            short_source = _docker_compose_short_volume_source(value)
            if _is_local_docker_compose_bind_source(short_source):
                sources.append(_docker_compose_scalar_value(short_source))
            continue

        if item_indent is None or indent <= item_indent:
            continue
        field_match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*?)\s*$", without_comment)
        if not field_match:
            continue
        field, value = field_match.groups()
        if field == "type":
            item_type = _docker_compose_scalar_value(value)
        elif field == "source":
            item_source = _docker_compose_scalar_value(value)

    flush_item()
    return list(dict.fromkeys(sources))


def _docker_compose_bind_source_exists(root: Path, compose_file: Path, source: str) -> bool:
    root_resolved = root.resolve()
    candidate = (compose_file.parent / source).resolve()
    return _is_within_root(candidate, root_resolved) and candidate.exists()


def check_missing_docker_compose_volume_sources(root: Path, files: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in files:
        if not _is_docker_compose_file(path):
            continue
        try:
            sources = _docker_compose_bind_sources_from_text(path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            continue
        missing_sources = [
            source
            for source in sources
            if not _docker_compose_bind_source_exists(root, path, source)
        ]
        if not missing_sources:
            continue
        findings.append(
            Finding(
                check_id="LC005",
                title="Referenced input artifact missing from repo",
                severity="high",
                category="artifacts",
                file_path=_relative_posix(path, root),
                evidence=(
                    f"Docker Compose bind source(s) {', '.join(missing_sources)} "
                    "are referenced, but those paths are not present in the scanned repo."
                ),
                why_it_matters="A new user may not be able to start the documented services because required bind-mounted inputs are missing.",
                suggested_fix="Commit the bind source path, generate it before running Compose, or document how to obtain it.",
            )
        )
    return findings


def _docker_compose_inline_object_value(value: str, field: str) -> str:
    object_value = value.strip()
    if not (object_value.startswith("{") and object_value.endswith("}")):
        return ""
    inner = object_value[1:-1]
    pattern = rf"(?:^|,)\s*{re.escape(field)}\s*:\s*([^,}}]+)"
    match = re.search(pattern, inner)
    return _docker_compose_scalar_value(match.group(1)) if match else ""


def _docker_compose_truthy(value: str) -> bool:
    return _docker_compose_scalar_value(value).lower() in {"1", "true", "yes", "on"}


def _docker_compose_resource_file_references_from_text(text: str) -> list[tuple[str, str, str]]:
    references: list[tuple[str, str, str]] = []
    lines = text.splitlines()
    root_indent = _docker_compose_root_indent(lines)
    index = 0

    while index < len(lines):
        without_comment = lines[index].split("#", 1)[0].rstrip()
        if not without_comment.strip():
            index += 1
            continue
        indent = len(without_comment) - len(without_comment.lstrip(" "))
        section_match = re.match(r"^\s*(secrets|configs)\s*:\s*$", without_comment)
        if not section_match or indent != root_indent:
            index += 1
            continue

        section_name = section_match.group(1)
        section_indent = indent
        entry_indent: int | None = None
        current_name = ""
        current_file = ""
        current_external = False

        def flush_entry() -> None:
            nonlocal current_name, current_file, current_external
            if current_name and current_file and not current_external and _is_local_docker_compose_path(current_file):
                references.append((section_name, current_name, _docker_compose_scalar_value(current_file)))
            current_name = ""
            current_file = ""
            current_external = False

        index += 1
        while index < len(lines):
            nested = lines[index].split("#", 1)[0].rstrip()
            if not nested.strip():
                index += 1
                continue
            nested_indent = len(nested) - len(nested.lstrip(" "))
            if nested_indent <= section_indent:
                break
            entry_match = re.match(r'^\s*["\']?([A-Za-z0-9][A-Za-z0-9_.-]*)["\']?\s*:\s*(.*?)\s*$', nested)
            if entry_match and (entry_indent is None or nested_indent == entry_indent):
                flush_entry()
                entry_indent = nested_indent
                current_name, raw_entry_value = entry_match.groups()
                current_file = _docker_compose_inline_object_value(raw_entry_value, "file")
                current_external = _docker_compose_truthy(_docker_compose_inline_object_value(raw_entry_value, "external"))
                index += 1
                continue
            if current_name and entry_indent is not None and nested_indent > entry_indent:
                field_match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*?)\s*$", nested)
                if field_match:
                    field, raw_value = field_match.groups()
                    if field == "file":
                        current_file = _docker_compose_scalar_value(raw_value)
                    elif field == "external":
                        current_external = _docker_compose_truthy(raw_value)
            index += 1
        flush_entry()

    return list(dict.fromkeys(references))


def _docker_compose_env_file_references_from_text(text: str) -> list[str]:
    env_files: list[str] = []
    lines = text.splitlines()
    services_indent: int | None = None
    service_indent: int | None = None
    current_service = ""
    index = 0

    while index < len(lines):
        without_comment = lines[index].split("#", 1)[0].rstrip()
        if not without_comment.strip():
            index += 1
            continue
        indent = len(without_comment) - len(without_comment.lstrip(" "))
        if services_indent is None:
            if re.match(r"^\s*services\s*:\s*$", without_comment):
                services_indent = indent
            index += 1
            continue
        if indent <= services_indent:
            break

        service_match = re.match(r'^\s*["\']?([A-Za-z0-9][A-Za-z0-9_.-]*)["\']?\s*:', without_comment)
        if service_match and (service_indent is None or indent == service_indent):
            service_indent = indent
            current_service = service_match.group(1)
            index += 1
            continue
        if not current_service or service_indent is None or indent <= service_indent:
            index += 1
            continue

        env_file_match = re.match(r"^\s*env_file\s*:\s*(.*?)\s*$", without_comment)
        if not env_file_match:
            index += 1
            continue
        value = env_file_match.group(1).strip()
        if value:
            inline_values = _docker_compose_inline_sequence_values(value)
            candidates = inline_values if inline_values else [_docker_compose_scalar_value(value)]
            env_files.extend(candidate for candidate in candidates if _is_local_docker_compose_path(candidate))
            index += 1
            continue

        env_file_indent = indent
        item_indent: int | None = None
        item_path = ""
        index += 1

        def flush_item() -> None:
            nonlocal item_path
            if item_path and _is_local_docker_compose_path(item_path):
                env_files.append(_docker_compose_scalar_value(item_path))
            item_path = ""

        while index < len(lines):
            nested = lines[index].split("#", 1)[0].rstrip()
            if not nested.strip():
                index += 1
                continue
            nested_indent = len(nested) - len(nested.lstrip(" "))
            if nested_indent <= env_file_indent:
                break
            list_match = re.match(r"^\s*-\s*(.*?)\s*$", nested)
            if list_match:
                flush_item()
                item_indent = nested_indent
                value = list_match.group(1).strip()
                field_match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*?)\s*$", value)
                if field_match and field_match.group(1) == "path":
                    item_path = _docker_compose_scalar_value(field_match.group(2))
                elif value:
                    candidate = _docker_compose_scalar_value(value)
                    if _is_local_docker_compose_path(candidate):
                        env_files.append(candidate)
                index += 1
                continue
            if item_indent is not None and nested_indent > item_indent:
                field_match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*?)\s*$", nested)
                if field_match and field_match.group(1) == "path":
                    item_path = _docker_compose_scalar_value(field_match.group(2))
            index += 1
        flush_item()

    return list(dict.fromkeys(env_files))


def _docker_compose_label_file_references_from_text(text: str) -> list[str]:
    label_files: list[str] = []
    lines = text.splitlines()
    services_indent: int | None = None
    service_indent: int | None = None
    current_service = ""
    index = 0

    while index < len(lines):
        without_comment = lines[index].split("#", 1)[0].rstrip()
        if not without_comment.strip():
            index += 1
            continue
        indent = len(without_comment) - len(without_comment.lstrip(" "))
        if services_indent is None:
            if re.match(r"^\s*services\s*:\s*$", without_comment):
                services_indent = indent
            index += 1
            continue
        if indent <= services_indent:
            break

        service_match = re.match(r'^\s*["\']?([A-Za-z0-9][A-Za-z0-9_.-]*)["\']?\s*:', without_comment)
        if service_match and (service_indent is None or indent == service_indent):
            service_indent = indent
            current_service = service_match.group(1)
            index += 1
            continue
        if not current_service or service_indent is None or indent <= service_indent:
            index += 1
            continue

        label_file_match = re.match(r"^\s*label_file\s*:\s*(.*?)\s*$", without_comment)
        if not label_file_match:
            index += 1
            continue
        value = label_file_match.group(1).strip()
        if value:
            inline_values = _docker_compose_inline_sequence_values(value)
            candidates = inline_values if inline_values else [_docker_compose_scalar_value(value)]
            label_files.extend(candidate for candidate in candidates if _is_local_docker_compose_path(candidate))
            index += 1
            continue

        label_file_indent = indent
        index += 1
        while index < len(lines):
            nested = lines[index].split("#", 1)[0].rstrip()
            if not nested.strip():
                index += 1
                continue
            nested_indent = len(nested) - len(nested.lstrip(" "))
            if nested_indent <= label_file_indent:
                break
            list_match = re.match(r"^\s*-\s*(.*?)\s*$", nested)
            if list_match:
                candidate = _docker_compose_scalar_value(list_match.group(1).strip())
                if _is_local_docker_compose_path(candidate):
                    label_files.append(candidate)
            index += 1

    return list(dict.fromkeys(label_files))


def _docker_compose_develop_watch_paths_from_text(text: str) -> list[str]:
    watch_paths: list[str] = []
    lines = text.splitlines()
    services_indent: int | None = None
    service_indent: int | None = None
    current_service = ""
    index = 0

    def add_candidate(value: str) -> None:
        candidate = _docker_compose_scalar_value(value)
        if _is_local_docker_compose_path(candidate):
            watch_paths.append(candidate)

    while index < len(lines):
        without_comment = lines[index].split("#", 1)[0].rstrip()
        if not without_comment.strip():
            index += 1
            continue
        indent = len(without_comment) - len(without_comment.lstrip(" "))
        if services_indent is None:
            if re.match(r"^\s*services\s*:\s*$", without_comment):
                services_indent = indent
            index += 1
            continue
        if indent <= services_indent:
            break

        service_match = re.match(r'^\s*["\']?([A-Za-z0-9][A-Za-z0-9_.-]*)["\']?\s*:', without_comment)
        if service_match and (service_indent is None or indent == service_indent):
            service_indent = indent
            current_service = service_match.group(1)
            index += 1
            continue
        if not current_service or service_indent is None or indent <= service_indent:
            index += 1
            continue

        develop_match = re.match(r"^\s*develop\s*:\s*$", without_comment)
        if not develop_match:
            index += 1
            continue

        develop_indent = indent
        index += 1
        while index < len(lines):
            develop_nested = lines[index].split("#", 1)[0].rstrip()
            if not develop_nested.strip():
                index += 1
                continue
            develop_nested_indent = len(develop_nested) - len(develop_nested.lstrip(" "))
            if develop_nested_indent <= develop_indent:
                break

            watch_match = re.match(r"^\s*watch\s*:\s*(.*?)\s*$", develop_nested)
            if not watch_match:
                index += 1
                continue

            watch_value = watch_match.group(1).strip()
            if watch_value:
                for inline_object in re.findall(r"\{[^}]*\}", watch_value):
                    watch_path = _docker_compose_inline_object_value(inline_object, "path")
                    if watch_path:
                        add_candidate(watch_path)
                index += 1
                continue

            watch_indent = develop_nested_indent
            current_path = ""
            index += 1

            def flush_item() -> None:
                nonlocal current_path
                if current_path:
                    add_candidate(current_path)
                current_path = ""

            while index < len(lines):
                watch_nested = lines[index].split("#", 1)[0].rstrip()
                if not watch_nested.strip():
                    index += 1
                    continue
                watch_nested_indent = len(watch_nested) - len(watch_nested.lstrip(" "))
                if watch_nested_indent <= watch_indent:
                    break
                list_match = re.match(r"^\s*-\s*(.*?)\s*$", watch_nested)
                if list_match:
                    flush_item()
                    item_value = list_match.group(1).strip()
                    if item_value.startswith("{"):
                        current_path = _docker_compose_inline_object_value(item_value, "path")
                    else:
                        field_match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*?)\s*$", item_value)
                        if field_match and field_match.group(1) == "path":
                            current_path = _docker_compose_scalar_value(field_match.group(2))
                    index += 1
                    continue
                field_match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*?)\s*$", watch_nested)
                if field_match and field_match.group(1) == "path":
                    current_path = _docker_compose_scalar_value(field_match.group(2))
                index += 1
            flush_item()

    return list(dict.fromkeys(watch_paths))


def _docker_compose_extends_references_from_text(text: str) -> list[tuple[str, str, str]]:
    references: list[tuple[str, str, str]] = []
    lines = text.splitlines()
    services_indent: int | None = None
    service_indent: int | None = None
    current_service = ""
    index = 0

    while index < len(lines):
        without_comment = lines[index].split("#", 1)[0].rstrip()
        if not without_comment.strip():
            index += 1
            continue
        indent = len(without_comment) - len(without_comment.lstrip(" "))
        if services_indent is None:
            if re.match(r"^\s*services\s*:\s*$", without_comment):
                services_indent = indent
            index += 1
            continue
        if indent <= services_indent:
            break

        service_match = re.match(r'^\s*["\']?([A-Za-z0-9][A-Za-z0-9_.-]*)["\']?\s*:', without_comment)
        if service_match and (service_indent is None or indent == service_indent):
            service_indent = indent
            current_service = service_match.group(1)
            index += 1
            continue
        if not current_service or service_indent is None or indent <= service_indent:
            index += 1
            continue

        extends_match = re.match(r"^\s*extends\s*:\s*(.*?)\s*$", without_comment)
        if not extends_match:
            index += 1
            continue

        value = extends_match.group(1).strip()
        if value:
            if value.startswith("{"):
                extends_file = _docker_compose_inline_object_value(value, "file")
                extends_service = _docker_compose_inline_object_value(value, "service")
                if extends_file or _is_docker_compose_service_reference(extends_service):
                    references.append((current_service, _docker_compose_scalar_value(extends_file), _docker_compose_scalar_value(extends_service)))
            else:
                extends_service = _docker_compose_scalar_value(value)
                if _is_docker_compose_service_reference(extends_service):
                    references.append((current_service, "", extends_service))
            index += 1
            continue

        extends_indent = indent
        extends_file = ""
        extends_service = ""
        index += 1
        while index < len(lines):
            nested = lines[index].split("#", 1)[0].rstrip()
            if not nested.strip():
                index += 1
                continue
            nested_indent = len(nested) - len(nested.lstrip(" "))
            if nested_indent <= extends_indent:
                break
            field_match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*?)\s*$", nested)
            if field_match:
                field, raw_value = field_match.groups()
                if field == "file":
                    extends_file = _docker_compose_scalar_value(raw_value)
                elif field == "service":
                    extends_service = _docker_compose_scalar_value(raw_value)
            index += 1
        if extends_file or _is_docker_compose_service_reference(extends_service):
            references.append((current_service, extends_file, extends_service))

    return list(dict.fromkeys(references))


def _docker_compose_include_references_from_text(text: str) -> list[str]:
    references: list[str] = []
    lines = text.splitlines()
    root_indent = _docker_compose_root_indent(lines)
    index = 0

    def add_candidate(value: str) -> None:
        inline_values = _docker_compose_inline_sequence_values(value)
        candidates = inline_values if inline_values else [_docker_compose_scalar_value(value)]
        references.extend(candidate for candidate in candidates if _is_local_docker_compose_path(candidate))

    while index < len(lines):
        without_comment = lines[index].split("#", 1)[0].rstrip()
        if not without_comment.strip():
            index += 1
            continue
        indent = len(without_comment) - len(without_comment.lstrip(" "))
        include_match = re.match(r"^\s*include\s*:\s*(.*?)\s*$", without_comment)
        if not include_match or indent != root_indent:
            index += 1
            continue

        value = include_match.group(1).strip()
        if value:
            if value.startswith("{"):
                include_path = _docker_compose_inline_object_value(value, "path")
                if include_path:
                    add_candidate(include_path)
            else:
                add_candidate(value)
            index += 1
            continue

        include_indent = indent
        item_indent: int | None = None
        path_list_indent: int | None = None
        index += 1
        while index < len(lines):
            nested = lines[index].split("#", 1)[0].rstrip()
            if not nested.strip():
                index += 1
                continue
            nested_indent = len(nested) - len(nested.lstrip(" "))
            if nested_indent <= include_indent:
                break

            if path_list_indent is not None:
                if nested_indent <= path_list_indent:
                    path_list_indent = None
                else:
                    path_item_match = re.match(r"^\s*-\s*(.*?)\s*$", nested)
                    if path_item_match:
                        add_candidate(path_item_match.group(1).strip())
                        index += 1
                        continue

            list_match = re.match(r"^\s*-\s*(.*?)\s*$", nested)
            if list_match:
                if item_indent is None:
                    item_indent = nested_indent
                if nested_indent == item_indent:
                    item_value = list_match.group(1).strip()
                    if item_value.startswith("{"):
                        include_path = _docker_compose_inline_object_value(item_value, "path")
                        if include_path:
                            add_candidate(include_path)
                    else:
                        field_match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*?)\s*$", item_value)
                        if field_match and field_match.group(1) == "path":
                            raw_value = field_match.group(2).strip()
                            if raw_value:
                                add_candidate(raw_value)
                            else:
                                path_list_indent = nested_indent
                        elif item_value:
                            add_candidate(item_value)
                index += 1
                continue

            field_match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*?)\s*$", nested)
            if field_match and field_match.group(1) == "path":
                raw_value = field_match.group(2).strip()
                if raw_value:
                    add_candidate(raw_value)
                else:
                    path_list_indent = nested_indent
            index += 1

    return list(dict.fromkeys(references))


def _docker_compose_build_references_from_text(text: str) -> list[tuple[str, str, bool]]:
    references: list[tuple[str, str, bool]] = []
    lines = text.splitlines()
    index = 0

    while index < len(lines):
        without_comment = lines[index].split("#", 1)[0].rstrip()
        if not without_comment.strip():
            index += 1
            continue
        indent = len(without_comment) - len(without_comment.lstrip(" "))
        build_match = re.match(r"^\s*build\s*:\s*(.*?)\s*$", without_comment)
        if not build_match:
            index += 1
            continue

        value = build_match.group(1).strip()
        if value:
            if value.startswith("{"):
                context = _docker_compose_inline_object_value(value, "context") or "."
                dockerfile = _docker_compose_inline_object_value(value, "dockerfile")
                has_inline_dockerfile = bool(_docker_compose_inline_object_value(value, "dockerfile_inline"))
                if _is_local_docker_compose_path(context):
                    references.append((
                        _docker_compose_scalar_value(context),
                        _docker_compose_scalar_value(dockerfile),
                        has_inline_dockerfile,
                    ))
            elif _is_local_docker_compose_path(value):
                references.append((_docker_compose_scalar_value(value), "", False))
            index += 1
            continue

        context = ""
        dockerfile = ""
        has_inline_dockerfile = False
        field_indent: int | None = None
        index += 1
        while index < len(lines):
            nested = lines[index].split("#", 1)[0].rstrip()
            if not nested.strip():
                index += 1
                continue
            nested_indent = len(nested) - len(nested.lstrip(" "))
            if nested_indent <= indent:
                break
            field_match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*?)\s*$", nested)
            if field_match:
                if field_indent is None:
                    field_indent = nested_indent
                if nested_indent == field_indent:
                    field, field_value = field_match.groups()
                    if field == "context":
                        context = _docker_compose_scalar_value(field_value)
                    elif field == "dockerfile":
                        dockerfile = _docker_compose_scalar_value(field_value)
                    elif field == "dockerfile_inline":
                        has_inline_dockerfile = True
            index += 1

        context = context or "."
        if _is_local_docker_compose_path(context):
            references.append((_docker_compose_scalar_value(context), _docker_compose_scalar_value(dockerfile), has_inline_dockerfile))

    return list(dict.fromkeys(references))


def _docker_compose_resolved_path(root: Path, base: Path, value: str) -> Path | None:
    root_resolved = root.resolve()
    candidate = (base / value).resolve()
    if not _is_within_root(candidate, root_resolved):
        return None
    return candidate


def _docker_compose_healthcheck_script_exists(root: Path, compose_file: Path, script: str) -> bool:
    root_resolved = root.resolve()
    candidates = [
        (compose_file.parent / script).resolve(),
        (root / script).resolve(),
    ]
    return any(_is_within_root(candidate, root_resolved) and candidate.is_file() for candidate in candidates)


def _docker_compose_resource_file_exists(root: Path, compose_file: Path, resource_file: str) -> bool:
    root_resolved = root.resolve()
    candidates = [
        (compose_file.parent / resource_file).resolve(),
        (root / resource_file).resolve(),
    ]
    return any(_is_within_root(candidate, root_resolved) and candidate.is_file() for candidate in candidates)


def _docker_compose_service_env_file_exists(root: Path, compose_file: Path, env_file: str) -> bool:
    root_resolved = root.resolve()
    candidates = [
        (compose_file.parent / env_file).resolve(),
        (root / env_file).resolve(),
    ]
    return any(_is_within_root(candidate, root_resolved) and candidate.is_file() for candidate in candidates)


def _docker_compose_service_label_file_exists(root: Path, compose_file: Path, label_file: str) -> bool:
    root_resolved = root.resolve()
    candidates = [
        (compose_file.parent / label_file).resolve(),
        (root / label_file).resolve(),
    ]
    return any(_is_within_root(candidate, root_resolved) and candidate.is_file() for candidate in candidates)


def _docker_compose_develop_watch_path_exists(root: Path, compose_file: Path, watch_path: str) -> bool:
    root_resolved = root.resolve()
    candidates = [
        (compose_file.parent / watch_path).resolve(),
        (root / watch_path).resolve(),
    ]
    return any(_is_within_root(candidate, root_resolved) and candidate.exists() for candidate in candidates)


def _docker_compose_extends_file_path(root: Path, compose_file: Path, extends_file: str) -> Path | None:
    if not _is_local_docker_compose_path(extends_file):
        return None
    root_resolved = root.resolve()
    candidates = [
        (compose_file.parent / extends_file).resolve(),
        (root / extends_file).resolve(),
    ]
    for candidate in candidates:
        if _is_within_root(candidate, root_resolved) and candidate.is_file():
            return candidate
    return None


def _docker_compose_include_file_exists(root: Path, compose_file: Path, include_file: str) -> bool:
    root_resolved = root.resolve()
    candidates = [
        (compose_file.parent / include_file).resolve(),
        (root / include_file).resolve(),
    ]
    return any(_is_within_root(candidate, root_resolved) and candidate.is_file() for candidate in candidates)


def check_missing_docker_compose_resource_files(root: Path, files: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in files:
        if not _is_docker_compose_file(path):
            continue
        try:
            references = _docker_compose_resource_file_references_from_text(path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            continue
        missing_files = [
            resource_file
            for _, _, resource_file in references
            if not _docker_compose_resource_file_exists(root, path, resource_file)
        ]
        if not missing_files:
            continue
        findings.append(
            Finding(
                check_id="LC068",
                title="Docker Compose secret/config references missing file",
                severity="medium",
                category="onboarding",
                file_path=_relative_posix(path, root),
                evidence=(
                    f"Docker Compose secret/config file(s) {', '.join(dict.fromkeys(missing_files))} "
                    "are referenced, but those files are not present in the scanned repo."
                ),
                why_it_matters="A fresh clone can fail at service startup when Compose secrets or configs point at local files that were not committed.",
                suggested_fix="Commit the referenced file, mark the secret/config as external, or document how the file is generated before running Compose.",
            )
        )
    return findings


def check_missing_docker_compose_develop_watch_paths(root: Path, files: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in files:
        if not _is_docker_compose_file(path):
            continue
        try:
            watch_paths = _docker_compose_develop_watch_paths_from_text(path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            continue
        missing_paths = [
            watch_path
            for watch_path in watch_paths
            if not _docker_compose_develop_watch_path_exists(root, path, watch_path)
        ]
        if not missing_paths:
            continue
        findings.append(
            Finding(
                check_id="LC073",
                title="Docker Compose develop watch references missing path",
                severity="medium",
                category="onboarding",
                file_path=_relative_posix(path, root),
                evidence=(
                    f"Docker Compose develop watch path(s) {', '.join(dict.fromkeys(missing_paths))} "
                    "are referenced, but those paths are not present in the scanned repo."
                ),
                why_it_matters="A fresh clone can fail or silently skip live-sync/rebuild behavior when Compose develop watches paths that were not committed.",
                suggested_fix="Commit the watched file or directory, update develop.watch.path to an included path, or document how the watched path is generated before running Compose.",
            )
        )
    return findings


def check_missing_docker_compose_service_label_files(root: Path, files: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in files:
        if not _is_docker_compose_file(path):
            continue
        try:
            label_files = _docker_compose_label_file_references_from_text(path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            continue
        missing_files = [
            label_file
            for label_file in label_files
            if not _docker_compose_service_label_file_exists(root, path, label_file)
        ]
        if not missing_files:
            continue
        findings.append(
            Finding(
                check_id="LC072",
                title="Docker Compose service label_file references missing file",
                severity="medium",
                category="onboarding",
                file_path=_relative_posix(path, root),
                evidence=(
                    f"Docker Compose service label_file(s) {', '.join(dict.fromkeys(missing_files))} "
                    "are referenced, but those files are not present in the scanned repo."
                ),
                why_it_matters="A fresh clone can fail at service startup or silently miss service labels when Compose services load label files that were not committed.",
                suggested_fix="Commit the label file, replace it with a safe example and documented copy step, or update label_file to an included path.",
            )
        )
    return findings


def check_missing_docker_compose_include_files(root: Path, files: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in files:
        if not _is_docker_compose_file(path):
            continue
        try:
            include_files = _docker_compose_include_references_from_text(path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            continue
        missing_files = [
            include_file
            for include_file in include_files
            if not _docker_compose_include_file_exists(root, path, include_file)
        ]
        if not missing_files:
            continue
        findings.append(
            Finding(
                check_id="LC071",
                title="Docker Compose include references missing file",
                severity="medium",
                category="onboarding",
                file_path=_relative_posix(path, root),
                evidence=(
                    f"Docker Compose include file(s) {', '.join(dict.fromkeys(missing_files))} "
                    "are referenced, but those files are not present in the scanned repo."
                ),
                why_it_matters="A fresh clone can fail before services are assembled when Compose include points at local files that were not committed.",
                suggested_fix="Commit the included Compose file, replace the include with an included path, or document how the file is generated before running Compose.",
            )
        )
    return findings


def check_missing_docker_compose_extends_targets(root: Path, files: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    service_cache: dict[Path, set[str]] = {}

    def service_names(path: Path, text: str | None = None) -> set[str]:
        if path not in service_cache:
            try:
                service_text = text if text is not None else path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                service_text = ""
            service_cache[path] = _docker_compose_service_names_from_text(service_text)
        return service_cache[path]

    for path in files:
        if not _is_docker_compose_file(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        local_services = service_names(path, text)
        references = _docker_compose_extends_references_from_text(text)
        missing_files: list[str] = []
        missing_services: list[str] = []

        for current_service, extends_file, extends_service in references:
            target_services = local_services
            if extends_file:
                if not _is_local_docker_compose_path(extends_file):
                    continue
                target_file = _docker_compose_extends_file_path(root, path, extends_file)
                if target_file is None:
                    missing_files.append(extends_file)
                    continue
                target_services = service_names(target_file)
            if extends_service and _is_docker_compose_service_reference(extends_service) and extends_service not in target_services:
                if extends_file:
                    missing_services.append(f"{current_service}->{extends_service} in {extends_file}")
                else:
                    missing_services.append(f"{current_service}->{extends_service}")

        evidence_parts: list[str] = []
        if missing_files:
            evidence_parts.append(
                f"Docker Compose extends file(s) {', '.join(dict.fromkeys(missing_files))} "
                "are referenced, but those files are not present in the scanned repo."
            )
        if missing_services:
            evidence_parts.append(
                f"Docker Compose extends service target(s) {', '.join(dict.fromkeys(missing_services))} "
                "are referenced, but those services are not defined in the target Compose file."
            )
        if not evidence_parts:
            continue
        findings.append(
            Finding(
                check_id="LC070",
                title="Docker Compose extends references missing file or service",
                severity="medium",
                category="onboarding",
                file_path=_relative_posix(path, root),
                evidence=" ".join(evidence_parts),
                why_it_matters="A fresh clone can fail at service startup when Compose inheritance points at a missing base file or renamed service.",
                suggested_fix="Commit the extended Compose file, add the missing base service, or update extends to reference an included file and service.",
            )
        )
    return findings


def check_missing_docker_compose_service_env_files(root: Path, files: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in files:
        if not _is_docker_compose_file(path):
            continue
        try:
            env_files = _docker_compose_env_file_references_from_text(path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            continue
        missing_files = [
            env_file
            for env_file in env_files
            if not _docker_compose_service_env_file_exists(root, path, env_file)
        ]
        if not missing_files:
            continue
        findings.append(
            Finding(
                check_id="LC069",
                title="Docker Compose service env_file references missing file",
                severity="medium",
                category="onboarding",
                file_path=_relative_posix(path, root),
                evidence=(
                    f"Docker Compose service env_file(s) {', '.join(dict.fromkeys(missing_files))} "
                    "are referenced, but those files are not present in the scanned repo."
                ),
                why_it_matters="A fresh clone can fail at service startup or silently miss configuration when Compose services load env files that were not committed.",
                suggested_fix="Commit the env file, replace it with a safe example file and documented copy step, or update env_file to an included path.",
            )
        )
    return findings


def check_missing_docker_compose_healthcheck_scripts(root: Path, files: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in files:
        if not _is_docker_compose_file(path):
            continue
        try:
            scripts = _docker_compose_healthcheck_script_references_from_text(path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            continue
        missing_scripts = [
            script
            for script in scripts
            if not _docker_compose_healthcheck_script_exists(root, path, script)
        ]
        if not missing_scripts:
            continue
        findings.append(
            Finding(
                check_id="LC067",
                title="Docker Compose healthcheck references missing script",
                severity="medium",
                category="onboarding",
                file_path=_relative_posix(path, root),
                evidence=(
                    f"Docker Compose healthcheck script(s) {', '.join(missing_scripts)} "
                    "are referenced, but those files are not present in the scanned repo."
                ),
                why_it_matters="A fresh clone can report unhealthy services when Compose healthchecks point at scripts that were not committed.",
                suggested_fix="Commit the healthcheck script, update healthcheck.test to an image-provided command, or document how the script is generated.",
            )
        )
    return findings


def _docker_compose_build_context_path(root: Path, compose_file: Path, context: str) -> Path | None:
    return _docker_compose_resolved_path(root, compose_file.parent, context)


def _docker_compose_dockerfile_path(root: Path, context_path: Path, dockerfile: str) -> Path | None:
    return _docker_compose_resolved_path(root, context_path, dockerfile or "Dockerfile")


def check_missing_docker_compose_build_paths(root: Path, files: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in files:
        if not _is_docker_compose_file(path):
            continue
        try:
            references = _docker_compose_build_references_from_text(path.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            continue

        missing_contexts: list[str] = []
        missing_dockerfiles: list[str] = []
        for context, dockerfile, has_inline_dockerfile in references:
            context_path = _docker_compose_build_context_path(root, path, context)
            if context_path is None or not context_path.is_dir():
                missing_contexts.append(context)
                continue
            if has_inline_dockerfile:
                continue
            dockerfile_path = _docker_compose_dockerfile_path(root, context_path, dockerfile)
            if dockerfile_path is None or not dockerfile_path.is_file():
                missing_dockerfiles.append(_relative_posix(dockerfile_path, root) if dockerfile_path else dockerfile or "Dockerfile")

        evidence_parts: list[str] = []
        if missing_contexts:
            evidence_parts.append(
                f"Docker Compose build context(s) {', '.join(dict.fromkeys(missing_contexts))} "
                "are referenced, but those directories are not present in the scanned repo."
            )
        if missing_dockerfiles:
            evidence_parts.append(
                f"Docker Compose Dockerfile(s) {', '.join(dict.fromkeys(missing_dockerfiles))} "
                "are referenced, but those files are not present in the scanned repo."
            )
        if not evidence_parts:
            continue
        findings.append(
            Finding(
                check_id="LC005",
                title="Referenced input artifact missing from repo",
                severity="high",
                category="artifacts",
                file_path=_relative_posix(path, root),
                evidence=" ".join(evidence_parts),
                why_it_matters="A new user may not be able to build the documented services because required Compose build inputs are missing.",
                suggested_fix="Commit the build context and Dockerfile, switch to dockerfile_inline, or update the Compose file to reference included paths.",
            )
        )
    return findings


def _dockerfile_stage_names(path: Path) -> set[str]:
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return set()
    stages: set[str] = set()
    pattern = re.compile(
        r"^\s*FROM(?:\s+--[^\s]+\s+)*\s+\S+(?:\s+AS\s+([A-Za-z0-9][A-Za-z0-9_.-]*))?\s*(?:#.*)?$",
        re.IGNORECASE | re.MULTILINE,
    )
    for match in pattern.finditer(content):
        if match.group(1):
            stages.add(match.group(1))
    return stages


def _helm_chart_exists(root: Path, chart_path: str) -> bool:
    normalized = chart_path.replace("\\", "/").rstrip("/") or "."
    path = root if normalized in {".", "./"} else root / normalized
    return path.is_dir() and (path / "Chart.yaml").is_file()


def _kustomization_exists(root: Path, kustomize_path: str) -> bool:
    normalized = kustomize_path.replace("\\", "/").rstrip("/") or "."
    path = root if normalized in {".", "./"} else root / normalized
    return path.is_dir() and any(
        (path / name).is_file()
        for name in ("kustomization.yaml", "kustomization.yml", "Kustomization")
    )


def _kubernetes_manifest_path_exists(root: Path, manifest_path: str) -> bool:
    normalized = manifest_path.replace("\\", "/").rstrip("/") or "."
    path = root if normalized in {".", "./"} else root / normalized
    if path.is_file():
        return path.name.endswith((".yaml", ".yml", ".json"))
    if not path.is_dir():
        return False
    try:
        return any(
            child.is_file() and child.name.endswith((".yaml", ".yml", ".json"))
            for child in path.iterdir()
        )
    except OSError:
        return False


def _terraform_working_dir_exists(root: Path, working_dir: str) -> bool:
    normalized = working_dir.replace("\\", "/").rstrip("/") or "."
    path = root if normalized in {".", "./"} else root / normalized
    if not path.is_dir():
        return False
    try:
        return any(
            child.is_file() and (child.name.endswith(".tf") or child.name.endswith(".tf.json"))
            for child in path.iterdir()
        )
    except OSError:
        return False


def _pulumi_project_dir_exists(root: Path, project_dir: str) -> bool:
    normalized = project_dir.replace("\\", "/").rstrip("/") or "."
    path = root if normalized in {".", "./"} else root / normalized
    return path.is_dir() and any((path / name).is_file() for name in ("Pulumi.yaml", "Pulumi.yml"))


def _ansible_playbook_exists(root: Path, playbook: str) -> bool:
    normalized = playbook.replace("\\", "/").rstrip("/")
    return (root / normalized).is_file()


def _ansible_inventory_exists(root: Path, inventory: str) -> bool:
    normalized = inventory.replace("\\", "/").rstrip("/")
    path = root / normalized
    return path.is_file() or path.is_dir()


def _packer_template_exists(root: Path, template_path: str) -> bool:
    normalized = template_path.replace("\\", "/").rstrip("/") or "."
    path = root if normalized in {".", "./"} else root / normalized
    if path.is_file():
        return path.name.endswith((".pkr.hcl", ".pkr.json"))
    if not path.is_dir():
        return False
    try:
        return any(
            child.is_file() and child.name.endswith((".pkr.hcl", ".pkr.json"))
            for child in path.iterdir()
        )
    except OSError:
        return False


def _string_list_literal(node: ast.AST) -> list[str]:
    if isinstance(node, (ast.List, ast.Tuple)):
        values: list[str] = []
        for element in node.elts:
            if isinstance(element, ast.Constant) and isinstance(element.value, str):
                values.append(element.value)
            else:
                return []
        return values
    return []


def _dagster_call_name(node: ast.AST) -> str:
    return _call_name(node).split(".")[-1]


def _dagster_job_name_from_decorator(decorator: ast.AST) -> str | None:
    if isinstance(decorator, ast.Name) and decorator.id == "job":
        return ""
    if isinstance(decorator, ast.Attribute) and decorator.attr == "job":
        return ""
    if isinstance(decorator, ast.Call):
        base = _dagster_job_name_from_decorator(decorator.func)
        if base is None:
            return None
        return _call_keyword_string(decorator, "name") or ""
    return None


def _dagster_asset_names_from_decorator(decorator: ast.AST, function_name: str) -> set[str]:
    names: set[str] = set()
    if isinstance(decorator, (ast.Name, ast.Attribute)):
        decorator_name = decorator.id if isinstance(decorator, ast.Name) else decorator.attr
        if decorator_name == "asset":
            names.add(function_name)
        return names
    if not isinstance(decorator, ast.Call):
        return names

    call_name = _dagster_call_name(decorator.func)
    if call_name == "asset":
        explicit_name = _call_keyword_string(decorator, "name") or _call_keyword_string(decorator, "key")
        asset_name = explicit_name or function_name
        key_prefix: list[str] = []
        for keyword in decorator.keywords:
            if keyword.arg == "key_prefix":
                if isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
                    key_prefix = [keyword.value.value]
                else:
                    key_prefix = _string_list_literal(keyword.value)
        names.add(asset_name)
        if key_prefix:
            names.add("/".join([*key_prefix, asset_name]))
        return names

    if call_name == "multi_asset":
        for keyword in decorator.keywords:
            if keyword.arg != "outs" or not isinstance(keyword.value, ast.Dict):
                continue
            for key in keyword.value.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    names.add(key.value)
        return names

    return names


def _dagster_names_from_python(path: Path) -> tuple[set[str], set[str]]:
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return set(), set()

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return set(), set()

    jobs: set[str] = set()
    assets: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                job_name = _dagster_job_name_from_decorator(decorator)
                if job_name is not None:
                    jobs.add(job_name or node.name)
                    continue
                assets.update(_dagster_asset_names_from_decorator(decorator, node.name))
            continue

        if not isinstance(node, ast.Call):
            continue
        call_name = _dagster_call_name(node.func)
        if call_name == "define_asset_job":
            name = _call_keyword_string(node, "name") or _literal_first_arg(node)
            if name:
                jobs.add(name)
        elif call_name == "AssetSpec":
            name = _call_keyword_string(node, "key") or _call_keyword_string(node, "name") or _literal_first_arg(node)
            if name:
                assets.add(name)

    return jobs, assets


def _dagster_names(root: Path) -> tuple[set[str], set[str]] | None:
    jobs: set[str] = set()
    assets: set[str] = set()
    found_dagster_names = False
    for path in root.rglob("*.py"):
        if ".venv" in path.parts or "site-packages" in path.parts:
            continue
        path_jobs, path_assets = _dagster_names_from_python(path)
        if path_jobs or path_assets:
            found_dagster_names = True
            jobs.update(path_jobs)
            assets.update(path_assets)

    if not found_dagster_names:
        return None
    return jobs, assets


def _dagster_target_exists(target: str, names: set[str]) -> bool:
    if target in names:
        return True
    normalized = target.strip().replace(".", "/")
    if normalized in names:
        return True
    if "/" in normalized and normalized.split("/")[-1] in names:
        return True
    return False


def _airflow_dag_decorator_name(decorator: ast.AST) -> str | None:
    if isinstance(decorator, ast.Name) and decorator.id == "dag":
        return ""
    if isinstance(decorator, ast.Attribute) and decorator.attr == "dag":
        return ""
    if isinstance(decorator, ast.Call):
        base = _airflow_dag_decorator_name(decorator.func)
        if base is None:
            return None
        return _call_keyword_string(decorator, "dag_id") or ""
    return None


def _airflow_task_decorator_name(decorator: ast.AST) -> str | None:
    if isinstance(decorator, ast.Name) and decorator.id == "task":
        return ""
    if isinstance(decorator, ast.Attribute):
        if decorator.attr == "task":
            return ""
        if isinstance(decorator.value, ast.Name) and decorator.value.id == "task":
            return ""
    if isinstance(decorator, ast.Call):
        base = _airflow_task_decorator_name(decorator.func)
        if base is None:
            return None
        return _call_keyword_string(decorator, "task_id") or ""
    return None


def _airflow_dag_task_names_from_python(path: Path) -> tuple[set[str], set[str]]:
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return set(), set()

    dag_ids: set[str] = set()
    task_ids: set[str] = set()
    try:
        tree = ast.parse(content)
    except SyntaxError:
        tree = None

    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call_name = _call_name(node.func).split(".")[-1]
                if call_name == "DAG":
                    dag_id = _call_keyword_string(node, "dag_id") or _literal_first_arg(node)
                    if dag_id:
                        dag_ids.add(dag_id)
                task_id = _call_keyword_string(node, "task_id")
                if task_id:
                    task_ids.add(task_id)
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                dag_name = _airflow_dag_decorator_name(decorator)
                if dag_name is not None:
                    dag_ids.add(dag_name or node.name)
                    continue
                task_name = _airflow_task_decorator_name(decorator)
                if task_name is not None:
                    task_ids.add(task_name or node.name)

    for match in re.finditer(r"\bDAG\s*\(\s*['\"]([^'\"]+)['\"]", content):
        dag_ids.add(match.group(1))
    for match in re.finditer(r"\bDAG\s*\([^)]*\bdag_id\s*=\s*['\"]([^'\"]+)['\"]", content, re.DOTALL):
        dag_ids.add(match.group(1))
    for match in re.finditer(r"@(?:[A-Za-z_][A-Za-z0-9_]*\.)?dag\([^)]*\bdag_id\s*=\s*['\"]([^'\"]+)['\"]", content, re.DOTALL):
        dag_ids.add(match.group(1))
    for match in re.finditer(
        r"@(?:[A-Za-z_][A-Za-z0-9_]*\.)?dag(?:\([^)]*\))?\s*\r?\n\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
        content,
        re.DOTALL,
    ):
        dag_ids.add(match.group(1))
    for match in re.finditer(r"\btask_id\s*=\s*['\"]([^'\"]+)['\"]", content):
        task_ids.add(match.group(1))
    for match in re.finditer(
        r"@(?:[A-Za-z_][A-Za-z0-9_]*\.)?task(?:\.[A-Za-z_][A-Za-z0-9_]*)?(?:\([^)]*\))?\s*\r?\n\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
        content,
        re.DOTALL,
    ):
        task_ids.add(match.group(1))
    return dag_ids, task_ids


def _airflow_dag_task_names(root: Path) -> tuple[set[str], set[str]] | None:
    dag_ids: set[str] = set()
    task_ids: set[str] = set()
    found_airflow_names = False
    for path in root.rglob("*.py"):
        if ".venv" in path.parts or "site-packages" in path.parts:
            continue
        path_dag_ids, path_task_ids = _airflow_dag_task_names_from_python(path)
        if path_dag_ids or path_task_ids:
            found_airflow_names = True
            dag_ids.update(path_dag_ids)
            task_ids.update(path_task_ids)

    if not found_airflow_names:
        return None
    return dag_ids, task_ids


def _mlflow_project_dir(root: Path, reference: str) -> Path | None:
    normalized = reference.replace("\\", "/").strip()
    if not normalized or normalized.startswith(("$", "${{", "~", "/", "<")) or "://" in normalized:
        return None
    return root if normalized == "." else root / normalized


def _mlflow_entry_points_from_project(project_dir: Path) -> set[str] | None:
    mlproject = project_dir / "MLproject"
    if not mlproject.exists():
        return None
    try:
        content = mlproject.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return set()

    entry_points: set[str] = set()
    in_entry_points = False
    section_indent = 0
    entry_indent: int | None = None
    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" \t"))
        if not in_entry_points:
            if re.match(r"^entry_points\s*:\s*(?:#.*)?$", stripped):
                in_entry_points = True
                section_indent = indent
            continue

        if indent <= section_indent:
            break
        if entry_indent is None:
            entry_indent = indent
        if indent != entry_indent:
            continue

        match = re.match(r"^\s*(?:['\"]([^'\"]+)['\"]|([A-Za-z0-9_.:-]+))\s*:", raw_line)
        if match:
            entry_points.add(match.group(1) or match.group(2))
    return entry_points


def _mlflow_entry_script_exists(project_dir: Path, entry_point: str) -> bool:
    if not entry_point.endswith((".py", ".sh")):
        return False
    return (project_dir / entry_point).exists()


def _is_metaflow_step_decorator(decorator: ast.AST) -> bool:
    if isinstance(decorator, ast.Name):
        return decorator.id == "step"
    if isinstance(decorator, ast.Attribute):
        return decorator.attr == "step"
    if isinstance(decorator, ast.Call):
        return _is_metaflow_step_decorator(decorator.func)
    return False


def _metaflow_steps_from_script(path: Path) -> set[str] | None:
    if not path.exists():
        return None
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return set()

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return set()

    steps: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if any(_is_metaflow_step_decorator(decorator) for decorator in node.decorator_list):
            steps.add(node.name)
    return steps


def _pyproject_scripts(root: Path) -> set[str] | None:
    payload = _read_toml(root / "pyproject.toml")
    if payload is None:
        return None

    scripts: set[str] = set()
    project = payload.get("project", {})
    if isinstance(project, dict):
        for section_name in ("scripts", "gui-scripts"):
            section = project.get(section_name, {})
            if isinstance(section, dict):
                scripts.update(str(name) for name in section)

    poetry = payload.get("tool", {}).get("poetry", {}) if isinstance(payload.get("tool"), dict) else {}
    if isinstance(poetry, dict):
        poetry_scripts = poetry.get("scripts", {})
        if isinstance(poetry_scripts, dict):
            scripts.update(str(name) for name in poetry_scripts)
    return scripts


def _workflow_files(root: Path, files: list[Path]) -> list[Path]:
    root_resolved = root.resolve()
    workflow_files: list[Path] = []
    for path in files:
        try:
            relative = path.resolve().relative_to(root_resolved).as_posix()
        except ValueError:
            continue
        if relative.startswith(".github/workflows/") and path.suffix.lower() in {".yml", ".yaml"}:
            workflow_files.append(path)
    return sorted(workflow_files)


def _workflow_command_candidate_lines(content: str) -> list[str]:
    candidates: list[str] = []
    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        stripped = re.sub(r"^(?:-\s+)?run:\s*", "", stripped)
        stripped = stripped.strip("'\"")
        if stripped in {"|", ">", "|-", ">-"}:
            continue
        if WORKFLOW_COMMAND_PREFIX_PATTERN.search(stripped):
            candidates.append(stripped)
    return candidates


def _path_exists_at_root(root: Path, reference: str) -> bool:
    normalized = reference.replace("\\", "/").strip()
    if not normalized or normalized.startswith(("$", "${{", "~", "/", "<")) or "://" in normalized:
        return True
    return (root / normalized).exists()


def _missing_pip_include_references(root: Path, command: str, tokens: list[str]) -> list[str]:
    if len(tokens) >= 2 and tokens[:2] == ["uv", "run"]:
        return _missing_pip_include_references(root, command, tokens[2:])

    args: list[str] | None = None
    if len(tokens) >= 2 and tokens[0] in {"pip", "pip3"} and tokens[1] == "install":
        args = tokens[2:]
    elif len(tokens) >= 4 and tokens[0] in {"python", "python3"} and tokens[1:4] == ["-m", "pip", "install"]:
        args = tokens[4:]
    elif len(tokens) >= 3 and tokens[:3] == ["uv", "pip", "install"]:
        args = tokens[3:]
    if args is None:
        return []

    missing: list[str] = []
    for index, token in enumerate(args):
        reference = ""
        if token in {"-r", "--requirement", "-c", "--constraint"} and index + 1 < len(args):
            reference = args[index + 1]
        elif token.startswith(("--requirement=", "--constraint=")):
            reference = token.split("=", 1)[1]
        elif token.startswith(("-r", "-c")) and len(token) > 2:
            reference = token[2:]
        if reference and not _path_exists_at_root(root, reference):
            missing.append(f"Command '{command}' references missing dependency file '{reference}'.")
    return missing


def _workflow_command_drift_issues(root: Path, command: str) -> list[str]:
    tokens = _shell_tokens(command)
    if not tokens:
        return []
    if len(tokens) >= 2 and tokens[:2] == ["uv", "run"]:
        return _workflow_command_drift_issues(root, " ".join(tokens[2:]))

    issues = _missing_pip_include_references(root, command, tokens)
    if len(tokens) >= 2 and tokens[0] in {"python", "python3"}:
        if tokens[1] == "-m" and len(tokens) >= 3 and "." in tokens[2] and not _python_module_exists(root, tokens[2]):
            issues.append(f"Command '{command}' references missing Python module '{tokens[2]}'.")
        elif tokens[1].endswith(".py") and not _path_exists_at_root(root, tokens[1]):
            issues.append(f"Command '{command}' points to missing script '{tokens[1]}'.")
    elif len(tokens) >= 2 and tokens[0] in {"bash", "sh"} and tokens[1].endswith(".sh") and not _path_exists_at_root(root, tokens[1]):
        issues.append(f"Command '{command}' points to missing shell script '{tokens[1]}'.")
    elif tokens[0] == "make" and len(tokens) >= 2:
        makefile = _find_makefile(root)
        if not makefile:
            issues.append(f"Command '{command}' requires a Makefile, but no Makefile is present.")
        elif tokens[1] not in _makefile_targets(makefile):
            issues.append(f"Command '{command}' references missing Makefile target '{tokens[1]}'.")
    elif len(tokens) >= 3 and tokens[0] in {"npm", "pnpm"} and tokens[1] == "run":
        scripts = _package_json_scripts(root)
        if not scripts:
            issues.append(f"Command '{command}' requires package.json scripts, but none are defined.")
        elif tokens[2] not in scripts:
            issues.append(f"Command '{command}' references missing package.json script '{tokens[2]}'.")
    elif len(tokens) >= 2 and tokens[0] == "yarn" and tokens[1] not in {"install", "add", "cache", "config"}:
        script = tokens[2] if tokens[1] == "run" and len(tokens) >= 3 else tokens[1]
        scripts = _package_json_scripts(root)
        if not scripts:
            issues.append(f"Command '{command}' requires package.json scripts, but none are defined.")
        elif script not in scripts:
            issues.append(f"Command '{command}' references missing package.json script '{script}'.")
    return issues


def check_ci_workflow_drift(root: Path, files: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    for path in _workflow_files(root, files):
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel_path = _relative_posix(path, root)
        for command in _workflow_command_candidate_lines(content):
            for issue in _workflow_command_drift_issues(root, command):
                key = (rel_path, issue)
                if key in seen:
                    continue
                seen.add(key)
                findings.append(
                    Finding(
                        check_id="LC025",
                        title="CI workflow command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path=rel_path,
                        evidence=issue,
                        why_it_matters="A repository's own CI workflow is often the closest thing to a reproducibility contract; stale commands make that contract fail before reviewers can trust it.",
                        suggested_fix="Update the workflow command or add the missing script, module, dependency file, Makefile target, or package script.",
                    )
                )
    return findings


def _workflow_has_setup(content: str) -> bool:
    return WORKFLOW_SETUP_PATTERN.search(content) is not None


def _workflow_has_verification(content: str) -> bool:
    return WORKFLOW_VERIFICATION_PATTERN.search(content) is not None


def _workflow_looks_like_validation(path: Path, root: Path, content: str) -> bool:
    try:
        relative = _relative_posix(path, root)
    except ValueError:
        relative = path.name
    haystack = "\n".join([relative, path.name, content])
    return WORKFLOW_VALIDATION_NAME_PATTERN.search(haystack) is not None


def check_ci_workflow_has_verification_step(root: Path, files: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in _workflow_files(root, files):
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if (
            not _workflow_looks_like_validation(path, root, content)
            or not _workflow_has_setup(content)
            or _workflow_has_verification(content)
        ):
            continue
        rel_path = _relative_posix(path, root)
        findings.append(
            Finding(
                check_id="LC044",
                title="CI workflow lacks verification step",
                severity="medium",
                category="onboarding",
                file_path=rel_path,
                evidence=f"{rel_path} installs or sets up an environment but no test, notebook execution, labcheck, or reproduce/check command was detected.",
                why_it_matters="CI is strongest as a reproducibility contract when it proves the repo still installs and runs something meaningful.",
                suggested_fix="Add a verification step such as pytest, jupyter nbconvert --execute, labcheck scan, make reproduce, or another documented smoke test.",
            )
        )
    return findings


def check_readme_drift(root: Path, references: list[ReadmeReference]) -> list[Finding]:
    findings: list[Finding] = []
    for reference in references:
        if reference.project_script:
            pyproject_scripts = _pyproject_scripts(root)
            if pyproject_scripts is None:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=f"Command '{reference.command}' requires pyproject.toml scripts, but no pyproject.toml is present.",
                        why_it_matters="Setup instructions lose trust quickly when they point to project scripts that cannot be run.",
                        suggested_fix="Add pyproject.toml with the project script, or update the README command to a real entrypoint.",
                    )
                )
                continue
            if reference.project_script not in pyproject_scripts:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references pyproject script "
                            f"'{reference.project_script}', but pyproject.toml does not define it."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to project scripts that cannot be run.",
                        suggested_fix="Add the pyproject.toml script or update the README command to match an existing project script.",
                    )
                )
                continue
            continue

        if reference.package_manager == "nextflow":
            if reference.nextflow_pipeline and _is_probably_local_nextflow_pipeline(reference.nextflow_pipeline):
                pipeline_path = root / reference.nextflow_pipeline
                if not pipeline_path.exists():
                    findings.append(
                        Finding(
                            check_id="LC008",
                            title="README command references a missing path",
                            severity="medium",
                            category="onboarding",
                            file_path="README.md",
                            evidence=(
                                f"Command '{reference.command}' references Nextflow pipeline "
                                f"'{reference.nextflow_pipeline}', but that file or directory is not present."
                            ),
                            why_it_matters="Setup instructions lose trust quickly when they point to workflow entrypoints that cannot be run.",
                            suggested_fix="Add the Nextflow pipeline file/directory or update the README command to match the actual workflow entrypoint.",
                        )
                    )
                    continue

            if reference.nextflow_profiles:
                declared_profiles = _nextflow_profiles(root)
                if declared_profiles is None:
                    findings.append(
                        Finding(
                            check_id="LC008",
                            title="README command references a missing path",
                            severity="medium",
                            category="onboarding",
                            file_path="README.md",
                            evidence=(
                                f"Command '{reference.command}' uses Nextflow profile(s) "
                                f"{', '.join(reference.nextflow_profiles)}, but no nextflow.config is present."
                            ),
                            why_it_matters="Setup instructions lose trust quickly when they point to workflow profiles that cannot be run.",
                            suggested_fix="Add nextflow.config with the documented profile(s), or update the README command to match existing profiles.",
                        )
                    )
                    continue
                missing_profiles = sorted(profile for profile in reference.nextflow_profiles if profile not in declared_profiles)
                if missing_profiles:
                    findings.append(
                        Finding(
                            check_id="LC008",
                            title="README command references a missing path",
                            severity="medium",
                            category="onboarding",
                            file_path="README.md",
                            evidence=(
                                f"Command '{reference.command}' references Nextflow profile(s) "
                                f"{', '.join(missing_profiles)}, but nextflow.config does not define them."
                            ),
                            why_it_matters="Setup instructions lose trust quickly when they point to workflow profiles that cannot be run.",
                            suggested_fix="Add the profile(s) under profiles { ... } or update the README command to match existing profiles.",
                        )
                    )
                    continue

            if reference.nextflow_entry:
                nextflow_names = _nextflow_names(root)
                if reference.nextflow_entry not in nextflow_names:
                    findings.append(
                        Finding(
                            check_id="LC008",
                            title="README command references a missing path",
                            severity="medium",
                            category="onboarding",
                            file_path="README.md",
                            evidence=(
                                f"Command '{reference.command}' references Nextflow entry "
                                f"'{reference.nextflow_entry}', but no matching process or workflow name was found."
                            ),
                            why_it_matters="Setup instructions lose trust quickly when they point to workflow entries that cannot be run.",
                            suggested_fix="Add the named process/workflow or update the README command to match an existing Nextflow entry.",
                        )
                    )
                    continue
            continue

        if reference.package_manager == "cromwell":
            if reference.wdl_workflow and not _path_exists_at_root(root, reference.wdl_workflow):
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references WDL workflow "
                            f"'{reference.wdl_workflow}', but that file is not present."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to workflow entrypoints that cannot be run.",
                        suggested_fix="Add the WDL workflow file or update the README command to match the actual Cromwell workflow entrypoint.",
                    )
                )
                continue

            missing_inputs = [path for path in reference.wdl_inputs if not _path_exists_at_root(root, path)]
            if missing_inputs:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Cromwell input file(s) "
                            f"{', '.join(missing_inputs)}, but they are not present."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to input JSON files that cannot be loaded.",
                        suggested_fix="Add the Cromwell input JSON file(s) or update the README command to match the actual inputs path.",
                    )
                )
                continue

            if reference.wdl_workflow_root and not _path_exists_at_root(root, reference.wdl_workflow_root):
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Cromwell workflow root "
                            f"'{reference.wdl_workflow_root}', but that directory is not present."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to workflow roots that cannot resolve imported WDL files.",
                        suggested_fix="Add the workflow root directory or update the README command to match the actual WDL import root.",
                    )
                )
                continue
            continue

        if reference.package_manager == "cwl":
            if reference.cwl_workflow and not _path_exists_at_root(root, reference.cwl_workflow):
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references CWL workflow/tool "
                            f"'{reference.cwl_workflow}', but that file is not present."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to workflow entrypoints that cannot be run.",
                        suggested_fix="Add the CWL workflow/tool file or update the README command to match the actual CWL entrypoint.",
                    )
                )
                continue

            if reference.cwl_job and not _path_exists_at_root(root, reference.cwl_job):
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references CWL job file "
                            f"'{reference.cwl_job}', but that file is not present."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to input/job files that cannot be loaded.",
                        suggested_fix="Add the CWL job YAML/JSON file or update the README command to match the actual job file.",
                    )
                )
                continue
            continue

        if reference.package_manager == "papermill":
            if reference.papermill_input and not _path_exists_at_root(root, reference.papermill_input):
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Papermill input notebook "
                            f"'{reference.papermill_input}', but that file is not present."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to notebooks that cannot be executed.",
                        suggested_fix="Add the Papermill input notebook or update the README command to match the actual notebook path.",
                    )
                )
                continue

            missing_parameter_files = [
                path for path in reference.papermill_parameter_files if not _path_exists_at_root(root, path)
            ]
            if missing_parameter_files:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Papermill parameter file(s) "
                            f"{', '.join(missing_parameter_files)}, but they are not present."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when parameterized notebook runs rely on missing YAML files.",
                        suggested_fix="Add the Papermill parameter YAML file(s) or update the README command to match the actual parameter file path.",
                    )
                )
                continue
            continue

        if reference.package_manager == "dvc":
            stages = _dvc_stage_names(root)
            missing_targets = [
                target for target in reference.dvc_targets if not _dvc_target_exists(root, target, stages)
            ]
            if missing_targets:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references DVC target(s) "
                            f"{', '.join(missing_targets)}, but no matching stage, path, or .dvc metadata file is present."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to data pipeline targets that cannot be restored or reproduced.",
                        suggested_fix="Add the documented DVC stage/path metadata, or update the README command to match the current dvc.yaml stages and .dvc files.",
                    )
                )
                continue
            continue

        if reference.package_manager == "quarto":
            if reference.quarto_target and not _path_exists_at_root(root, reference.quarto_target):
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Quarto render target "
                            f"'{reference.quarto_target}', but that file or directory is not present."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to reports, manuscripts, notebooks, or site projects that cannot be rendered.",
                        suggested_fix="Add the Quarto document/project target or update the README command to match the current report path.",
                    )
                )
                continue
            continue

        if reference.package_manager == "jupytext":
            missing_targets = [
                target for target in reference.jupytext_targets if not _path_exists_at_root(root, target)
            ]
            if missing_targets:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Jupytext sync target(s) "
                            f"{', '.join(missing_targets)}, but they are not present."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when paired notebook/text files cannot be synchronized from a fresh clone.",
                        suggested_fix="Add the documented Jupytext target file(s), or update the README command to match the current notebook/text pair paths.",
                    )
                )
                continue
            continue

        if reference.package_manager == "kedro":
            kedro_pipelines = _kedro_pipeline_names(root)
            if kedro_pipelines is None:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Kedro pipeline(s) "
                            f"{', '.join(reference.kedro_pipelines)}, but no pipeline_registry.py or pipelines/ directory is present."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to data-science pipeline targets that cannot be discovered from a fresh clone.",
                        suggested_fix="Add the Kedro pipeline registry/pipeline directory, or update the README command to match the current pipeline names.",
                    )
                )
                continue

            missing_pipelines = [
                pipeline for pipeline in reference.kedro_pipelines if pipeline not in kedro_pipelines
            ]
            if missing_pipelines:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Kedro pipeline(s) "
                            f"{', '.join(missing_pipelines)}, but the Kedro registry/directories do not define them."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to data-science pipeline targets that cannot be run.",
                        suggested_fix="Add the Kedro pipeline(s) or update the README command to match an existing pipeline name.",
                    )
                )
                continue
            continue

        if reference.package_manager == "prefect":
            prefect_flows = _prefect_flow_names(root)
            if prefect_flows is None:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Prefect flow "
                            f"'{reference.prefect_flow}', but no @flow definitions or prefect.yaml entrypoints were found."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to workflow orchestration targets that cannot be discovered from a fresh clone.",
                        suggested_fix="Add the Prefect flow definition/entrypoint, or update the README command to match an existing flow/deployment reference.",
                    )
                )
                continue

            if reference.prefect_flow not in prefect_flows:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Prefect flow "
                            f"'{reference.prefect_flow}', but local @flow definitions/entrypoints do not define it."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to workflow orchestration targets that cannot be run.",
                        suggested_fix="Add the Prefect flow or update the README command to match an existing flow/deployment reference.",
                    )
                )
                continue
            continue

        if reference.package_manager == "mlflow":
            project_dir = _mlflow_project_dir(root, reference.mlflow_project)
            if project_dir is None or not project_dir.exists():
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references MLflow project "
                            f"'{reference.mlflow_project}', but that path is not present."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to experiment packages that cannot be found from a fresh clone.",
                        suggested_fix="Add the MLflow project directory or update the README command to match the current experiment package path.",
                    )
                )
                continue

            entry_points = _mlflow_entry_points_from_project(project_dir)
            if entry_points is None:
                if _mlflow_entry_script_exists(project_dir, reference.mlflow_entry_point):
                    continue
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references MLflow entry point "
                            f"'{reference.mlflow_entry_point}', but no MLproject file or matching script is present."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to experiment entry points that cannot be discovered from a fresh clone.",
                        suggested_fix="Add MLproject with the documented entry point, add the matching script, or update the README command.",
                    )
                )
                continue

            if reference.mlflow_entry_point not in entry_points and not _mlflow_entry_script_exists(
                project_dir,
                reference.mlflow_entry_point,
            ):
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references MLflow entry point "
                            f"'{reference.mlflow_entry_point}', but MLproject does not define it."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to experiment entry points that cannot be run.",
                        suggested_fix="Add the MLflow entry point under entry_points in MLproject, or update the README command to match an existing entry point.",
                    )
                )
                continue
            continue

        if reference.package_manager == "dbt":
            dbt_models = _dbt_model_names(root)
            if dbt_models is None:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references dbt selector(s) "
                            f"{', '.join(reference.dbt_selectors)}, but no dbt project, model files, or selector files were found."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to transformation models that cannot be discovered from a fresh clone.",
                        suggested_fix="Add the dbt model/selector files or update the README command to match the current dbt project.",
                    )
                )
                continue

            model_names, model_paths, selector_names = dbt_models
            missing_selectors = [
                selector
                for selector in reference.dbt_selectors
                if not _dbt_selector_reference_exists(root, selector, model_names, model_paths, selector_names)
            ]
            if missing_selectors:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references dbt selector(s) "
                            f"{', '.join(missing_selectors)}, but local dbt models/selectors do not define them."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to transformation models or selector names that cannot be run.",
                        suggested_fix="Add the dbt model/selector or update the README command to match an existing model, path, or selectors.yml entry.",
                    )
                )
                continue
            continue

        if reference.package_manager == "great_expectations":
            gx_checkpoints = _gx_checkpoint_names(root)
            if gx_checkpoints is None:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Great Expectations checkpoint "
                            f"'{reference.gx_checkpoint}', but no checkpoint directory or config files were found."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to data-quality checkpoints that cannot be discovered from a fresh clone.",
                        suggested_fix="Add the Great Expectations checkpoint config under great_expectations/checkpoints or gx/checkpoints, or update the README command to match an existing checkpoint.",
                    )
                )
                continue

            if reference.gx_checkpoint not in gx_checkpoints:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Great Expectations checkpoint "
                            f"'{reference.gx_checkpoint}', but local checkpoint configs do not define it."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to data-quality checkpoints that cannot be run.",
                        suggested_fix="Add the Great Expectations checkpoint config or update the README command to match an existing checkpoint name.",
                    )
                )
                continue
            continue

        if reference.package_manager == "ploomber":
            ploomber_tasks = _ploomber_task_names(root)
            if ploomber_tasks is None:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Ploomber task(s) "
                            f"{', '.join(reference.ploomber_tasks)}, but no pipeline.yaml or pipeline.yml spec was found."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to pipeline tasks that cannot be discovered from a fresh clone.",
                        suggested_fix="Add the Ploomber pipeline spec or update the README command to match an existing task.",
                    )
                )
                continue

            missing_tasks = [
                task for task in reference.ploomber_tasks if task not in ploomber_tasks
            ]
            if missing_tasks:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Ploomber task(s) "
                            f"{', '.join(missing_tasks)}, but local Ploomber specs do not define them."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to pipeline tasks that cannot be run.",
                        suggested_fix="Add the Ploomber task to the pipeline spec or update the README command to match existing task names.",
                    )
                )
                continue
            continue

        if reference.package_manager == "luigi":
            luigi_tasks = _luigi_task_names(root, reference.luigi_module)
            if luigi_tasks is None:
                module_part = f" in module '{reference.luigi_module}'" if reference.luigi_module else ""
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Luigi task "
                            f"'{reference.luigi_task}'{module_part}, but no matching Luigi task definitions were found."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to pipeline tasks that cannot be discovered from a fresh clone.",
                        suggested_fix="Add the Luigi task class/module or update the README command to match an existing task.",
                    )
                )
                continue

            if not _luigi_task_exists(reference.luigi_task, luigi_tasks):
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Luigi task "
                            f"'{reference.luigi_task}', but local Luigi task classes do not define it."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to pipeline tasks that cannot be run.",
                        suggested_fix="Add the Luigi task class or update the README command to match an existing task class.",
                    )
                )
                continue
            continue

        if reference.package_manager == "meltano":
            meltano_jobs = _meltano_job_names(root)
            target_summary = ", ".join(reference.meltano_jobs)
            if meltano_jobs is None:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Meltano job(s) "
                            f"{target_summary}, but no meltano.yml or meltano.yaml project file was found."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to data pipeline jobs that cannot be discovered from a fresh clone.",
                        suggested_fix="Add meltano.yml with the documented job, or update the README command to match the current Meltano project.",
                    )
                )
                continue

            missing_jobs = [
                job for job in reference.meltano_jobs if job not in meltano_jobs
            ]
            if missing_jobs:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Meltano job(s) "
                            f"{', '.join(missing_jobs)}, but the Meltano project does not define them."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to data pipeline jobs that cannot be run.",
                        suggested_fix="Add the Meltano job under jobs: in meltano.yml, or update the README command to match an existing job.",
                    )
                )
                continue
            continue

        if reference.package_manager == "flyte":
            script_path = root / reference.flyte_script
            targets = _flyte_targets_from_script(script_path)
            if targets is None:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Flyte script "
                            f"'{reference.flyte_script}', but that file is not present."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to workflow scripts that are missing from a fresh clone.",
                        suggested_fix="Add the Flyte workflow/task script or update the README command to match the current path.",
                    )
                )
                continue

            if not _flyte_target_exists(reference.flyte_target, targets):
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Flyte workflow/task "
                            f"'{reference.flyte_target}', but the script does not define a matching Flyte-decorated function."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to workflow tasks that cannot be run.",
                        suggested_fix="Add the Flyte @task/@workflow function or update the README command to match an existing Flyte target.",
                    )
                )
                continue
            continue

        if reference.package_manager == "argo":
            workflow_path = root / reference.argo_workflow
            workflow_info = _argo_workflow_entrypoint_and_templates(workflow_path)
            if workflow_info is None:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Argo workflow file "
                            f"'{reference.argo_workflow}', but that file is not present."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to workflow manifests that are missing from a fresh clone.",
                        suggested_fix="Add the Argo Workflow/WorkflowTemplate YAML or update the README command to match the current manifest path.",
                    )
                )
                continue

            declared_entrypoint, templates = workflow_info
            entrypoint = reference.argo_entrypoint or declared_entrypoint
            if entrypoint and not templates:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Argo entrypoint "
                            f"'{entrypoint}', but no local template names were found in '{reference.argo_workflow}'."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to workflow templates that cannot be discovered from the checked-in manifest.",
                        suggested_fix="Add the named template under spec.templates, or update the README command/manifests to match the current Argo workflow.",
                    )
                )
                continue
            if entrypoint and entrypoint not in templates:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Argo entrypoint "
                            f"'{entrypoint}', but '{reference.argo_workflow}' does not define a matching template."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to workflow entrypoints that cannot be run.",
                        suggested_fix="Add the Argo template under spec.templates or update the README command to match an existing template name.",
                    )
                )
                continue
            continue

        if reference.package_manager == "tekton":
            if reference.tekton_file:
                tekton_file = root / reference.tekton_file
                if not tekton_file.exists():
                    findings.append(
                        Finding(
                            check_id="LC008",
                            title="README command references a missing path",
                            severity="medium",
                            category="onboarding",
                            file_path="README.md",
                            evidence=(
                                f"Command '{reference.command}' references Tekton manifest "
                                f"'{reference.tekton_file}', but that file is not present."
                            ),
                            why_it_matters="Setup instructions lose trust quickly when they point to pipeline manifests that are missing from a fresh clone.",
                            suggested_fix="Add the Tekton Pipeline/Task YAML or update the README command to match the current manifest path.",
                        )
                    )
                    continue
                if reference.tekton_name:
                    resources = _tekton_resources_from_file(tekton_file)
                    matching_kind = {
                        name for kind, name in resources if kind == reference.tekton_kind
                    }
                    if matching_kind and reference.tekton_name not in matching_kind:
                        findings.append(
                            Finding(
                                check_id="LC008",
                                title="README command references a missing path",
                                severity="medium",
                                category="onboarding",
                                file_path="README.md",
                                evidence=(
                                    f"Command '{reference.command}' references Tekton {reference.tekton_kind} "
                                    f"'{reference.tekton_name}', but '{reference.tekton_file}' does not define it."
                                ),
                                why_it_matters="Setup instructions lose trust quickly when they point to pipeline resources that cannot be started.",
                                suggested_fix="Add the named Tekton resource to the manifest or update the README command to match the checked-in resource name.",
                            )
                        )
                        continue
                continue

            tekton_names = _tekton_resource_names(root)
            if tekton_names is None:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Tekton {reference.tekton_kind} "
                            f"'{reference.tekton_name}', but no local Tekton Pipeline/Task manifests were found."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to cluster resources that cannot be discovered from the checked-in project.",
                        suggested_fix="Add local Tekton Pipeline/Task YAML or update the README command to include a current --filename manifest.",
                    )
                )
                continue
            if reference.tekton_name not in tekton_names.get(reference.tekton_kind, set()):
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Tekton {reference.tekton_kind} "
                            f"'{reference.tekton_name}', but local Tekton manifests do not define it."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to pipeline resources that cannot be started from checked-in manifests.",
                        suggested_fix="Add the Tekton Pipeline/Task manifest or update the README command to match an existing resource name.",
                    )
                )
                continue
            continue

        if reference.package_manager == "ray":
            if reference.ray_script and not _path_exists_at_root(root, reference.ray_script):
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Ray job script "
                            f"'{reference.ray_script}', but that file is not present."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to Ray job entrypoints that cannot be submitted from a fresh clone.",
                        suggested_fix="Add the Ray job script or update the README command to match the current Python entrypoint.",
                    )
                )
                continue

            if reference.ray_module and not _python_module_exists(root, reference.ray_module):
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Ray job module "
                            f"'{reference.ray_module}', but no matching module file or package is present."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to Ray job entrypoints that cannot be submitted from a fresh clone.",
                        suggested_fix="Add the Ray job module/package or update the README command to match the current Python entrypoint.",
                    )
                )
                continue
            continue

        if reference.package_manager == "dagger":
            module_label = reference.dagger_module or "."
            functions = _dagger_function_names(root, reference.dagger_module)
            if functions is None:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Dagger module "
                            f"'{module_label}', but no dagger.json is present."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to Dagger modules that cannot be loaded from a fresh clone.",
                        suggested_fix="Add dagger.json for the documented module path or update the README command to match the current Dagger module.",
                    )
                )
                continue

            if reference.dagger_function not in functions:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Dagger function "
                            f"'{reference.dagger_function}', but the local Dagger module does not define it."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to Dagger functions that cannot be called from a fresh clone.",
                        suggested_fix="Add the Dagger function to the module source or update the README command to match an existing function.",
                    )
                )
                continue
            continue

        if reference.package_manager == "bazel":
            missing_targets = [
                target for target in reference.bazel_targets if not _bazel_target_exists(root, target)
            ]
            if missing_targets:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Bazel target(s) "
                            f"{', '.join(missing_targets)}, but local BUILD files do not define them."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to Bazel targets that cannot be built, tested, or run from a fresh clone.",
                        suggested_fix="Add the BUILD/BUILD.bazel package target or update the README command to match an existing Bazel label.",
                    )
                )
                continue
            continue

        if reference.package_manager == "pants":
            missing_specs = [
                spec for spec in reference.pants_specs if not _pants_spec_exists(root, spec)
            ]
            if missing_specs:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Pants target spec(s) "
                            f"{', '.join(missing_specs)}, but local Pants BUILD files or source files do not define them."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to Pants specs that cannot be checked, tested, packaged, or run from a fresh clone.",
                        suggested_fix="Add the Pants BUILD target/source file or update the README command to match an existing Pants spec.",
                    )
                )
                continue
            continue

        if reference.package_manager == "nix":
            missing_installables = [
                installable
                for installable in reference.nix_installables
                if not _nix_installable_exists(root, reference.nix_command, installable)
            ]
            if missing_installables:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Nix flake output(s) "
                            f"{', '.join(missing_installables)}, but local flake.nix files do not define them."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to Nix flake outputs that cannot be checked, built, or run from a fresh clone.",
                        suggested_fix="Add the flake.nix output or update the README command to match an existing local Nix flake output.",
                    )
                )
                continue
            continue

        if reference.package_manager == "docker_compose":
            missing_project_dirs = [
                project_dir
                for project_dir in reference.docker_compose_project_dirs
                if not _docker_compose_project_dir_exists(root, project_dir)
            ]
            if missing_project_dirs:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Docker Compose project dir(s) "
                            f"{', '.join(missing_project_dirs)}, but they do not exist."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to Compose project directories that are missing from a fresh clone.",
                        suggested_fix="Add the Docker Compose project directory or update the README command to use an included local project directory.",
                    )
                )
                continue

            compose_files, missing_files = _docker_compose_files_for_reference(root, reference)
            if missing_files:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Docker Compose file(s) "
                            f"{', '.join(missing_files)}, but they do not exist."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to Compose files or services that cannot be loaded from a fresh clone.",
                        suggested_fix="Add the Docker Compose file or update the README command to use an existing compose.yaml/docker-compose.yml file.",
                    )
                )
                continue

            missing_env_files = [
                env_file
                for env_file in reference.docker_compose_env_files
                if not _docker_compose_env_file_exists(root, env_file)
            ]
            if missing_env_files:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Docker Compose env-file(s) "
                            f"{', '.join(missing_env_files)}, but they do not exist."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they depend on Compose environment files that are missing from a fresh clone.",
                        suggested_fix="Add the Docker Compose env-file or update the README command to use an included local env file.",
                    )
                )
                continue

            profile_names = _docker_compose_profile_names(compose_files)
            missing_profiles = [
                profile
                for profile in reference.docker_compose_profiles
                if profile not in profile_names
            ]
            if missing_profiles:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Docker Compose profile(s) "
                            f"{', '.join(missing_profiles)}, but local Compose files do not define them."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to Compose profiles that cannot be enabled from a fresh clone.",
                        suggested_fix="Add the Docker Compose service profile or update the README command to match an included Compose profile name.",
                    )
                )
                continue

            service_names = _docker_compose_service_names(compose_files)
            missing_services = [
                service
                for service in reference.docker_compose_services
                if service not in service_names
            ]
            if missing_services:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Docker Compose service(s) "
                            f"{', '.join(missing_services)}, but local Compose files do not define them."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to Compose services that cannot be started, run, or inspected from a fresh clone.",
                        suggested_fix="Add the Docker Compose service or update the README command to match an existing service name.",
                    )
                )
                continue
            continue

        if reference.package_manager == "docker_build":
            dockerfile = root / reference.docker_build_file
            if not dockerfile.exists():
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Dockerfile "
                            f"'{reference.docker_build_file}', but it does not exist."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to Docker build targets that cannot be built from a fresh clone.",
                        suggested_fix="Add the Dockerfile or update the README command to use an existing Dockerfile path.",
                    )
                )
                continue

            stage_names = _dockerfile_stage_names(dockerfile)
            if reference.docker_build_target not in stage_names:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Docker build stage "
                            f"'{reference.docker_build_target}', but {reference.docker_build_file} does not define it."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to Docker multi-stage build targets that do not exist.",
                        suggested_fix="Add the named Dockerfile stage with FROM ... AS <stage>, or update the README command to match an existing stage.",
                    )
                )
                continue
            continue

        if reference.package_manager == "helm":
            missing_charts = [
                chart_path
                for chart_path in reference.helm_chart_paths
                if not _helm_chart_exists(root, chart_path)
            ]
            if missing_charts:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Helm chart path(s) "
                            f"{', '.join(missing_charts)}, but local chart directories with Chart.yaml do not define them."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to Helm chart paths that cannot be rendered or installed from a fresh clone.",
                        suggested_fix="Add the Helm chart directory with Chart.yaml or update the README command to match an existing local chart path.",
                    )
                )
                continue
            continue

        if reference.package_manager == "kustomize":
            missing_paths = [
                kustomize_path
                for kustomize_path in reference.kustomize_paths
                if not _kustomization_exists(root, kustomize_path)
            ]
            if missing_paths:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Kustomize path(s) "
                            f"{', '.join(missing_paths)}, but local directories with kustomization.yaml do not define them."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to Kubernetes overlays that cannot be built from a fresh clone.",
                        suggested_fix="Add the Kustomize overlay/base directory with kustomization.yaml, or update the README command to match an existing local kustomization path.",
                    )
                )
                continue
            continue

        if reference.package_manager == "kubernetes":
            missing_manifests = [
                manifest_path
                for manifest_path in reference.kubernetes_manifest_paths
                if not _kubernetes_manifest_path_exists(root, manifest_path)
            ]
            if missing_manifests:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Kubernetes manifest path(s) "
                            f"{', '.join(missing_manifests)}, but included .yaml/.yml/.json files do not define them."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to deployment manifests that cannot be applied or diffed from a fresh clone.",
                        suggested_fix="Add the Kubernetes manifest file/directory or update the README command to match included local manifests.",
                    )
                )
                continue
            continue

        if reference.package_manager == "terraform":
            missing_dirs = [
                working_dir
                for working_dir in reference.terraform_working_dirs
                if not _terraform_working_dir_exists(root, working_dir)
            ]
            if missing_dirs:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Terraform working dir(s) "
                            f"{', '.join(missing_dirs)}, but local directories with .tf files do not define them."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to infrastructure directories that cannot be planned or validated from a fresh clone.",
                        suggested_fix="Add the Terraform working directory with .tf files or update the README command to match an existing local Terraform root module.",
                    )
                )
                continue
            continue

        if reference.package_manager == "pulumi":
            missing_dirs = [
                project_dir
                for project_dir in reference.pulumi_project_dirs
                if not _pulumi_project_dir_exists(root, project_dir)
            ]
            if missing_dirs:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Pulumi project dir(s) "
                            f"{', '.join(missing_dirs)}, but local directories with Pulumi.yaml do not define them."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to infrastructure project directories that cannot be previewed from a fresh clone.",
                        suggested_fix="Add the Pulumi project directory with Pulumi.yaml or update the README command to match an existing local Pulumi project.",
                    )
                )
                continue
            continue

        if reference.package_manager == "ansible":
            missing_playbooks = [
                playbook
                for playbook in reference.ansible_playbooks
                if not _ansible_playbook_exists(root, playbook)
            ]
            missing_inventories = [
                inventory
                for inventory in reference.ansible_inventories
                if not _ansible_inventory_exists(root, inventory)
            ]
            if missing_playbooks or missing_inventories:
                missing_parts: list[str] = []
                if missing_playbooks:
                    missing_parts.append(f"playbook(s) {', '.join(missing_playbooks)}")
                if missing_inventories:
                    missing_parts.append(f"inventory path(s) {', '.join(missing_inventories)}")
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Ansible "
                            f"{'; '.join(missing_parts)}, but included files/directories do not define them."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to automation playbooks or inventories that cannot be found from a fresh clone.",
                        suggested_fix="Add the Ansible playbook/inventory path or update the README command to match included local automation files.",
                    )
                )
                continue
            continue

        if reference.package_manager == "packer":
            missing_templates = [
                template
                for template in reference.packer_templates
                if not _packer_template_exists(root, template)
            ]
            if missing_templates:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Packer template path(s) "
                            f"{', '.join(missing_templates)}, but included .pkr.hcl/.pkr.json files do not define them."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to image-template paths that cannot be initialized, validated, or built from a fresh clone.",
                        suggested_fix="Add the Packer template file/directory or update the README command to match included local Packer templates.",
                    )
                )
                continue
            continue

        if reference.package_manager == "dagster":
            dagster_names = _dagster_names(root)
            if dagster_names is None:
                target_summary = ", ".join((*reference.dagster_jobs, *reference.dagster_assets))
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Dagster target(s) "
                            f"{target_summary}, but no Dagster job or asset definitions were found."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to orchestration targets that cannot be discovered from a fresh clone.",
                        suggested_fix="Add the Dagster job/asset definitions or update the README command to match existing definitions.",
                    )
                )
                continue

            dagster_jobs, dagster_assets = dagster_names
            missing_jobs = [
                job for job in reference.dagster_jobs if not _dagster_target_exists(job, dagster_jobs)
            ]
            missing_assets = [
                asset for asset in reference.dagster_assets if not _dagster_target_exists(asset, dagster_assets)
            ]
            if missing_jobs or missing_assets:
                missing_parts: list[str] = []
                if missing_jobs:
                    missing_parts.append(f"job(s) {', '.join(missing_jobs)}")
                if missing_assets:
                    missing_parts.append(f"asset(s) {', '.join(missing_assets)}")
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Dagster "
                            f"{'; '.join(missing_parts)}, but local Dagster definitions do not define them."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to orchestration jobs or assets that cannot be run.",
                        suggested_fix="Add the Dagster job/asset definitions or update the README command to match existing jobs and assets.",
                    )
                )
                continue
            continue

        if reference.package_manager == "airflow":
            airflow_names = _airflow_dag_task_names(root)
            if airflow_names is None:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Airflow DAG "
                            f"'{reference.airflow_dag_id}', but no Airflow DAG/task definitions were found."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to orchestration targets that cannot be discovered from a fresh clone.",
                        suggested_fix="Add the Airflow DAG/task definition, include the DAG file in the repo, or update the README command to match the current DAG ID.",
                    )
                )
                continue

            dag_ids, task_ids = airflow_names
            if reference.airflow_dag_id not in dag_ids:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Airflow DAG "
                            f"'{reference.airflow_dag_id}', but local DAG definitions do not define it."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to orchestration DAGs that cannot be run.",
                        suggested_fix="Add the Airflow DAG or update the README command to match an existing DAG ID.",
                    )
                )
                continue

            if reference.airflow_task_id and reference.airflow_task_id not in task_ids:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Airflow task "
                            f"'{reference.airflow_task_id}', but local task definitions do not define it."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to orchestration tasks that cannot be run.",
                        suggested_fix="Add the Airflow task or update the README command to match an existing task ID.",
                    )
                )
                continue
            continue

        if reference.package_manager == "metaflow":
            script_path = root / reference.metaflow_script
            steps = _metaflow_steps_from_script(script_path)
            if steps is None:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Metaflow script "
                            f"'{reference.metaflow_script}', but that file is not present."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to workflow scripts that are missing from a fresh clone.",
                        suggested_fix="Add the Metaflow flow script or update the README command to match the current script path.",
                    )
                )
                continue
            if reference.metaflow_step not in steps:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references Metaflow step "
                            f"'{reference.metaflow_step}', but the script does not define an @step with that name."
                        ),
                        why_it_matters="Debugging or resume instructions lose trust quickly when they point to workflow steps that cannot be resumed.",
                        suggested_fix="Add the Metaflow @step method or update the README command to match an existing step name.",
                    )
                )
                continue
            continue

        if reference.package_script:
            if reference.package_manager == "just":
                just_recipes = _just_recipes(root)
                if just_recipes is None:
                    findings.append(
                        Finding(
                            check_id="LC008",
                            title="README command references a missing path",
                            severity="medium",
                            category="onboarding",
                            file_path="README.md",
                            evidence=f"Command '{reference.command}' requires a justfile, but no justfile is present.",
                            why_it_matters="Setup instructions lose trust quickly when they point to task-runner aliases that cannot be run.",
                            suggested_fix="Add the justfile with the documented recipe, or update the README command to match the actual entrypoint.",
                        )
                    )
                    continue
                if reference.package_script not in just_recipes:
                    findings.append(
                        Finding(
                            check_id="LC008",
                            title="README command references a missing path",
                            severity="medium",
                            category="onboarding",
                            file_path="README.md",
                            evidence=(
                                f"Command '{reference.command}' references just recipe "
                                f"'{reference.package_script}', but the justfile does not define it."
                            ),
                            why_it_matters="Setup instructions lose trust quickly when they point to task-runner aliases that cannot be run.",
                            suggested_fix="Add the just recipe or update the README command to match an existing recipe.",
                        )
                    )
                    continue
                continue

            if reference.package_manager == "doit":
                doit_tasks = _doit_tasks(root)
                if doit_tasks is None:
                    findings.append(
                        Finding(
                            check_id="LC008",
                            title="README command references a missing path",
                            severity="medium",
                            category="onboarding",
                            file_path="README.md",
                            evidence=f"Command '{reference.command}' requires dodo.py, but no dodo.py is present.",
                            why_it_matters="Setup instructions lose trust quickly when they point to task-runner aliases that cannot be run.",
                            suggested_fix="Add dodo.py with the documented task, or update the README command to match the actual entrypoint.",
                        )
                    )
                    continue
                if reference.package_script not in doit_tasks:
                    findings.append(
                        Finding(
                            check_id="LC008",
                            title="README command references a missing path",
                            severity="medium",
                            category="onboarding",
                            file_path="README.md",
                            evidence=(
                                f"Command '{reference.command}' references doit task "
                                f"'{reference.package_script}', but dodo.py does not define it."
                            ),
                            why_it_matters="Setup instructions lose trust quickly when they point to task-runner aliases that cannot be run.",
                            suggested_fix="Add a task_<name>() function to dodo.py or update the README command to match an existing task.",
                        )
                    )
                    continue
                continue

            if reference.package_manager == "invoke":
                invoke_tasks = _invoke_tasks(root)
                if invoke_tasks is None:
                    findings.append(
                        Finding(
                            check_id="LC008",
                            title="README command references a missing path",
                            severity="medium",
                            category="onboarding",
                            file_path="README.md",
                            evidence=f"Command '{reference.command}' requires tasks.py, but no tasks.py is present.",
                            why_it_matters="Setup instructions lose trust quickly when they point to task-runner aliases that cannot be run.",
                            suggested_fix="Add tasks.py with the documented Invoke task, or update the README command to match the actual entrypoint.",
                        )
                    )
                    continue
                if reference.package_script not in invoke_tasks:
                    findings.append(
                        Finding(
                            check_id="LC008",
                            title="README command references a missing path",
                            severity="medium",
                            category="onboarding",
                            file_path="README.md",
                            evidence=(
                                f"Command '{reference.command}' references Invoke task "
                                f"'{reference.package_script}', but tasks.py does not define it."
                            ),
                            why_it_matters="Setup instructions lose trust quickly when they point to task-runner aliases that cannot be run.",
                            suggested_fix="Add an @task-decorated function to tasks.py or update the README command to match an existing Invoke task.",
                        )
                    )
                    continue
                continue

            if reference.package_manager == "rake":
                rake_tasks = _rake_tasks(root)
                if rake_tasks is None:
                    findings.append(
                        Finding(
                            check_id="LC008",
                            title="README command references a missing path",
                            severity="medium",
                            category="onboarding",
                            file_path="README.md",
                            evidence=f"Command '{reference.command}' requires a Rakefile, but no Rakefile is present.",
                            why_it_matters="Setup instructions lose trust quickly when they point to task-runner aliases that cannot be run.",
                            suggested_fix="Add a Rakefile with the documented task, or update the README command to match the actual entrypoint.",
                        )
                    )
                    continue
                if reference.package_script not in rake_tasks:
                    findings.append(
                        Finding(
                            check_id="LC008",
                            title="README command references a missing path",
                            severity="medium",
                            category="onboarding",
                            file_path="README.md",
                            evidence=(
                                f"Command '{reference.command}' references Rake task "
                                f"'{reference.package_script}', but the Rakefile does not define it."
                            ),
                            why_it_matters="Setup instructions lose trust quickly when they point to task-runner aliases that cannot be run.",
                            suggested_fix="Add the Rake task or update the README command to match an existing task.",
                        )
                    )
                    continue
                continue

            if reference.package_manager == "hatch":
                hatch_tasks = _hatch_tasks(root)
                if hatch_tasks is None:
                    findings.append(
                        Finding(
                            check_id="LC008",
                            title="README command references a missing path",
                            severity="medium",
                            category="onboarding",
                            file_path="README.md",
                            evidence=(
                                f"Command '{reference.command}' requires Hatch scripts, "
                                "but no pyproject.toml or hatch.toml manifest is present."
                            ),
                            why_it_matters="Setup instructions lose trust quickly when they point to task-runner aliases that cannot be run.",
                            suggested_fix="Add the Hatch manifest with the script, or update the README command to match the actual entrypoint.",
                        )
                    )
                    continue
                if reference.package_script not in hatch_tasks:
                    findings.append(
                        Finding(
                            check_id="LC008",
                            title="README command references a missing path",
                            severity="medium",
                            category="onboarding",
                            file_path="README.md",
                            evidence=(
                                f"Command '{reference.command}' references Hatch script "
                                f"'{reference.package_script}', but the Hatch manifest does not define it."
                            ),
                            why_it_matters="Setup instructions lose trust quickly when they point to task-runner aliases that cannot be run.",
                            suggested_fix="Add the Hatch script or update the README command to match an existing script.",
                        )
                    )
                    continue
                continue

            if reference.package_manager == "pdm":
                pdm_scripts = _pdm_scripts(root)
                if pdm_scripts is None:
                    findings.append(
                        Finding(
                            check_id="LC008",
                            title="README command references a missing path",
                            severity="medium",
                            category="onboarding",
                            file_path="README.md",
                            evidence=f"Command '{reference.command}' requires PDM scripts, but no pyproject.toml is present.",
                            why_it_matters="Setup instructions lose trust quickly when they point to task-runner aliases that cannot be run.",
                            suggested_fix="Add pyproject.toml with [tool.pdm.scripts], or update the README command to match the actual entrypoint.",
                        )
                    )
                    continue
                if reference.package_script not in pdm_scripts:
                    findings.append(
                        Finding(
                            check_id="LC008",
                            title="README command references a missing path",
                            severity="medium",
                            category="onboarding",
                            file_path="README.md",
                            evidence=(
                                f"Command '{reference.command}' references PDM script "
                                f"'{reference.package_script}', but pyproject.toml does not define it."
                            ),
                            why_it_matters="Setup instructions lose trust quickly when they point to task-runner aliases that cannot be run.",
                            suggested_fix="Add the PDM script under [tool.pdm.scripts] or update the README command to match an existing script.",
                        )
                    )
                    continue
                continue

            if reference.package_manager == "pixi":
                pixi_tasks = _pixi_tasks(root)
                if pixi_tasks is None:
                    findings.append(
                        Finding(
                            check_id="LC008",
                            title="README command references a missing path",
                            severity="medium",
                            category="onboarding",
                            file_path="README.md",
                            evidence=(
                                f"Command '{reference.command}' requires pixi tasks, "
                                "but no pyproject.toml or pixi.toml manifest is present."
                            ),
                            why_it_matters="Setup instructions lose trust quickly when they point to task-runner aliases that cannot be run.",
                            suggested_fix="Add the pixi manifest with the task, or update the README command to match the actual entrypoint.",
                        )
                    )
                    continue
                if reference.package_script not in pixi_tasks:
                    findings.append(
                        Finding(
                            check_id="LC008",
                            title="README command references a missing path",
                            severity="medium",
                            category="onboarding",
                            file_path="README.md",
                            evidence=(
                                f"Command '{reference.command}' references pixi task "
                                f"'{reference.package_script}', but the pixi manifest does not define it."
                            ),
                            why_it_matters="Setup instructions lose trust quickly when they point to task-runner aliases that cannot be run.",
                            suggested_fix="Add the pixi task or update the README command to match an existing task.",
                        )
                    )
                    continue
                continue

            if reference.package_manager == "taskipy":
                taskipy_tasks = _taskipy_tasks(root)
                taskfile_tasks = _taskfile_tasks(root)
                if (
                    (taskipy_tasks is not None and reference.package_script in taskipy_tasks)
                    or (taskfile_tasks is not None and reference.package_script in taskfile_tasks)
                ):
                    continue
                if taskipy_tasks is None and taskfile_tasks is None:
                    findings.append(
                        Finding(
                            check_id="LC008",
                            title="README command references a missing path",
                            severity="medium",
                            category="onboarding",
                            file_path="README.md",
                            evidence=(
                                f"Command '{reference.command}' requires taskipy tasks or a Taskfile, "
                                "but no pyproject.toml or Taskfile is present."
                            ),
                            why_it_matters="Setup instructions lose trust quickly when they point to task-runner aliases that cannot be run.",
                            suggested_fix="Add pyproject.toml with [tool.taskipy.tasks], add a Taskfile with the documented task, or update the README command to match the actual entrypoint.",
                        )
                    )
                    continue
                if taskipy_tasks is not None and taskfile_tasks is None:
                    findings.append(
                        Finding(
                            check_id="LC008",
                            title="README command references a missing path",
                            severity="medium",
                            category="onboarding",
                            file_path="README.md",
                            evidence=(
                                f"Command '{reference.command}' references taskipy task "
                                f"'{reference.package_script}', but pyproject.toml does not define it."
                            ),
                            why_it_matters="Setup instructions lose trust quickly when they point to task-runner aliases that cannot be run.",
                            suggested_fix="Add the taskipy task under [tool.taskipy.tasks] or update the README command to match an existing task.",
                        )
                    )
                    continue
                if taskipy_tasks is None and taskfile_tasks is not None:
                    findings.append(
                        Finding(
                            check_id="LC008",
                            title="README command references a missing path",
                            severity="medium",
                            category="onboarding",
                            file_path="README.md",
                            evidence=(
                                f"Command '{reference.command}' references Taskfile task "
                                f"'{reference.package_script}', but the Taskfile does not define it."
                            ),
                            why_it_matters="Setup instructions lose trust quickly when they point to task-runner aliases that cannot be run.",
                            suggested_fix="Add the Taskfile task or update the README command to match an existing task.",
                        )
                    )
                    continue
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references task "
                            f"'{reference.package_script}', but neither pyproject.toml taskipy tasks nor the Taskfile define it."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to task-runner aliases that cannot be run.",
                        suggested_fix="Add the task to [tool.taskipy.tasks] or the Taskfile, or update the README command to match an existing task.",
                    )
                )
                continue

            if reference.package_manager == "nox":
                nox_sessions = _nox_sessions(root)
                if nox_sessions is None:
                    findings.append(
                        Finding(
                            check_id="LC008",
                            title="README command references a missing path",
                            severity="medium",
                            category="onboarding",
                            file_path="README.md",
                            evidence=f"Command '{reference.command}' requires noxfile.py, but no noxfile.py is present.",
                            why_it_matters="Setup instructions lose trust quickly when they point to task-runner aliases that cannot be run.",
                            suggested_fix="Add noxfile.py with the documented session, or update the README command to match the actual entrypoint.",
                        )
                    )
                    continue
                if reference.package_script not in nox_sessions:
                    findings.append(
                        Finding(
                            check_id="LC008",
                            title="README command references a missing path",
                            severity="medium",
                            category="onboarding",
                            file_path="README.md",
                            evidence=(
                                f"Command '{reference.command}' references nox session "
                                f"'{reference.package_script}', but noxfile.py does not define it."
                            ),
                            why_it_matters="Setup instructions lose trust quickly when they point to task-runner aliases that cannot be run.",
                            suggested_fix="Add the nox session or update the README command to match an existing session.",
                        )
                    )
                    continue
                continue

            if reference.package_manager == "tox":
                tox_envs = _tox_envs(root)
                requested_envs = _split_tox_env_names(reference.package_script)
                if tox_envs is None:
                    findings.append(
                        Finding(
                            check_id="LC008",
                            title="README command references a missing path",
                            severity="medium",
                            category="onboarding",
                            file_path="README.md",
                            evidence=(
                                f"Command '{reference.command}' requires tox configuration, "
                                "but no tox.ini, setup.cfg, or pyproject.toml tox config is present."
                            ),
                            why_it_matters="Setup instructions lose trust quickly when they point to task-runner aliases that cannot be run.",
                            suggested_fix="Add tox configuration with the documented environment, or update the README command to match the actual entrypoint.",
                        )
                    )
                    continue
                declared_envs, has_generic_testenv = tox_envs
                if not requested_envs:
                    continue
                missing_envs = sorted(env for env in requested_envs if env not in declared_envs)
                if missing_envs and not (has_generic_testenv and not declared_envs):
                    findings.append(
                        Finding(
                            check_id="LC008",
                            title="README command references a missing path",
                            severity="medium",
                            category="onboarding",
                            file_path="README.md",
                            evidence=(
                                f"Command '{reference.command}' references tox environment(s) "
                                f"{', '.join(missing_envs)}, but the tox config does not define them."
                            ),
                            why_it_matters="Setup instructions lose trust quickly when they point to task-runner aliases that cannot be run.",
                            suggested_fix="Add the tox environment to env_list/envlist or [testenv:<name>], or update the README command to match an existing tox environment.",
                        )
                    )
                    continue
                continue

            if reference.package_manager == "snakemake":
                snakemake_targets = _snakemake_targets(root)
                if snakemake_targets is None:
                    findings.append(
                        Finding(
                            check_id="LC008",
                            title="README command references a missing path",
                            severity="medium",
                            category="onboarding",
                            file_path="README.md",
                            evidence=f"Command '{reference.command}' requires a Snakefile, but no Snakefile is present.",
                            why_it_matters="Setup instructions lose trust quickly when they point to workflow targets that cannot be run.",
                            suggested_fix="Add the Snakefile with the documented rule/output target, or update the README command to match the actual workflow entrypoint.",
                        )
                    )
                    continue
                if reference.package_script not in snakemake_targets and not _path_exists_at_root(
                    root, reference.package_script
                ):
                    findings.append(
                        Finding(
                            check_id="LC008",
                            title="README command references a missing path",
                            severity="medium",
                            category="onboarding",
                            file_path="README.md",
                            evidence=(
                                f"Command '{reference.command}' references Snakemake target "
                                f"'{reference.package_script}', but the Snakefile does not define it as a rule or simple output."
                            ),
                            why_it_matters="Setup instructions lose trust quickly when they point to workflow targets that cannot be run.",
                            suggested_fix="Add the Snakemake rule/output target or update the README command to match an existing workflow target.",
                        )
                    )
                    continue
                continue

            package_json = root / "package.json"
            if not package_json.exists():
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=f"Command '{reference.command}' requires package.json, but no package.json is present.",
                        why_it_matters="Setup instructions lose trust quickly when they point to task-runner scripts that cannot be run.",
                        suggested_fix="Add package.json or update the README command to match the actual entrypoint.",
                    )
                )
                continue
            if reference.package_script not in _package_json_scripts(root):
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=(
                            f"Command '{reference.command}' references package.json script "
                            f"'{reference.package_script}', but package.json does not define it."
                        ),
                        why_it_matters="Setup instructions lose trust quickly when they point to task-runner scripts that cannot be run.",
                        suggested_fix="Add the package.json script or update the README command to match an existing script.",
                    )
                )
                continue
            continue

        if reference.module_name:
            if _python_module_exists(root, reference.module_name):
                continue
            findings.append(
                Finding(
                    check_id="LC008",
                    title="README command references a missing path",
                    severity="medium",
                    category="onboarding",
                    file_path="README.md",
                    evidence=(
                        f"Command '{reference.command}' references Python module "
                        f"'{reference.module_name}', but no matching module file or package is present."
                    ),
                    why_it_matters="Setup instructions lose trust quickly when they point to entrypoints that cannot be run.",
                    suggested_fix="Add the Python module/package or update the README command to match the actual entrypoint.",
                )
            )
            continue

        if reference.make_target:
            makefile = _find_makefile(root)
            if not makefile:
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=f"Command '{reference.command}' requires a Makefile, but no Makefile is present.",
                        why_it_matters="Setup instructions lose trust quickly when they point to build targets that cannot be run.",
                        suggested_fix="Add the Makefile or update the README command to match the actual entrypoint.",
                    )
                )
                continue
            if reference.make_target not in _makefile_targets(makefile):
                findings.append(
                    Finding(
                        check_id="LC008",
                        title="README command references a missing path",
                        severity="medium",
                        category="onboarding",
                        file_path="README.md",
                        evidence=f"Command '{reference.command}' references Makefile target '{reference.make_target}', but {makefile.name} does not define it.",
                        why_it_matters="Setup instructions lose trust quickly when they point to build targets that cannot be run.",
                        suggested_fix="Add the Makefile target or update the README command to match an existing target.",
                    )
                )
                continue
            continue

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


def check_missing_dependency_setup_instructions(
    root: Path,
    notebooks: list[NotebookDocument],
    python_files: list[Path],
) -> list[Finding]:
    if not notebooks and not python_files:
        return []
    if not (root / "README.md").exists():
        return []

    manifests = sorted(name for name in MANIFEST_FILES if (root / name).exists())
    if not manifests:
        return []
    if readme_has_dependency_setup_instructions(root / "README.md"):
        return []

    manifest_text = ", ".join(manifests)
    return [
        Finding(
            check_id="LC021",
            title="Dependency setup step is undocumented",
            severity="medium",
            category="onboarding",
            file_path="README.md",
            evidence=f"Found dependency manifest(s) {manifest_text}, but README.md does not show an install/setup command.",
            why_it_matters="A README can show what to run and still fail handoff if the next person never installs the dependencies.",
            suggested_fix="Add a setup step before the run command, such as `python -m pip install -r requirements.txt`, `uv sync`, `poetry install`, or `conda env create -f environment.yml`.",
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
