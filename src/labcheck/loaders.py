from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import zipfile


def is_github_repo_url(target: str) -> bool:
    normalized = target.strip().lower()
    return normalized.startswith("https://github.com/") or normalized.startswith("http://github.com/")


def _safe_zip_member_path(extract_root: Path, member_name: str) -> Path:
    normalized_name = member_name.replace("\\", "/")
    parts = [part for part in normalized_name.split("/") if part]
    has_drive_prefix = len(parts[0]) >= 2 and parts[0][1] == ":" if parts else False
    if not parts or normalized_name.startswith("/") or has_drive_prefix or any(part in {".", ".."} for part in parts):
        raise ValueError(f"Unsafe zip member path: {member_name}")

    root = extract_root.resolve()
    destination = (root / Path(*parts)).resolve()
    if destination != root and root not in destination.parents:
        raise ValueError(f"Unsafe zip member path: {member_name}")
    return destination


def _is_zip_symlink(member: zipfile.ZipInfo) -> bool:
    file_type = (member.external_attr >> 16) & 0o170000
    return file_type == stat.S_IFLNK


def _safe_extract_zip(archive: zipfile.ZipFile, extract_root: Path) -> None:
    for member in archive.infolist():
        if _is_zip_symlink(member):
            raise ValueError(f"Refusing to extract zip symlink: {member.filename}")

        destination = _safe_zip_member_path(extract_root, member.filename)
        if member.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(member) as source, destination.open("wb") as target:
            shutil.copyfileobj(source, target)


@contextmanager
def prepared_target(target: str):
    raw_target = target.strip()

    if is_github_repo_url(raw_target):
        git_binary = shutil.which("git")
        if not git_binary:
            raise RuntimeError("Git is required to scan public GitHub repository URLs.")
        with tempfile.TemporaryDirectory(prefix="labcheck-git-") as temp_dir:
            repo_dir = Path(temp_dir) / "repo"
            subprocess.run(
                [git_binary, "clone", "--depth", "1", raw_target, str(repo_dir)],
                capture_output=True,
                text=True,
                check=True,
            )
            yield raw_target, repo_dir
        return

    path = Path(raw_target).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Target does not exist: {target}")

    if path.is_file() and path.suffix.lower() == ".zip":
        with tempfile.TemporaryDirectory(prefix="labcheck-zip-") as temp_dir:
            extract_root = Path(temp_dir) / "unzipped"
            extract_root.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(path) as archive:
                _safe_extract_zip(archive, extract_root)
            extracted_children = [child for child in extract_root.iterdir()]
            if len(extracted_children) == 1 and extracted_children[0].is_dir():
                yield raw_target, extracted_children[0]
            else:
                yield raw_target, extract_root
        return

    yield raw_target, path.resolve()
