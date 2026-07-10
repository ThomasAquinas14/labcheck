from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys


DEFAULT_REPO = "ThomasAquinas14/labcheck"
DEFAULT_DESCRIPTION = "No-key reproducibility audits for notebook-heavy research and ML repos."
DEFAULT_HOMEPAGE = "https://thomasaquinas14.github.io/labcheck/"
DEFAULT_TOPICS = [
    "reproducibility",
    "jupyter-notebook",
    "machine-learning",
    "research-software",
    "data-science",
    "github-action",
    "static-analysis",
    "notebook",
    "ci",
    "open-source",
]


class CommandResult:
    def __init__(self, returncode: int, stdout: str, stderr: str) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _run(command: list[str], cwd: Path) -> CommandResult:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    return CommandResult(result.returncode, result.stdout.strip(), result.stderr.strip())


def _expected_remote_urls(repo: str) -> set[str]:
    owner, name = repo.split("/", 1)
    return {
        f"https://github.com/{owner}/{name}.git",
        f"https://github.com/{owner}/{name}",
        f"git@github.com:{owner}/{name}.git",
    }


def check_local_publish_ready(repo_root: Path, repo: str = DEFAULT_REPO) -> list[str]:
    """Return local issues that should be fixed before pushing the public repo."""
    issues: list[str] = []
    repo_root = repo_root.resolve()

    if not (repo_root / ".git").exists():
        return ["not a standalone Git repository; run git init first"]

    branch = _run(["git", "branch", "--show-current"], repo_root)
    if branch.returncode != 0:
        issues.append(f"could not read current branch: {branch.stderr}")
    elif branch.stdout != "main":
        issues.append(f"current branch is {branch.stdout!r}, expected 'main'")

    head = _run(["git", "rev-parse", "--verify", "HEAD"], repo_root)
    if head.returncode != 0:
        issues.append("repository has no commits yet")

    status = _run(["git", "status", "--porcelain"], repo_root)
    if status.returncode != 0:
        issues.append(f"could not read git status: {status.stderr}")
    elif status.stdout:
        issues.append("working tree is not clean; commit or remove local changes first")

    remote = _run(["git", "remote", "get-url", "origin"], repo_root)
    if remote.returncode == 0 and remote.stdout not in _expected_remote_urls(repo):
        issues.append(f"origin points to {remote.stdout!r}, expected GitHub repo {repo!r}")

    return issues


def publish_commands(repo: str = DEFAULT_REPO) -> list[str]:
    topics = ",".join(DEFAULT_TOPICS)
    return [
        "python scripts/release_check.py",
        f"gh repo create {repo} --public --source=. --remote=origin --push",
        'git tag -a v1 -m "labcheck GitHub Action v1"',
        "git push origin v1",
        (
            f'gh repo edit {repo} --description "{DEFAULT_DESCRIPTION}" '
            f'--homepage "{DEFAULT_HOMEPAGE}" --add-topic "{topics}"'
        ),
    ]


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    repo = args[0] if args else DEFAULT_REPO
    if len(args) > 1:
        print("Usage: python scripts/check_publish_ready.py [owner/repo]", file=sys.stderr)
        return 2

    repo_root = Path(__file__).resolve().parents[1]
    issues = check_local_publish_ready(repo_root, repo)
    if issues:
        print("labcheck publish readiness failed:", file=sys.stderr)
        for issue in issues:
            print(f"- {issue}", file=sys.stderr)
        return 1

    print("labcheck publish readiness OK")
    print()
    if shutil.which("gh"):
        auth = _run(["gh", "auth", "status"], repo_root)
        print("GitHub CLI: available")
        print("GitHub auth: OK" if auth.returncode == 0 else "GitHub auth: not ready")
        existing = _run(["gh", "repo", "view", repo, "--json", "nameWithOwner,url,visibility"], repo_root)
        if existing.returncode == 0:
            print(f"GitHub repo already exists: {repo}")
        else:
            print(f"GitHub repo appears available or inaccessible: {repo}")
    else:
        print("GitHub CLI: not found")
    print()
    print("Publish commands:")
    for command in publish_commands(repo):
        print(command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
