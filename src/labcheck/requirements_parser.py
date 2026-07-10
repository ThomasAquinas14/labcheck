from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path
import re
import shlex
import tomllib
from urllib.parse import unquote, urlparse


@dataclass(slots=True)
class UnpinnedDependency:
    file_path: str
    dependency: str


@dataclass(slots=True)
class PythonRuntimeSpec:
    file_path: str
    spec: str


@dataclass(slots=True)
class MissingRequirementInclude:
    file_path: str
    referenced_path: str
    directive: str


@dataclass(slots=True)
class MissingLocalDependencyPath:
    file_path: str
    dependency: str
    referenced_path: str


@dataclass(slots=True)
class VCSDependency:
    file_path: str
    dependency: str
    reason: str


VERSION_OPERATORS = ("===", "==", ">=", "<=", "~=", "!=", ">", "<", "=")
VCS_SCHEMES = ("git+", "hg+", "svn+", "bzr+")
VCS_DEPENDENCY_PATTERN = re.compile(r"\b(?:git|hg|svn|bzr)\+[^\s\"'<>]+", re.IGNORECASE)
MOVING_VCS_REFS = {
    "canary",
    "current",
    "dev",
    "develop",
    "development",
    "edge",
    "head",
    "latest",
    "main",
    "master",
    "nightly",
    "rolling",
    "snapshot",
    "stable",
    "trunk",
}
ROOT_REQUIREMENT_FILES = (
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-test.txt",
    "constraints.txt",
)
ROOT_REQUIREMENT_PATTERNS = (
    "*requirements*.txt",
    "*constraints*.txt",
    "requirements/*.txt",
    "constraints/*.txt",
)
ENVIRONMENT_FILES = ("environment.yml", "environment.yaml")
DOCKER_PYTHON_IMAGE_PATTERN = re.compile(
    r"^\s*FROM\s+(?:--platform=\S+\s+)?(?:\S+/)?python:([^\s]+)",
    re.IGNORECASE,
)
RUNTIME_DOCKERFILE_SKIP_DIRS = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "dist",
    "htmlcov",
    "node_modules",
    "site-packages",
    "venv",
}
FILE_URL_PATTERN = re.compile(r"\bfile:[^\s,;'\"\])]+", re.IGNORECASE)
LOCAL_ARCHIVE_SUFFIXES = (
    ".tar",
    ".tar.gz",
    ".tgz",
    ".zip",
    ".whl",
)
LOCAL_PATH_VALUE_OPTIONS = {
    "-e": "editable",
    "--editable": "editable",
    "-f": "find-links",
    "--find-links": "find-links",
}
LOCAL_PATH_VALUE_PREFIXES = {
    "--editable=": "editable",
    "--find-links=": "find-links",
}
PACKAGE_NAME_PATTERN = re.compile(r"^\s*([A-Za-z0-9_.-]+)")


def _strip_inline_comment(line: str) -> str:
    return line.split(" #", 1)[0].strip()


def _normalize_dependency_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower().strip()


def _dependency_name_from_spec(spec: str) -> str | None:
    stripped = _strip_inline_comment(spec.strip())
    if not stripped or stripped.startswith(("#", "-", "$", "%", "<")):
        return None
    if stripped.startswith(("git+", "http://", "https://", "file:")):
        egg_match = re.search(r"[#&]egg=([A-Za-z0-9_.-]+)", stripped)
        return _normalize_dependency_name(egg_match.group(1)) if egg_match else None
    if " @ " in stripped:
        name = stripped.split(" @ ", 1)[0].strip()
        return _normalize_dependency_name(name) if name else None

    match = PACKAGE_NAME_PATTERN.match(stripped)
    if not match:
        return None
    name = match.group(1).split("[", 1)[0]
    if name.lower() in {"python", "pip"}:
        return None
    return _normalize_dependency_name(name)


def _has_version_constraint(spec: str) -> bool:
    normalized = spec.strip()
    if " @ " in normalized or normalized.startswith((*VCS_SCHEMES, "http://", "https://")):
        return True
    return any(operator in normalized for operator in VERSION_OPERATORS)


def _is_requirement_line_unpinned(line: str) -> bool:
    if not line or line.startswith("#") or line.startswith("-") or _requirement_include_from_line(line) is not None:
        return False
    if line.startswith(VCS_SCHEMES) or "://" in line:
        return False
    return not _has_version_constraint(line)


def find_unpinned_requirements(path: Path) -> list[str]:
    unpinned: list[str] = []
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = _strip_inline_comment(raw_line.strip())
        if _is_requirement_line_unpinned(line):
            unpinned.append(line)
    return unpinned


