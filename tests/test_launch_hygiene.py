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
    assert "docs/comparison.md" in checker.REQUIRED_FILES
    assert "docs/demo-video-script.md" in checker.REQUIRED_FILES
    assert "docs/first-audit.md" in checker.REQUIRED_FILES
    assert "docs/install.md" in checker.REQUIRED_FILES
    assert "docs/issue-labels.md" in checker.REQUIRED_FILES
    assert "docs/launch-post-after-action.md" in checker.REQUIRED_FILES
    assert "docs/maintainer-reply-templates.md" in checker.REQUIRED_FILES
    assert "docs/privacy-and-safety.md" in checker.REQUIRED_FILES
    assert "docs/public-triage-board.md" in checker.REQUIRED_FILES
    assert "docs/reply-derived-case-study-seed.md" in checker.REQUIRED_FILES
    assert "docs/reply-to-case-study-checklist.md" in checker.REQUIRED_FILES
    assert ".github/labels.yml" in checker.REQUIRED_FILES
    assert "docs/sample-audits/broken-repo-labeled-issue.md" in checker.REQUIRED_FILES
    assert "docs/sample-audits/broken-repo-issue-draft.md" in checker.REQUIRED_FILES
    assert "docs/sample-audits/broken-repo-target-fit.md" in checker.REQUIRED_FILES
    assert "scripts/check_compare_smoke.py" in checker.REQUIRED_FILES
    assert "scripts/check_public_urls.py" in checker.REQUIRED_FILES
    assert "scripts/check_static_export.py" in checker.REQUIRED_FILES


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


def test_launch_hygiene_allows_safe_env_examples(tmp_path: Path) -> None:
    checker = _load_checker()
    (tmp_path / ".gitignore").write_text(
        "\n".join(checker.REQUIRED_IGNORE_PATTERNS) + "\n",
        encoding="utf-8",
    )
    (tmp_path / ".env.example").write_text("LABCHECK_DATA_ROOT=/path/to/data\n", encoding="utf-8")
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

    assert not any(".env.example" in issue for issue in issues)


def test_launch_hygiene_flags_stale_public_copy(tmp_path: Path) -> None:
    checker = _load_checker()
    (tmp_path / ".gitignore").write_text(
        "\n".join(checker.REQUIRED_IGNORE_PATTERNS) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        "![preview](docs/assets/scorecard-preview.svg)\n"
        "No paid APIs. No inference bill. No backend secret to protect.\n"
        "- CI usage later\n",
        encoding="utf-8",
    )
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "launch-kit.md").write_text(
        "Repository name\nDescription\nTopics\nProfessor Outreach\nFounder Outreach\n",
        encoding="utf-8",
    )

    issues = checker.check_launch_hygiene(tmp_path)

    assert "README.md contains stale public copy 'CI usage later'; use 'CI usage now'" in issues


def test_launch_hygiene_flags_stale_sample_metrics(tmp_path: Path) -> None:
    checker = _load_checker()
    (tmp_path / ".gitignore").write_text(
        "\n".join(checker.REQUIRED_IGNORE_PATTERNS) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        "![preview](docs/assets/scorecard-preview.svg)\n"
        "No paid APIs. No inference bill. No backend secret to protect.\n"
        "Overall score: 44/100\n"
        "Findings: 13 (4 high, 6 medium, 2 low)\n"
        "fix 4 high-severity findings\n",
        encoding="utf-8",
    )
    docs = tmp_path / "docs"
    sample_audits = docs / "sample-audits"
    assets = docs / "assets"
    sample_audits.mkdir(parents=True)
    assets.mkdir()
    (docs / "launch-kit.md").write_text(
        "Repository name\nDescription\nTopics\nProfessor Outreach\nFounder Outreach\n",
        encoding="utf-8",
    )
    (sample_audits / "broken-repo-scorecard.md").write_text(
        "# labcheck Scorecard\n\n"
        "- Overall score: **39/100**\n"
        "- Findings: **14** (`5` high, `7` medium, `2` low)\n",
        encoding="utf-8",
    )
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text(
        '<div class="score">44</div><span>4 high-severity findings</span>',
        encoding="utf-8",
    )
    (assets / "scorecard-preview.svg").write_text("<text>44</text>\n", encoding="utf-8")

    issues = checker.check_launch_hygiene(tmp_path)

    assert any("README.md sample metric copy is stale" in issue for issue in issues)
    assert any("site/index.html sample metric copy is stale" in issue for issue in issues)
    assert any("docs/assets/scorecard-preview.svg sample metric copy is stale" in issue for issue in issues)


