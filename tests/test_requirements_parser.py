from __future__ import annotations

from pathlib import Path

from labcheck.requirements_parser import (
    find_declared_dependency_names,
    find_missing_local_dependency_paths,
    find_missing_requirement_includes,
    find_python_runtime_spec,
    find_python_runtime_specs,
    find_unpinned_dependencies,
    find_unpinned_environment_dependencies,
    find_unpinned_pyproject_dependencies,
    find_unpinned_requirements,
    find_unpinned_vcs_dependencies,
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
                "-rbase.txt",
                "-cconstraints.txt",
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


def test_find_unpinned_dependencies_follows_conda_pip_requirement_includes(tmp_path: Path) -> None:
    deps_dir = tmp_path / "deps"
    deps_dir.mkdir()
    (tmp_path / "environment.yml").write_text(
        "dependencies:\n  - python=3.11\n  - pip:\n    - -r deps/pip.txt\n",
        encoding="utf-8",
    )
    (deps_dir / "pip.txt").write_text("pandas\nnumpy==2.0\n", encoding="utf-8")

    findings = find_unpinned_dependencies(tmp_path)

    assert [(finding.file_path, finding.dependency) for finding in findings] == [
        ("deps/pip.txt", "pandas"),
    ]


def test_find_unpinned_vcs_dependencies_follows_conda_pip_requirement_includes(tmp_path: Path) -> None:
    deps_dir = tmp_path / "deps"
    deps_dir.mkdir()
    (tmp_path / "environment.yml").write_text(
        "dependencies:\n  - pip:\n    - -r deps/pip.txt\n",
        encoding="utf-8",
    )
    (deps_dir / "pip.txt").write_text(
        "git+https://github.com/example/research-utils.git@main#egg=research-utils\n",
        encoding="utf-8",
    )

    findings = find_unpinned_vcs_dependencies(tmp_path)

    assert [(finding.file_path, finding.reason) for finding in findings] == [
        ("deps/pip.txt", "uses moving ref 'main'"),
    ]


def test_find_unpinned_vcs_dependencies_flags_direct_conda_pip_entries(tmp_path: Path) -> None:
    (tmp_path / "environment.yml").write_text(
        "\n".join(
            [
                "dependencies:",
                "  - python=3.11",
                "  - pip:",
                "    - git+https://github.com/example/research-utils.git@main#egg=research-utils",
            ]
        ),
        encoding="utf-8",
    )

    findings = find_unpinned_vcs_dependencies(tmp_path)

    assert [(finding.file_path, finding.reason) for finding in findings] == [
        ("environment.yml", "uses moving ref 'main'"),
    ]


def test_find_declared_dependency_names_combines_supported_manifests(tmp_path: Path) -> None:
    requirements_dir = tmp_path / "requirements"
    requirements_dir.mkdir()
    (tmp_path / "requirements.txt").write_text(
        "\n".join(
            [
                "-r requirements/dev.txt",
                "scikit-learn==1.5.0",
                "opencv-python>=4.10",
                "custom @ git+https://github.com/example/custom.git#egg=custom-pkg",
            ]
        ),
        encoding="utf-8",
    )
    (requirements_dir / "dev.txt").write_text("python-dotenv==1.0.1\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
dependencies = ["Pillow==10.4.0"]

[tool.poetry.dependencies]
python = "^3.11"
PyYAML = "^6.0"
""",
        encoding="utf-8",
    )
    (tmp_path / "environment.yml").write_text(
        "dependencies:\n  - pandas=2.2\n  - pip:\n    - httpx==0.27.0\n",
        encoding="utf-8",
    )

    assert find_declared_dependency_names(tmp_path) == {
        "custom",
        "httpx",
        "opencv-python",
        "pandas",
        "pillow",
        "python-dotenv",
        "pyyaml",
        "scikit-learn",
    }


def test_find_declared_dependency_names_follows_conda_pip_requirement_includes(tmp_path: Path) -> None:
    deps_dir = tmp_path / "deps"
    deps_dir.mkdir()
    (tmp_path / "environment.yml").write_text(
        "dependencies:\n  - pip:\n    - -r deps/pip.txt\n",
        encoding="utf-8",
    )
    (deps_dir / "pip.txt").write_text("scikit-learn==1.5.0\n", encoding="utf-8")

    assert find_declared_dependency_names(tmp_path) == {"scikit-learn"}


def test_find_missing_requirement_includes_flags_absent_local_files(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text(
        "\n".join(
            [
                "-r requirements/base.txt",
                "--constraint constraints.txt",
                "--requirement=requirements/dev.txt",
            ]
        ),
        encoding="utf-8",
    )
    requirements_dir = tmp_path / "requirements"
    requirements_dir.mkdir()
    (requirements_dir / "base.txt").write_text("pandas==2.2.2\n", encoding="utf-8")

    missing = find_missing_requirement_includes(tmp_path)

    assert [(item.file_path, item.directive, item.referenced_path) for item in missing] == [
        ("requirements.txt", "--constraint", "constraints.txt"),
        ("requirements.txt", "--requirement", "requirements/dev.txt"),
    ]


def test_find_missing_requirement_includes_follows_nested_existing_files(tmp_path: Path) -> None:
    requirements_dir = tmp_path / "requirements"
    requirements_dir.mkdir()
    (tmp_path / "requirements.txt").write_text("-r requirements/base.txt\n", encoding="utf-8")
    (requirements_dir / "base.txt").write_text("-c ../constraints/prod.txt\n", encoding="utf-8")

    missing = find_missing_requirement_includes(tmp_path)

    assert [(item.file_path, item.directive, item.referenced_path) for item in missing] == [
        ("requirements/base.txt", "-c", "../constraints/prod.txt"),
    ]


def test_find_missing_requirement_includes_scans_common_root_requirement_names(tmp_path: Path) -> None:
    (tmp_path / "dev-requirements.txt").write_text("-r requirements/dev-base.txt\n", encoding="utf-8")

    missing = find_missing_requirement_includes(tmp_path)

    assert [(item.file_path, item.referenced_path) for item in missing] == [
        ("dev-requirements.txt", "requirements/dev-base.txt"),
    ]


def test_find_missing_requirement_includes_accepts_present_and_remote_includes(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text(
        "\n".join(
            [
                "-r base.txt",
                "-r https://example.com/requirements.txt",
                "-r ${REQUIREMENTS_FILE}",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "base.txt").write_text("pandas==2.2.2\n", encoding="utf-8")

    assert find_missing_requirement_includes(tmp_path) == []


def test_find_missing_requirement_includes_flags_conda_pip_includes(tmp_path: Path) -> None:
    (tmp_path / "environment.yml").write_text(
        "\n".join(
            [
                "name: demo",
                "dependencies:",
                "  - python=3.11",
                "  - pip:",
                "    - -r requirements/pip.txt",
                "    - --constraint constraints.txt",
                "    - -r https://example.com/requirements.txt",
                "    - -r ${PIP_REQUIREMENTS}",
            ]
        ),
        encoding="utf-8",
    )
    requirements_dir = tmp_path / "requirements"
    requirements_dir.mkdir()
    (requirements_dir / "pip.txt").write_text("pandas==2.2.2\n", encoding="utf-8")

    missing = find_missing_requirement_includes(tmp_path)

    assert [(item.file_path, item.directive, item.referenced_path) for item in missing] == [
        ("environment.yml", "--constraint", "constraints.txt"),
    ]


def test_find_missing_requirement_includes_follows_conda_pip_includes(tmp_path: Path) -> None:
    requirements_dir = tmp_path / "requirements"
    requirements_dir.mkdir()
    (tmp_path / "environment.yaml").write_text(
        "dependencies:\n  - pip:\n    - -r requirements/pip.txt\n",
        encoding="utf-8",
    )
    (requirements_dir / "pip.txt").write_text("-r nested.txt\n", encoding="utf-8")

    missing = find_missing_requirement_includes(tmp_path)

    assert [(item.file_path, item.directive, item.referenced_path) for item in missing] == [
        ("requirements/pip.txt", "-r", "nested.txt"),
    ]


def test_find_missing_local_dependency_paths_flags_requirements_refs(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text(
        "\n".join(
            [
                "-e ./local-lib",
                "--find-links=./wheelhouse",
                "model-utils @ file:./vendor/model-utils",
                "./dist/custom_model-0.1.0-py3-none-any.whl",
                "pandas==2.2.2",
            ]
        ),
        encoding="utf-8",
    )

    missing = find_missing_local_dependency_paths(tmp_path)

    assert [(item.file_path, item.dependency, item.referenced_path) for item in missing] == [
        ("requirements.txt", "editable", "./local-lib"),
        ("requirements.txt", "find-links", "./wheelhouse"),
        ("requirements.txt", "file", "./vendor/model-utils"),
        ("requirements.txt", "path", "./dist/custom_model-0.1.0-py3-none-any.whl"),
    ]


def test_find_missing_local_dependency_paths_accepts_existing_and_remote_refs(tmp_path: Path) -> None:
    (tmp_path / "local-lib").mkdir()
    (tmp_path / "wheelhouse").mkdir()
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "custom_model-0.1.0-py3-none-any.whl").write_text("", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text(
        "\n".join(
            [
                "-e ./local-lib",
                "--find-links ./wheelhouse",
                "./dist/custom_model-0.1.0-py3-none-any.whl",
                "git+https://github.com/example/pkg.git",
                "pkg @ https://example.com/pkg-1.0.0.whl",
                "-e ${LOCAL_PACKAGE_PATH}",
            ]
        ),
        encoding="utf-8",
    )

    assert find_missing_local_dependency_paths(tmp_path) == []


def test_find_missing_local_dependency_paths_follows_nested_requirements(tmp_path: Path) -> None:
    requirements_dir = tmp_path / "requirements"
    requirements_dir.mkdir()
    (tmp_path / "requirements.txt").write_text("-r requirements/dev.txt\n", encoding="utf-8")
    (requirements_dir / "dev.txt").write_text("-e ../missing-dev-lib\n", encoding="utf-8")

    missing = find_missing_local_dependency_paths(tmp_path)

    assert [(item.file_path, item.referenced_path) for item in missing] == [
        ("requirements/dev.txt", "../missing-dev-lib"),
    ]


def test_find_missing_local_dependency_paths_follows_conda_pip_requirement_includes(tmp_path: Path) -> None:
    deps_dir = tmp_path / "deps"
    deps_dir.mkdir()
    (tmp_path / "environment.yml").write_text(
        "dependencies:\n  - pip:\n    - -r deps/pip.txt\n",
        encoding="utf-8",
    )
    (deps_dir / "pip.txt").write_text("-e ../missing-local-lib\n", encoding="utf-8")

    missing = find_missing_local_dependency_paths(tmp_path)

    assert [(item.file_path, item.referenced_path) for item in missing] == [
        ("deps/pip.txt", "../missing-local-lib"),
    ]


def test_find_missing_local_dependency_paths_flags_direct_conda_pip_entries(tmp_path: Path) -> None:
    (tmp_path / "environment.yml").write_text(
        "\n".join(
            [
                "dependencies:",
                "  - pip:",
                "    - -e ../missing-local-lib",
                "    - model-utils @ file:./vendor/model-utils",
            ]
        ),
        encoding="utf-8",
    )

    missing = find_missing_local_dependency_paths(tmp_path)

    assert [(item.file_path, item.dependency, item.referenced_path) for item in missing] == [
        ("environment.yml", "editable", "../missing-local-lib"),
        ("environment.yml", "file", "./vendor/model-utils"),
    ]


def test_find_missing_local_dependency_paths_flags_pyproject_refs(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
dependencies = [
  "model-utils @ file:./vendor/model-utils",
]

[tool.poetry.dependencies]
python = "^3.11"
local-lib = { path = "./libs/local-lib", develop = true }

[tool.poetry.group.dev.dependencies]
dev-lib = { path = "../dev-lib" }
""",
        encoding="utf-8",
    )

    missing = find_missing_local_dependency_paths(tmp_path)

    assert [(item.file_path, item.dependency, item.referenced_path) for item in missing] == [
        ("pyproject.toml", "file", "./vendor/model-utils"),
        ("pyproject.toml", "local-lib", "./libs/local-lib"),
        ("pyproject.toml", "dev-lib", "../dev-lib"),
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


def test_find_python_runtime_specs_collects_multiple_sources(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11.9\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nrequires-python = ">=3.11"\n',
        encoding="utf-8",
    )
    (tmp_path / "Dockerfile").write_text("FROM python:3.11-slim\n", encoding="utf-8")

    specs = find_python_runtime_specs(tmp_path)

    assert [(spec.file_path, spec.spec) for spec in specs] == [
        (".python-version", "3.11.9"),
        ("pyproject.toml", ">=3.11"),
        ("Dockerfile", "python:3.11-slim"),
    ]


def test_find_python_runtime_specs_reads_dockerfile_variants(tmp_path: Path) -> None:
    docker_dir = tmp_path / "docker"
    docker_dir.mkdir()
    service_dir = tmp_path / "services" / "api"
    service_dir.mkdir(parents=True)
    (docker_dir / "Dockerfile").write_text("FROM --platform=linux/amd64 python:3.11-slim AS app\n", encoding="utf-8")
    (tmp_path / "Dockerfile.release").write_text("FROM python:3.11-bookworm\n", encoding="utf-8")
    (service_dir / "worker.Dockerfile").write_text("FROM ghcr.io/example/python:3.11-runtime\n", encoding="utf-8")
    ignored = tmp_path / "node_modules" / "pkg"
    ignored.mkdir(parents=True)
    (ignored / "Dockerfile").write_text("FROM python:3.8-slim\n", encoding="utf-8")

    specs = find_python_runtime_specs(tmp_path)

    assert [(spec.file_path, spec.spec) for spec in specs] == [
        ("docker/Dockerfile", "python:3.11-slim"),
        ("Dockerfile.release", "python:3.11-bookworm"),
        ("services/api/worker.Dockerfile", "python:3.11-runtime"),
    ]


def test_find_python_runtime_spec_returns_none_when_missing(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")

    assert find_python_runtime_spec(tmp_path) is None