def _find_unpinned_pyproject_project_dependencies(data: dict) -> list[str]:
    unpinned: list[str] = []
    project = data.get("project", {})
    if not isinstance(project, dict):
        return unpinned

    dependencies = project.get("dependencies", [])
    if isinstance(dependencies, list):
        for dependency in dependencies:
            if isinstance(dependency, str) and _is_requirement_line_unpinned(dependency):
                unpinned.append(dependency)

    optional_dependencies = project.get("optional-dependencies", {})
    if isinstance(optional_dependencies, dict):
        for group_dependencies in optional_dependencies.values():
            if not isinstance(group_dependencies, list):
                continue
            for dependency in group_dependencies:
                if isinstance(dependency, str) and _is_requirement_line_unpinned(dependency):
                    unpinned.append(dependency)
    return unpinned


def _is_poetry_dependency_unpinned(name: str, value: object) -> bool:
    if name.lower() == "python":
        return False
    if isinstance(value, str):
        return value.strip() in {"", "*"}
    if isinstance(value, dict):
        if any(key in value for key in ("path", "git", "url")):
            return False
        version = value.get("version")
        return not isinstance(version, str) or version.strip() in {"", "*"}
    return False


def _find_unpinned_poetry_dependencies(data: dict) -> list[str]:
    unpinned: list[str] = []
    poetry = data.get("tool", {}).get("poetry", {}) if isinstance(data.get("tool"), dict) else {}
    if not isinstance(poetry, dict):
        return unpinned

    for section_name in ("dependencies", "dev-dependencies"):
        dependencies = poetry.get(section_name, {})
        if not isinstance(dependencies, dict):
            continue
        for name, value in dependencies.items():
            if _is_poetry_dependency_unpinned(str(name), value):
                unpinned.append(str(name))

    groups = poetry.get("group", {})
    if isinstance(groups, dict):
        for group in groups.values():
            if not isinstance(group, dict):
                continue
            dependencies = group.get("dependencies", {})
            if not isinstance(dependencies, dict):
                continue
            for name, value in dependencies.items():
                if _is_poetry_dependency_unpinned(str(name), value):
                    unpinned.append(str(name))
    return unpinned


def find_unpinned_pyproject_dependencies(path: Path) -> list[str]:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except tomllib.TOMLDecodeError:
        return []
    return _find_unpinned_pyproject_project_dependencies(data) + _find_unpinned_poetry_dependencies(data)


def find_unpinned_environment_dependencies(path: Path) -> list[str]:
    unpinned: list[str] = []
    current_section = ""
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if raw_line == raw_line.lstrip() and stripped.endswith(":"):
            current_section = stripped[:-1]
            continue
        if current_section != "dependencies" or not stripped.startswith("- "):
            continue

        dependency = _strip_inline_comment(stripped[2:].strip())
        if not dependency or dependency in {"pip", "pip:"} or dependency.endswith(":"):
            continue
        if _is_requirement_line_unpinned(dependency):
            unpinned.append(dependency)
    return unpinned


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _first_nonempty_line(path: Path) -> str | None:
    for line in _read_text(path).splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return None


def _runtime_specs_from_pyproject(path: Path) -> list[PythonRuntimeSpec]:
    try:
        data = tomllib.loads(_read_text(path))
    except tomllib.TOMLDecodeError:
        return []

    specs: list[PythonRuntimeSpec] = []
    project = data.get("project", {})
    if isinstance(project, dict):
        requires_python = project.get("requires-python")
        if isinstance(requires_python, str) and requires_python.strip():
            specs.append(PythonRuntimeSpec(file_path="pyproject.toml", spec=requires_python.strip()))

    poetry = data.get("tool", {}).get("poetry", {}) if isinstance(data.get("tool"), dict) else {}
    if isinstance(poetry, dict):
        dependencies = poetry.get("dependencies", {})
        if isinstance(dependencies, dict):
            python_spec = dependencies.get("python")
            if isinstance(python_spec, str) and python_spec.strip():
                specs.append(PythonRuntimeSpec(file_path="pyproject.toml", spec=python_spec.strip()))
    return specs


def _runtime_from_pyproject(path: Path) -> PythonRuntimeSpec | None:
    specs = _runtime_specs_from_pyproject(path)
    return specs[0] if specs else None


def _runtime_from_pipfile(path: Path) -> PythonRuntimeSpec | None:
    try:
        data = tomllib.loads(_read_text(path))
    except tomllib.TOMLDecodeError:
        return None

    requires = data.get("requires", {})
    if not isinstance(requires, dict):
        return None
    for key in ("python_full_version", "python_version"):
        value = requires.get(key)
        if isinstance(value, str) and value.strip():
            return PythonRuntimeSpec(file_path="Pipfile", spec=value.strip())
    return None


