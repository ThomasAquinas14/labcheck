from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile


def _run(command: list[str]) -> None:
    subprocess.run(command, check=True, cwd=Path.cwd())


def _temporary_prefix() -> str:
    prefix = os.environ.get("LABCHECK_COMPARE_TMP_PREFIX", ".tmp-release-compare-")
    if not prefix.startswith(".tmp-") or any(separator in prefix for separator in ("/", "\\")):
        raise ValueError("LABCHECK_COMPARE_TMP_PREFIX must be a safe .tmp-* prefix")
    return prefix


def main() -> int:
    """Smoke-test the before/after compare workflow used in release notes and PRs."""
    with tempfile.TemporaryDirectory(prefix=_temporary_prefix(), dir=Path.cwd()) as temp_dir:
        temp_root = Path(temp_dir)
        before_json = temp_root / "before.json"
        after_json = temp_root / "after.json"
        compare_markdown = temp_root / "labcheck-compare.md"
        python = sys.executable
        _run(
            [
                python,
                "-m",
                "labcheck.cli",
                "scan",
                "examples/broken-repo",
                "--format",
                "json",
                "--output",
                str(before_json),
            ]
        )
        _run(
            [
                python,
                "-m",
                "labcheck.cli",
                "scan",
                "examples/clean-notebook",
                "--format",
                "json",
                "--output",
                str(after_json),
            ]
        )
        _run(
            [
                python,
                "-m",
                "labcheck.cli",
                "compare",
                str(before_json),
                str(after_json),
                "--output",
                str(compare_markdown),
            ]
        )
        compare_note = compare_markdown.read_text(encoding="utf-8")
        required_snippets = [
            "# labcheck Before/After Compare",
            "Score change: **+61** points (39 -> 100)",
            "Findings change: **-14** (14 -> 0)",
            "Resolved findings: **14**",
            "New findings: **0**",
            "No API key or hosted backend was used",
        ]
        missing = [snippet for snippet in required_snippets if snippet not in compare_note]
        if missing:
            print("labcheck compare smoke failed:", file=sys.stderr)
            for snippet in missing:
                print(f"- missing {snippet!r}", file=sys.stderr)
            return 1
        print("labcheck compare smoke OK")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
