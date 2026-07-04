from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import sys


@dataclass(frozen=True)
class ReleaseCheck:
    name: str
    command: tuple[str, ...]
    expected_exit_code: int = 0
    cleanup_path: str | None = None
    cleanup_zip_path: str | None = None


def build_checks(python: str = sys.executable) -> list[ReleaseCheck]:
    """Return the release-readiness gates that should pass before public launch."""
    return [
        ReleaseCheck("unit tests", (python, "-m", "pytest", "-q")),
        ReleaseCheck("doctor preflight", (python, "-m", "labcheck.cli", "doctor", ".", "--config", ".labcheck.toml")),
        ReleaseCheck("scorecard smoke", (python, "-m", "labcheck.cli", "scorecard", "examples/clean-notebook")),
        ReleaseCheck("sample audit export", (python, "scripts/build_sample_audits.py")),
        ReleaseCheck("static site export", (python, "scripts/build_static_site.py")),
        ReleaseCheck("launch hygiene", (python, "scripts/check_launch_hygiene.py")),
        ReleaseCheck(
            "standalone repo export smoke",
            (python, "scripts/export_standalone_repo.py", ".tmp-standalone-labcheck"),
            cleanup_path=".tmp-standalone-labcheck",
        ),
        ReleaseCheck(
            "self scan stays clean",
            (
                python,
                "-m",
                "labcheck.cli",
                "scan",
                ".",
                "--config",
                ".labcheck.toml",
                "--format",
                "json",
                "--min-score",
                "100",
            ),
        ),
        ReleaseCheck(
            "clean example remains clean",
            (python, "-m", "labcheck.cli", "scan", "examples/clean-notebook", "--min-score", "100"),
        ),
        ReleaseCheck(
            "audit pack smoke",
            (
                python,
                "-m",
                "labcheck.cli",
                "pack",
                "examples/clean-notebook",
                "--output-dir",
                ".tmp-release-audit-pack",
                "--zip",
                "--min-score",
                "100",
            ),
            cleanup_path=".tmp-release-audit-pack",
            cleanup_zip_path=".tmp-release-audit-pack.zip",
        ),
        ReleaseCheck(
            "broken example still fails the high-severity gate",
            (python, "-m", "labcheck.cli", "scan", "examples/broken-repo", "--fail-on", "high"),
            expected_exit_code=2,
        ),
    ]


def _format_command(command: tuple[str, ...]) -> str:
    return " ".join(command)


def _cleanup_generated_path(repo_root: Path, cleanup_path: str | None) -> None:
    if not cleanup_path:
        return
    path = (repo_root / cleanup_path).resolve()
    if not path.name.startswith(".tmp-") or repo_root.resolve() not in path.parents:
        raise ValueError(f"Refusing to clean unsafe release-check path: {path}")
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def _run_check(repo_root: Path, check: ReleaseCheck, *, verbose: bool = False) -> bool:
    _cleanup_generated_path(repo_root, check.cleanup_path)
    _cleanup_generated_path(repo_root, check.cleanup_zip_path)
    print(f"\n==> {check.name}", flush=True)
    print(f"$ {_format_command(check.command)}", flush=True)
    result = subprocess.run(
        check.command,
        cwd=repo_root,
        check=False,
        capture_output=not verbose,
        text=not verbose,
    )
    if result.returncode == check.expected_exit_code:
        _cleanup_generated_path(repo_root, check.cleanup_path)
        _cleanup_generated_path(repo_root, check.cleanup_zip_path)
        print(f"OK: exit code {result.returncode}")
        return True
    if not verbose:
        if result.stdout:
            sys.stdout.write(result.stdout)
        if result.stderr:
            sys.stderr.write(result.stderr)
    print(
        f"FAILED: expected exit code {check.expected_exit_code}, got {result.returncode}",
        file=sys.stderr,
    )
    return False


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    checks = build_checks()
    if args == ["--list"]:
        for check in checks:
            suffix = "" if check.expected_exit_code == 0 else f"  # expect {check.expected_exit_code}"
            print(f"{_format_command(check.command)}{suffix}")
        return 0
    verbose = args == ["--verbose"]
    if args:
        if not verbose:
            print("Usage: python scripts/release_check.py [--list|--verbose]", file=sys.stderr)
            return 2
    if verbose:
        args = []
    if args:
        return 2

    repo_root = Path(__file__).resolve().parents[1]
    print("Running labcheck release-readiness gates...")
    failures = 0
    for check in checks:
        if not _run_check(repo_root, check, verbose=verbose):
            failures += 1

    if failures:
        print(f"\n{failures} release check(s) failed.", file=sys.stderr)
        return 1
    print("\nAll release checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