def _runtime_from_environment(path: Path) -> PythonRuntimeSpec | None:
    current_section = ""
    for raw_line in _read_text(path).splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if raw_line == raw_line.lstrip() and stripped.endswith(":"):
            current_section = stripped[:-1]
            continue
        if current_section != "dependencies" or not stripped.startswith("- "):
            continue

        dependency = _strip_inline_comment(stripped[2:].strip())
        if dependency.lower().startswith("python") and _has_version_constraint(dependency):
            return PythonRuntimeSpec(file_path=path.name, spec=dependency)
    return None


def _runtime_from_setup_cfg(path: Path) -> PythonRuntimeSpec | None:
    parser = configparser.ConfigParser()
    parser.read(path, encoding="utf-8-sig")
    if not parser.has_option("options", "python_requires"):
        return None
    value = parser.get("options", "python_requires").strip()
    if not value:
        return None
    return PythonRuntimeSpec(file_path="setup.cfg", spec=value)


def _is_runtime_dockerfile(path: Path) -> bool:
    name = path.name.lower()
    return name == "dockerfile" or name.startswith("dockerfile.") or name.endswith(".dockerfile")


def _should_skip_runtime_dockerfile(path: Path, root: Path) -> bool:
    try:
        relative_parts = path.relative_to(root).parts
    except ValueError:
        return True
    return any(part in RUNTIME_DOCKERFILE_SKIP_DIRS for part in relative_parts[:-1])


def _iter_runtime_dockerfiles(root: Path) -> list[Path]:
    dockerfiles: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or not _is_runtime_dockerfile(path):
            continue
        if _should_skip_runtime_dockerfile(path, root):
            continue
        dockerfiles.append(path)
    return sorted(dockerfiles, key=lambda path: path.relative_to(root).as_posix().lower())


def _runtime_specs_from_dockerfile(path: Path, root: Path) -> list[PythonRuntimeSpec]:
    specs: list[PythonRuntimeSpec] = []
    file_path = _repo_relative(path, root)
    for raw_line in _read_text(path).splitlines():
        match = DOCKER_PYTHON_IMAGE_PATTERN.match(raw_line)
        if match:
            specs.append(PythonRuntimeSpec(file_path=file_path, spec=f"python:{match.group(1)}"))
    return specs


def find_python_runtime_specs(root: Path) -> list[PythonRuntimeSpec]:
    specs: list[PythonRuntimeSpec] = []
    for file_name in (".python-version", "runtime.txt"):
        path = root / file_name
        if not path.exists():
            continue
        value = _first_nonempty_line(path)
        if value:
            specs.append(PythonRuntimeSpec(file_path=file_name, spec=value))

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        specs.extend(_runtime_specs_from_pyproject(pyproject))

    pipfile = root / "Pipfile"
    if pipfile.exists():
        runtime = _runtime_from_pipfile(pipfile)
        if runtime:
            specs.append(runtime)

    for file_name in ("environment.yml", "environment.yaml"):
        path = root / file_name
        if not path.exists():
            continue
        runtime = _runtime_from_environment(path)
        if runtime:
            specs.append(runtime)

    setup_cfg = root / "setup.cfg"
    if setup_cfg.exists():
        runtime = _runtime_from_setup_cfg(setup_cfg)
        if runtime:
            specs.append(runtime)

    for dockerfile in _iter_runtime_dockerfiles(root):
        specs.extend(_runtime_specs_from_dockerfile(dockerfile, root))
    return specs


def find_python_runtime_spec(root: Path) -> PythonRuntimeSpec | None:
    specs = find_python_runtime_specs(root)
    if specs:
        return specs[0]
    return None


def find_unpinned_dependencies(root: Path) -> list[UnpinnedDependency]:
    findings: list[UnpinnedDependency] = []
    root = root.resolve()
    for path in _iter_requirement_files(root):
        try:
            file_path = _repo_relative(path.resolve(), root)
        except ValueError:
            continue
        for dependency in find_unpinned_requirements(path):
            findings.append(UnpinnedDependency(file_path=file_path, dependency=dependency))

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        for dependency in find_unpinned_pyproject_dependencies(pyproject):
            findings.append(UnpinnedDependency(file_path="pyproject.toml", dependency=dependency))

    for file_path in ENVIRONMENT_FILES:
        path = root / file_path
        if not path.exists():
            continue
        for dependency in find_unpinned_environment_dependencies(path):
            findings.append(UnpinnedDependency(file_path=file_path, dependency=dependency))
    return findings


