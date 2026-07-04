from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from pathlib import Path
import tomllib

DEFAULT_CONFIG_NAME = ".labcheck.toml"


@dataclass(slots=True)
class LabcheckConfig:
    exclude: list[str] = field(default_factory=list)
    disabled_checks: set[str] = field(default_factory=set)


def load_config(path: Path) -> LabcheckConfig:
    data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    exclude = data.get("exclude", [])
    if not isinstance(exclude, list) or not all(isinstance(pattern, str) for pattern in exclude):
        raise ValueError("Invalid labcheck config: exclude must be a list of strings")
    disabled_checks = data.get("disabled_checks", [])
    if not isinstance(disabled_checks, list) or not all(isinstance(check_id, str) for check_id in disabled_checks):
        raise ValueError("Invalid labcheck config: disabled_checks must be a list of strings")
    return LabcheckConfig(
        exclude=exclude,
        disabled_checks={check_id.strip().upper() for check_id in disabled_checks if check_id.strip()},
    )


def discover_config(repo_root: Path, config_path: str | None = None) -> LabcheckConfig:
    if config_path:
        path = Path(config_path).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"Labcheck config does not exist: {config_path}")
        return load_config(path)

    default_path = repo_root / DEFAULT_CONFIG_NAME
    if default_path.exists():
        return load_config(default_path)
    return LabcheckConfig()


def _normalize_pattern(pattern: str) -> str:
    return pattern.replace("\\", "/").lstrip("./")


def _matches_exclude_pattern(relative_path: str, pattern: str) -> bool:
    normalized_pattern = _normalize_pattern(pattern)
    normalized_path = relative_path.replace("\\", "/").lstrip("./")
    if not normalized_pattern:
        return False
    if normalized_pattern.endswith("/"):
        prefix = normalized_pattern.rstrip("/")
        return normalized_path == prefix or normalized_path.startswith(prefix + "/")
    if normalized_pattern.endswith("/**"):
        prefix = normalized_pattern[:-3].rstrip("/")
        return normalized_path == prefix or normalized_path.startswith(prefix + "/")
    if "/" not in normalized_pattern:
        return any(fnmatchcase(part, normalized_pattern) for part in normalized_path.split("/"))
    return fnmatchcase(normalized_path, normalized_pattern)


def is_excluded(path: Path, repo_root: Path, config: LabcheckConfig) -> bool:
    try:
        relative_path = path.relative_to(repo_root).as_posix()
    except ValueError:
        relative_path = path.name
    return any(_matches_exclude_pattern(relative_path, pattern) for pattern in config.exclude)


def is_check_disabled(check_id: str, config: LabcheckConfig) -> bool:
    return check_id.upper() in config.disabled_checks
