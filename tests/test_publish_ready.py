from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess


def _load_checker():
    script_path = Path("scripts/check_publish_ready.py")
    spec = importlib.util.spec_from_file_location("check_publish_ready", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)


def test_clean_main_repo_is_locally_publish_ready(tmp_path: Path) -> None:
    checker = _load_checker()
    _run(["git", "init", "-b", "main"], tmp_path)
    _run(["git", "config", "user.name", "labcheck test"], tmp_path)
    _run(["git", "config", "user.email", "labcheck@example.com"], tmp_path)
    (tmp_path / "README.md").write_text("# test\n", encoding="utf-8")
    _run(["git", "add", "README.md"], tmp_path)
    _run(["git", "commit", "-m", "initial"], tmp_path)

    assert checker.check_local_publish_ready(tmp_path) == []


def test_publish_commands_include_create_push_and_metadata() -> None:
    checker = _load_checker()

    commands = checker.publish_commands("ThomasAquinas14/labcheck")

    assert commands[0] == "python scripts/release_check.py"
    assert "gh repo create ThomasAquinas14/labcheck --public --source=. --remote=origin --push" in commands
    assert 'git tag -a v1 -m "labcheck GitHub Action v1"' in commands
    assert "git push origin v1" in commands
    assert any("gh repo edit ThomasAquinas14/labcheck" in command for command in commands)
    assert any("--add-topic" in command for command in commands)
    assert any("No-key reproducibility audits" in command for command in commands)