def _repo_relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _requirement_include_from_line(line: str) -> tuple[str, str] | None:
    stripped = _strip_inline_comment(line.strip())
    if not stripped or stripped.startswith("#"):
        return None
    try:
        tokens = shlex.split(stripped, comments=True, posix=True)
    except ValueError:
        tokens = stripped.split()
    if not tokens:
        return None

    first = tokens[0]
    if first in {"-r", "--requirement", "-c", "--constraint"} and len(tokens) >= 2:
        return first, tokens[1]
    for directive in ("--requirement=", "--constraint="):
        if first.startswith(directive):
            return directive.rstrip("="), first.removeprefix(directive)
    for directive in ("-r", "-c"):
        if first.startswith(directive) and len(first) > len(directive):
            return directive, first[len(directive) :]
    return None


def _is_local_requirement_include(reference: str) -> bool:
    lowered = reference.lower()
    return not (
        "://" in lowered
        or lowered.startswith(("git+", "http://", "https://"))
        or reference.startswith(("$", "%", "<"))
    )


def _is_external_or_placeholder_reference(reference: str) -> bool:
    lowered = reference.lower()
    return (
        "://" in lowered and not lowered.startswith("file:")
        or lowered.startswith(("git+", "http://", "https://"))
        or reference.startswith(("$", "%", "<", "{"))
        or "${" in reference
        or "%" in reference
    )


def _strip_environment_marker(reference: str) -> str:
    return reference.split(";", 1)[0].strip()


def _strip_requirement_extras(reference: str) -> str:
    stripped = reference.strip()
    if stripped.endswith("]") and "[" in stripped:
        candidate = stripped[: stripped.rfind("[")]
        if candidate:
            return candidate
    return stripped


def _file_url_to_path(reference: str) -> str | None:
    parsed = urlparse(reference)
    if parsed.scheme.lower() != "file":
        return None
    if parsed.netloc and parsed.netloc.lower() not in {"", "localhost"}:
        return f"//{parsed.netloc}{unquote(parsed.path)}"
    return unquote(parsed.path)


def _normalize_local_dependency_reference(reference: str) -> str:
    stripped = _strip_environment_marker(reference.strip().strip("'\""))
    if stripped.lower().startswith("file:"):
        file_path = _file_url_to_path(stripped)
        if file_path is not None:
            stripped = file_path
    return _strip_requirement_extras(stripped)


def _looks_like_local_dependency_path(reference: str) -> bool:
    normalized = _normalize_local_dependency_reference(reference)
    if not normalized or _is_external_or_placeholder_reference(normalized):
        return False
    if normalized.startswith("-"):
        return False
    lowered = normalized.lower()
    if lowered.startswith(("file:", "./", "../", ".\\", "..\\", "/", "~")):
        return True
    if "/" in normalized or "\\" in normalized:
        return True
    return lowered.endswith(LOCAL_ARCHIVE_SUFFIXES)


def _local_dependency_references_from_requirement_line(line: str) -> list[tuple[str, str]]:
    stripped = _strip_inline_comment(line.strip())
    if not stripped or stripped.startswith("#") or _requirement_include_from_line(stripped) is not None:
        return []
    try:
        tokens = shlex.split(stripped, comments=True, posix=True)
    except ValueError:
        tokens = stripped.split()
    if not tokens:
        return []

    references: list[tuple[str, str]] = []
    first = tokens[0]
    if first in LOCAL_PATH_VALUE_OPTIONS and len(tokens) >= 2:
        references.append((LOCAL_PATH_VALUE_OPTIONS[first], tokens[1]))
    for prefix, dependency_type in LOCAL_PATH_VALUE_PREFIXES.items():
        if first.startswith(prefix):
            references.append((dependency_type, first.removeprefix(prefix)))

    for match in FILE_URL_PATTERN.finditer(stripped):
        references.append(("file", match.group(0)))

    if _looks_like_local_dependency_path(first):
        references.append(("path", first))

    unique: dict[tuple[str, str], tuple[str, str]] = {}
    for dependency_type, reference in references:
        normalized = _normalize_local_dependency_reference(reference)
        if normalized and not _is_external_or_placeholder_reference(normalized):
            unique[(dependency_type, normalized)] = (dependency_type, normalized)
    return list(unique.values())


def _missing_local_dependency(
    root: Path,
    manifest_path: Path,
    dependency: str,
    referenced_path: str,
) -> MissingLocalDependencyPath | None:
    normalized = _normalize_local_dependency_reference(referenced_path)
    if not normalized or not _looks_like_local_dependency_path(normalized):
        return None
    if _is_external_or_placeholder_reference(normalized):
        return None

    candidate = Path(normalized)
    if not candidate.is_absolute():
        candidate = manifest_path.parent / candidate
    candidate = candidate.resolve()
    try:
        file_path = _repo_relative(manifest_path.resolve(), root)
    except ValueError:
        return None
    if _is_within_root(candidate, root) and candidate.exists():
        return None
    return MissingLocalDependencyPath(
        file_path=file_path,
        dependency=dependency,
        referenced_path=referenced_path,
    )


