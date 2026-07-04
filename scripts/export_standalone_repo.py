from __future__ import annotations

from pathlib import Path
import shutil
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from check_launch_hygiene import _is_ignored, _read_gitignore, check_launch_hygiene


DEFAULT_OUTPUT_DIR = Path(".tmp-standalone-labcheck")
EXTRA_EXCLUDES = {
    ".git",
}


def _safe_clean_output(repo_root: Path, output_dir: Path) -> None:
    resolved_repo = repo_root.resolve()
    resolved_output = output_dir.resolve()
    if resolved_output == resolved_repo or resolved_repo not in resolved_output.parents:
        raise ValueError(f"Refusing to clean output outside repository: {resolved_output}")
    if not resolved_output.name.startswith(".tmp-"):
        raise ValueError(f"Refusing to clean non-temporary output directory: {resolved_output}")
    if resolved_output.exists():
        shutil.rmtree(resolved_output)


def _should_skip(path: Path, repo_root: Path, ignore_patterns: set[str], output_dir: Path) -> bool:
    relative = path.relative_to(repo_root).as_posix()
    if path.resolve() == output_dir.resolve() or output_dir.resolve() in path.resolve().parents:
        return True
    if any(part in EXTRA_EXCLUDES for part in path.relative_to(repo_root).parts):
        return True
    return _is_ignored(relative, ignore_patterns)


def iter_export_files(repo_root: Path, output_dir: Path) -> list[Path]:
    """Return files that belong in the standalone public repository export."""
    repo_root = repo_root.resolve()
    output_dir = output_dir.resolve()
    ignore_patterns = _read_gitignore(repo_root)
    files: list[Path] = []
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if _should_skip(path, repo_root, ignore_patterns, output_dir):
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(repo_root).as_posix())


def export_standalone_repo(repo_root: Path, output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    """Copy publishable project files into a clean temporary standalone repo folder."""
    repo_root = repo_root.resolve()
    output_dir = (repo_root / output_dir).resolve() if not output_dir.is_absolute() else output_dir.resolve()

    hygiene_issues = check_launch_hygiene(repo_root)
    if hygiene_issues:
        joined = "\n".join(f"- {issue}" for issue in hygiene_issues)
        message = "Launch hygiene failed; refusing export."
        raise RuntimeError(f"{message}\n{joined}")

    _safe_clean_output(repo_root, output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for source in iter_export_files(repo_root, output_dir):
        relative = source.relative_to(repo_root)
        destination = output_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return output_dir


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    repo_root = Path(__file__).resolve().parents[1]
    output_dir = Path(args[0]) if args else DEFAULT_OUTPUT_DIR
    if len(args) > 1:
        print("Usage: python scripts/export_standalone_repo.py [output-dir]", file=sys.stderr)
        return 2
    exported = export_standalone_repo(repo_root, output_dir)
    file_count = len(iter_export_files(repo_root, exported))
    print(f"Exported {file_count} files to {exported}")
    print("Next: cd into the export, run `git init`, then push to the new public repo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
