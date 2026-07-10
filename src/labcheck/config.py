from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from pathlib import Path
import tomllib

from .check_catalog import CHECK_BY_ID

DEFAULT_CONFIG_NAME = ".labcheck.toml"

VALID_PROFILES = {"default", "education"}
VALID_SEVERITIES = {"high", "medium", "low"}

EDUCATION_PROFILE_SEVERITY_OVERRIDES = {
    "LC001": "medium",
    "LC002": "medium",
}

EDUCATION_PROFILE_FINDING_LIMITS = {
    "LC001": 25,
    "LC002": 25,
    "LC010": 25,
    "LC014": 25,
    "LC015": 25,
}


@dataclass(slots=True)
class IgnoredFinding:
    check_id: str
    path: str
    reason: str = ""


@dataclass(slots=True)
class LabcheckConfig:
    profile: str = "default"
    exclude: list[str] = field(default_factory=list)
    disabled_checks: set[str] = field(default_factory=set)
    ignored_findings: list[IgnoredFinding] = field(default_factory=list)
    severity_overrides: dict[str, str] = field(default_factory=dict)
    finding_limits: dict[str, int] = field(default_factory=dict)


def _load_ignored_findings(data: dict) -> list[IgnoredFinding]:
    ignored_findings = data.get("ignored_findings", [])
    if not isinstance(ignored_findings, list):
        raise ValueError("Invalid labcheck config: ignored_findings must be a list of tables")

    parsed: list[IgnoredFinding] = []
    for index, item in enumerate(ignored_findings, start=1):
        if not isinstance(item, dict):
            raise ValueError("Invalid labcheck config: each ignored_findings entry must be a table")
        check_id = item.get("check_id")
        path = item.get("path")
        reason = item.get("reason", "")
        if not isinstance(check_id, str) or not check_id.strip():
            raise ValueError(f"Invalid labcheck config: ignored_findings entry {index} needs a check_id")
        if not isinstance(path, str) or not path.strip():
            raise ValueError(f"Invalid labcheck config: ignored_findings entry {index} needs a path")
        if not isinstance(reason, str):
            raise ValueError(f"Invalid labcheck config: ignored_findings entry {index} reason must be a string")
        parsed.append(IgnoredFinding(check_id=check_id.strip().upper(), path=path.strip(), reason=reason.strip()))
    return parsed


def _load_severity_overrides(data: dict) -> dict[str, str]:
    severity_overrides = data.get("severity_overrides", {})
    if not isinstance(severity_overrides, dict):
        raise ValueError("Invalid labcheck config: severity_overrides must be a table")
    parsed: dict[str, str] = {}
    for check_id, severity in severity_overrides.items():
        if not isinstance(check_id, str) or not check_id.strip():
            raise ValueError("Invalid labcheck config: severity_overrides keys must be check IDs")
        normalized_check_id = check_id.strip().upper()
        if normalized_check_id not in CHECK_BY_ID:
            raise ValueError(f"Invalid labcheck config: unknown check ID in severity_overrides: {check_id}")
        if not isinstance(severity, str) or severity.lower() not in VALID_SEVERITIES:
            raise ValueError(
                "Invalid labcheck config: severity_overrides values must be one of high, medium, or low"
            )
        parsed[normalized_check_id] = severity.lower()
    return parsed


def _load_finding_limits(data: dict) -> dict[str, int]:
    finding_limits = data.get("finding_limits", {})
    if not isinstance(finding_limits, dict):
        raise ValueError("Invalid labcheck config: finding_limits must be a table")
    parsed: dict[str, int] = {}
    for check_id, limit in finding_limits.items():
        if not isinstance(check_id, str) or not check_id.strip():
            raise ValueError("Invalid labcheck config: finding_limits keys must be check IDs")
        normalized_check_id = check_id.strip().upper()
        if normalized_check_id not in CHECK_BY_ID:
            raise ValueError(f"Invalid labcheck config: unknown check ID in finding_limits: {check_id}")
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError("Invalid labcheck config: finding_limits values must be positive integers")
        parsed[normalized_check_id] = limit
    return parsed


def load_config(path: Path) -> LabcheckConfig:
    data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    profile = data.get("profile", "default")
    if not isinstance(profile, str) or profile.strip().lower() not in VALID_PROFILES:
        raise ValueError("Invalid labcheck config: profile must be one of default or education")
    exclude = data.get("exclude", [])
    if not isinstance(exclude, list) or not all(isinstance(pattern, str) for pattern in exclude):
        raise ValueError("Invalid labcheck config: exclude must be a list of strings")
    disabled_checks = data.get("disabled_checks", [])
    if not isinstance(disabled_checks, list) or not all(isinstance(check_id, str) for check_id in disabled_checks):
        raise ValueError("Invalid labcheck config: disabled_checks must be a list of strings")
    return LabcheckConfig(
        profile=profile.strip().lower(),
        exclude=exclude,
        disabled_checks={check_id.strip().upper() for check_id in disabled_checks if check_id.strip()},
        ignored_findings=_load_ignored_findings(data),
        severity_overrides=_load_severity_overrides(data),
        finding_limits=_load_finding_limits(data),
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


def is_finding_ignored(check_id: str, file_path: str, config: LabcheckConfig) -> bool:
    normalized_check_id = check_id.strip().upper()
    return any(
        ignored.check_id == normalized_check_id and _matches_exclude_pattern(file_path, ignored.path)
        for ignored in config.ignored_findings
    )


def effective_severity_overrides(config: LabcheckConfig) -> dict[str, str]:
    overrides: dict[str, str] = {}
    if config.profile == "education":
        overrides.update(EDUCATION_PROFILE_SEVERITY_OVERRIDES)
    overrides.update(config.severity_overrides)
    return overrides


def effective_finding_limits(config: LabcheckConfig) -> dict[str, int]:
    limits: dict[str, int] = {}
    if config.profile == "education":
        limits.update(EDUCATION_PROFILE_FINDING_LIMITS)
    limits.update(config.finding_limits)
    return limits
