from __future__ import annotations

from pathlib import Path
import stat
import subprocess
import zipfile

from labcheck.loaders import is_github_repo_url, prepared_target


def test_prepared_target_extracts_zip_archive(tmp_path: Path) -> None:
    source_dir = Path("examples/broken-repo")
    zip_path = tmp_path / "broken-repo.zip"

    with zipfile.ZipFile(zip_path, "w") as archive:
        for path in source_dir.rglob("*"):
            if path.is_file():
                archive.write(path, Path("broken-repo") / path.relative_to(source_dir))

    with prepared_target(str(zip_path)) as (display_target, resolved_root):
        assert display_target.endswith("broken-repo.zip")
        assert (resolved_root / "requirements.txt").exists()
        assert (resolved_root / "notebooks" / "analysis.ipynb").exists()


def test_prepared_target_rejects_zip_path_traversal(tmp_path: Path) -> None:
    zip_path = tmp_path / "unsafe.zip"
    outside_path = tmp_path / "escape.txt"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("../escape.txt", "bad")

    try:
        with prepared_target(str(zip_path)):
            pass
    except ValueError as error:
        assert "Unsafe zip member path" in str(error)
    else:
        raise AssertionError("Expected unsafe zip member to be rejected")
    assert not outside_path.exists()


def test_prepared_target_rejects_windows_zip_path_traversal(tmp_path: Path) -> None:
    zip_path = tmp_path / "unsafe-windows.zip"
    outside_path = tmp_path / "escape.txt"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("..\\escape.txt", "bad")

    try:
        with prepared_target(str(zip_path)):
            pass
    except ValueError as error:
        assert "Unsafe zip member path" in str(error)
    else:
        raise AssertionError("Expected unsafe zip member to be rejected")
    assert not outside_path.exists()


def test_prepared_target_rejects_absolute_zip_member(tmp_path: Path) -> None:
    zip_path = tmp_path / "absolute.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("C:/Users/hp/escape.txt", "bad")

    try:
        with prepared_target(str(zip_path)):
            pass
    except ValueError as error:
        assert "Unsafe zip member path" in str(error)
    else:
        raise AssertionError("Expected absolute zip member to be rejected")


def test_prepared_target_rejects_zip_symlink(tmp_path: Path) -> None:
    zip_path = tmp_path / "symlink.zip"
    member = zipfile.ZipInfo("link")
    member.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(member, "target")

    try:
        with prepared_target(str(zip_path)):
            pass
    except ValueError as error:
        assert "Refusing to extract zip symlink" in str(error)
    else:
        raise AssertionError("Expected zip symlink to be rejected")


def test_prepared_target_clones_public_github_url(monkeypatch, tmp_path: Path) -> None:
    def fake_run(command, capture_output, text, check):
        repo_dir = Path(command[-1])
        repo_dir.mkdir(parents=True, exist_ok=True)
        (repo_dir / "README.md").write_text("# demo\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("labcheck.loaders.shutil.which", lambda _: "git")
    monkeypatch.setattr("labcheck.loaders.subprocess.run", fake_run)

    with prepared_target("https://github.com/example/repo") as (display_target, resolved_root):
        assert display_target == "https://github.com/example/repo"
        assert (resolved_root / "README.md").exists()


def test_is_github_repo_url_recognizes_supported_urls() -> None:
    assert is_github_repo_url("https://github.com/example/repo")
    assert is_github_repo_url("http://github.com/example/repo")
    assert not is_github_repo_url("https://gitlab.com/example/repo")
