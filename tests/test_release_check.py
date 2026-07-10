from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
import uuid


def _load_release_check():
    script_path = Path("scripts/release_check.py")
    spec = importlib.util.spec_from_file_location("release_check", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_release_check_lists_public_launch_gates(capsys) -> None:
    release_check = _load_release_check()

    exit_code = release_check.main(["--list"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "pytest -q" in captured.out
    assert "labcheck.cli doctor . --config .labcheck.toml" in captured.out
    assert "labcheck.cli scorecard examples/clean-notebook" in captured.out
    assert "labcheck.cli issue examples/clean-notebook --output .tmp-release-issue-draft.md" in captured.out
    assert "scripts/build_sample_audits.py" in captured.out
    assert "scripts/build_static_site.py" in captured.out
    assert "scripts/check_static_export.py" in captured.out
    assert "scripts/check_compare_smoke.py" in captured.out
    assert "labcheck.cli scan . --config .labcheck.toml" in captured.out
    assert "examples/clean-notebook --min-score 100" in captured.out
    assert "labcheck.cli pack examples/clean-notebook --output-dir .tmp-release-audit-pack" in captured.out
    assert "--zip" in captured.out
    assert "examples/broken-repo --fail-on high" in captured.out
    assert "# expect 2" in captured.out


def test_release_check_models_expected_failure_for_broken_fixture() -> None:
    release_check = _load_release_check()
    checks = release_check.build_checks("python")

    expected_failure_checks = [check for check in checks if check.expected_exit_code != 0]

    assert len(expected_failure_checks) == 1
    assert expected_failure_checks[0].expected_exit_code == 2
    assert "examples/broken-repo" in " ".join(expected_failure_checks[0].command)


def test_compare_smoke_script_passes_and_cleans_temp_files() -> None:
    script = Path("scripts/check_compare_smoke.py")
    temp_prefix = f".tmp-release-compare-test-{uuid.uuid4().hex}-"

    import subprocess

    result = subprocess.run(
        [sys.executable, str(script)],
        check=False,
        capture_output=True,
        env={**os.environ, "LABCHECK_COMPARE_TMP_PREFIX": temp_prefix},
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "labcheck compare smoke OK" in result.stdout
    assert not list(Path.cwd().glob(f"{temp_prefix}*"))


def test_release_check_cleans_only_tmp_release_artifacts(tmp_path: Path) -> None:
    release_check = _load_release_check()
    cleanup_dir = tmp_path / ".tmp-release-audit-pack"
    cleanup_dir.mkdir()
    (cleanup_dir / "README.md").write_text("temporary", encoding="utf-8")

    release_check._cleanup_generated_path(tmp_path, ".tmp-release-audit-pack")

    assert not cleanup_dir.exists()


def test_release_checklist_documents_static_public_launch() -> None:
    checklist = Path("docs/release-checklist.md").read_text(encoding="utf-8")

    assert "python scripts/release_check.py" in checklist
    assert "python scripts/release_check.py --verbose" in checklist
    assert "install/target preflight command passes" in checklist
    assert "static site export builds" in checklist
    assert "python scripts/check_static_export.py" in checklist
    assert "python scripts/check_compare_smoke.py" in checklist
    assert "python scripts/check_public_urls.py https://thomasaquinas14.github.io/labcheck/" in checklist
    assert "sample audits are regenerated" in checklist
    assert "score of 100" in checklist
    assert "Marketplace branding" in checklist
    assert "uses: ThomasAquinas14/labcheck@v1" in checklist
    assert "labcheck target-fit examples/broken-repo --audience founder" in checklist
    assert "labcheck issue examples/broken-repo --output labcheck-issue-draft.md" in checklist
    assert "expected failure" in checklist
