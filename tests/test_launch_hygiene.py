from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_checker():
    script_path = Path("scripts/check_launch_hygiene.py")
    spec = importlib.util.spec_from_file_location("check_launch_hygiene", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_current_repo_passes_launch_hygiene() -> None:
    checker = _load_checker()

    assert checker.check_launch_hygiene(Path.cwd()) == []


def test_launch_hygiene_flags_missing_secret_ignore(tmp_path: Path) -> None:
    checker = _load_checker()
    (tmp_path / ".gitignore").write_text(".pytest_cache/\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "![preview](docs/assets/scorecard-preview.svg)\n"
        "No paid APIs. No inference bill. No backend secret to protect.\n",
        encoding="utf-8",
    )
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "launch-kit.md").write_text(
        "Repository name\nDescription\nTopics\nProfessor Outreach\nFounder Outreach\n",
        encoding="utf-8",
    )

    issues = checker.check_launch_hygiene(tmp_path)

    assert ".gitignore is missing required pattern: .env" in issues
    assert ".gitignore is missing required pattern: *.pem" in issues