def test_launch_hygiene_flags_stale_package_metadata(tmp_path: Path) -> None:
    checker = _load_checker()
    (tmp_path / ".gitignore").write_text(
        "\n".join(checker.REQUIRED_IGNORE_PATTERNS) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        "![preview](docs/assets/scorecard-preview.svg)\n"
        "No paid APIs. No inference bill. No backend secret to protect.\n",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\n'
        'description = "A reproducibility auditor."\n'
        'keywords = ["reproducibility"]\n'
        '[project.urls]\n'
        'Homepage = "https://github.com/ThomasAquinas14/labcheck"\n',
        encoding="utf-8",
    )
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "launch-kit.md").write_text(
        "Repository name\nDescription\nTopics\nProfessor Outreach\nFounder Outreach\n",
        encoding="utf-8",
    )

    issues = checker.check_launch_hygiene(tmp_path)

    assert "pyproject.toml description does not match the public launch positioning" in issues
    assert any("pyproject.toml is missing package keyword(s)" in issue for issue in issues)
    assert "pyproject.toml project.urls.Homepage should be 'https://thomasaquinas14.github.io/labcheck/'" in issues


def test_launch_hygiene_flags_windows_paths_in_public_case_study_audits(tmp_path: Path) -> None:
    checker = _load_checker()
    (tmp_path / ".gitignore").write_text(
        "\n".join(checker.REQUIRED_IGNORE_PATTERNS) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        "![preview](docs/assets/scorecard-preview.svg)\n"
        "No paid APIs. No inference bill. No backend secret to protect.\n",
        encoding="utf-8",
    )
    docs = tmp_path / "docs"
    sample_audits = docs / "sample-audits"
    sample_audits.mkdir(parents=True)
    (docs / "launch-kit.md").write_text(
        "Repository name\nDescription\nTopics\nProfessor Outreach\nFounder Outreach\n",
        encoding="utf-8",
    )
    (sample_audits / "handson-ml3-audit.md").write_text(
        "# labcheck Report\n\n- File: `docker\\README.md`\n",
        encoding="utf-8",
    )
    (sample_audits / "python-data-science-handbook-audit.md").write_text(
        "# labcheck Report\n\n- File: `notebooks/intro.ipynb`\n",
        encoding="utf-8",
    )

    issues = checker.check_launch_hygiene(tmp_path)

    assert (
        "docs/sample-audits/handson-ml3-audit.md contains Windows-style path separators; "
        "use POSIX-style '/' paths in public audit snapshots"
    ) in issues


def test_launch_hygiene_flags_missing_static_json_ld(tmp_path: Path) -> None:
    checker = _load_checker()
    (tmp_path / ".gitignore").write_text(
        "\n".join(checker.REQUIRED_IGNORE_PATTERNS) + "\n",
        encoding="utf-8",
    )
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
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("<html><head></head><body></body></html>", encoding="utf-8")
    (site / "demo.html").write_text(
        '<script type="application/ld+json">{"@type":"SoftwareApplication"}</script>',
        encoding="utf-8",
    )

    issues = checker.check_launch_hygiene(tmp_path)

    assert "site/index.html is missing JSON-LD structured data" in issues
    assert 'site/demo.html JSON-LD is missing "@type": "WebApplication"' in issues