def _root_requirement_files(root: Path) -> list[Path]:
    candidates = [root / file_name for file_name in ROOT_REQUIREMENT_FILES]
    for pattern in ROOT_REQUIREMENT_PATTERNS:
        candidates.extend(root.glob(pattern))
    unique = {path.resolve(): path for path in candidates if path.exists() and path.is_file()}
    return [unique[key] for key in sorted(unique)]


def _environment_requirement_files(root: Path) -> list[Path]:
    candidates: list[Path] = []
    for file_name in ENVIRONMENT_FILES:
        environment_path = root / file_name
        if not environment_path.exists() or not environment_path.is_file():
            continue
        for _, referenced_path in _environment_pip_requirement_includes(environment_path):
            if not _is_local_requirement_include(referenced_path):
                continue
            candidate = (environment_path.parent / referenced_path).resolve()
            if _is_within_root(candidate, root) and candidate.is_file():
                candidates.append(candidate)
    unique = {path.resolve(): path for path in candidates}
    return [unique[key] for key in sorted(unique)]


def _requirement_seed_files(root: Path) -> list[Path]:
    candidates = _root_requirement_files(root)
    candidates.extend(_environment_requirement_files(root))
    unique = {path.resolve(): path for path in candidates if path.exists() and path.is_file()}
    return [unique[key] for key in sorted(unique)]


