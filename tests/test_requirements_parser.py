from __future__ import annotations

from pathlib import Path

from labcheck.requirements_parser import (
    find_python_runtime_spec,
    find_unpinned_dependencies,
    find_unpinned_environment_dependencies,
    find_unpinned_pyproject_dependencies,
    find_unpinned_requirements,
)


def test_find_unpinned_requirements_ignores_version_constraints(tmp_path: Path) -> None:
    path = tmp_path / "requirements.txt"
    path.write_text(
        "\n".join(
            [
                "pandas",
                "numpy==2.0.0",
                "scipy>=1.12",
                "git+https://github.com/example/project.git",
                "-r base.txt",
            ]
        ),
        encoding="utf-8",
    )

    assert find_unpinned_requirements(path) == ["pandas"]


def test_find_unpinned_pyproject_project_dependencies(tmp_path: Path) -> None:
    path = tmp_path / "pyproject.toml"
    path.write_text(
        """
[project]
dependencies = [
  "pandas",
  "numpy==2.0.0",
]

[project.optional-dependencies]
dev = [
  "pytest",
  "ruff>=0.5",
]
""",
        encoding="utf-8",
    )

    assert find_unpinned_pyproject_dependencies(path) == ["pandas", "pytest"]


def test_find_unpinned_pyproject_poetry_dependencies(tmp_path: Path) -> None:
    path = tmp_path / "pyproject.toml"
    path.write_text(
        """
[tool.poetry.dependencies]
python = "^3.11"
pandas = "*"
numpy = "^2.0"
scipy = { version = "*" }
matplotlib = { version = ">=3.8" }
local-lib = { path = "../local-lib" }

[tool.poetry.group.dev.dependencies]
pytest = "*"
ruff = "^0.5"
""",
        encoding="utf-8",
    )

    assert find_unpinned_pyproject_dependencies(path) == ["pandas", "scipy", "pytest"]


def test_find_unpinned_environment_dependencies_only_reads_dependencies_section(tmp_path: Path) -> None:
    path = tmp_path / "environment.yml"
    path.write_text(
        """
name: demo
channels:
  - conda-forge
dependencies:
  - python=3.11
  - pandas
  - numpy>=2
  - pip:
    - pytest
    - ruff==0.5
""",
        encoding="utf-8",
    )

    assert find_unpinned_environment_dependencies(path) == ["pandas", "pytest"]


def test_find_unpinned_dependencies_combines_supported_manifests(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("pandas\nnumpy==2.0\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[project]\ndependencies = ["scipy"]\n', encoding="utf-8")
    (tmp_path / "environment.yml").write_text("dependencies:\n  - matplotlib\n", encoding="utf-8")

    findings = find_unpinned_dependencies(tmp_path)

    assert [(finding.file_path, finding.dependency) for finding in findings] == [
        ("requirements.txt", "pandas"),
        ("pyproject.toml", "scipy"),
        ("environment.yml", "matplotlib"),
    ]


def test_find_unpinned_dependencies_accepts_utf8_bom_manifests(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("\ufeffpandas\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("\ufeff[project]\ndependencies = [\"scipy\"]\n", encoding="utf-8")
    (tmp_path / "environment.yml").write_text("\ufeffdependencies:\n  - matplotlib\n", encoding="utf-8")

    findings = find_unpinned_dependencies(tmp_path)

    assert [(finding.file_path, finding.dependency) for finding in findings] == [
        ("requirements.txt", "pandas"),
        ("pyproject.toml", "scipy"),
        ("environment.yml", "matplotlib"),
    ]


def test_find_python_runtime_spec_reads_pyproject_requires_python(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nrequires-python = ">=3.11"\n',
        encoding="utf-8",
    )

    runtime = find_python_runtime_spec(tmp_path)

    assert runtime is not None
    assert runtime.file_path == "pyproject.toml"
    assert runtime.spec == ">=3.11"


def test_find_python_runtime_spec_reads_common_runtime_files(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.12\n", encoding="utf-8")

    runtime = find_python_runtime_spec(tmp_path)

    assert runtime is not None
    assert runtime.file_path == ".python-version"
    assert runtime.spec == "3.12"


def test_find_python_runtime_spec_reads_pipfile_requires(tmp_path: Path) -> None:
    (tmp_path / "Pipfile").write_text(
        '[requires]\npython_version = "3.11"\n',
        encoding="utf-8",
    )

    runtime = find_python_runtime_spec(tmp_path)

    assert runtime is not None
    assert runtime.file_path == "Pipfile"
    assert runtime.spec == "3.11"


def test_find_python_runtime_spec_reads_conda_python_dependency(tmp_path: Path) -> None:
    (tmp_path / "environment.yml").write_text(
        "dependencies:\n  - python=3.11\n  - pandas\n",
        encoding="utf-8",
    )

    runtime = find_python_runtime_spec(tmp_path)

    assert runtime is not None
    assert runtime.file_path == "environment.yml"
    assert runtime.spec == "python=3.11"


def test_find_python_runtime_spec_reads_setup_cfg_python_requires(tmp_path: Path) -> None:
    (tmp_path / "setup.cfg").write_text(
        "[options]\npython_requires = >=3.10\n",
        encoding="utf-8",
    )

    runtime = find_python_runtime_spec(tmp_path)

    assert runtime is not None
    assert runtime.file_path == "setup.cfg"
    assert runtime.spec == ">=3.10"


def test_find_python_runtime_spec_returns_none_when_missing(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")

    assert find_python_runtime_spec(tmp_path) is None
