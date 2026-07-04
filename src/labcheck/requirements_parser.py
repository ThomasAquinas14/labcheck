from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(slots=True)
class UnpinnedDependency:
    file_path: str
    dependency: str


@dataclass(slots=True)
class PythonRuntimeSpec:
    file_path: str
    spec: str


VERSION_OPERATORS = ("===", "==", ">=", "<=", "~=", "!=", ">", "<", "=")


def _strip_inline_comment(line: str) -> str:
    return line.split(" #", 1)[0].strip()


def _has_version_constraint(spec: str) -> bool:
    normalized = spec.strip()
    if " @ " in normalized or normalized.startswith(("git+", "http://", "https://")):
        return True
    return any(operator in normalized for operator in VERSION_OPERATORS)


def _is_requirement_line_unpinned(line: str) -> bool:
    if not line or line.startswith("#") or line.startswith(("-r ", "--")):
        return False
    if line.startswith("git+") or "://" in line:
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


def _runtime_from_pyproject(path: Path) -> PythonRuntimeSpec | None:
    try:
        data = tomllib.loads(_read_text(path))
    except tomllib.TOMLDecodeError:
        return None

    project = data.get("project", {})
    if isinstance(project, dict):
        requires_python = project.get("requires-python")
        if isinstance(requires_python, str) and requires_python.strip():
            return PythonRuntimeSpec(file_path="pyproject.toml", spec=requires_python.strip())

    poetry = data.get("tool", {}).get("poetry", {}) if isinstance(data.get("tool"), dict) else {}
    if isinstance(poetry, dict):
        dependencies = poetry.get("dependencies", {})
        if isinstance(dependencies, dict):
            python_spec = dependencies.get("python")
            if isinstance(python_spec, str) and python_spec.strip():
                return PythonRuntimeSpec(file_path="pyproject.toml", spec=python_spec.strip())
    return None


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


def find_python_runtime_spec(root: Path) -> PythonRuntimeSpec | None:
    for file_name in (".python-version", "runtime.txt"):
        path = root / file_name
        if not path.exists():
            continue
        value = _first_nonempty_line(path)
        if value:
            return PythonRuntimeSpec(file_path=file_name, spec=value)

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        runtime = _runtime_from_pyproject(pyproject)
        if runtime:
            return runtime

    pipfile = root / "Pipfile"
    if pipfile.exists():
        runtime = _runtime_from_pipfile(pipfile)
        if runtime:
            return runtime

    for file_name in ("environment.yml", "environment.yaml"):
        path = root / file_name
        if not path.exists():
            continue
        runtime = _runtime_from_environment(path)
        if runtime:
            return runtime

    setup_cfg = root / "setup.cfg"
    if setup_cfg.exists():
        runtime = _runtime_from_setup_cfg(setup_cfg)
        if runtime:
            return runtime
    return None


def find_unpinned_dependencies(root: Path) -> list[UnpinnedDependency]:
    checks = [
        ("requirements.txt", find_unpinned_requirements),
        ("pyproject.toml", find_unpinned_pyproject_dependencies),
        ("environment.yml", find_unpinned_environment_dependencies),
        ("environment.yaml", find_unpinned_environment_dependencies),
    ]

    findings: list[UnpinnedDependency] = []
    for file_path, finder in checks:
        path = root / file_path
        if not path.exists():
            continue
        for dependency in finder(path):
            findings.append(UnpinnedDependency(file_path=file_path, dependency=dependency))
    return findings