def _leading_space_count(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _environment_pip_entries(path: Path) -> list[tuple[int, str]]:
    entries: list[tuple[int, str]] = []
    current_section = ""
    pip_parent_indent: int | None = None

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if raw_line == raw_line.lstrip() and stripped.endswith(":"):
            current_section = stripped[:-1]
            pip_parent_indent = None
            continue
        if current_section != "dependencies" or not stripped.startswith("- "):
            continue

        indent = _leading_space_count(raw_line)
        dependency = _strip_inline_comment(stripped[2:].strip())
        if pip_parent_indent is not None and indent > pip_parent_indent:
            if dependency:
                entries.append((line_number, dependency))
            continue
        if pip_parent_indent is not None and indent <= pip_parent_indent:
            pip_parent_indent = None
        if dependency.lower() == "pip:":
            pip_parent_indent = indent
    return entries


def _environment_pip_requirement_includes(path: Path) -> list[tuple[str, str]]:
    includes: list[tuple[str, str]] = []
    for _, dependency in _environment_pip_entries(path):
        include = _requirement_include_from_line(dependency)
        if include is not None:
            includes.append(include)
    return includes


def _iter_requirement_files(root: Path) -> list[Path]:
    root = root.resolve()
    queue = _requirement_seed_files(root)
    seen: set[Path] = set()
    ordered: list[Path] = []

    while queue:
        path = queue.pop(0).resolve()
        if path in seen:
            continue
        seen.add(path)
        if not path.is_file():
            continue
        ordered.append(path)

        try:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        except (FileNotFoundError, UnicodeDecodeError):
            continue

        for raw_line in lines:
            include = _requirement_include_from_line(raw_line)
            if include is None:
                continue
            _, referenced_path = include
            if not _is_local_requirement_include(referenced_path):
                continue
            candidate = (path.parent / referenced_path).resolve()
            if _is_within_root(candidate, root) and candidate.is_file() and candidate not in seen:
                queue.append(candidate)
    return ordered


def _clean_vcs_spec(spec: str) -> str:
    return spec.strip().strip("'\"").rstrip(".,)]}")


def _vcs_url_without_prefix(spec: str) -> str:
    cleaned = _clean_vcs_spec(spec)
    without_fragment = cleaned.split("#", 1)[0].split(";", 1)[0].strip()
    lowered = without_fragment.lower()
    for scheme in VCS_SCHEMES:
        if lowered.startswith(scheme):
            return without_fragment[len(scheme) :]
    return without_fragment


def _vcs_ref_from_spec(spec: str) -> str | None:
    url = _vcs_url_without_prefix(spec)
    parsed = urlparse(url)
    path = parsed.path or url
    if "@" in path:
        return path.rsplit("@", 1)[1].split("?", 1)[0].strip("/")

    git_separator = re.search(r"\.git@([^?#]+)", url, re.IGNORECASE)
    if git_separator:
        return git_separator.group(1).split("?", 1)[0].strip("/")
    return None


def _is_moving_vcs_ref(reference: str) -> bool:
    normalized = reference.strip().strip("'\"").lower()
    if normalized.startswith("refs/heads/"):
        return True
    if normalized.startswith(("origin/", "remotes/")):
        return True
    return normalized in MOVING_VCS_REFS


def _vcs_dependency_reason(spec: str) -> str | None:
    reference = _vcs_ref_from_spec(spec)
    if not reference:
        return "has no @ref pin"
    if _is_moving_vcs_ref(reference):
        return f"uses moving ref '{reference}'"
    return None


def _vcs_dependencies_from_text(file_path: str, text: str) -> list[VCSDependency]:
    findings: list[VCSDependency] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = _strip_inline_comment(raw_line.strip())
        if not stripped or stripped.startswith("#"):
            continue
        for match in VCS_DEPENDENCY_PATTERN.finditer(stripped):
            spec = _clean_vcs_spec(match.group(0))
            reason = _vcs_dependency_reason(spec)
            if reason:
                findings.append(
                    VCSDependency(
                        file_path=file_path,
                        dependency=f"line {line_number}: {spec}",
                        reason=reason,
                    )
                )
    return findings


def _vcs_dependencies_from_requirements(root: Path) -> list[VCSDependency]:
    root = root.resolve()
    findings: list[VCSDependency] = []

    for path in _iter_requirement_files(root):
        try:
            file_path = _repo_relative(path, root)
        except ValueError:
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (FileNotFoundError, UnicodeDecodeError):
            continue

        findings.extend(_vcs_dependencies_from_text(file_path, text))
    return findings


def _vcs_dependencies_from_environment(root: Path) -> list[VCSDependency]:
    root = root.resolve()
    findings: list[VCSDependency] = []
    for file_name in ENVIRONMENT_FILES:
        path = root / file_name
        if not path.exists() or not path.is_file():
            continue
        for line_number, dependency in _environment_pip_entries(path):
            if _requirement_include_from_line(dependency) is not None:
                continue
            for match in VCS_DEPENDENCY_PATTERN.finditer(dependency):
                spec = _clean_vcs_spec(match.group(0))
                reason = _vcs_dependency_reason(spec)
                if reason:
                    findings.append(
                        VCSDependency(
                            file_path=file_name,
                            dependency=f"line {line_number}: {spec}",
                            reason=reason,
                        )
                    )
    return findings


def _poetry_git_dependency_reason(value: dict) -> str | None:
    rev = value.get("rev")
    if isinstance(rev, str) and rev.strip():
        return None

    tag = value.get("tag")
    if isinstance(tag, str) and tag.strip():
        return f"uses moving tag '{tag.strip()}'" if _is_moving_vcs_ref(tag) else None

    branch = value.get("branch")
    if isinstance(branch, str) and branch.strip():
        return f"uses moving branch '{branch.strip()}'"

    return "has no rev or tag pin"


def _poetry_git_dependencies_from_section(file_path: str, section: object) -> list[VCSDependency]:
    if not isinstance(section, dict):
        return []

    findings: list[VCSDependency] = []
    for name, value in section.items():
        if not isinstance(value, dict):
            continue
        git_url = value.get("git")
        if not isinstance(git_url, str) or not git_url.strip():
            continue
        reason = _poetry_git_dependency_reason(value)
        if not reason:
            continue
        findings.append(
            VCSDependency(
                file_path=file_path,
                dependency=f"{name} -> {git_url.strip()}",
                reason=reason,
            )
        )
    return findings


def _poetry_git_dependencies_from_pyproject(path: Path, root: Path) -> list[VCSDependency]:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except tomllib.TOMLDecodeError:
        return []

    try:
        file_path = _repo_relative(path.resolve(), root.resolve())
    except ValueError:
        return []

    poetry = data.get("tool", {}).get("poetry", {}) if isinstance(data.get("tool"), dict) else {}
    if not isinstance(poetry, dict):
        return []

    findings: list[VCSDependency] = []
    findings.extend(_poetry_git_dependencies_from_section(file_path, poetry.get("dependencies", {})))
    findings.extend(_poetry_git_dependencies_from_section(file_path, poetry.get("dev-dependencies", {})))

    groups = poetry.get("group", {})
    if isinstance(groups, dict):
        for group in groups.values():
            if isinstance(group, dict):
                findings.extend(_poetry_git_dependencies_from_section(file_path, group.get("dependencies", {})))
    return findings


def _vcs_dependencies_from_pyproject(root: Path) -> list[VCSDependency]:
    path = root / "pyproject.toml"
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return []

    try:
        file_path = _repo_relative(path.resolve(), root.resolve())
    except ValueError:
        return []

    findings = _vcs_dependencies_from_text(file_path, text)
    findings.extend(_poetry_git_dependencies_from_pyproject(path, root))
    return findings


def find_unpinned_vcs_dependencies(root: Path) -> list[VCSDependency]:
    """Return VCS dependencies that use missing or moving refs."""
    root = root.resolve()
    findings = _vcs_dependencies_from_requirements(root)
    findings.extend(_vcs_dependencies_from_environment(root))
    findings.extend(_vcs_dependencies_from_pyproject(root))

    unique: dict[tuple[str, str, str], VCSDependency] = {}
    for item in findings:
        unique[(item.file_path, item.dependency, item.reason)] = item
    return list(unique.values())


def vcs_dependency_issue_reason(spec: str) -> str | None:
    """Return why a VCS dependency spec is mutable, or None when it is sufficiently pinned."""
    return _vcs_dependency_reason(spec)


def find_missing_requirement_includes(root: Path) -> list[MissingRequirementInclude]:
    """Return local requirements/constraints includes that cannot be resolved."""
    root = root.resolve()
    queue = _requirement_seed_files(root)
    seen: set[Path] = set()
    missing: list[MissingRequirementInclude] = []

    for file_name in ENVIRONMENT_FILES:
        environment_path = root / file_name
        if not environment_path.exists() or not environment_path.is_file():
            continue
        for directive, referenced_path in _environment_pip_requirement_includes(environment_path):
            if not _is_local_requirement_include(referenced_path):
                continue
            candidate = (environment_path.parent / referenced_path).resolve()
            if not _is_within_root(candidate, root) or not candidate.is_file():
                missing.append(
                    MissingRequirementInclude(
                        file_path=file_name,
                        referenced_path=referenced_path,
                        directive=directive,
                    )
                )
                continue
            if candidate not in seen:
                queue.append(candidate)

    while queue:
        path = queue.pop(0).resolve()
        if path in seen:
            continue
        seen.add(path)
        try:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        except (FileNotFoundError, UnicodeDecodeError):
            continue

        try:
            file_path = _repo_relative(path, root)
        except ValueError:
            continue

        for raw_line in lines:
            include = _requirement_include_from_line(raw_line)
            if include is None:
                continue
            directive, referenced_path = include
            if not _is_local_requirement_include(referenced_path):
                continue
            candidate = (path.parent / referenced_path).resolve()
            if not _is_within_root(candidate, root) or not candidate.is_file():
                missing.append(
                    MissingRequirementInclude(
                        file_path=file_path,
                        referenced_path=referenced_path,
                        directive=directive,
                    )
                )
                continue
            if candidate.is_file() and candidate not in seen:
                queue.append(candidate)
    return missing


def _project_dependency_strings_from_pyproject(data: dict) -> list[str]:
    dependencies: list[str] = []
    project = data.get("project", {})
    if not isinstance(project, dict):
        return dependencies

    project_dependencies = project.get("dependencies", [])
    if isinstance(project_dependencies, list):
        dependencies.extend(dependency for dependency in project_dependencies if isinstance(dependency, str))

    optional_dependencies = project.get("optional-dependencies", {})
    if isinstance(optional_dependencies, dict):
        for group_dependencies in optional_dependencies.values():
            if not isinstance(group_dependencies, list):
                continue
            dependencies.extend(dependency for dependency in group_dependencies if isinstance(dependency, str))
    return dependencies


def _declared_dependency_names_from_pyproject(path: Path) -> set[str]:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except tomllib.TOMLDecodeError:
        return set()

    names: set[str] = set()
    for dependency in _project_dependency_strings_from_pyproject(data):
        name = _dependency_name_from_spec(dependency)
        if name:
            names.add(name)

    poetry = data.get("tool", {}).get("poetry", {}) if isinstance(data.get("tool"), dict) else {}
    if isinstance(poetry, dict):
        for section_name in ("dependencies", "dev-dependencies"):
            section = poetry.get(section_name, {})
            if isinstance(section, dict):
                names.update(_normalize_dependency_name(str(name)) for name in section if str(name).lower() != "python")
        groups = poetry.get("group", {})
        if isinstance(groups, dict):
            for group in groups.values():
                if not isinstance(group, dict):
                    continue
                dependencies = group.get("dependencies", {})
                if isinstance(dependencies, dict):
                    names.update(
                        _normalize_dependency_name(str(name))
                        for name in dependencies
                        if str(name).lower() != "python"
                    )
    return names


def _poetry_path_dependencies_from_section(section: object) -> list[tuple[str, str]]:
    dependencies: list[tuple[str, str]] = []
    if not isinstance(section, dict):
        return dependencies
    for name, value in section.items():
        if not isinstance(value, dict):
            continue
        path = value.get("path")
        if isinstance(path, str) and path.strip():
            dependencies.append((str(name), path.strip()))
    return dependencies


def _poetry_path_dependencies_from_pyproject(data: dict) -> list[tuple[str, str]]:
    poetry = data.get("tool", {}).get("poetry", {}) if isinstance(data.get("tool"), dict) else {}
    if not isinstance(poetry, dict):
        return []

    dependencies: list[tuple[str, str]] = []
    dependencies.extend(_poetry_path_dependencies_from_section(poetry.get("dependencies", {})))
    dependencies.extend(_poetry_path_dependencies_from_section(poetry.get("dev-dependencies", {})))

    groups = poetry.get("group", {})
    if isinstance(groups, dict):
        for group in groups.values():
            if isinstance(group, dict):
                dependencies.extend(_poetry_path_dependencies_from_section(group.get("dependencies", {})))
    return dependencies


def _missing_local_dependency_paths_from_requirements(root: Path) -> list[MissingLocalDependencyPath]:
    missing: list[MissingLocalDependencyPath] = []

    for path in _iter_requirement_files(root):
        try:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        except (FileNotFoundError, UnicodeDecodeError):
            continue

        for raw_line in lines:
            for dependency, referenced_path in _local_dependency_references_from_requirement_line(raw_line):
                missing_dependency = _missing_local_dependency(root, path, dependency, referenced_path)
                if missing_dependency:
                    missing.append(missing_dependency)
    return missing


def _missing_local_dependency_paths_from_pyproject(root: Path) -> list[MissingLocalDependencyPath]:
    path = root / "pyproject.toml"
    if not path.exists():
        return []
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except tomllib.TOMLDecodeError:
        return []

    missing: list[MissingLocalDependencyPath] = []
    for dependency in _project_dependency_strings_from_pyproject(data):
        for dependency_type, referenced_path in _local_dependency_references_from_requirement_line(dependency):
            missing_dependency = _missing_local_dependency(root, path, dependency_type, referenced_path)
            if missing_dependency:
                missing.append(missing_dependency)

    for dependency_name, referenced_path in _poetry_path_dependencies_from_pyproject(data):
        missing_dependency = _missing_local_dependency(root, path, dependency_name, referenced_path)
        if missing_dependency:
            missing.append(missing_dependency)
    return missing


def _missing_local_dependency_paths_from_environment(root: Path) -> list[MissingLocalDependencyPath]:
    root = root.resolve()
    missing: list[MissingLocalDependencyPath] = []
    for file_name in ENVIRONMENT_FILES:
        path = root / file_name
        if not path.exists() or not path.is_file():
            continue
        for _, dependency in _environment_pip_entries(path):
            for dependency_type, referenced_path in _local_dependency_references_from_requirement_line(dependency):
                missing_dependency = _missing_local_dependency(root, path, dependency_type, referenced_path)
                if missing_dependency:
                    missing.append(missing_dependency)
    return missing


def find_missing_local_dependency_paths(root: Path) -> list[MissingLocalDependencyPath]:
    """Return local package, wheelhouse, or file dependencies that are not in the scanned repo."""
    root = root.resolve()
    missing = _missing_local_dependency_paths_from_requirements(root)
    missing.extend(_missing_local_dependency_paths_from_environment(root))
    missing.extend(_missing_local_dependency_paths_from_pyproject(root))

    unique: dict[tuple[str, str, str], MissingLocalDependencyPath] = {}
    for item in missing:
        unique[(item.file_path, item.dependency, item.referenced_path)] = item
    return list(unique.values())


def _declared_dependency_names_from_requirements(root: Path) -> set[str]:
    names: set[str] = set()

    for path in _iter_requirement_files(root):
        try:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        except (FileNotFoundError, UnicodeDecodeError):
            continue

        for raw_line in lines:
            if _requirement_include_from_line(raw_line) is not None:
                continue
            name = _dependency_name_from_spec(raw_line)
            if name:
                names.add(name)
    return names


def _declared_dependency_names_from_environment(path: Path) -> set[str]:
    names: set[str] = set()
    current_section = ""
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if raw_line == raw_line.lstrip() and stripped.endswith(":"):
            current_section = stripped[:-1]
            continue
        if current_section != "dependencies" or not stripped.startswith("- "):
            continue

        dependency = _strip_inline_comment(stripped[2:].strip())
        if not dependency or dependency in {"pip", "pip:"} or dependency.endswith(":"):
            continue
        name = _dependency_name_from_spec(dependency)
        if name:
            names.add(name)
    return names


def find_declared_dependency_names(root: Path) -> set[str]:
    """Return normalized dependency package names declared by supported manifests."""
    root = root.resolve()
    names = _declared_dependency_names_from_requirements(root)

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        names.update(_declared_dependency_names_from_pyproject(pyproject))

    for file_name in ("environment.yml", "environment.yaml"):
        environment = root / file_name
        if environment.exists():
            names.update(_declared_dependency_names_from_environment(environment))
    return names


def _is_within_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
