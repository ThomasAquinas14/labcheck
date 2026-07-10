from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import uuid

import pytest


def _load_exporter():
    script_path = Path("scripts/export_standalone_repo.py")
    spec = importlib.util.spec_from_file_location("export_standalone_repo", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _repo_temp_dir(name: str) -> Path:
    return Path.cwd() / f".tmp-{name}-{uuid.uuid4().hex}"


def test_standalone_export_file_list_excludes_generated_and_cache_files() -> None:
    exporter = _load_exporter()
    repo_root = Path.cwd()
    output_dir = _repo_temp_dir("standalone-export-test")

    exported = {
        path.relative_to(repo_root).as_posix()
        for path in exporter.iter_export_files(repo_root, output_dir)
    }

    assert "README.md" in exported
    assert "action.yml" in exported
    assert "docs/assets/scorecard-preview.svg" in exported
    assert "docs/demo-video-script.md" in exported
    assert "docs/launch-kit.md" in exported
    assert "scripts/check_public_urls.py" in exported
    assert "scripts/export_standalone_repo.py" in exported
    assert "dist/site/index.html" not in exported
    assert not any("__pycache__" in path for path in exported)
    assert not any(path.startswith(".pytest_cache/") for path in exported)


def test_standalone_export_creates_clean_temporary_repo_copy() -> None:
    exporter = _load_exporter()
    repo_root = Path.cwd()
    output_dir = _repo_temp_dir("standalone-export-test")
    shutil.rmtree(output_dir, ignore_errors=True)

    try:
        exported_dir = exporter.export_standalone_repo(repo_root, output_dir)

        assert (exported_dir / "README.md").exists()
        assert (exported_dir / "action.yml").exists()
        assert (exported_dir / "docs" / "demo-video-script.md").exists()
        assert (exported_dir / "docs" / "launch-kit.md").exists()
        assert (exported_dir / "docs" / "assets" / "scorecard-preview.svg").exists()
        assert not (exported_dir / "dist").exists()
        assert not (exported_dir / ".pytest_cache").exists()
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)


def test_standalone_export_refuses_non_temporary_output_inside_repo() -> None:
    exporter = _load_exporter()
    repo_root = Path.cwd()

    with pytest.raises(ValueError, match="non-temporary output"):
        exporter.export_standalone_repo(repo_root, repo_root / "standalone-export")
