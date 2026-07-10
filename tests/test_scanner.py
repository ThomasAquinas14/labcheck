from __future__ import annotations

import json
from pathlib import Path
import zipfile

from labcheck.checks import (
    check_absolute_paths,
    check_ci_python_runtime_conflict,
    check_ci_workflow_has_verification_step,
    check_ci_workflow_drift,
    check_dockerfile_missing_dependency_install,
    check_current_time_usage,
    check_floating_docker_base_images,
    check_floating_github_action_refs,
    check_gitignored_input_artifacts,
    check_hardcoded_secrets,
    check_inline_command_missing_paths,
    check_inline_system_package_installs,
    check_interactive_prompts,
    check_missing_local_dependency_paths,
    check_missing_dependency_setup_instructions,
    check_missing_data_versioning_restore_steps,
    check_missing_input_artifacts,
    check_missing_notebook_kernel_metadata,
    check_missing_numpy_default_rng_seed,
    check_missing_output_directories,
    check_missing_requirement_include_files,
    check_missing_local_module_imports,
    check_notebook_inline_unpinned_installs,
    check_missing_globbed_input_paths,
    check_mutable_remote_input_artifacts,
    check_missing_optuna_sampler_seed,
    check_missing_pandas_random_state,
    check_missing_polars_seed,
    check_missing_pytorch_dataloader_generator,
    check_missing_pytorch_dataloader_worker_init,
    check_missing_pytorch_random_split_generator,
    check_missing_sklearn_random_state,
    check_missing_tensorflow_seed,
    check_missing_xgboost_random_state,
    check_orphan_output_artifacts,
    check_python_hash_usage,
    check_pytorch_deterministic_backend,
    check_reused_jax_prng_key,
    check_remote_artifact_without_checksum,
    check_remote_download_without_timeout,
    check_set_derived_order,
    check_timestamped_output_paths,
    check_undeclared_common_imports,
    check_undocumented_accelerator_requirement,
    check_undocumented_environment_variables,
    check_unpinned_huggingface_revisions,
    check_unpinned_vcs_dependencies,
    check_unsorted_file_discovery_order,
    check_working_directory_changes,
)
from labcheck.graph import build_provenance_graph
from labcheck.scanner import scan_path
from labcheck.source_analysis import SourceArtifact


def test_scan_broken_repo_finds_expected_checks() -> None:
    report = scan_path("examples/broken-repo")
    found = {finding.check_id for finding in report.findings}
    assert {"LC001", "LC002", "LC004", "LC005", "LC006", "LC007", "LC008", "LC010", "LC011", "LC012"}.issubset(found)
    assert len(report.graph.nodes) >= 4
    assert len(report.graph.edges) >= 2


def test_scan_clean_notebook_has_no_findings() -> None:
    report = scan_path("examples/clean-notebook")
    assert report.findings == []
    assert report.scores.overall_score == 100
    assert len(report.graph.nodes) >= 1


def test_scan_single_notebook_reports_missing_manifest() -> None:
    notebook_path = Path("examples/notebook-only/analysis.ipynb")
    report = scan_path(str(notebook_path))
    found = {finding.check_id for finding in report.findings}
    assert "LC003" in found


def test_missing_input_artifact_finding_mentions_missing_path() -> None:
    report = scan_path("examples/broken-repo")
    finding = next(finding for finding in report.findings if finding.check_id == "LC005")
    assert "data/train.csv" in finding.evidence
    assert finding.file_path == "notebooks/analysis.ipynb"


def test_scan_report_paths_are_posix_style() -> None:
    report = scan_path("examples/broken-repo")
    assert all("\\" not in finding.file_path for finding in report.findings)
    assert all("\\" not in node.label for node in report.graph.nodes)


def test_hidden_notebook_state_finding_mentions_missing_name() -> None:
    report = scan_path("examples/broken-repo")
    finding = next(finding for finding in report.findings if finding.check_id == "LC002")
    assert "1 cells reference names" in finding.evidence
    assert "external_state" in finding.evidence


def test_saved_notebook_error_output_is_flagged(tmp_path: Path) -> None:
    notebook_path = tmp_path / "analysis.ipynb"
    notebook_path.write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "code",
                        "execution_count": 1,
                        "outputs": [
                            {
                                "output_type": "error",
                                "ename": "NameError",
                                "evalue": "name 'df' is not defined",
                                "traceback": ["NameError: name 'df' is not defined"],
                            }
                        ],
                        "source": ["print(df)\n"],
                    }
                ],
                "metadata": {},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        ),
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC011")

    assert finding.severity == "high"
    assert finding.file_path == "analysis.ipynb"
    assert "NameError" in finding.evidence


def test_notebook_without_execution_evidence_is_flagged(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\njupyter notebook analysis.ipynb\n```\n",
        encoding="utf-8",
    )
    notebook_path = tmp_path / "analysis.ipynb"
    notebook_path.write_text(
        json.dumps(
            {
                "cells": [
                    {"cell_type": "code", "execution_count": None, "outputs": [], "source": ["x = 1\n"]},
                    {"cell_type": "code", "execution_count": None, "outputs": [], "source": ["print(x)\n"]},
                ],
                "metadata": {},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        ),
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC014")

    assert finding.severity == "low"
    assert finding.file_path == "analysis.ipynb"
    assert "empty execution counts" in finding.evidence


def test_notebook_with_some_execution_evidence_is_not_flagged(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\njupyter notebook analysis.ipynb\n```\n",
        encoding="utf-8",
    )
    notebook_path = tmp_path / "analysis.ipynb"
    notebook_path.write_text(
        json.dumps(
            {
                "cells": [
                    {"cell_type": "code", "execution_count": 1, "outputs": [], "source": ["x = 1\n"]},
                    {"cell_type": "code", "execution_count": None, "outputs": [], "source": ["print(x)\n"]},
                ],
                "metadata": {},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        ),
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC014" not in {finding.check_id for finding in report.findings}


def test_notebook_without_kernel_metadata_is_flagged(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\njupyter notebook analysis.ipynb\n```\n",
        encoding="utf-8",
    )
    notebook_path = tmp_path / "analysis.ipynb"
    notebook_path.write_text(
        json.dumps(
            {
                "cells": [
                    {"cell_type": "code", "execution_count": 1, "outputs": [], "source": ["x = 1\n"]},
                ],
                "metadata": {},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        ),
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC015")

    assert finding.severity == "low"
    assert finding.category == "environment"
    assert finding.file_path == "analysis.ipynb"
    assert "kernelspec.name" in finding.evidence
    assert "language_info.name" in finding.evidence


def test_notebook_with_kernel_metadata_is_not_flagged(tmp_path: Path) -> None:
    notebook = json.loads(Path("examples/clean-notebook/analysis.ipynb").read_text(encoding="utf-8"))
    parsed_path = tmp_path / "analysis.ipynb"
    parsed_path.write_text(json.dumps(notebook), encoding="utf-8")

    from labcheck.notebook_parser import parse_notebook

    findings = check_missing_notebook_kernel_metadata([parse_notebook(parsed_path)], tmp_path)

    assert findings == []


def test_orphan_workflow_node_finding_mentions_python_file() -> None:
    report = scan_path("examples/broken-repo")
    finding = next(finding for finding in report.findings if finding.check_id == "LC010")
    assert finding.file_path == "experiment.py"


def test_scan_zip_archive_finds_expected_checks(tmp_path: Path) -> None:
    source_dir = Path("examples/broken-repo")
    zip_path = tmp_path / "broken-repo.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        for path in source_dir.rglob("*"):
            if path.is_file():
                archive.write(path, Path("broken-repo") / path.relative_to(source_dir))

    report = scan_path(str(zip_path))
    found = {finding.check_id for finding in report.findings}
    assert "LC005" in found
    assert report.summary.target.endswith("broken-repo.zip")


def test_scan_uses_default_labcheck_config_excludes(tmp_path: Path) -> None:
    (tmp_path / ".labcheck.toml").write_text('exclude = ["archived/**"]\n', encoding="utf-8")
    archived = tmp_path / "archived"
    archived.mkdir()
    (archived / "old.py").write_text("import random\nrandom.random()\n", encoding="utf-8")
    active = tmp_path / "active.py"
    active.write_text("print('ready')\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert report.summary.python_files == 1
    assert all("archived" not in finding.file_path for finding in report.findings)
    assert all("archived" not in node.label for node in report.graph.nodes)


def test_scan_accepts_explicit_config_path(tmp_path: Path) -> None:
    config_path = tmp_path / "custom.toml"
    config_path.write_text('exclude = ["ignored.py"]\n', encoding="utf-8")
    (tmp_path / "ignored.py").write_text("import random\nrandom.random()\n", encoding="utf-8")

    report = scan_path(str(tmp_path), config_path=str(config_path))

    assert report.summary.python_files == 0
    assert report.findings == []


def test_scan_config_can_disable_noisy_checks(tmp_path: Path) -> None:
    config_path = tmp_path / "custom.toml"
    config_path.write_text('disabled_checks = ["lc003"]\n', encoding="utf-8")
    (tmp_path / "analysis.py").write_text("print('ready')\n", encoding="utf-8")

    report = scan_path(str(tmp_path), config_path=str(config_path))

    assert "LC003" not in {finding.check_id for finding in report.findings}
    assert report.summary.findings_count == len(report.findings)


def test_scan_config_can_ignore_specific_finding_for_path(tmp_path: Path) -> None:
    config_path = tmp_path / "custom.toml"
    config_path.write_text(
        '[[ignored_findings]]\ncheck_id = "lc010"\npath = "archive/old.py"\nreason = "archival example"\n',
        encoding="utf-8",
    )
    archive_dir = tmp_path / "archive"
    archive_dir.mkdir()
    (archive_dir / "old.py").write_text("print('archival')\n", encoding="utf-8")

    report = scan_path(str(tmp_path), config_path=str(config_path))

    assert not any(finding.check_id == "LC010" and finding.file_path == "archive/old.py" for finding in report.findings)
    assert report.summary.findings_count == len(report.findings)


def test_scan_config_ignored_findings_support_path_patterns(tmp_path: Path) -> None:
    config_path = tmp_path / "custom.toml"
    config_path.write_text(
        '[[ignored_findings]]\ncheck_id = "LC007"\npath = "archive/**"\n',
        encoding="utf-8",
    )
    archive_dir = tmp_path / "archive"
    active_dir = tmp_path / "active"
    archive_dir.mkdir()
    active_dir.mkdir()
    (archive_dir / "old.py").write_text("import random\nrandom.random()\n", encoding="utf-8")
    (active_dir / "live.py").write_text("import random\nrandom.random()\n", encoding="utf-8")

    report = scan_path(str(tmp_path), config_path=str(config_path))

    assert not any(finding.check_id == "LC007" and finding.file_path == "archive/old.py" for finding in report.findings)
    assert any(finding.check_id == "LC007" and finding.file_path == "active/live.py" for finding in report.findings)


def test_scan_flags_missing_python_runtime_for_runnable_repo(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "analysis.py").write_text("print('ready')\n", encoding="utf-8")

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC012")

    assert finding.severity == "medium"
    assert finding.category == "environment"
    assert "Python runtime version" in finding.title


def test_scan_flags_missing_run_instructions_for_runnable_repo(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "analysis.py").write_text("print('ready')\n", encoding="utf-8")

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC013")

    assert finding.severity == "medium"
    assert finding.category == "onboarding"
    assert "README.md is missing" in finding.evidence


def test_scan_accepts_readme_run_instructions(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "analysis.py").write_text("print('ready')\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        """
## Quick start

```bash
python analysis.py
```
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC013" not in {finding.check_id for finding in report.findings}


def test_scan_flags_missing_dependency_setup_when_manifest_exists(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "analysis.py").write_text("print('ready')\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\npython analysis.py\n```\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC021")

    assert finding.severity == "medium"
    assert finding.category == "onboarding"
    assert "requirements.txt" in finding.evidence


def test_dependency_setup_check_accepts_documented_install_step(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\npython -m pip install -r requirements.txt\npython analysis.py\n```\n",
        encoding="utf-8",
    )

    findings = check_missing_dependency_setup_instructions(
        tmp_path,
        notebooks=[],
        python_files=[tmp_path / "analysis.py"],
    )

    assert findings == []


def test_scan_flags_readme_make_target_when_makefile_is_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "```bash\nmake reproduce\n```\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC008")

    assert finding.file_path == "README.md"
    assert "requires a Makefile" in finding.evidence


def test_scan_flags_readme_make_target_when_target_is_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "```bash\nmake reproduce\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "Makefile").write_text(
        "train:\n\tpython train.py\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC008")

    assert finding.file_path == "README.md"
    assert "target 'reproduce'" in finding.evidence


def test_scan_accepts_existing_readme_make_target(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "```bash\nmake reproduce\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "Makefile").write_text(
        "train reproduce:\n\tpython train.py\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_python_module_when_module_is_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "```bash\npython -m demo_lab.train\n```\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC008")

    assert finding.file_path == "README.md"
    assert "Python module 'demo_lab.train'" in finding.evidence


def test_scan_accepts_existing_root_readme_python_module(tmp_path: Path) -> None:
    package_dir = tmp_path / "demo_lab"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "train.py").write_text("print('ready')\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\npython -m demo_lab.train\n```\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_accepts_existing_src_layout_readme_python_module(tmp_path: Path) -> None:
    package_dir = tmp_path / "src" / "demo_lab" / "workflow"
    package_dir.mkdir(parents=True)
    (package_dir / "__main__.py").write_text("print('ready')\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\npython -m demo_lab.workflow\n```\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_uv_python_script_when_script_is_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "- uv run python scripts/train.py --seed 7\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC008")

    assert finding.file_path == "README.md"
    assert "uv run python scripts/train.py" in finding.evidence
    assert "scripts/train.py" in finding.evidence


def test_scan_accepts_existing_readme_uv_python_module(tmp_path: Path) -> None:
    package_dir = tmp_path / "src" / "demo_lab"
    package_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "report.py").write_text("print('ready')\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "- uv run python -m demo_lab.report\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_accepts_existing_readme_uv_project_script(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "```bash\nuv run train-model --seed 7\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "demo-lab"
version = "0.1.0"

[project.scripts]
train-model = "demo_lab.train:main"
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_uv_project_script_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "```bash\nuv run train-model --seed 7\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "demo-lab"
version = "0.1.0"

[project.scripts]
report = "demo_lab.report:main"
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC008")

    assert finding.file_path == "README.md"
    assert "uv run train-model" in finding.evidence
    assert "pyproject script 'train-model'" in finding.evidence


def test_scan_accepts_existing_readme_task_runner_aliases(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
pixi run reproduce
nox -s tests
nox --session docs
task train
uv run task report
```
""",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "demo-lab"
version = "0.1.0"

[tool.pixi.tasks]
reproduce = "python scripts/reproduce.py"

[tool.taskipy.tasks]
train = "python scripts/train.py"
report = "python scripts/report.py"
""",
        encoding="utf-8",
    )
    (tmp_path / "noxfile.py").write_text(
        """
import nox

@nox.session
def tests(session):
    session.run("pytest")

@nox.session(name="docs")
def build_docs(session):
    session.run("python", "docs.py")
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_task_runner_aliases_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
pixi run reproduce
nox -s tests
task train
```
""",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "demo-lab"
version = "0.1.0"

[tool.pixi.tasks]
lint = "ruff check ."

[tool.taskipy.tasks]
format = "ruff format ."
""",
        encoding="utf-8",
    )
    (tmp_path / "noxfile.py").write_text(
        """
import nox

@nox.session
def lint(session):
    session.run("ruff", "check", ".")
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "pixi task 'reproduce'" in evidence
    assert "nox session 'tests'" in evidence
    assert "taskipy task 'train'" in evidence


def test_scan_accepts_existing_readme_invoke_and_taskfile_aliases(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
invoke reproduce
inv report
task build
```
""",
        encoding="utf-8",
    )
    (tmp_path / "tasks.py").write_text(
        """
from invoke import task

@task
def reproduce(c):
    c.run("python scripts/reproduce.py")

@task(name="report")
def build_report(c):
    c.run("python scripts/report.py")
""",
        encoding="utf-8",
    )
    (tmp_path / "Taskfile.yml").write_text(
        """
version: '3'
tasks:
  build:
    cmds:
      - python scripts/build.py
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_invoke_and_taskfile_aliases_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
invoke reproduce
inv report
task build
```
""",
        encoding="utf-8",
    )
    (tmp_path / "tasks.py").write_text(
        """
from invoke import task

@task
def lint(c):
    c.run("ruff check .")
""",
        encoding="utf-8",
    )
    (tmp_path / "Taskfile.yml").write_text(
        """
version: '3'
tasks:
  lint:
    cmds:
      - ruff check .
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Invoke task 'reproduce'" in evidence
    assert "Invoke task 'report'" in evidence
    assert "Taskfile task 'build'" in evidence


def test_scan_accepts_existing_readme_tox_and_rake_aliases(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
tox -e py311,lint
tox run -e docs
rake reproduce
bundle exec rake data:build
```
""",
        encoding="utf-8",
    )
    (tmp_path / "tox.ini").write_text(
        """
[tox]
envlist =
    py{310,311}
    lint

[testenv:docs]
commands = python docs.py
""",
        encoding="utf-8",
    )
    (tmp_path / "Rakefile").write_text(
        """
task :reproduce do
  sh "python scripts/reproduce.py"
end

namespace :data do
  task :build do
    sh "python scripts/build_data.py"
  end
end
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_tox_and_rake_aliases_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
tox -e py311,docs
rake reproduce
bundle exec rake data:build
```
""",
        encoding="utf-8",
    )
    (tmp_path / "tox.ini").write_text(
        """
[tox]
envlist = lint
""",
        encoding="utf-8",
    )
    (tmp_path / "Rakefile").write_text(
        """
task :lint do
  sh "ruby -c app.rb"
end
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "tox environment(s) docs, py311" in evidence
    assert "Rake task 'reproduce'" in evidence
    assert "Rake task 'data:build'" in evidence


def test_scan_accepts_existing_readme_snakemake_targets(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
snakemake --cores 4 all
snakemake --use-conda results/summary.csv
snakemake plots/final.png
```
""",
        encoding="utf-8",
    )
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "summary.csv").write_text("metric,value\n", encoding="utf-8")
    (tmp_path / "Snakefile").write_text(
        """
rule all:
    input:
        "results/summary.csv"

rule plot:
    output:
        "plots/final.png"
    shell:
        "python scripts/plot.py"
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_snakemake_targets_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
snakemake --cores 4 report
snakemake results/missing.csv
```
""",
        encoding="utf-8",
    )
    (tmp_path / "Snakefile").write_text(
        """
rule all:
    input:
        "results/summary.csv"

rule build:
    output:
        "results/summary.csv"
    shell:
        "python scripts/build.py"
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Snakemake target 'report'" in evidence
    assert "Snakemake target 'results/missing.csv'" in evidence


def test_scan_accepts_existing_readme_nextflow_profiles_and_entries(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
nextflow run main.nf -profile docker,test -entry align_reads
nextflow run nf-core/rnaseq -profile test,docker
```
""",
        encoding="utf-8",
    )
    (tmp_path / "main.nf").write_text(
        """
process ALIGN {
  script:
  "echo ok"
}

workflow align_reads {
  ALIGN()
}
""",
        encoding="utf-8",
    )
    (tmp_path / "nextflow.config").write_text(
        """
profiles {
  docker {
    docker.enabled = true
  }
  test {
    params.test = true
  }
}
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_nextflow_profiles_and_entries_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
nextflow run missing.nf -profile docker,slurm -entry align_reads
```
""",
        encoding="utf-8",
    )
    (tmp_path / "main.nf").write_text(
        """
workflow report {
  emit:
  done = true
}
""",
        encoding="utf-8",
    )
    (tmp_path / "nextflow.config").write_text(
        """
profiles {
  docker {
    docker.enabled = true
  }
}
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Nextflow pipeline 'missing.nf'" in evidence

    (tmp_path / "missing.nf").write_text("workflow report {}\n", encoding="utf-8")
    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Nextflow profile(s) slurm" in evidence
    assert "Nextflow entry 'align_reads'" not in evidence

    (tmp_path / "nextflow.config").write_text(
        """
profiles {
  docker {}
  slurm {}
}
""",
        encoding="utf-8",
    )
    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Nextflow entry 'align_reads'" in evidence


def test_scan_accepts_existing_readme_cromwell_workflow_inputs_and_root(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
java -jar cromwell.jar run workflows/main.wdl --inputs inputs/demo.json --workflow-root workflows
cromwell run https://example.org/workflow.wdl --inputs inputs/remote.json
```
""",
        encoding="utf-8",
    )
    (tmp_path / "workflows").mkdir()
    (tmp_path / "workflows" / "main.wdl").write_text("workflow demo {}\n", encoding="utf-8")
    (tmp_path / "inputs").mkdir()
    (tmp_path / "inputs" / "demo.json").write_text("{}\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_cromwell_workflow_inputs_and_root_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
java -jar cromwell.jar run workflows/main.wdl --inputs inputs/demo.json --workflow-root workflows
```
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "WDL workflow 'workflows/main.wdl'" in evidence

    (tmp_path / "workflows").mkdir()
    (tmp_path / "workflows" / "main.wdl").write_text("workflow demo {}\n", encoding="utf-8")
    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Cromwell input file(s) inputs/demo.json" in evidence

    (tmp_path / "inputs").mkdir()
    (tmp_path / "inputs" / "demo.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        """
```bash
java -jar cromwell.jar run workflows/main.wdl --inputs inputs/demo.json --workflow-root imports
```
""",
        encoding="utf-8",
    )
    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Cromwell workflow root 'imports'" in evidence


def test_scan_accepts_existing_readme_cwl_workflow_and_job_files(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
cwltool --outdir results workflows/main.cwl inputs/demo.yml
cwl-runner https://example.org/workflow.cwl inputs/remote.yml
```
""",
        encoding="utf-8",
    )
    (tmp_path / "workflows").mkdir()
    (tmp_path / "workflows" / "main.cwl").write_text("cwlVersion: v1.2\nclass: Workflow\n", encoding="utf-8")
    (tmp_path / "inputs").mkdir()
    (tmp_path / "inputs" / "demo.yml").write_text("{}\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_cwl_workflow_and_job_files_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
cwltool workflows/main.cwl inputs/demo.yml
```
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "CWL workflow/tool 'workflows/main.cwl'" in evidence

    (tmp_path / "workflows").mkdir()
    (tmp_path / "workflows" / "main.cwl").write_text("cwlVersion: v1.2\nclass: Workflow\n", encoding="utf-8")
    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "CWL job file 'inputs/demo.yml'" in evidence


def test_scan_accepts_existing_readme_papermill_input_and_parameter_files(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
papermill --log-output notebooks/input.ipynb reports/output.ipynb -f params/demo.yaml
papermill s3://bucket/input.ipynb s3://bucket/output.ipynb
```
""",
        encoding="utf-8",
    )
    (tmp_path / "notebooks").mkdir()
    (tmp_path / "notebooks" / "input.ipynb").write_text(
        json.dumps(
            {
                "cells": [],
                "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3"}},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "params").mkdir()
    (tmp_path / "params" / "demo.yaml").write_text("alpha: 0.1\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_papermill_input_and_parameter_files_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
papermill notebooks/input.ipynb reports/output.ipynb -f params/demo.yaml
```
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Papermill input notebook 'notebooks/input.ipynb'" in evidence

    (tmp_path / "notebooks").mkdir()
    (tmp_path / "notebooks" / "input.ipynb").write_text(
        json.dumps({"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}),
        encoding="utf-8",
    )
    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Papermill parameter file(s) params/demo.yaml" in evidence


def test_scan_accepts_existing_readme_dvc_targets(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
dvc repro train
dvc repro dvc.yaml:evaluate
dvc pull data/raw
```
""",
        encoding="utf-8",
    )
    (tmp_path / "dvc.yaml").write_text(
        """
stages:
  train:
    cmd: python train.py
  evaluate:
    cmd: python evaluate.py
""",
        encoding="utf-8",
    )
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "raw.dvc").write_text("outs:\n- md5: abc\n  path: raw\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_dvc_targets_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
dvc repro train
dvc pull data/raw
```
""",
        encoding="utf-8",
    )
    (tmp_path / "dvc.yaml").write_text(
        """
stages:
  evaluate:
    cmd: python evaluate.py
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "DVC target(s) train" in evidence
    assert "DVC target(s) data/raw" in evidence


def test_scan_accepts_existing_readme_quarto_render_targets(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
quarto render paper.qmd --to html
quarto render notebooks/demo.ipynb
quarto render docs
quarto render
```
""",
        encoding="utf-8",
    )
    (tmp_path / "paper.qmd").write_text("---\ntitle: Demo\n---\n\nReady.\n", encoding="utf-8")
    (tmp_path / "notebooks").mkdir()
    (tmp_path / "notebooks" / "demo.ipynb").write_text(
        json.dumps({"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}),
        encoding="utf-8",
    )
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "index.qmd").write_text("---\ntitle: Docs\n---\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_quarto_render_targets_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
quarto render paper.qmd --to html
quarto render docs
```
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Quarto render target 'paper.qmd'" in evidence
    assert "Quarto render target 'docs'" in evidence


def test_scan_accepts_existing_readme_jupytext_sync_targets(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
jupytext --sync notebooks/demo.ipynb
jupytext --set-formats ipynb,py:percent --sync notebooks/pair.py
jupytext --sync --pipe black notebooks/clean.ipynb
```
""",
        encoding="utf-8",
    )
    (tmp_path / "notebooks").mkdir()
    for name in ("demo.ipynb", "clean.ipynb"):
        (tmp_path / "notebooks" / name).write_text(
            json.dumps({"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}),
            encoding="utf-8",
        )
    (tmp_path / "notebooks" / "pair.py").write_text("# %%\nprint('ready')\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_jupytext_sync_targets_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
jupytext --sync notebooks/demo.ipynb
jupytext --sync notebooks/pair.py
```
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Jupytext sync target(s) notebooks/demo.ipynb" in evidence
    assert "Jupytext sync target(s) notebooks/pair.py" in evidence


def test_scan_accepts_existing_readme_kedro_pipeline_targets(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
kedro run --pipeline data_science
kedro run --pipelines=data_engineering,reporting
kedro run
```
""",
        encoding="utf-8",
    )
    registry = tmp_path / "src" / "demo_project" / "pipeline_registry.py"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        """
def register_pipelines():
    return {
        "__default__": None,
        "data_science": None,
        "reporting": None,
    }
""",
        encoding="utf-8",
    )
    pipeline_dir = tmp_path / "src" / "demo_project" / "pipelines" / "data_engineering"
    pipeline_dir.mkdir(parents=True)
    (pipeline_dir / "pipeline.py").write_text("def create_pipeline(): pass\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_kedro_pipeline_targets_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
kedro run --pipeline data_science
kedro run -p reporting
```
""",
        encoding="utf-8",
    )
    registry = tmp_path / "src" / "demo_project" / "pipeline_registry.py"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        """
def register_pipelines():
    return {"data_engineering": None}
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Kedro pipeline(s) data_science" in evidence
    assert "Kedro pipeline(s) reporting" in evidence


def test_scan_accepts_existing_readme_prefect_flow_names(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
prefect deployment run train-flow/prod
uv run prefect deployment run data-flow/daily
prefect deployment run yaml_flow/nightly
```
""",
        encoding="utf-8",
    )
    flows = tmp_path / "flows.py"
    flows.write_text(
        """
from prefect import flow

@flow(name="train-flow")
def train_model():
    pass

@flow
def data_flow():
    pass
""",
        encoding="utf-8",
    )
    (tmp_path / "prefect.yaml").write_text(
        """
deployments:
  - name: nightly
    entrypoint: flows.py:yaml_flow
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_prefect_flow_names_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
prefect deployment run train-flow/prod
uv run prefect deployment run data-flow/daily
```
""",
        encoding="utf-8",
    )
    (tmp_path / "flows.py").write_text(
        """
from prefect import flow

@flow(name="other-flow")
def other():
    pass
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Prefect flow 'train-flow'" in evidence
    assert "Prefect flow 'data-flow'" in evidence


def test_scan_accepts_existing_readme_mlflow_entry_points(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
mlflow run . -e train
uv run mlflow run experiments/model --entry-point evaluate
mlflow run scripts -e train.py
```
""",
        encoding="utf-8",
    )
    (tmp_path / "MLproject").write_text(
        """
name: demo
entry_points:
  train:
    command: "python train.py"
""",
        encoding="utf-8",
    )
    project_dir = tmp_path / "experiments" / "model"
    project_dir.mkdir(parents=True)
    (project_dir / "MLproject").write_text(
        """
entry_points:
  evaluate:
    command: "python evaluate.py"
""",
        encoding="utf-8",
    )
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "train.py").write_text("print('ready')\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_mlflow_entry_points_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
mlflow run . -e train
uv run mlflow run experiments/model --entry-point evaluate
```
""",
        encoding="utf-8",
    )
    (tmp_path / "MLproject").write_text(
        """
entry_points:
  score:
    command: "python score.py"
""",
        encoding="utf-8",
    )
    (tmp_path / "experiments").mkdir()

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "MLflow entry point 'train'" in evidence
    assert "MLflow project 'experiments/model'" in evidence


def test_scan_accepts_existing_readme_dbt_selectors(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
dbt run --select orders
dbt test -s path:models/marts/customers.sql
uv run dbt build --cache-selected-only --models staging.orders,staging.customers --target prod
dbt ls --selector nightly
```
""",
        encoding="utf-8",
    )
    (tmp_path / "dbt_project.yml").write_text("name: demo_dbt\n", encoding="utf-8")
    models_dir = tmp_path / "models" / "marts"
    models_dir.mkdir(parents=True)
    (models_dir / "orders.sql").write_text("select 1 as order_id\n", encoding="utf-8")
    (models_dir / "customers.sql").write_text("select 1 as customer_id\n", encoding="utf-8")
    (tmp_path / "selectors.yml").write_text(
        """
selectors:
  - name: nightly
    definition:
      method: path
      value: models/marts
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_dbt_selectors_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
dbt run --select missing_model
dbt test -s path:models/marts/missing.sql
dbt ls --selector stale
```
""",
        encoding="utf-8",
    )
    (tmp_path / "dbt_project.yml").write_text("name: demo_dbt\n", encoding="utf-8")
    models_dir = tmp_path / "models" / "marts"
    models_dir.mkdir(parents=True)
    (models_dir / "orders.sql").write_text("select 1 as order_id\n", encoding="utf-8")
    (tmp_path / "selectors.yml").write_text(
        """
selectors:
  - name: nightly
    definition:
      method: path
      value: models/marts
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "dbt selector(s) missing_model" in evidence
    assert "dbt selector(s) path:models/marts/missing.sql" in evidence
    assert "dbt selector(s) selector:stale" in evidence


def test_scan_accepts_existing_readme_great_expectations_checkpoints(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
great_expectations checkpoint run daily
gx checkpoint run --checkpoint-name weekly
uv run gx checkpoint run --context-root-dir gx nightly
```
""",
        encoding="utf-8",
    )
    ge_checkpoints = tmp_path / "great_expectations" / "checkpoints"
    ge_checkpoints.mkdir(parents=True)
    (ge_checkpoints / "daily.yml").write_text("name: daily\n", encoding="utf-8")
    (ge_checkpoints / "weekly.yaml").write_text("name: weekly_explicit\n", encoding="utf-8")
    gx_checkpoints = tmp_path / "gx" / "checkpoints"
    gx_checkpoints.mkdir(parents=True)
    (gx_checkpoints / "nightly.json").write_text('{"name": "nightly"}\n', encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_great_expectations_checkpoints_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
great_expectations checkpoint run missing_checkpoint
gx checkpoint run stale
```
""",
        encoding="utf-8",
    )
    checkpoints = tmp_path / "great_expectations" / "checkpoints"
    checkpoints.mkdir(parents=True)
    (checkpoints / "daily.yml").write_text("name: daily\n", encoding="utf-8")

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Great Expectations checkpoint 'missing_checkpoint'" in evidence
    assert "Great Expectations checkpoint 'stale'" in evidence


def test_scan_accepts_existing_readme_dagster_targets(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
dagster job execute -f definitions.py -j train_model
dg launch --job daily_assets --assets target/main/raw_customers,feature_table
uv run dagster asset materialize --select target/main/raw_customers
```
""",
        encoding="utf-8",
    )
    (tmp_path / "definitions.py").write_text(
        """
from dagster import AssetOut, asset, define_asset_job, job, multi_asset

@job(name="train_model")
def train_job():
    pass

daily_assets = define_asset_job("daily_assets")

@asset(key_prefix=["target", "main"], name="raw_customers")
def raw_customers_asset():
    pass

@asset
def feature_table():
    pass

@multi_asset(outs={"summary_table": AssetOut()})
def summaries():
    pass
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_dagster_targets_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
dagster job execute -f definitions.py -j missing_job
dg launch --assets missing_asset
```
""",
        encoding="utf-8",
    )
    (tmp_path / "definitions.py").write_text(
        """
from dagster import asset, job

@job
def train_model():
    pass

@asset
def raw_customers():
    pass
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Dagster job(s) missing_job" in evidence
    assert "asset(s) missing_asset" in evidence


def test_scan_accepts_existing_readme_ploomber_targets(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
ploomber task --status load_data
ploomber build --partially train_model
uv run ploomber build --entry-point pipeline.yaml --partially imported_task
```
""",
        encoding="utf-8",
    )
    (tmp_path / "pipeline.yaml").write_text(
        """
import_tasks_from:
  - imported.yaml
tasks:
  - source: tasks/load_data.py
  - source: tasks/train.py
    name: train_model
""",
        encoding="utf-8",
    )
    (tmp_path / "imported.yaml").write_text(
        """
tasks:
  - source: tasks/imported.py
    name: imported_task
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_ploomber_targets_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
ploomber task missing_task
ploomber build --partially stale_task
```
""",
        encoding="utf-8",
    )
    (tmp_path / "pipeline.yaml").write_text(
        """
tasks:
  - source: tasks/load_data.py
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Ploomber task(s) missing_task" in evidence
    assert "Ploomber task(s) stale_task" in evidence


def test_scan_accepts_existing_readme_luigi_targets(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
luigi --module workflows.tasks TrainModel --local-scheduler --date 2026-01-01
uv run luigi --module workflows.tasks experiments.NamespacedTask --scheduler-host localhost
```
""",
        encoding="utf-8",
    )
    tasks_file = tmp_path / "workflows" / "tasks.py"
    tasks_file.parent.mkdir()
    tasks_file.write_text(
        """
import luigi

class TrainModel(luigi.Task):
    pass

class NamespacedTask(luigi.WrapperTask):
    task_namespace = "experiments"
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_luigi_targets_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
luigi --module workflows.tasks MissingTask --local-scheduler
luigi --module workflows.missing TrainModel --local-scheduler
```
""",
        encoding="utf-8",
    )
    tasks_file = tmp_path / "workflows" / "tasks.py"
    tasks_file.parent.mkdir()
    tasks_file.write_text(
        """
import luigi

class TrainModel(luigi.Task):
    pass
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Luigi task 'MissingTask'" in evidence
    assert "in module 'workflows.missing'" in evidence


def test_scan_accepts_existing_readme_meltano_jobs(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
meltano run daily-load
uv run meltano --environment=prod run nightly-sync --dry-run
meltano run tap-gitlab target-postgres
```
""",
        encoding="utf-8",
    )
    (tmp_path / "meltano.yml").write_text(
        """
version: 1
jobs:
  - name: daily-load
    tasks:
      - tap-gitlab target-postgres
  - name: nightly-sync
    tasks:
      - tap-gitlab target-bigquery
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_meltano_jobs_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
meltano run stale-load
```
""",
        encoding="utf-8",
    )
    (tmp_path / "meltano.yml").write_text(
        """
version: 1
jobs:
  - name: daily-load
    tasks:
      - tap-gitlab target-postgres
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Meltano job(s) stale-load" in evidence


def test_scan_flags_readme_meltano_jobs_when_project_file_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
meltano run daily-load
```
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "no meltano.yml or meltano.yaml project file was found" in evidence


def test_scan_accepts_existing_readme_flyte_targets(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
flyte run --local workflows/train.py train_model --epochs 2
uv run pyflyte run --remote workflows/train.py scoring_workflow --name smoke
pyflyte --config config.yaml run --remote workflows/train.py package_model --image ghcr.io/acme/flyte:latest
flyte run deployed-task project.domain.task
```
""",
        encoding="utf-8",
    )
    script = tmp_path / "workflows" / "train.py"
    script.parent.mkdir()
    script.write_text(
        """
from flytekit import task, workflow
import flyte

env = flyte.TaskEnvironment(name="modeling")

@task
def train_model(epochs: int = 1) -> str:
    return "model"

@workflow
def scoring_workflow() -> str:
    return train_model()

@env.task
async def package_model() -> str:
    return "package"
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_flyte_targets_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
flyte run workflows/train.py missing_workflow
pyflyte run workflows/missing.py train_model
```
""",
        encoding="utf-8",
    )
    script = tmp_path / "workflows" / "train.py"
    script.parent.mkdir()
    script.write_text(
        """
from flytekit import task

@task
def train_model() -> str:
    return "model"
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Flyte workflow/task 'missing_workflow'" in evidence
    assert "Flyte script 'workflows/missing.py'" in evidence


def test_scan_accepts_existing_readme_argo_targets(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
argo submit workflows/model.yaml --entrypoint train
uv run argo submit --entrypoint=score workflows/model.yaml -p split=test
argo submit workflows/default.yaml
argo submit --from workflowtemplate/cluster-template
```
""",
        encoding="utf-8",
    )
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()
    (workflow_dir / "model.yaml").write_text(
        """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
spec:
  entrypoint: main
  templates:
    - name: main
      steps:
        - - name: train
            template: train
    - name: train
      container:
        image: python:3.11
    - name: score
      container:
        image: python:3.11
""",
        encoding="utf-8",
    )
    (workflow_dir / "default.yaml").write_text(
        """
apiVersion: argoproj.io/v1alpha1
kind: WorkflowTemplate
spec:
  entrypoint: run-all
  templates:
    - name: run-all
      container:
        image: alpine:3.20
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_argo_targets_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
argo submit workflows/model.yaml --entrypoint stale
argo submit workflows/missing.yaml --entrypoint train
argo submit workflows/no-templates.yaml --entrypoint train
```
""",
        encoding="utf-8",
    )
    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()
    (workflow_dir / "model.yaml").write_text(
        """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
spec:
  entrypoint: train
  templates:
    - name: train
      container:
        image: python:3.11
""",
        encoding="utf-8",
    )
    (workflow_dir / "no-templates.yaml").write_text(
        """
apiVersion: argoproj.io/v1alpha1
kind: Workflow
spec:
  entrypoint: train
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Argo entrypoint 'stale'" in evidence
    assert "Argo workflow file 'workflows/missing.yaml'" in evidence
    assert "no local template names were found in 'workflows/no-templates.yaml'" in evidence


def test_scan_accepts_existing_readme_tekton_targets(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
tkn pipeline start build-and-test
uv run tkn task start unit-test --param image=python:3.11
tkn pipeline start -f tekton/pipeline.yaml
tkn task start --filename=tekton/task.yaml unit-test
tkn task start --image ghcr.io/acme/remote-task:latest remote-task
```
""",
        encoding="utf-8",
    )
    tekton_dir = tmp_path / "tekton"
    tekton_dir.mkdir()
    (tekton_dir / "pipeline.yaml").write_text(
        """
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: build-and-test
spec:
  tasks: []
""",
        encoding="utf-8",
    )
    (tekton_dir / "task.yaml").write_text(
        """
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: unit-test
spec:
  steps: []
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_tekton_targets_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
tkn pipeline start stale-pipeline
tkn task start missing-task
tkn pipeline start -f tekton/missing.yaml
tkn task start --filename=tekton/task.yaml wrong-task
```
""",
        encoding="utf-8",
    )
    tekton_dir = tmp_path / "tekton"
    tekton_dir.mkdir()
    (tekton_dir / "pipeline.yaml").write_text(
        """
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: build-and-test
spec:
  tasks: []
""",
        encoding="utf-8",
    )
    (tekton_dir / "task.yaml").write_text(
        """
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: unit-test
spec:
  steps: []
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Tekton pipeline 'stale-pipeline'" in evidence
    assert "Tekton task 'missing-task'" in evidence
    assert "Tekton manifest 'tekton/missing.yaml'" in evidence
    assert "Tekton task 'wrong-task'" in evidence


def test_scan_accepts_existing_readme_ray_job_entrypoints(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
ray job submit --address http://127.0.0.1:8265 -- python scripts/train.py --epochs 2
uv run ray job submit --working-dir . -- uv run python -m demo.jobs.train --smoke
ray job submit -- bash scripts/train.sh
```
""",
        encoding="utf-8",
    )
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "train.py").write_text("print('train')\n", encoding="utf-8")
    jobs_dir = tmp_path / "demo" / "jobs"
    jobs_dir.mkdir(parents=True)
    (tmp_path / "demo" / "__init__.py").write_text("", encoding="utf-8")
    (jobs_dir / "__init__.py").write_text("", encoding="utf-8")
    (jobs_dir / "train.py").write_text("print('module')\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_ray_job_entrypoints_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
ray job submit -- python scripts/missing.py
ray job submit -- python -m demo.jobs.missing
```
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Ray job script 'scripts/missing.py'" in evidence
    assert "Ray job module 'demo.jobs.missing'" in evidence


def test_scan_accepts_existing_readme_dagger_call_targets(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
dagger call train-model --source=.
dagger -m ./ci call build-image
uv run dagger --mod ./ci call lint --json
dagger -m github.com/dagger/hello-dagger call hello
```
""",
        encoding="utf-8",
    )
    (tmp_path / "dagger.json").write_text(
        '{"name": "demo", "sdk": "python", "source": "."}\n',
        encoding="utf-8",
    )
    src_dir = tmp_path / "src" / "demo"
    src_dir.mkdir(parents=True)
    (src_dir / "main.py").write_text(
        """
from dagger import function, object_type

@object_type
class Demo:
    @function
    async def train_model(self) -> str:
        return "ok"
""",
        encoding="utf-8",
    )
    ci_dir = tmp_path / "ci"
    ci_dir.mkdir()
    (ci_dir / "dagger.json").write_text(
        '{"name": "ci", "sdk": "go", "source": "."}\n',
        encoding="utf-8",
    )
    (ci_dir / "main.go").write_text(
        """
package main

import "context"

type Ci struct{}

func (m *Ci) BuildImage(ctx context.Context) (string, error) {
    return "image", nil
}

func (m *Ci) Lint(ctx context.Context) (string, error) {
    return "lint", nil
}
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_dagger_call_targets_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
dagger call train-model
dagger -m ./ci call missing-function
```
""",
        encoding="utf-8",
    )
    ci_dir = tmp_path / "ci"
    ci_dir.mkdir()
    (ci_dir / "dagger.json").write_text(
        '{"name": "ci", "sdk": "go", "source": "."}\n',
        encoding="utf-8",
    )
    (ci_dir / "main.go").write_text(
        """
package main

type Ci struct{}

func (m *Ci) BuildImage() string {
    return "image"
}
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Dagger module '.'" in evidence
    assert "Dagger function 'missing-function'" in evidence


def test_scan_accepts_existing_readme_bazel_targets(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
bazel build //src:train //...
uv run bazel test --config=ci //tests:unit
bazel run --platforms //tools:linux //apps:serve -- --port 8000
bazel build @rules_python//python:defs.bzl
```
""",
        encoding="utf-8",
    )
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "BUILD").write_text(
        """
py_binary(
    name = "train",
    srcs = ["train.py"],
)
""",
        encoding="utf-8",
    )
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "BUILD.bazel").write_text(
        """
py_test(
    name = "unit",
    srcs = ["test_unit.py"],
)
""",
        encoding="utf-8",
    )
    apps_dir = tmp_path / "apps"
    apps_dir.mkdir()
    (apps_dir / "BUILD").write_text(
        """
py_binary(
    name = "serve",
    srcs = ["serve.py"],
)
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_bazel_targets_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
bazel build //src:missing
bazel test //missing:unit
```
""",
        encoding="utf-8",
    )
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "BUILD").write_text(
        """
py_binary(
    name = "train",
    srcs = ["train.py"],
)
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Bazel target(s) //src:missing" in evidence
    assert "//missing:unit" in evidence


def test_scan_accepts_existing_readme_pants_specs(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
pants test src/python:: tests:unit
./pants run src/python/app.py -- --port 8000
uv run pants --changed-since=HEAD lint src/python:lib
```
""",
        encoding="utf-8",
    )
    (tmp_path / "pants.toml").write_text("[GLOBAL]\npants_version = \"2.23.0\"\n", encoding="utf-8")
    src_dir = tmp_path / "src" / "python"
    src_dir.mkdir(parents=True)
    (src_dir / "BUILD").write_text(
        """
python_sources(
    name = "lib",
)
pex_binary(
    name = "app",
    entry_point = "app.py",
)
""",
        encoding="utf-8",
    )
    (src_dir / "app.py").write_text("print('ready')\n", encoding="utf-8")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "BUILD").write_text(
        """
python_tests(
    name = "unit",
)
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_pants_specs_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
pants test src/python:missing tests:unit
pants run src/python/missing_app.py
```
""",
        encoding="utf-8",
    )
    (tmp_path / "pants.toml").write_text("[GLOBAL]\npants_version = \"2.23.0\"\n", encoding="utf-8")
    src_dir = tmp_path / "src" / "python"
    src_dir.mkdir(parents=True)
    (src_dir / "BUILD").write_text(
        """
python_sources(
    name = "lib",
)
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Pants target spec(s) src/python:missing, tests:unit" in evidence
    assert "src/python/missing_app.py" in evidence


def test_scan_accepts_existing_readme_nix_flake_outputs(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
nix flake check
nix build .#labcheck .#dockerImage
nix run .#cli -- --help
uv run nix build path:./nix#tool
nix build nixpkgs#hello
```
""",
        encoding="utf-8",
    )
    (tmp_path / "flake.nix").write_text(
        """
{
  outputs = { self, nixpkgs }: {
    packages.x86_64-linux.default = nixpkgs.legacyPackages.x86_64-linux.hello;
    packages.x86_64-linux.labcheck = nixpkgs.legacyPackages.x86_64-linux.hello;
    packages.x86_64-linux.dockerImage = nixpkgs.legacyPackages.x86_64-linux.hello;
    apps.x86_64-linux.cli = {
      type = "app";
      program = "${self.packages.x86_64-linux.labcheck}/bin/labcheck";
    };
    checks.x86_64-linux.unit = self.packages.x86_64-linux.labcheck;
  };
}
""",
        encoding="utf-8",
    )
    nix_dir = tmp_path / "nix"
    nix_dir.mkdir()
    (nix_dir / "flake.nix").write_text(
        """
{
  outputs = { nixpkgs, ... }: {
    packages.x86_64-linux.tool = nixpkgs.legacyPackages.x86_64-linux.hello;
  };
}
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_nix_flake_outputs_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
nix build .#missing
nix run .#missingApp
nix flake check ./nix
```
""",
        encoding="utf-8",
    )
    (tmp_path / "flake.nix").write_text(
        """
{
  outputs = { nixpkgs, ... }: {
    packages.x86_64-linux.labcheck = nixpkgs.legacyPackages.x86_64-linux.hello;
    apps.x86_64-linux.cli = {
      type = "app";
      program = "${nixpkgs.legacyPackages.x86_64-linux.hello}/bin/hello";
    };
  };
}
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Nix flake output(s) .#missing" in evidence
    assert ".#missingApp" in evidence
    assert "./nix" in evidence


def test_scan_accepts_existing_readme_docker_compose_services(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
docker compose up -d api worker
docker compose -f compose.dev.yml run --rm api pytest -q
docker compose --profile obs logs -f grafana
docker-compose restart db
```
""",
        encoding="utf-8",
    )
    (tmp_path / "compose.yaml").write_text(
        """
services:
  api:
    image: python:3.11-slim
  worker:
    image: python:3.11-slim
  grafana:
    image: grafana/grafana:11.0.0
    profiles: [obs]
  db:
    image: postgres:16
volumes:
  db-data:
""",
        encoding="utf-8",
    )
    (tmp_path / "compose.dev.yml").write_text(
        """
services:
  api:
    build: .
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_docker_compose_services_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
docker compose up api worker
docker compose -f compose.dev.yml run api pytest
```
""",
        encoding="utf-8",
    )
    (tmp_path / "compose.yaml").write_text(
        """
services:
  api:
    image: python:3.11-slim
volumes:
  worker:
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Docker Compose service(s) worker" in evidence
    assert "Docker Compose file(s) compose.dev.yml" in evidence


def test_scan_accepts_existing_readme_docker_compose_env_files(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
docker compose --env-file .env.demo up -d
docker compose --env-file config/dev.env run api pytest -q
docker-compose --env-file=.env.local restart db
docker compose --env-file $COMPOSE_ENV up -d
```
""",
        encoding="utf-8",
    )
    (tmp_path / "compose.yaml").write_text(
        """
services:
  api:
    image: python:3.11
  db:
    image: postgres:16
""",
        encoding="utf-8",
    )
    (tmp_path / ".env.demo").write_text("DEBUG=1\n", encoding="utf-8")
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "dev.env").write_text("APP_ENV=dev\n", encoding="utf-8")
    (tmp_path / ".env.local").write_text("APP_ENV=local\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_docker_compose_env_files_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
docker compose --env-file .env.demo up -d
docker compose --env-file config/dev.env run api pytest -q
```
""",
        encoding="utf-8",
    )
    (tmp_path / "compose.yaml").write_text(
        """
services:
  api:
    image: python:3.11
""",
        encoding="utf-8",
    )
    (tmp_path / "config").mkdir()

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Docker Compose env-file(s) .env.demo" in evidence
    assert "Docker Compose env-file(s) config/dev.env" in evidence


def test_scan_accepts_existing_readme_docker_compose_project_dirs(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
docker compose --project-directory deploy up -d
docker compose --project-directory ./ops run api pytest -q
docker-compose --project-directory stacks/dev logs db
docker compose --project-directory $COMPOSE_PROJECT_DIR up -d
```
""",
        encoding="utf-8",
    )
    deploy = tmp_path / "deploy"
    deploy.mkdir()
    (deploy / "compose.yaml").write_text(
        """
services:
  web:
    image: nginx:1.27
""",
        encoding="utf-8",
    )
    ops = tmp_path / "ops"
    ops.mkdir()
    (ops / "compose.yml").write_text(
        """
services:
  api:
    image: python:3.11
""",
        encoding="utf-8",
    )
    stack = tmp_path / "stacks" / "dev"
    stack.mkdir(parents=True)
    (stack / "docker-compose.yml").write_text(
        """
services:
  db:
    image: postgres:16
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_docker_compose_project_dirs_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
docker compose --project-directory missing up -d
docker compose --project-directory deploy run api pytest -q
```
""",
        encoding="utf-8",
    )
    (tmp_path / "deploy").mkdir()

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Docker Compose project dir(s) missing" in evidence
    assert "Docker Compose file(s) deploy/compose.yaml" in evidence


def test_scan_accepts_existing_readme_docker_compose_profiles(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
docker compose --profile obs logs grafana
docker compose --profile gpu run trainer pytest -q
docker-compose --profile=debug --profile qa up worker
docker compose --profile $COMPOSE_PROFILE up -d
```
""",
        encoding="utf-8",
    )
    (tmp_path / "compose.yaml").write_text(
        """
services:
  grafana:
    image: grafana/grafana:11.0.0
    profiles: [obs]
  trainer:
    image: python:3.11
    profiles:
      - gpu
  worker:
    image: python:3.11
    profiles: ["debug", "qa"]
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_docker_compose_profiles_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
docker compose --profile obs logs grafana
docker compose --profile gpu run trainer pytest -q
```
""",
        encoding="utf-8",
    )
    (tmp_path / "compose.yaml").write_text(
        """
services:
  grafana:
    image: grafana/grafana:11.0.0
  trainer:
    image: python:3.11
    profiles: [cpu]
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Docker Compose profile(s) obs" in evidence
    assert "Docker Compose profile(s) gpu" in evidence


def test_scan_accepts_existing_docker_compose_volume_sources(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Run with docker compose up.\n", encoding="utf-8")
    (tmp_path / "data").mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / "logs").mkdir()
    (tmp_path / "shared").mkdir()
    (tmp_path / "compose.yaml").write_text(
        """
services:
  api:
    image: python:3.11
    volumes:
      - ./data:/data
      - ./config:/config:ro
      - type: bind
        source: ./logs
        target: /logs
      - db-data:/var/lib/postgresql/data
      - /tmp/cache:/cache
      - ${HOST_DATA}:/host-data
volumes:
  db-data:
""",
        encoding="utf-8",
    )
    deploy = tmp_path / "deploy"
    deploy.mkdir()
    (deploy / "compose.yml").write_text(
        """
services:
  worker:
    image: python:3.11
    volumes:
      - ../shared:/shared
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC005")

    assert "Docker Compose bind source" not in evidence


def test_scan_flags_missing_docker_compose_volume_sources(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Run with docker compose up.\n", encoding="utf-8")
    (tmp_path / "compose.yaml").write_text(
        """
services:
  api:
    image: python:3.11
    volumes:
      - ./data:/data
      - ../secrets:/run/secrets
      - type: bind
        source: ./logs
        target: /logs
      - db-data:/var/lib/postgresql/data
      - /tmp/cache:/cache
volumes:
  db-data:
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC005")

    assert "Docker Compose bind source(s)" in evidence
    assert "./data" in evidence
    assert "../secrets" in evidence
    assert "./logs" in evidence
    assert "db-data" not in evidence
    assert "/tmp/cache" not in evidence


def test_scan_accepts_existing_docker_compose_build_paths(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Run with docker compose up --build.\n", encoding="utf-8")
    (tmp_path / "Dockerfile").write_text("FROM python:3.11-slim\n", encoding="utf-8")
    app = tmp_path / "app"
    app.mkdir()
    (app / "Dockerfile").write_text("FROM python:3.11-slim\n", encoding="utf-8")
    api = tmp_path / "services" / "api"
    api.mkdir(parents=True)
    (api / "Dockerfile.prod").write_text("FROM python:3.11-slim\n", encoding="utf-8")
    inline = tmp_path / "services" / "inline"
    inline.mkdir(parents=True)
    object_context = tmp_path / "object"
    object_context.mkdir()
    (object_context / "Dockerfile.custom").write_text("FROM python:3.11-slim\n", encoding="utf-8")
    (tmp_path / "compose.yaml").write_text(
        """
services:
  root:
    build: .
  api:
    build: ./app
  worker:
    build:
      context: services/api
      dockerfile: Dockerfile.prod
  inline:
    build:
      context: services/inline
      dockerfile_inline: |
        FROM python:3.11-slim
  object:
    build: { context: ./object, dockerfile: Dockerfile.custom }
  remote:
    build: https://github.com/example/project.git
  db:
    image: postgres:16
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC005")

    assert "Docker Compose build" not in evidence


def test_scan_flags_missing_docker_compose_build_paths(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Run with docker compose up --build.\n", encoding="utf-8")
    api = tmp_path / "services" / "api"
    api.mkdir(parents=True)
    default_context = tmp_path / "services" / "default"
    default_context.mkdir(parents=True)
    inline = tmp_path / "services" / "inline"
    inline.mkdir(parents=True)
    (tmp_path / "compose.yaml").write_text(
        """
services:
  api:
    build: ./missing
  default:
    build: services/default
  worker:
    build:
      context: services/api
      dockerfile: Dockerfile.prod
  escape:
    build:
      context: ../outside
  inline:
    build:
      context: services/inline
      dockerfile_inline: |
        FROM python:3.11-slim
  remote:
    build: https://github.com/example/project.git
  db:
    image: postgres:16
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC005")

    assert "Docker Compose build context(s)" in evidence
    assert "./missing" in evidence
    assert "../outside" in evidence
    assert "Docker Compose Dockerfile(s)" in evidence
    assert "services/default/Dockerfile" in evidence
    assert "services/api/Dockerfile.prod" in evidence
    assert "services/inline/Dockerfile" not in evidence
    assert "github.com/example/project" not in evidence


def test_scan_accepts_existing_docker_compose_depends_on_services(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Run with docker compose up.\n", encoding="utf-8")
    (tmp_path / "compose.yaml").write_text(
        """
services:
  api:
    image: python:3.11
    depends_on:
      - db
      - redis
  worker:
    image: python:3.11
    depends_on: [api, db]
  dashboard:
    image: nginx:1.27
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
  db:
    image: postgres:16
  redis:
    image: redis:7
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC065" not in {finding.check_id for finding in report.findings}


def test_scan_flags_missing_docker_compose_depends_on_services(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Run with docker compose up.\n", encoding="utf-8")
    (tmp_path / "compose.yaml").write_text(
        """
services:
  api:
    image: python:3.11
    depends_on:
      - db
      - missing-cache
  worker:
    image: python:3.11
    depends_on: [api, stale-db]
  dashboard:
    image: nginx:1.27
    depends_on:
      redis:
        condition: service_started
      missing-queue:
        condition: service_healthy
  db:
    image: postgres:16
  redis:
    image: redis:7
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC065")

    assert "Docker Compose depends_on service(s)" in evidence
    assert "missing-cache" in evidence
    assert "missing-queue" in evidence
    assert "stale-db" in evidence
    assert "condition" not in evidence
    assert "service_started" not in evidence


def test_scan_accepts_existing_docker_compose_service_networks(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Run with docker compose up.\n", encoding="utf-8")
    (tmp_path / "compose.yaml").write_text(
        """
services:
  api:
    image: python:3.11
    networks:
      - backend
      - default
  worker:
    image: python:3.11
    networks: [backend, external-net]
  dashboard:
    image: nginx:1.27
    networks:
      frontend:
        aliases:
          - web
      backend:
        aliases:
          - api
networks:
  backend:
  frontend:
  external-net:
    external: true
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC066" not in {finding.check_id for finding in report.findings}


def test_scan_flags_missing_docker_compose_service_networks(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Run with docker compose up.\n", encoding="utf-8")
    (tmp_path / "compose.yaml").write_text(
        """
services:
  api:
    image: python:3.11
    networks:
      - backend
      - stale-net
  worker:
    image: python:3.11
    networks: [backend, missing-inline]
  dashboard:
    image: nginx:1.27
    networks:
      frontend:
        aliases:
          - web
      missing-map:
        aliases:
          - dash
      default:
        aliases:
          - dashboard
networks:
  backend:
  frontend:
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC066")

    assert "Docker Compose network(s)" in evidence
    assert "missing-inline" in evidence
    assert "missing-map" in evidence
    assert "stale-net" in evidence
    assert "aliases" not in evidence
    assert "default" not in evidence


def test_scan_accepts_existing_docker_compose_healthcheck_scripts(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Run with docker compose up.\n", encoding="utf-8")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "healthcheck.sh").write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
    (scripts / "worker_health.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
    (scripts / "check-api.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
    (tmp_path / "compose.yaml").write_text(
        """
services:
  api:
    image: python:3.11
    healthcheck:
      test: ["CMD", "./scripts/healthcheck.sh"]
  worker:
    image: python:3.11
    healthcheck:
      test: ["CMD-SHELL", "python scripts/worker_health.py || exit 1"]
  dashboard:
    image: python:3.11
    healthcheck:
      test:
        - CMD
        - scripts/check-api.py
  db:
    image: postgres:16
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "postgres"]
  cache:
    image: redis:7
    healthcheck:
      test: CMD-SHELL curl -f http://localhost:8080/health || exit 1
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC067" not in {finding.check_id for finding in report.findings}


def test_scan_flags_missing_docker_compose_healthcheck_scripts(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Run with docker compose up.\n", encoding="utf-8")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "existing.sh").write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
    (tmp_path / "compose.yaml").write_text(
        """
services:
  api:
    image: python:3.11
    healthcheck:
      test: ["CMD", "./scripts/missing.sh"]
  worker:
    image: python:3.11
    healthcheck:
      test: ["CMD-SHELL", "python scripts/missing_health.py || exit 1"]
  dashboard:
    image: python:3.11
    healthcheck:
      test:
        - CMD-SHELL
        - ./scripts/missing-list.sh --flag
  good:
    image: python:3.11
    healthcheck:
      test: ["CMD", "./scripts/existing.sh"]
  remote:
    image: python:3.11
    healthcheck:
      test: ["CMD-SHELL", "curl -f https://example.com/health || exit 1"]
  db:
    image: postgres:16
    healthcheck:
      test: ["CMD", "/usr/bin/pg_isready", "-U", "postgres"]
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC067")

    assert "Docker Compose healthcheck script(s)" in evidence
    assert "./scripts/missing.sh" in evidence
    assert "scripts/missing_health.py" in evidence
    assert "./scripts/missing-list.sh" in evidence
    assert "./scripts/existing.sh" not in evidence
    assert "https://example.com" not in evidence
    assert "/usr/bin/pg_isready" not in evidence


def test_scan_accepts_existing_docker_compose_secret_config_files(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Run with docker compose up.\n", encoding="utf-8")
    secret_dir = tmp_path / "compose-secrets"
    secret_dir.mkdir()
    (secret_dir / "db.txt").write_text("placeholder\n", encoding="utf-8")
    (secret_dir / "api.txt").write_text("placeholder\n", encoding="utf-8")
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "app.yml").write_text("debug: false\n", encoding="utf-8")
    (config_dir / "root.yml").write_text("debug: true\n", encoding="utf-8")
    (tmp_path / "compose.yaml").write_text(
        """
services:
  api:
    image: python:3.11
secrets:
  db_secret:
    file: ./compose-secrets/db.txt
  api_secret: { file: ./compose-secrets/api.txt }
  external_secret:
    external: true
configs:
  app_config:
    file: ./config/app.yml
  root_config: { file: config/root.yml }
  inline_config:
    content: |
      debug: true
  external_config:
    external: true
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC068" not in {finding.check_id for finding in report.findings}


def test_scan_flags_missing_docker_compose_secret_config_files(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Run with docker compose up.\n", encoding="utf-8")
    secret_dir = tmp_path / "compose-secrets"
    secret_dir.mkdir()
    (secret_dir / "existing.txt").write_text("placeholder\n", encoding="utf-8")
    (tmp_path / "compose.yaml").write_text(
        """
services:
  api:
    image: python:3.11
secrets:
  missing_secret:
    file: ./compose-secrets/missing.txt
  existing_secret:
    file: ./compose-secrets/existing.txt
  external_secret:
    file: ./compose-secrets/external-only.txt
    external: true
  remote_secret:
    file: https://example.com/secret.txt
configs:
  missing_config:
    file: ./config/missing.yml
  inline_config:
    content: |
      debug: true
  external_config:
    external: true
  image_config:
    file: /etc/app/config.yml
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC068")

    assert "Docker Compose secret/config file(s)" in evidence
    assert "./compose-secrets/missing.txt" in evidence
    assert "./config/missing.yml" in evidence
    assert "./compose-secrets/existing.txt" not in evidence
    assert "external-only.txt" not in evidence
    assert "https://example.com" not in evidence
    assert "/etc/app/config.yml" not in evidence


def test_scan_accepts_existing_docker_compose_service_env_files(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Run with docker compose up.\n", encoding="utf-8")
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    deploy_dir = tmp_path / "deploy"
    deploy_dir.mkdir()
    (tmp_path / ".env").write_text("DEBUG=1\n", encoding="utf-8")
    (config_dir / "dev.env").write_text("APP_ENV=dev\n", encoding="utf-8")
    (deploy_dir / "worker.env").write_text("WORKER_COUNT=2\n", encoding="utf-8")
    (tmp_path / "compose.yaml").write_text(
        """
services:
  api:
    image: python:3.11
    env_file: .env
  worker:
    image: python:3.11
    env_file:
      - config/dev.env
      - path: deploy/worker.env
        required: true
  dynamic:
    image: python:3.11
    env_file: ${COMPOSE_ENV_FILE}
  absolute:
    image: python:3.11
    env_file: /etc/app.env
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC069" not in {finding.check_id for finding in report.findings}


def test_scan_flags_missing_docker_compose_service_env_files(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Run with docker compose up.\n", encoding="utf-8")
    (tmp_path / ".env").write_text("DEBUG=1\n", encoding="utf-8")
    (tmp_path / "compose.yaml").write_text(
        """
services:
  api:
    image: python:3.11
    env_file: missing.env
  worker:
    image: python:3.11
    env_file:
      - config/missing.env
      - path: deploy/missing-worker.env
        required: false
      - .env
  dynamic:
    image: python:3.11
    env_file: $COMPOSE_ENV_FILE
  absolute:
    image: python:3.11
    env_file: /etc/app.env
  remote:
    image: python:3.11
    env_file: https://example.com/app.env
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC069")
    missing_items = (
        evidence.split("Docker Compose service env_file(s) ", 1)[1]
        .split(" are referenced", 1)[0]
        .split(", ")
    )

    assert "Docker Compose service env_file(s)" in evidence
    assert "missing.env" in evidence
    assert "config/missing.env" in evidence
    assert "deploy/missing-worker.env" in evidence
    assert ".env" not in missing_items
    assert "$COMPOSE_ENV_FILE" not in evidence
    assert "/etc/app.env" not in evidence
    assert "https://example.com" not in evidence


def test_scan_accepts_existing_docker_compose_extends_targets(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Run with docker compose up.\n", encoding="utf-8")
    (tmp_path / "compose.base.yml").write_text(
        """
services:
  base_worker:
    image: python:3.11
  base_web:
    image: nginx:1.27
""",
        encoding="utf-8",
    )
    (tmp_path / "compose.yaml").write_text(
        """
services:
  base_api:
    image: python:3.11
  api:
    extends: base_api
  worker:
    extends:
      file: compose.base.yml
      service: base_worker
  web:
    extends: { file: compose.base.yml, service: base_web }
  dynamic:
    extends:
      file: ${BASE_COMPOSE_FILE}
      service: base_api
  remote:
    extends:
      file: https://example.com/compose.yml
      service: base_api
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC070" not in {finding.check_id for finding in report.findings}


def test_scan_flags_missing_docker_compose_extends_targets(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Run with docker compose up.\n", encoding="utf-8")
    (tmp_path / "compose.base.yml").write_text(
        """
services:
  base_worker:
    image: python:3.11
""",
        encoding="utf-8",
    )
    (tmp_path / "compose.yaml").write_text(
        """
services:
  base_api:
    image: python:3.11
  good:
    extends: base_api
  api:
    extends: missing_base
  worker:
    extends:
      file: missing-compose.yml
      service: base_worker
  web:
    extends: { file: compose.base.yml, service: missing_web }
  dynamic:
    extends:
      file: $BASE_COMPOSE_FILE
      service: missing_dynamic
  absolute:
    extends:
      file: /etc/compose.yml
      service: missing_absolute
  remote:
    extends:
      file: https://example.com/compose.yml
      service: missing_remote
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC070")

    assert "Docker Compose extends file(s)" in evidence
    assert "missing-compose.yml" in evidence
    assert "Docker Compose extends service target(s)" in evidence
    assert "api->missing_base" in evidence
    assert "web->missing_web in compose.base.yml" in evidence
    assert "good->base_api" not in evidence
    assert "$BASE_COMPOSE_FILE" not in evidence
    assert "missing_dynamic" not in evidence
    assert "/etc/compose.yml" not in evidence
    assert "https://example.com" not in evidence


def test_scan_accepts_existing_docker_compose_include_files(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Run with docker compose up.\n", encoding="utf-8")
    include_dir = tmp_path / "compose"
    include_dir.mkdir()
    (include_dir / "common.yml").write_text("services:\n  common:\n    image: alpine:3.20\n", encoding="utf-8")
    (include_dir / "worker.yml").write_text("services:\n  worker:\n    image: python:3.11\n", encoding="utf-8")
    (tmp_path / "db.yml").write_text("services:\n  db:\n    image: postgres:16\n", encoding="utf-8")
    (tmp_path / "cache.yml").write_text("services:\n  cache:\n    image: redis:7\n", encoding="utf-8")
    (tmp_path / "object.yml").write_text("services:\n  object:\n    image: alpine:3.20\n", encoding="utf-8")
    object_dir = tmp_path / "objects"
    object_dir.mkdir()
    (tmp_path / "compose.yaml").write_text(
        """
include:
  - compose/common.yml
  - path: compose/worker.yml
  - { path: db.yml }
  - path:
      - cache.yml
  - ${COMPOSE_INCLUDE_FILE}
  - https://example.com/compose.yml
services:
  api:
    image: python:3.11
""",
        encoding="utf-8",
    )
    (object_dir / "compose.yaml").write_text("include: { path: ../object.yml }\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert "LC071" not in {finding.check_id for finding in report.findings}


def test_scan_flags_missing_docker_compose_include_files(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Run with docker compose up.\n", encoding="utf-8")
    include_dir = tmp_path / "compose"
    include_dir.mkdir()
    (include_dir / "common.yml").write_text("services:\n  common:\n    image: alpine:3.20\n", encoding="utf-8")
    object_dir = tmp_path / "objects"
    object_dir.mkdir()
    (tmp_path / "compose.yaml").write_text(
        """
include:
  - compose/common.yml
  - compose/missing.yml
  - path: compose/missing-worker.yml
  - { path: missing-db.yml }
  - path:
      - missing-cache.yml
  - $COMPOSE_INCLUDE_FILE
  - /etc/compose.yml
  - https://example.com/compose.yml
services:
  api:
    image: python:3.11
""",
        encoding="utf-8",
    )
    (object_dir / "compose.yaml").write_text("include: { path: ../missing-object.yml }\n", encoding="utf-8")

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC071")

    assert "Docker Compose include file(s)" in evidence
    assert "compose/missing.yml" in evidence
    assert "compose/missing-worker.yml" in evidence
    assert "missing-db.yml" in evidence
    assert "missing-cache.yml" in evidence
    assert "../missing-object.yml" in evidence
    assert "compose/common.yml" not in evidence
    assert "$COMPOSE_INCLUDE_FILE" not in evidence
    assert "/etc/compose.yml" not in evidence
    assert "https://example.com" not in evidence


def test_scan_accepts_existing_docker_compose_service_label_files(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Run with docker compose up.\n", encoding="utf-8")
    labels_dir = tmp_path / "labels"
    labels_dir.mkdir()
    (labels_dir / "api.labels").write_text("com.example.role=api\n", encoding="utf-8")
    (labels_dir / "worker.labels").write_text("com.example.role=worker\n", encoding="utf-8")
    (labels_dir / "common.labels").write_text("com.example.team=platform\n", encoding="utf-8")
    (tmp_path / "compose.yaml").write_text(
        """
services:
  api:
    image: python:3.11
    label_file: labels/api.labels
  worker:
    image: python:3.11
    label_file:
      - labels/worker.labels
      - labels/common.labels
  inline:
    image: python:3.11
    label_file: [labels/api.labels, labels/common.labels]
  dynamic:
    image: python:3.11
    label_file: ${COMPOSE_LABEL_FILE}
  absolute:
    image: python:3.11
    label_file: /etc/docker/labels
  remote:
    image: python:3.11
    label_file: https://example.com/labels
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC072" not in {finding.check_id for finding in report.findings}


def test_scan_flags_missing_docker_compose_service_label_files(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Run with docker compose up.\n", encoding="utf-8")
    labels_dir = tmp_path / "labels"
    labels_dir.mkdir()
    (labels_dir / "common.labels").write_text("com.example.team=platform\n", encoding="utf-8")
    (tmp_path / "compose.yaml").write_text(
        """
services:
  api:
    image: python:3.11
    label_file: labels/missing-api.labels
  worker:
    image: python:3.11
    label_file:
      - labels/missing-worker.labels
      - labels/common.labels
  inline:
    image: python:3.11
    label_file: [labels/missing-inline.labels, labels/common.labels]
  dynamic:
    image: python:3.11
    label_file: $COMPOSE_LABEL_FILE
  absolute:
    image: python:3.11
    label_file: /etc/docker/labels
  remote:
    image: python:3.11
    label_file: https://example.com/labels
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC072")

    assert "Docker Compose service label_file(s)" in evidence
    assert "labels/missing-api.labels" in evidence
    assert "labels/missing-worker.labels" in evidence
    assert "labels/missing-inline.labels" in evidence
    assert "labels/common.labels" not in evidence
    assert "$COMPOSE_LABEL_FILE" not in evidence
    assert "/etc/docker/labels" not in evidence
    assert "https://example.com" not in evidence


def test_scan_accepts_existing_docker_compose_develop_watch_paths(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Run with docker compose up --watch.\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "web").mkdir()
    (tmp_path / "package.json").write_text('{"scripts":{"dev":"vite"}}\n', encoding="utf-8")
    (tmp_path / "compose.yaml").write_text(
        """
services:
  api:
    image: python:3.11
    develop:
      watch:
        - action: sync
          path: src
          target: /app/src
        - action: rebuild
          path: package.json
        - { action: sync, path: web, target: /app/web }
  dynamic:
    image: python:3.11
    develop:
      watch:
        - action: sync
          path: ${WATCH_PATH}
          target: /app/dynamic
  absolute:
    image: python:3.11
    develop:
      watch:
        - action: sync
          path: /tmp/project
          target: /tmp/project
  remote:
    image: python:3.11
    develop:
      watch:
        - action: sync
          path: https://example.com/src
          target: /app/remote
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC073" not in {finding.check_id for finding in report.findings}


def test_scan_flags_missing_docker_compose_develop_watch_paths(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Run with docker compose up --watch.\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "package.json").write_text('{"scripts":{"dev":"vite"}}\n', encoding="utf-8")
    (tmp_path / "compose.yaml").write_text(
        """
services:
  api:
    image: python:3.11
    develop:
      watch:
        - action: sync
          path: missing-src
          target: /app/src
        - action: rebuild
          path: config/missing.yml
        - { action: sync, path: missing-web, target: /app/web }
        - action: rebuild
          path: package.json
  dynamic:
    image: python:3.11
    develop:
      watch:
        - action: sync
          path: $WATCH_PATH
          target: /app/dynamic
  absolute:
    image: python:3.11
    develop:
      watch:
        - action: sync
          path: /tmp/project
          target: /tmp/project
  remote:
    image: python:3.11
    develop:
      watch:
        - action: sync
          path: https://example.com/src
          target: /app/remote
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC073")

    assert "Docker Compose develop watch path(s)" in evidence
    assert "missing-src" in evidence
    assert "config/missing.yml" in evidence
    assert "missing-web" in evidence
    assert "package.json" not in evidence
    assert "$WATCH_PATH" not in evidence
    assert "/tmp/project" not in evidence
    assert "https://example.com" not in evidence


def test_scan_accepts_existing_readme_docker_build_targets(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
docker build --target runtime -t demo .
docker build -f docker/Dockerfile --target=prod .
docker image build --file Dockerfile.worker --target worker .
docker buildx build --platform linux/amd64 --target release .
```
""",
        encoding="utf-8",
    )
    (tmp_path / "Dockerfile").write_text(
        """
FROM python:3.11-slim AS base
FROM base AS runtime
FROM base AS release
""",
        encoding="utf-8",
    )
    docker_dir = tmp_path / "docker"
    docker_dir.mkdir()
    (docker_dir / "Dockerfile").write_text(
        """
FROM python:3.11-slim AS builder
FROM builder AS prod
""",
        encoding="utf-8",
    )
    (tmp_path / "Dockerfile.worker").write_text(
        """
FROM python:3.11-slim AS worker
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_docker_build_targets_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
docker build --target prod .
docker build -f docker/Missingfile --target worker .
```
""",
        encoding="utf-8",
    )
    (tmp_path / "Dockerfile").write_text(
        """
FROM python:3.11-slim AS base
FROM base AS runtime
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Docker build stage 'prod'" in evidence
    assert "Dockerfile does not define it" in evidence
    assert "Dockerfile 'docker/Missingfile'" in evidence


def test_scan_accepts_existing_readme_helm_chart_paths(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
helm template ./charts/api -f values/dev.yaml
helm install api ./charts/api --namespace demo
helm upgrade api charts/api --install
helm lint charts/api charts/worker
uv run helm package ./charts/worker
helm install nginx bitnami/nginx
```
""",
        encoding="utf-8",
    )
    api_chart = tmp_path / "charts" / "api"
    api_chart.mkdir(parents=True)
    (api_chart / "Chart.yaml").write_text("apiVersion: v2\nname: api\nversion: 0.1.0\n", encoding="utf-8")
    worker_chart = tmp_path / "charts" / "worker"
    worker_chart.mkdir(parents=True)
    (worker_chart / "Chart.yaml").write_text("apiVersion: v2\nname: worker\nversion: 0.1.0\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_helm_chart_paths_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
helm template ./charts/api
helm lint charts/api charts/worker
```
""",
        encoding="utf-8",
    )
    api_chart = tmp_path / "charts" / "api"
    api_chart.mkdir(parents=True)

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Helm chart path(s) ./charts/api" in evidence
    assert "charts/api, charts/worker" in evidence


def test_scan_accepts_existing_readme_kustomize_paths(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
kustomize build overlays/dev
kustomize build --enable-helm ./overlays/prod
kubectl apply -k overlays/dev
kubectl diff --kustomize=overlays/prod
kubectl kustomize ./base
kubectl apply -f deployment.yaml
kubectl apply -k https://github.com/example/repo//overlays/dev
```
""",
        encoding="utf-8",
    )
    dev_overlay = tmp_path / "overlays" / "dev"
    dev_overlay.mkdir(parents=True)
    (dev_overlay / "kustomization.yaml").write_text("resources: []\n", encoding="utf-8")
    prod_overlay = tmp_path / "overlays" / "prod"
    prod_overlay.mkdir(parents=True)
    (prod_overlay / "kustomization.yml").write_text("resources: []\n", encoding="utf-8")
    base = tmp_path / "base"
    base.mkdir()
    (base / "Kustomization").write_text("resources: []\n", encoding="utf-8")
    (tmp_path / "deployment.yaml").write_text(
        "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: demo\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_kustomize_paths_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
kustomize build overlays/dev
kubectl apply -k overlays/missing
```
""",
        encoding="utf-8",
    )
    (tmp_path / "overlays" / "dev").mkdir(parents=True)

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Kustomize path(s) overlays/dev" in evidence
    assert "Kustomize path(s) overlays/missing" in evidence


def test_scan_accepts_existing_readme_kubernetes_manifest_paths(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
kubectl apply -f manifests/app.yaml
kubectl diff --filename deploy/
uv run kubectl apply --filename=manifests/db.json
kubectl delete -f deploy/api.yaml -f deploy/job.yml
kubectl apply -f manifests/app.yaml,deploy/worker.yaml
kubectl apply -f https://example.com/app.yaml
kubectl apply -f $KUBERNETES_MANIFEST
kubectl apply -k overlays/dev
```
""",
        encoding="utf-8",
    )
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    (manifests / "app.yaml").write_text("apiVersion: v1\nkind: Service\nmetadata:\n  name: app\n", encoding="utf-8")
    (manifests / "db.json").write_text('{"apiVersion":"v1","kind":"ConfigMap","metadata":{"name":"db"}}\n', encoding="utf-8")
    deploy = tmp_path / "deploy"
    deploy.mkdir()
    (deploy / "api.yaml").write_text("apiVersion: v1\nkind: Service\nmetadata:\n  name: api\n", encoding="utf-8")
    (deploy / "job.yml").write_text("apiVersion: batch/v1\nkind: Job\nmetadata:\n  name: job\n", encoding="utf-8")
    (deploy / "worker.yaml").write_text("apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: worker\n", encoding="utf-8")
    overlay = tmp_path / "overlays" / "dev"
    overlay.mkdir(parents=True)
    (overlay / "kustomization.yaml").write_text("resources: []\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_kubernetes_manifest_paths_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
kubectl apply -f manifests/app.yaml
kubectl diff --filename deploy/
```
""",
        encoding="utf-8",
    )
    (tmp_path / "deploy").mkdir()

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Kubernetes manifest path(s) manifests/app.yaml" in evidence
    assert "Kubernetes manifest path(s) deploy/" in evidence


def test_scan_accepts_existing_readme_terraform_working_dirs(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
terraform -chdir=infra plan
terraform -chdir deploy apply -auto-approve
terraform -chdir=infra fmt -check
uv run terraform -chdir=envs/dev validate
terraform -chdir=./stack/test test
terraform plan -out=tfplan
terraform -chdir=https://github.com/example/infra plan
terraform -chdir=$TF_DIR plan
```
""",
        encoding="utf-8",
    )
    infra = tmp_path / "infra"
    infra.mkdir()
    (infra / "main.tf").write_text('resource "null_resource" "demo" {}\n', encoding="utf-8")
    deploy = tmp_path / "deploy"
    deploy.mkdir()
    (deploy / "main.tf.json").write_text('{"resource":{}}\n', encoding="utf-8")
    env = tmp_path / "envs" / "dev"
    env.mkdir(parents=True)
    (env / "versions.tf").write_text('terraform { required_version = ">= 1.6" }\n', encoding="utf-8")
    stack = tmp_path / "stack" / "test"
    stack.mkdir(parents=True)
    (stack / "main.tf").write_text('resource "null_resource" "test" {}\n', encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_terraform_working_dirs_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
terraform -chdir=infra plan
terraform -chdir=deploy/missing validate
```
""",
        encoding="utf-8",
    )
    (tmp_path / "infra").mkdir()

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Terraform working dir(s) infra" in evidence
    assert "Terraform working dir(s) deploy/missing" in evidence


def test_scan_accepts_existing_readme_pulumi_project_dirs(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
pulumi -C infra preview
pulumi --cwd deploy up --yes
pulumi preview --cwd=envs/dev --stack dev
uv run pulumi install -C ./stacks/prod
pulumi -C./stacks/test refresh
pulumi preview
pulumi --cwd https://github.com/example/infra preview
pulumi --cwd $PULUMI_DIR preview
```
""",
        encoding="utf-8",
    )
    infra = tmp_path / "infra"
    infra.mkdir()
    (infra / "Pulumi.yaml").write_text("name: infra\nruntime: yaml\n", encoding="utf-8")
    deploy = tmp_path / "deploy"
    deploy.mkdir()
    (deploy / "Pulumi.yml").write_text("name: deploy\nruntime: yaml\n", encoding="utf-8")
    env = tmp_path / "envs" / "dev"
    env.mkdir(parents=True)
    (env / "Pulumi.yaml").write_text("name: dev\nruntime: yaml\n", encoding="utf-8")
    prod = tmp_path / "stacks" / "prod"
    prod.mkdir(parents=True)
    (prod / "Pulumi.yaml").write_text("name: prod\nruntime: yaml\n", encoding="utf-8")
    test = tmp_path / "stacks" / "test"
    test.mkdir(parents=True)
    (test / "Pulumi.yaml").write_text("name: test\nruntime: yaml\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_pulumi_project_dirs_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
pulumi -C infra preview
pulumi --cwd deploy/missing up
```
""",
        encoding="utf-8",
    )
    (tmp_path / "infra").mkdir()

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Pulumi project dir(s) infra" in evidence
    assert "Pulumi project dir(s) deploy/missing" in evidence


def test_scan_accepts_existing_readme_ansible_paths(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
ansible-playbook playbooks/site.yml -i inventory.ini
ansible-playbook -i inventories/dev playbooks/deploy.yaml --tags app
uv run ansible-playbook playbooks/check.yml --inventory=inventories/prod.yml
ansible-playbook -iinventory/hosts.yml playbooks/site.yml
ansible-playbook https://example.com/site.yml
ansible-playbook playbooks/${PLAYBOOK}.yml -i localhost,
```
""",
        encoding="utf-8",
    )
    playbooks = tmp_path / "playbooks"
    playbooks.mkdir()
    (playbooks / "site.yml").write_text("- hosts: all\n  tasks: []\n", encoding="utf-8")
    (playbooks / "deploy.yaml").write_text("- hosts: app\n  tasks: []\n", encoding="utf-8")
    (playbooks / "check.yml").write_text("- hosts: all\n  tasks: []\n", encoding="utf-8")
    (tmp_path / "inventory.ini").write_text("[all]\nlocalhost\n", encoding="utf-8")
    inventory_dir = tmp_path / "inventories" / "dev"
    inventory_dir.mkdir(parents=True)
    (inventory_dir / "hosts.ini").write_text("[app]\nlocalhost\n", encoding="utf-8")
    inventories = tmp_path / "inventories"
    (inventories / "prod.yml").write_text("all:\n  hosts:\n    localhost:\n", encoding="utf-8")
    inventory = tmp_path / "inventory"
    inventory.mkdir()
    (inventory / "hosts.yml").write_text("all:\n  hosts:\n    localhost:\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_ansible_paths_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
ansible-playbook playbooks/site.yml -i inventory.ini
ansible-playbook playbooks/missing.yml --inventory inventories/missing
```
""",
        encoding="utf-8",
    )
    (tmp_path / "playbooks").mkdir()
    (tmp_path / "inventory.ini").write_text("[all]\nlocalhost\n", encoding="utf-8")

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "playbook(s) playbooks/site.yml" in evidence
    assert "playbook(s) playbooks/missing.yml" in evidence
    assert "inventory path(s) inventories/missing" in evidence


def test_scan_accepts_existing_readme_packer_template_paths(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
packer init templates/web.pkr.hcl
packer validate -var-file vars/dev.pkrvars.hcl templates/
uv run packer build -only amazon-ebs.web images/web.pkr.hcl
packer fmt templates images/db.pkr.hcl
packer inspect ./templates/web.pkr.hcl
packer validate https://example.com/template.pkr.hcl
packer build $PACKER_TEMPLATE
```
""",
        encoding="utf-8",
    )
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "web.pkr.hcl").write_text('source "null" "web" {}\n', encoding="utf-8")
    images = tmp_path / "images"
    images.mkdir()
    (images / "web.pkr.hcl").write_text('source "null" "web" {}\n', encoding="utf-8")
    (images / "db.pkr.hcl").write_text('source "null" "db" {}\n', encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_packer_template_paths_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
packer validate templates/
packer build images/missing.pkr.hcl
```
""",
        encoding="utf-8",
    )
    (tmp_path / "templates").mkdir()

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Packer template path(s) templates/" in evidence
    assert "Packer template path(s) images/missing.pkr.hcl" in evidence


def test_scan_accepts_existing_readme_airflow_targets(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
airflow dags test -B local demo_dag
airflow tasks test --task-params params.json demo_dag train 2026-01-01
uv run airflow tasks run --ship-dag decorated_dag evaluate 2026-01-01
```
""",
        encoding="utf-8",
    )
    dags_dir = tmp_path / "dags"
    dags_dir.mkdir()
    (dags_dir / "demo.py").write_text(
        """
from airflow import DAG
from airflow.decorators import dag, task
from airflow.operators.empty import EmptyOperator

with DAG(dag_id="demo_dag"):
    train = EmptyOperator(task_id="train")

@dag(dag_id="decorated_dag")
def decorated():
    @task(task_id="evaluate")
    def evaluate_task():
        return "ready"

    evaluate_task()
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_airflow_targets_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
airflow dags test missing_dag
airflow tasks test demo_dag missing_task 2026-01-01
```
""",
        encoding="utf-8",
    )
    dags_dir = tmp_path / "dags"
    dags_dir.mkdir()
    (dags_dir / "demo.py").write_text(
        """
from airflow import DAG
from airflow.operators.empty import EmptyOperator

with DAG(dag_id="demo_dag"):
    train = EmptyOperator(task_id="train")
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Airflow DAG 'missing_dag'" in evidence
    assert "Airflow task 'missing_task'" in evidence


def test_scan_accepts_existing_readme_metaflow_resume_steps(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
python flow.py resume train_model
uv run python flow.py resume --origin-run-id 42 evaluate
```
""",
        encoding="utf-8",
    )
    (tmp_path / "flow.py").write_text(
        """
from metaflow import FlowSpec, step

class DemoFlow(FlowSpec):
    @step
    def start(self):
        self.next(self.train_model)

    @step
    def train_model(self):
        self.next(self.evaluate)

    @step
    def evaluate(self):
        self.next(self.end)

    @step
    def end(self):
        pass
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_metaflow_resume_steps_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
python flow.py resume train_model
python missing_flow.py resume evaluate
```
""",
        encoding="utf-8",
    )
    (tmp_path / "flow.py").write_text(
        """
from metaflow import FlowSpec, step

class DemoFlow(FlowSpec):
    @step
    def start(self):
        self.next(self.end)

    @step
    def end(self):
        pass
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Metaflow step 'train_model'" in evidence
    assert "Metaflow script 'missing_flow.py'" in evidence


def test_scan_accepts_existing_readme_hatch_and_pdm_aliases(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
hatch run reproduce
hatch run docs:build
pdm run report
```
""",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "demo-lab"
version = "0.1.0"

[tool.hatch.envs.default.scripts]
reproduce = "python scripts/reproduce.py"

[tool.pdm.scripts]
report = "python scripts/report.py"
""",
        encoding="utf-8",
    )
    (tmp_path / "hatch.toml").write_text(
        """
[envs.docs.scripts]
build = "mkdocs build"
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_hatch_and_pdm_aliases_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
hatch run reproduce
hatch run docs:build
pdm run report
```
""",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "demo-lab"
version = "0.1.0"

[tool.hatch.envs.default.scripts]
lint = "ruff check ."

[tool.pdm.scripts]
format = "ruff format ."
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "Hatch script 'reproduce'" in evidence
    assert "Hatch script 'docs:build'" in evidence
    assert "PDM script 'report'" in evidence


def test_scan_accepts_existing_readme_just_and_doit_aliases(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
just reproduce
just r
doit report
```
""",
        encoding="utf-8",
    )
    (tmp_path / "justfile").write_text(
        """
alias r := reproduce

reproduce seed='7':
    python scripts/reproduce.py {{seed}}
""",
        encoding="utf-8",
    )
    (tmp_path / "dodo.py").write_text(
        """
def task_report():
    return {"actions": ["python scripts/report.py"]}
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_just_and_doit_aliases_when_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        """
```bash
just reproduce
doit report
doit list
```
""",
        encoding="utf-8",
    )
    (tmp_path / "justfile").write_text(
        """
lint:
    ruff check .
""",
        encoding="utf-8",
    )
    (tmp_path / "dodo.py").write_text(
        """
def task_lint():
    return {"actions": ["ruff check ."]}
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    evidence = "\n".join(finding.evidence for finding in report.findings if finding.check_id == "LC008")

    assert "just recipe 'reproduce'" in evidence
    assert "doit task 'report'" in evidence
    assert "doit list" not in evidence


def test_scan_ignores_readme_uv_run_common_dependency_clis(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "```bash\nuv run pytest\nuv run ruff check .\n```\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_npm_script_when_package_json_is_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "```bash\nnpm run reproduce\n```\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC008")

    assert finding.file_path == "README.md"
    assert "requires package.json" in finding.evidence


def test_scan_flags_readme_npm_script_when_script_is_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "```bash\nnpm run reproduce\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "package.json").write_text(
        '{"scripts": {"test": "echo ok"}}\n',
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC008")

    assert finding.file_path == "README.md"
    assert "script 'reproduce'" in finding.evidence


def test_scan_accepts_existing_readme_npm_script(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "```bash\nnpm run reproduce\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "package.json").write_text(
        '{"scripts": {"reproduce": "python train.py"}}\n',
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_readme_pnpm_script_when_script_is_missing(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "```bash\npnpm run dashboard\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "package.json").write_text(
        '{"scripts": {"test": "echo ok"}}\n',
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC008")

    assert "pnpm run dashboard" in finding.evidence
    assert "script 'dashboard'" in finding.evidence


def test_scan_accepts_existing_readme_yarn_scripts(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "```bash\nyarn report\nyarn run figures\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "package.json").write_text(
        '{"scripts": {"report": "node report.js", "figures": "node figures.js"}}\n',
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert "LC008" not in {finding.check_id for finding in report.findings}


def test_scan_flags_markdown_link_to_missing_local_file(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "analysis.py").write_text("print('ready')\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "\n".join(
            [
                "# Demo",
                "",
                "Run `python analysis.py`.",
                "",
                "[External](https://example.com) and [anchor](#usage) are fine.",
                "[Missing notebook](notebooks/missing.ipynb) should be flagged.",
                "![Missing figure](docs/figures/missing.png)",
                "```markdown",
                "[Example-only missing link](docs/example-only.md)",
                "```",
            ]
        ),
        encoding="utf-8",
    )
    (docs_dir / "guide.md").write_text(
        "[Back to README](../README.md)\n[Missing policy](policy.md)\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    findings = [finding for finding in report.findings if finding.check_id == "LC062"]

    evidence_by_path = sorted((finding.file_path, finding.evidence) for finding in findings)

    assert len(evidence_by_path) == 3
    assert ("README.md", "Markdown link target 'docs/figures/missing.png' is not present in the scanned repo.") in evidence_by_path
    assert ("README.md", "Markdown link target 'notebooks/missing.ipynb' is not present in the scanned repo.") in evidence_by_path
    assert ("docs/guide.md", "Markdown link target 'policy.md' is not present in the scanned repo.") in evidence_by_path
    assert all("example.com" not in finding.evidence for finding in findings)


def test_scan_accepts_existing_markdown_local_links(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    assets_dir = docs_dir / "assets"
    assets_dir.mkdir(parents=True)
    (tmp_path / "README.md").write_text(
        "[Guide](docs/guide.md)\n![Scorecard](docs/assets/scorecard.svg)\n",
        encoding="utf-8",
    )
    (docs_dir / "guide.md").write_text("[Back](../README.md)\n", encoding="utf-8")
    (assets_dir / "scorecard.svg").write_text("<svg></svg>\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert "LC062" not in {finding.check_id for finding in report.findings}


def test_scan_flags_missing_reuse_metadata_for_notebook_repo(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "Run the notebook:\n\n```bash\njupyter notebook analysis.ipynb\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "analysis.ipynb").write_text(
        json.dumps(
            {
                "cells": [
                    {"cell_type": "code", "execution_count": 1, "metadata": {}, "outputs": [], "source": ["x = 1\n"]},
                ],
                "metadata": {
                    "kernelspec": {"name": "python3"},
                    "language_info": {"name": "python"},
                },
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        ),
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    findings = {finding.check_id: finding for finding in report.findings}

    assert findings["LC063"].severity == "low"
    assert findings["LC063"].category == "onboarding"
    assert "LICENSE/COPYING" in findings["LC063"].evidence
    assert findings["LC064"].severity == "low"
    assert "CITATION.cff" in findings["LC064"].evidence


def test_scan_accepts_license_and_citation_metadata(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.1.0"\nlicense = { text = "MIT" }\n',
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        "\n".join(
            [
                "# Demo research repo",
                "",
                "Run the experiment:",
                "",
                "```bash",
                "python analysis.py",
                "```",
                "",
                "## Citation",
                "",
                "Please cite this repository if it helps your research.",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "analysis.py").write_text("print('ready')\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert "LC063" not in {finding.check_id for finding in report.findings}
    assert "LC064" not in {finding.check_id for finding in report.findings}


def test_scan_flags_ci_workflow_missing_script(tmp_path: Path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text(
        "jobs:\n  test:\n    steps:\n      - run: python scripts/train.py\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC025")

    assert finding.severity == "medium"
    assert finding.category == "onboarding"
    assert finding.file_path == ".github/workflows/ci.yml"
    assert "scripts/train.py" in finding.evidence


def test_ci_workflow_drift_flags_missing_requirement_file(tmp_path: Path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    workflow = workflows / "ci.yml"
    workflow.write_text(
        "jobs:\n  test:\n    steps:\n      - run: python -m pip install -r requirements-ci.txt\n",
        encoding="utf-8",
    )

    findings = check_ci_workflow_drift(tmp_path, [workflow])

    assert len(findings) == 1
    assert findings[0].check_id == "LC025"
    assert "requirements-ci.txt" in findings[0].evidence


def test_ci_workflow_drift_accepts_existing_paths_and_external_modules(tmp_path: Path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    workflow = workflows / "ci.yml"
    workflow.write_text(
        "\n".join(
            [
                "jobs:",
                "  test:",
                "    steps:",
                "      - run: python -m pytest",
                "      - run: python -m pip install -r requirements.txt",
                "      - run: python scripts/train.py",
                "      - run: make reproduce",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "requirements.txt").write_text("pytest==8.0.0\n", encoding="utf-8")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "train.py").write_text("print('ready')\n", encoding="utf-8")
    (tmp_path / "Makefile").write_text("reproduce:\n\tpython scripts/train.py\n", encoding="utf-8")

    assert check_ci_workflow_drift(tmp_path, [workflow, tmp_path / "requirements.txt", scripts / "train.py"]) == []


def test_ci_workflow_verification_check_flags_setup_only_workflow(tmp_path: Path) -> None:
    workflow = tmp_path / ".github" / "workflows" / "ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        "\n".join(
            [
                "jobs:",
                "  smoke:",
                "    steps:",
                "      - uses: actions/setup-python@v5",
                "      - run: python -m pip install -r requirements.txt",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "requirements.txt").write_text("pytest==8.0.0\n", encoding="utf-8")

    findings = check_ci_workflow_has_verification_step(tmp_path, [workflow, tmp_path / "requirements.txt"])

    assert len(findings) == 1
    assert findings[0].check_id == "LC044"
    assert findings[0].severity == "medium"
    assert findings[0].category == "onboarding"
    assert findings[0].file_path == ".github/workflows/ci.yml"
    assert "no test" in findings[0].evidence


def test_ci_workflow_verification_check_accepts_pytest_labcheck_and_reproduce(tmp_path: Path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    pytest_workflow = workflows / "pytest.yml"
    pytest_workflow.write_text(
        "jobs:\n  test:\n    steps:\n      - uses: actions/setup-python@v5\n      - run: python -m pip install -r requirements.txt\n      - run: python -m pytest\n",
        encoding="utf-8",
    )
    labcheck_workflow = workflows / "labcheck.yml"
    labcheck_workflow.write_text(
        "jobs:\n  audit:\n    steps:\n      - run: uv sync\n      - run: labcheck scan . --fail-on high\n",
        encoding="utf-8",
    )
    reproduce_workflow = workflows / "reproduce.yml"
    reproduce_workflow.write_text(
        "jobs:\n  repro:\n    steps:\n      - run: poetry install\n      - run: make reproduce\n",
        encoding="utf-8",
    )
    smoke_check_workflow = workflows / "static-export.yml"
    smoke_check_workflow.write_text(
        "jobs:\n  pages:\n    steps:\n      - uses: actions/setup-python@v5\n      - run: python scripts/check_static_export.py\n",
        encoding="utf-8",
    )

    assert check_ci_workflow_has_verification_step(
        tmp_path,
        [pytest_workflow, labcheck_workflow, reproduce_workflow, smoke_check_workflow],
    ) == []


def test_ci_workflow_verification_check_ignores_pages_deploy_workflow(tmp_path: Path) -> None:
    workflow = tmp_path / ".github" / "workflows" / "pages.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        "\n".join(
            [
                "name: pages",
                "jobs:",
                "  build:",
                "    steps:",
                "      - uses: actions/setup-python@v5",
                "      - run: python scripts/build_static_site.py",
                "      - uses: actions/upload-pages-artifact@v3",
                "  deploy:",
                "    steps:",
                "      - uses: actions/deploy-pages@v4",
            ]
        ),
        encoding="utf-8",
    )

    assert check_ci_workflow_has_verification_step(tmp_path, [workflow]) == []


def test_scan_flags_ci_workflow_without_verification_step(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pytest==8.0.0\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("```bash\npython analysis.py\n```\n", encoding="utf-8")
    (tmp_path / "analysis.py").write_text("print('ready')\n", encoding="utf-8")
    workflow = tmp_path / ".github" / "workflows" / "ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        "jobs:\n  test:\n    steps:\n      - uses: actions/setup-python@v5\n      - run: python -m pip install -r requirements.txt\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC044")

    assert finding.category == "onboarding"
    assert finding.file_path == ".github/workflows/ci.yml"


def test_scan_flags_floating_github_action_ref(tmp_path: Path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text(
        "jobs:\n  test:\n    steps:\n      - uses: actions/checkout@main\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC030")

    assert finding.severity == "medium"
    assert finding.category == "onboarding"
    assert finding.file_path == ".github/workflows/ci.yml"
    assert "actions/checkout@main" in finding.evidence


def test_floating_github_action_ref_check_flags_missing_ref(tmp_path: Path) -> None:
    workflow = tmp_path / ".github" / "workflows" / "ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        "jobs:\n  test:\n    steps:\n      - uses: owner/custom-action\n",
        encoding="utf-8",
    )

    findings = check_floating_github_action_refs(tmp_path, [workflow])

    assert len(findings) == 1
    assert findings[0].check_id == "LC030"
    assert "does not specify an action ref" in findings[0].evidence


def test_floating_github_action_ref_check_accepts_version_tag_and_sha(tmp_path: Path) -> None:
    workflow = tmp_path / ".github" / "workflows" / "ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        "\n".join(
            [
                "jobs:",
                "  test:",
                "    steps:",
                "      - uses: actions/checkout@v4",
                f"      - uses: owner/custom-action@{'a' * 40}",
            ]
        ),
        encoding="utf-8",
    )

    assert check_floating_github_action_refs(tmp_path, [workflow]) == []


def test_floating_github_action_ref_check_ignores_local_docker_and_dynamic_uses(tmp_path: Path) -> None:
    workflow = tmp_path / ".github" / "workflows" / "ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        "\n".join(
            [
                "jobs:",
                "  test:",
                "    steps:",
                "      - uses: ./.github/actions/setup",
                "      - uses: docker://alpine:latest",
                "      - uses: owner/action@${{ matrix.ref }}",
            ]
        ),
        encoding="utf-8",
    )

    assert check_floating_github_action_refs(tmp_path, [workflow]) == []


def test_scan_accepts_pyproject_python_runtime(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nrequires-python = ">=3.11"\ndependencies = ["pandas==2.2.2"]\n',
        encoding="utf-8",
    )
    (tmp_path / "analysis.py").write_text("print('ready')\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert "LC012" not in {finding.check_id for finding in report.findings}


def test_scan_flags_conflicting_exact_python_runtime_specs(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.10\n", encoding="utf-8")
    (tmp_path / "Dockerfile").write_text("FROM python:3.11-slim\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("```bash\npython analysis.py\n```\n", encoding="utf-8")
    (tmp_path / "analysis.py").write_text("print('ready')\n", encoding="utf-8")

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC019")

    assert finding.severity == "medium"
    assert finding.category == "environment"
    assert ".python-version declares 3.10" in finding.evidence
    assert "Dockerfile declares python:3.11-slim" in finding.evidence


def test_scan_accepts_matching_runtime_metadata_variants(tmp_path: Path) -> None:
    docker_dir = tmp_path / "docker"
    docker_dir.mkdir()
    (tmp_path / "Pipfile").write_text('[requires]\npython_version = "3.11"\n', encoding="utf-8")
    (tmp_path / "setup.cfg").write_text("[options]\npython_requires = >=3.11\n", encoding="utf-8")
    (docker_dir / "Dockerfile").write_text("FROM python:3.11-slim\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("```bash\npython analysis.py\n```\n", encoding="utf-8")
    (tmp_path / "analysis.py").write_text("print('ready')\n", encoding="utf-8")

    report = scan_path(str(tmp_path))
    check_ids = {finding.check_id for finding in report.findings}

    assert "LC012" not in check_ids
    assert "LC019" not in check_ids


def test_scan_flags_conflicting_nested_dockerfile_runtime_variant(tmp_path: Path) -> None:
    docker_dir = tmp_path / "docker"
    docker_dir.mkdir()
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (docker_dir / "Dockerfile").write_text("FROM python:3.10-slim\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("```bash\npython analysis.py\n```\n", encoding="utf-8")
    (tmp_path / "analysis.py").write_text("print('ready')\n", encoding="utf-8")

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC019")

    assert ".python-version declares 3.11" in finding.evidence
    assert "docker/Dockerfile declares python:3.10-slim" in finding.evidence


def test_scan_flags_ci_python_runtime_conflict(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text(
        "jobs:\n  test:\n    steps:\n      - uses: actions/setup-python@v5\n        with:\n          python-version: '3.10'\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC026")

    assert finding.severity == "medium"
    assert finding.category == "environment"
    assert finding.file_path == ".github/workflows/ci.yml"
    assert "Python 3.10" in finding.evidence
    assert "Python 3.11" in finding.evidence


def test_ci_python_runtime_conflict_accepts_matching_workflow_version(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11.8\n", encoding="utf-8")
    workflow = tmp_path / ".github" / "workflows" / "ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        "jobs:\n  test:\n    steps:\n      - uses: actions/setup-python@v5\n        with:\n          python-version: '3.11'\n",
        encoding="utf-8",
    )

    assert check_ci_python_runtime_conflict(tmp_path, [workflow]) == []


def test_ci_python_runtime_conflict_ignores_dynamic_workflow_expression(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    workflow = tmp_path / ".github" / "workflows" / "ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        "jobs:\n  test:\n    steps:\n      - uses: actions/setup-python@v5\n        with:\n          python-version: ${{ matrix.python-version }}\n",
        encoding="utf-8",
    )

    assert check_ci_python_runtime_conflict(tmp_path, [workflow]) == []


def test_scan_flags_floating_docker_base_image_tag(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\npython -m pip install -r requirements.txt\npython analysis.py\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "analysis.py").write_text("print('ready')\n", encoding="utf-8")
    (tmp_path / "Dockerfile").write_text("FROM python:latest\n", encoding="utf-8")

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC029")

    assert finding.severity == "medium"
    assert finding.category == "environment"
    assert finding.file_path == "Dockerfile"
    assert "python:latest" in finding.evidence


def test_floating_docker_base_image_check_flags_untagged_image(tmp_path: Path) -> None:
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM ubuntu\n", encoding="utf-8")

    findings = check_floating_docker_base_images(tmp_path, [dockerfile])

    assert len(findings) == 1
    assert findings[0].check_id == "LC029"
    assert "does not specify a tag" in findings[0].evidence


def test_floating_docker_base_image_check_accepts_versioned_tag(tmp_path: Path) -> None:
    dockerfile = tmp_path / "Dockerfile"
    dockerfile.write_text("FROM python:3.11-slim\n", encoding="utf-8")

    assert check_floating_docker_base_images(tmp_path, [dockerfile]) == []


def test_floating_docker_base_image_check_accepts_digest_pin(tmp_path: Path) -> None:
    dockerfile = tmp_path / "Dockerfile.release"
    digest = "a" * 64
    dockerfile.write_text(f"FROM python:3.11-slim@sha256:{digest}\n", encoding="utf-8")

    assert check_floating_docker_base_images(tmp_path, [dockerfile]) == []


def test_floating_docker_base_image_check_accepts_stage_alias(tmp_path: Path) -> None:
    dockerfile = tmp_path / "service.Dockerfile"
    dockerfile.write_text(
        "FROM --platform=$BUILDPLATFORM python:3.11-slim AS base\nFROM base AS runtime\n",
        encoding="utf-8",
    )

    assert check_floating_docker_base_images(tmp_path, [dockerfile]) == []


def test_dockerfile_dependency_install_check_flags_missing_install(tmp_path: Path) -> None:
    dockerfile = tmp_path / "Dockerfile"
    requirements = tmp_path / "requirements.txt"
    dockerfile.write_text("FROM python:3.11-slim\nWORKDIR /app\nCOPY . .\n", encoding="utf-8")
    requirements.write_text("pandas==2.2.2\n", encoding="utf-8")

    findings = check_dockerfile_missing_dependency_install(tmp_path, [dockerfile, requirements])

    assert len(findings) == 1
    assert findings[0].check_id == "LC049"
    assert findings[0].severity == "medium"
    assert findings[0].category == "environment"
    assert findings[0].file_path == "Dockerfile"
    assert "requirements.txt" in findings[0].evidence


def test_dockerfile_dependency_install_check_accepts_manifest_install(tmp_path: Path) -> None:
    dockerfile = tmp_path / "Dockerfile"
    requirements = tmp_path / "requirements.txt"
    dockerfile.write_text(
        "FROM python:3.11-slim\n"
        "WORKDIR /app\n"
        "COPY requirements.txt .\n"
        "RUN python -m pip install \\\n"
        "    -r requirements.txt\n"
        "COPY . .\n",
        encoding="utf-8",
    )
    requirements.write_text("pandas==2.2.2\n", encoding="utf-8")

    assert check_dockerfile_missing_dependency_install(tmp_path, [dockerfile, requirements]) == []


def test_dockerfile_dependency_install_check_accepts_project_install(tmp_path: Path) -> None:
    dockerfile = tmp_path / "Dockerfile"
    pyproject = tmp_path / "pyproject.toml"
    dockerfile.write_text(
        "FROM python:3.11-slim\nWORKDIR /app\nCOPY . .\nRUN pip install .\n",
        encoding="utf-8",
    )
    pyproject.write_text('[project]\ndependencies = ["pandas==2.2.2"]\n', encoding="utf-8")

    assert check_dockerfile_missing_dependency_install(tmp_path, [dockerfile, pyproject]) == []


def test_scan_flags_dockerfile_missing_dependency_install(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "Dockerfile").write_text("FROM python:3.11-slim\nWORKDIR /app\nCOPY . .\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\npython -m pip install -r requirements.txt\npython analysis.py\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "analysis.py").write_text("print('ready')\n", encoding="utf-8")

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC049")

    assert finding.category == "environment"
    assert finding.file_path == "Dockerfile"
    assert "requirements.txt" in finding.evidence


def test_scan_accepts_matching_exact_python_runtime_specs(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11.8\n", encoding="utf-8")
    (tmp_path / "Dockerfile").write_text("FROM python:3.11-slim\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("```bash\npython analysis.py\n```\n", encoding="utf-8")
    (tmp_path / "analysis.py").write_text("print('ready')\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert "LC019" not in {finding.check_id for finding in report.findings}


def test_notebook_inline_install_check_flags_unpinned_packages(tmp_path: Path) -> None:
    notebook_path = tmp_path / "analysis.ipynb"
    artifact = SourceArtifact(
        path=notebook_path,
        kind="notebook",
        content="\n".join(
            [
                "%pip install pandas scikit-learn==1.5.0",
                "!python -m pip install -q torch",
                "!uv pip install polars>=1.0",
            ]
        ),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_notebook_inline_unpinned_installs(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC020"
    assert findings[0].severity == "medium"
    assert "pandas" in findings[0].evidence
    assert "torch" in findings[0].evidence
    assert "scikit-learn" not in findings[0].evidence
    assert "polars" not in findings[0].evidence


def test_notebook_inline_install_check_accepts_manifest_and_pinned_installs(tmp_path: Path) -> None:
    notebook_path = tmp_path / "analysis.ipynb"
    artifact = SourceArtifact(
        path=notebook_path,
        kind="notebook",
        content="\n".join(
            [
                "%pip install pandas==2.2.2",
                "!python -m pip install -r requirements.txt",
                "!pip install -e .",
                "%conda install -y numpy=2.0",
                "!pip install demo-pkg @ https://example.com/demo-pkg.whl",
            ]
        ),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_notebook_inline_unpinned_installs(tmp_path, [artifact]) == []


def test_scan_flags_notebook_inline_unpinned_install(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("```bash\njupyter notebook analysis.ipynb\n```\n", encoding="utf-8")
    (tmp_path / "analysis.ipynb").write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "code",
                        "execution_count": 1,
                        "outputs": [],
                        "source": ["%pip install pandas\n", "print('ready')\n"],
                    }
                ],
                "metadata": {
                    "kernelspec": {"name": "python3"},
                    "language_info": {"name": "python"},
                },
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        ),
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC020")

    assert finding.category == "environment"
    assert finding.file_path == "analysis.ipynb"
    assert "pip install" in finding.evidence


def test_inline_command_missing_path_check_flags_notebook_commands(tmp_path: Path) -> None:
    notebook_path = tmp_path / "analysis.ipynb"
    artifact = SourceArtifact(
        path=notebook_path,
        kind="notebook",
        content="%run scripts/preprocess.py\n!python scripts/train.py --epochs 1\n!bash scripts/setup.sh\n",
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_inline_command_missing_paths(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC052"
    assert findings[0].severity == "medium"
    assert findings[0].category == "onboarding"
    assert "scripts/preprocess.py" in findings[0].evidence
    assert "scripts/train.py" in findings[0].evidence
    assert "scripts/setup.sh" in findings[0].evidence


def test_inline_command_missing_path_check_flags_shell_cell_magic(tmp_path: Path) -> None:
    notebook_path = tmp_path / "analysis.ipynb"
    artifact = SourceArtifact(
        path=notebook_path,
        kind="notebook",
        content=(
            "%%bash\n"
            "set -e\n"
            "python scripts/build_features.py --input data/raw.csv\n"
            "bash scripts/train.sh\n\n"
            "print('next python cell')\n"
            "%%script sh\n"
            "python scripts/export_report.py\n"
        ),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_inline_command_missing_paths(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC052"
    assert "scripts/build_features.py" in findings[0].evidence
    assert "scripts/train.sh" in findings[0].evidence
    assert "scripts/export_report.py" in findings[0].evidence


def test_inline_command_missing_path_check_flags_subprocess_and_os_system(tmp_path: Path) -> None:
    source_path = tmp_path / "analysis.py"
    source_path.write_text(
        """
import os
import subprocess as sp
from os import system
from subprocess import run

sp.run(["python", "scripts/build_features.py"])
run(["bash", "scripts/train.sh"])
os.system("python scripts/report.py --format json")
system("bash scripts/export.sh")
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_inline_command_missing_paths(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC052"
    assert "scripts/build_features.py" in findings[0].evidence
    assert "scripts/train.sh" in findings[0].evidence
    assert "scripts/report.py" in findings[0].evidence
    assert "scripts/export.sh" in findings[0].evidence


def test_inline_command_missing_path_check_accepts_existing_scripts(tmp_path: Path) -> None:
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "preprocess.py").write_text("print('ready')\n", encoding="utf-8")
    (scripts_dir / "setup.sh").write_text("echo ready\n", encoding="utf-8")
    artifact = SourceArtifact(
        path=tmp_path / "analysis.ipynb",
        kind="notebook",
        content="%run scripts/preprocess.py\n!bash scripts/setup.sh\n!python -m demo.module\n",
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_inline_command_missing_paths(tmp_path, [artifact]) == []


def test_scan_flags_inline_command_missing_path(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\npython -m pip install -r requirements.txt\npython analysis.py\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "analysis.py").write_text(
        "import subprocess\nsubprocess.run(['python', 'scripts/missing_train.py'])\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC052")

    assert finding.severity == "medium"
    assert finding.category == "onboarding"
    assert finding.file_path == "analysis.py"
    assert "scripts/missing_train.py" in finding.evidence


def test_inline_system_package_check_flags_shell_installs(tmp_path: Path) -> None:
    notebook_path = tmp_path / "analysis.ipynb"
    artifact = SourceArtifact(
        path=notebook_path,
        kind="notebook",
        content="\n".join(
            [
                "!apt-get update",
                "!sudo apt-get install -y graphviz libgl1",
                "!brew install libomp",
                "!apk add --no-cache geos",
            ]
        ),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_inline_system_package_installs(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC048"
    assert findings[0].severity == "medium"
    assert findings[0].category == "environment"
    assert "graphviz" in findings[0].evidence
    assert "libomp" in findings[0].evidence
    assert "geos" in findings[0].evidence
    assert "update" not in findings[0].evidence


def test_inline_system_package_check_accepts_python_package_installs(tmp_path: Path) -> None:
    notebook_path = tmp_path / "analysis.ipynb"
    artifact = SourceArtifact(
        path=notebook_path,
        kind="notebook",
        content="%pip install pandas\n!conda install -y numpy=2.0\n!apt-get update\n",
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_inline_system_package_installs(tmp_path, [artifact]) == []


def test_scan_flags_inline_system_package_install(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("```bash\njupyter notebook analysis.ipynb\n```\n", encoding="utf-8")
    (tmp_path / "analysis.ipynb").write_text(
        json.dumps(
            {
                "cells": [
                    {
                        "cell_type": "code",
                        "execution_count": 1,
                        "outputs": [],
                        "source": ["!sudo apt-get install -y graphviz\n", "print('ready')\n"],
                    }
                ],
                "metadata": {
                    "kernelspec": {"name": "python3"},
                    "language_info": {"name": "python"},
                },
                "nbformat": 4,
                "nbformat_minor": 5,
            }
        ),
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC048")

    assert finding.category == "environment"
    assert finding.file_path == "analysis.ipynb"
    assert "apt-get install" in finding.evidence


def test_scan_does_not_flag_runtime_range_as_conflict(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.12\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nrequires-python = ">=3.11"\ndependencies = ["pandas==2.2.2"]\n',
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("```bash\npython analysis.py\n```\n", encoding="utf-8")
    (tmp_path / "analysis.py").write_text("print('ready')\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert "LC019" not in {finding.check_id for finding in report.findings}


def test_scan_rejects_invalid_disabled_checks_config(tmp_path: Path) -> None:
    config_path = tmp_path / "custom.toml"
    config_path.write_text('disabled_checks = "LC010"\n', encoding="utf-8")

    try:
        scan_path(str(tmp_path), config_path=str(config_path))
    except ValueError as exc:
        assert "disabled_checks must be a list of strings" in str(exc)
    else:
        raise AssertionError("Expected invalid disabled_checks config to fail")


def test_scan_rejects_invalid_ignored_findings_config(tmp_path: Path) -> None:
    config_path = tmp_path / "custom.toml"
    config_path.write_text('[[ignored_findings]]\ncheck_id = "LC010"\n', encoding="utf-8")

    try:
        scan_path(str(tmp_path), config_path=str(config_path))
    except ValueError as exc:
        assert "ignored_findings entry 1 needs a path" in str(exc)
    else:
        raise AssertionError("Expected invalid ignored_findings config to fail")


def test_scan_accepts_labcheck_config_with_utf8_bom(tmp_path: Path) -> None:
    (tmp_path / ".labcheck.toml").write_text('\ufeffexclude = ["skip.py"]\n', encoding="utf-8")
    (tmp_path / "skip.py").write_text("import random\nrandom.random()\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert report.summary.python_files == 0
    assert report.findings == []


def test_scan_flags_unpinned_pyproject_dependency(tmp_path: Path) -> None:
    (tmp_path / "analysis.py").write_text("print('ready')\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[project]\ndependencies = ["pandas"]\n', encoding="utf-8")

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC004")

    assert finding.file_path == "pyproject.toml"
    assert "pandas" in finding.evidence


def test_scan_flags_unpinned_environment_dependency(tmp_path: Path) -> None:
    (tmp_path / "analysis.py").write_text("print('ready')\n", encoding="utf-8")
    (tmp_path / "environment.yml").write_text("dependencies:\n  - pandas\n", encoding="utf-8")

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC004")

    assert finding.file_path == "environment.yml"
    assert "pandas" in finding.evidence


def test_scan_flags_missing_conda_pip_requirement_include(tmp_path: Path) -> None:
    (tmp_path / "analysis.py").write_text("print('ready')\n", encoding="utf-8")
    (tmp_path / "environment.yml").write_text(
        "dependencies:\n  - python=3.11\n  - pip:\n    - -r requirements/pip.txt\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC023")

    assert finding.file_path == "environment.yml"
    assert "requirements/pip.txt" in finding.evidence
    assert "Conda pip include" in finding.why_it_matters


def test_scan_follows_conda_pip_requirement_include_for_dependency_checks(tmp_path: Path) -> None:
    deps_dir = tmp_path / "deps"
    deps_dir.mkdir()
    (tmp_path / "README.md").write_text(
        "```bash\nconda env create -f environment.yml\npython analysis.py\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "environment.yml").write_text(
        "dependencies:\n  - python=3.11\n  - pip:\n    - -r deps/pip.txt\n",
        encoding="utf-8",
    )
    (deps_dir / "pip.txt").write_text("pandas\nscikit-learn==1.5.0\n", encoding="utf-8")
    (tmp_path / "analysis.py").write_text(
        "import pandas as pd\nfrom sklearn.model_selection import train_test_split\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))

    assert any(
        finding.check_id == "LC004" and finding.file_path == "deps/pip.txt" and "pandas" in finding.evidence
        for finding in report.findings
    )
    assert not any(
        finding.check_id == "LC028" and "scikit-learn" in finding.evidence
        for finding in report.findings
    )


def test_scan_flags_direct_conda_pip_vcs_and_local_path_dependencies(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "```bash\nconda env create -f environment.yml\npython analysis.py\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "environment.yml").write_text(
        "\n".join(
            [
                "dependencies:",
                "  - python=3.11",
                "  - pip:",
                "    - git+https://github.com/example/research-utils.git@main#egg=research-utils",
                "    - -e ../missing-local-lib",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "analysis.py").write_text("print('ready')\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert any(
        finding.check_id == "LC043"
        and finding.file_path == "environment.yml"
        and "moving ref" in finding.evidence
        for finding in report.findings
    )
    assert any(
        finding.check_id == "LC027"
        and finding.file_path == "environment.yml"
        and "../missing-local-lib" in finding.evidence
        for finding in report.findings
    )


def test_scan_flags_vcs_dependency_moving_ref(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text(
        "git+https://github.com/example/research-utils.git@main#egg=research-utils\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC043")

    assert finding.severity == "medium"
    assert finding.category == "environment"
    assert finding.file_path == "requirements.txt"
    assert "line 1" in finding.evidence
    assert "main" in finding.evidence


def test_vcs_dependency_check_accepts_commit_sha_and_release_tag(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text(
        "\n".join(
            [
                "git+https://github.com/example/research-utils.git@9fceb02b70d8b8d49e9d7f4d4b109b965b8f74d3#egg=research-utils",
                "git+https://github.com/example/analysis-kit.git@v1.2.3#egg=analysis-kit",
            ]
        ),
        encoding="utf-8",
    )

    assert check_unpinned_vcs_dependencies(tmp_path, []) == []


def test_vcs_dependency_check_flags_poetry_branch(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.poetry.dependencies]
python = "^3.11"
research-utils = { git = "https://github.com/example/research-utils.git", branch = "main" }
analysis-kit = { git = "https://github.com/example/analysis-kit.git", tag = "v1.2.3" }
""",
        encoding="utf-8",
    )

    findings = check_unpinned_vcs_dependencies(tmp_path, [])

    assert len(findings) == 1
    assert findings[0].check_id == "LC043"
    assert findings[0].file_path == "pyproject.toml"
    assert "research-utils" in findings[0].evidence
    assert "main" in findings[0].evidence


def test_vcs_dependency_check_flags_inline_notebook_install(tmp_path: Path) -> None:
    notebook_path = tmp_path / "analysis.ipynb"
    artifact = SourceArtifact(
        path=notebook_path,
        kind="notebook",
        content="!pip install git+https://github.com/example/research-utils.git@main#egg=research-utils\n",
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_unpinned_vcs_dependencies(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC043"
    assert findings[0].file_path == "analysis.ipynb"
    assert "line 1" in findings[0].evidence
    assert "main" in findings[0].evidence


def test_scan_flags_missing_requirement_include_file(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("-r requirements/base.txt\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\npython -m pip install -r requirements.txt\npython analysis.py\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "analysis.py").write_text("print('ready')\n", encoding="utf-8")

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC023")

    assert finding.severity == "high"
    assert finding.category == "environment"
    assert finding.file_path == "requirements.txt"
    assert "requirements/base.txt" in finding.evidence


def test_requirement_include_check_accepts_present_include_file(tmp_path: Path) -> None:
    requirements_dir = tmp_path / "requirements"
    requirements_dir.mkdir()
    (tmp_path / "requirements.txt").write_text("-r requirements/base.txt\n", encoding="utf-8")
    (requirements_dir / "base.txt").write_text("pandas==2.2.2\n", encoding="utf-8")

    assert check_missing_requirement_include_files(tmp_path) == []


def test_scan_flags_missing_local_dependency_path(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("-e ./vendor/private-utils\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\npython -m pip install -r requirements.txt\npython analysis.py\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "analysis.py").write_text("print('ready')\n", encoding="utf-8")

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC027")

    assert finding.severity == "high"
    assert finding.category == "environment"
    assert finding.file_path == "requirements.txt"
    assert "./vendor/private-utils" in finding.evidence


def test_local_dependency_path_check_accepts_present_path(tmp_path: Path) -> None:
    vendor = tmp_path / "vendor" / "private-utils"
    vendor.mkdir(parents=True)
    (tmp_path / "requirements.txt").write_text("-e ./vendor/private-utils\n", encoding="utf-8")

    assert check_missing_local_dependency_paths(tmp_path) == []


def test_scan_flags_undeclared_common_import(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("numpy==2.0.0\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\npython -m pip install -r requirements.txt\npython analysis.py\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "analysis.py").write_text(
        "import pandas as pd\nfrom sklearn.model_selection import train_test_split\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC028")

    assert finding.severity == "medium"
    assert finding.category == "environment"
    assert finding.file_path == "analysis.py"
    assert "pandas" in finding.evidence
    assert "scikit-learn" in finding.evidence


def test_undeclared_common_import_check_accepts_declared_imports(tmp_path: Path) -> None:
    source_path = tmp_path / "analysis.py"
    source_path.write_text("from sklearn.model_selection import train_test_split\nimport PIL.Image\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("scikit-learn==1.5.0\nPillow==10.4.0\n", encoding="utf-8")
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_undeclared_common_imports(tmp_path, [artifact]) == []


def test_undeclared_common_import_check_handles_notebook_magic(tmp_path: Path) -> None:
    notebook_path = tmp_path / "analysis.ipynb"
    (tmp_path / "requirements.txt").write_text("numpy==2.0.0\n", encoding="utf-8")
    artifact = SourceArtifact(
        path=notebook_path,
        kind="notebook",
        content="%matplotlib inline\nimport pandas as pd\n",
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_undeclared_common_imports(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC028"
    assert "pandas" in findings[0].evidence


def test_undeclared_common_import_check_skips_when_manifest_missing(tmp_path: Path) -> None:
    source_path = tmp_path / "analysis.py"
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content="import pandas as pd\n",
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_undeclared_common_imports(tmp_path, [artifact]) == []


def test_missing_local_module_import_check_flags_project_helper_imports(tmp_path: Path) -> None:
    source_path = tmp_path / "analysis.py"
    source_path.write_text(
        "import utils\nfrom preprocessing.clean import normalize\nfrom models.trainer import Trainer\n",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_missing_local_module_imports(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC045"
    assert findings[0].severity == "medium"
    assert findings[0].category == "onboarding"
    assert "line 1: utils" in findings[0].evidence
    assert "line 2: preprocessing.clean" in findings[0].evidence
    assert "line 3: models.trainer" in findings[0].evidence


def test_missing_local_module_import_check_accepts_present_local_modules(tmp_path: Path) -> None:
    source_path = tmp_path / "analysis.py"
    source_path.write_text("import utils\nfrom preprocessing.clean import normalize\n", encoding="utf-8")
    (tmp_path / "utils.py").write_text("VALUE = 1\n", encoding="utf-8")
    package_dir = tmp_path / "preprocessing"
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "clean.py").write_text("def normalize(value): return value\n", encoding="utf-8")
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_missing_local_module_imports(tmp_path, [artifact]) == []


def test_missing_local_module_import_check_accepts_declared_dependency(tmp_path: Path) -> None:
    source_path = tmp_path / "analysis.py"
    source_path.write_text("import utils\nimport requests\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("utils==1.0.0\nrequests==2.32.3\n", encoding="utf-8")
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_missing_local_module_imports(tmp_path, [artifact]) == []


def test_scan_flags_missing_local_helper_import(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("```bash\npython analysis.py\n```\n", encoding="utf-8")
    (tmp_path / "analysis.py").write_text("import pandas as pd\nfrom helpers.cleaning import normalize\n", encoding="utf-8")

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC045")

    assert finding.severity == "medium"
    assert finding.category == "onboarding"
    assert finding.file_path == "analysis.py"
    assert "helpers.cleaning" in finding.evidence


def test_scan_flags_undocumented_environment_variable(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\npython -m pip install -r requirements.txt\npython analysis.py\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "analysis.py").write_text(
        "import os\nDATA_DIR = os.environ['LABCHECK_DATA_DIR']\nprint(DATA_DIR)\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC024")

    assert finding.severity == "medium"
    assert finding.category == "onboarding"
    assert finding.file_path == "analysis.py"
    assert "LABCHECK_DATA_DIR" in finding.evidence


def test_environment_variable_check_accepts_env_example_documentation(tmp_path: Path) -> None:
    source_path = tmp_path / "analysis.py"
    source_path.write_text(
        "import os\napi_url = os.getenv('LABCHECK_API_URL')\n",
        encoding="utf-8",
    )
    (tmp_path / ".env.example").write_text("LABCHECK_API_URL=https://example.test\n", encoding="utf-8")
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_undocumented_environment_variables(tmp_path, list(tmp_path.rglob("*")), [artifact]) == []


def test_environment_variable_check_ignores_standard_runtime_vars(tmp_path: Path) -> None:
    source_path = tmp_path / "analysis.py"
    source = "import os\nprint(os.getenv('PATH'))\nprint(os.environ.get('GITHUB_SHA'))\n"
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source,
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_undocumented_environment_variables(tmp_path, [source_path], [artifact]) == []


def test_environment_variable_check_handles_notebook_magic_lines(tmp_path: Path) -> None:
    notebook_path = tmp_path / "analysis.ipynb"
    artifact = SourceArtifact(
        path=notebook_path,
        kind="notebook",
        content="%%time\nimport os\nvalue = os.environ.get('LABCHECK_TOKEN')\n",
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_undocumented_environment_variables(tmp_path, [notebook_path], [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC024"
    assert "LABCHECK_TOKEN" in findings[0].evidence


def test_hardcoded_secret_check_flags_env_file_and_masks_value(tmp_path: Path) -> None:
    secret = "sk-proj-" + ("A" * 28)
    env_file = tmp_path / ".env"
    env_file.write_text(f"OPENAI_API_KEY={secret}\n", encoding="utf-8")

    findings = check_hardcoded_secrets(tmp_path, [env_file])

    assert len(findings) == 1
    assert findings[0].check_id == "LC054"
    assert findings[0].severity == "high"
    assert findings[0].category == "onboarding"
    assert "OPENAI_API_KEY" in findings[0].evidence
    assert secret not in findings[0].evidence
    assert "sk-p...AAAA" in findings[0].evidence


def test_hardcoded_secret_check_ignores_env_example_placeholder(tmp_path: Path) -> None:
    env_file = tmp_path / ".env.example"
    env_file.write_text("OPENAI_API_KEY=your_api_key\n", encoding="utf-8")

    assert check_hardcoded_secrets(tmp_path, [env_file]) == []


def test_hardcoded_secret_check_flags_python_token_assignment(tmp_path: Path) -> None:
    token = "ghp_" + ("A" * 36)
    script = tmp_path / "client.py"
    script.write_text(f'github_token = "{token}"\n', encoding="utf-8")

    findings = check_hardcoded_secrets(tmp_path, [script])

    assert len(findings) == 1
    assert findings[0].check_id == "LC054"
    assert findings[0].file_path == "client.py"
    assert token not in findings[0].evidence


def test_hardcoded_secret_check_flags_private_key_marker(tmp_path: Path) -> None:
    marker = "-----BEGIN " + "PRIVATE KEY-----"
    key_file = tmp_path / "service-account.key"
    key_file.write_text(f"{marker}\nredacted\n", encoding="utf-8")

    findings = check_hardcoded_secrets(tmp_path, [key_file])

    assert len(findings) == 1
    assert findings[0].check_id == "LC054"
    assert "private key block" in findings[0].evidence


def test_scan_flags_hardcoded_secret(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("requests==2.32.3\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\npython -m pip install -r requirements.txt\npython client.py\n```\n",
        encoding="utf-8",
    )
    token = "hf_" + ("A" * 32)
    (tmp_path / "client.py").write_text(f'API_TOKEN = "{token}"\nprint("ready")\n', encoding="utf-8")

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC054")

    assert finding.file_path == "client.py"
    assert token not in finding.evidence
    assert "API_TOKEN" in finding.evidence


def test_interactive_prompt_check_flags_input_and_getpass(tmp_path: Path) -> None:
    source_path = tmp_path / "analysis.py"
    source_path.write_text(
        """
import getpass
from getpass import getpass as password_prompt

run_label = input("Run label: ")
token = getpass.getpass("Token: ")
secret = password_prompt("Secret: ")
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_interactive_prompts(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC041"
    assert findings[0].severity == "medium"
    assert findings[0].category == "onboarding"
    assert "input" in findings[0].evidence
    assert "getpass.getpass" in findings[0].evidence
    assert "password_prompt" in findings[0].evidence


def test_interactive_prompt_check_ignores_shadowed_input(tmp_path: Path) -> None:
    source_path = tmp_path / "analysis.py"
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=(
            "def input(value):\n"
            "    return value\n"
            "label = input('not a terminal prompt')\n"
        ),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_interactive_prompts(tmp_path, [artifact]) == []


def test_interactive_prompt_check_handles_notebook_magic_lines(tmp_path: Path) -> None:
    notebook_path = tmp_path / "analysis.ipynb"
    artifact = SourceArtifact(
        path=notebook_path,
        kind="notebook",
        content="%%time\nrun_label = input('Run label: ')\n",
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_interactive_prompts(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC041"


def test_scan_flags_interactive_prompt(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\npython -m pip install -r requirements.txt\npython analysis.py\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "analysis.py").write_text("run_label = input('Run label: ')\n", encoding="utf-8")

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC041")

    assert finding.severity == "medium"
    assert finding.category == "onboarding"
    assert finding.file_path == "analysis.py"


def test_working_directory_change_check_flags_chdir_aliases(tmp_path: Path) -> None:
    source_path = tmp_path / "analysis.py"
    source_path.write_text(
        """
import os
import os as operating_system
from os import chdir as cd

os.chdir("notebooks")
operating_system.chdir("../data")
cd("experiments")
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_working_directory_changes(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC051"
    assert findings[0].severity == "medium"
    assert findings[0].category == "portability"
    assert "os.chdir" in findings[0].evidence
    assert "operating_system.chdir" in findings[0].evidence
    assert "cd(...)" in findings[0].evidence


def test_working_directory_change_check_handles_notebook_cd_magic(tmp_path: Path) -> None:
    notebook_path = tmp_path / "analysis.ipynb"
    artifact = SourceArtifact(
        path=notebook_path,
        kind="notebook",
        content=(
            "%%time\n"
            "%cd notebooks\n"
            "get_ipython().run_line_magic('cd', '../data')\n"
        ),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_working_directory_changes(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC051"
    assert "%cd notebooks" in findings[0].evidence
    assert "run_line_magic('cd'" in findings[0].evidence


def test_working_directory_change_check_ignores_nonpersistent_shell_cd(tmp_path: Path) -> None:
    notebook_path = tmp_path / "analysis.ipynb"
    artifact = SourceArtifact(
        path=notebook_path,
        kind="notebook",
        content="!cd notebooks\nprint('done')\n",
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_working_directory_changes(tmp_path, [artifact]) == []


def test_scan_flags_working_directory_change(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\npython -m pip install -r requirements.txt\npython analysis.py\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "analysis.py").write_text("import os\nos.chdir('notebooks')\n", encoding="utf-8")

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC051")

    assert finding.severity == "medium"
    assert finding.category == "portability"
    assert finding.file_path == "analysis.py"


def test_accelerator_requirement_check_flags_cuda_without_docs(tmp_path: Path) -> None:
    source_path = tmp_path / "train.py"
    source_path.write_text(
        "import torch\nmodel = build_model().cuda()\ndevice = torch.device('cuda')\n",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_undocumented_accelerator_requirement(tmp_path, [source_path], [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC046"
    assert findings[0].severity == "medium"
    assert findings[0].category == "onboarding"
    assert ".cuda" in findings[0].evidence
    assert "torch.device" in findings[0].evidence


def test_accelerator_requirement_check_accepts_documented_gpu(tmp_path: Path) -> None:
    readme_path = tmp_path / "README.md"
    source_path = tmp_path / "train.py"
    readme_path.write_text(
        "Requires an NVIDIA CUDA GPU. CPU fallback is not supported.\n",
        encoding="utf-8",
    )
    source_path.write_text("import torch\nmodel = model.to('cuda')\n", encoding="utf-8")
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_undocumented_accelerator_requirement(
        tmp_path,
        [readme_path, source_path],
        [artifact],
    )

    assert findings == []


def test_scan_flags_undocumented_accelerator_requirement(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("torch==2.4.0\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\npython -m pip install -r requirements.txt\npython train.py\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "train.py").write_text(
        "import torch\ndevice = torch.device('cuda')\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC046")

    assert finding.severity == "medium"
    assert finding.category == "onboarding"
    assert finding.file_path == "train.py"


def test_absolute_path_check_ignores_urls(tmp_path: Path) -> None:
    readme_path = tmp_path / "README.md"
    readme_path.write_text("Open https://colab.research.google.com/demo.ipynb", encoding="utf-8")

    findings = check_absolute_paths(tmp_path, [readme_path])

    assert findings == []


def test_absolute_path_check_ignores_escaped_notebook_newlines(tmp_path: Path) -> None:
    notebook_path = tmp_path / "analysis.ipynb"
    notebook_path.write_text('{"source": ["Something:\\n", "Following:\\n"]}', encoding="utf-8")

    findings = check_absolute_paths(tmp_path, [notebook_path])

    assert findings == []


def test_absolute_path_check_ignores_regex_and_illustrative_examples(tmp_path: Path) -> None:
    source_path = tmp_path / "checks.py"
    catalog_path = tmp_path / "catalog.py"
    source_path.write_text('re.compile(r"/Users/[^\\\\s\\"\\\']+")\n', encoding="utf-8")
    catalog_path.write_text(
        'detects="Hardcoded paths such as C:\\\\Users\\\\..., /content/drive/..., or /kaggle/input/...."\n',
        encoding="utf-8",
    )

    findings = check_absolute_paths(tmp_path, [source_path, catalog_path])

    assert findings == []


def test_absolute_path_check_flags_literal_machine_path(tmp_path: Path) -> None:
    notebook_path = tmp_path / "analysis.ipynb"
    notebook_path.write_text('"C:\\\\Users\\\\researcher\\\\Desktop\\\\data.csv"', encoding="utf-8")

    findings = check_absolute_paths(tmp_path, [notebook_path])

    assert len(findings) == 1
    assert findings[0].check_id == "LC006"


def test_absolute_path_check_flags_hosted_notebook_paths(tmp_path: Path) -> None:
    notebook_path = tmp_path / "analysis.ipynb"
    script_path = tmp_path / "train.py"
    notebook_path.write_text('"/content/drive/MyDrive/research/data.csv"', encoding="utf-8")
    script_path.write_text('DATA = "/kaggle/input/chest-xray/train.csv"\n', encoding="utf-8")

    findings = check_absolute_paths(tmp_path, [notebook_path, script_path])

    assert [finding.check_id for finding in findings] == ["LC006", "LC006"]
    assert "/content/drive/MyDrive/research/data.csv" in findings[0].evidence
    assert "/kaggle/input/chest-xray/train.csv" in findings[1].evidence


def test_missing_input_artifacts_are_deduplicated_per_file(tmp_path: Path) -> None:
    notebook_path = tmp_path / "analysis.ipynb"
    notebook_path.write_text("{}", encoding="utf-8")
    artifact = SourceArtifact(
        path=notebook_path,
        kind="notebook",
        content="",
        reads=["data/train.csv", "data/train.csv"],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_missing_input_artifacts(tmp_path, [artifact])

    assert len(findings) == 1
    assert "data/train.csv" in findings[0].evidence


def test_missing_input_artifacts_accept_repo_root_relative_paths(tmp_path: Path) -> None:
    notebook_dir = tmp_path / "notebooks"
    notebook_dir.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "train.csv").write_text("value\n1\n", encoding="utf-8")
    notebook_path = notebook_dir / "analysis.ipynb"
    notebook_path.write_text("{}", encoding="utf-8")
    artifact = SourceArtifact(
        path=notebook_path,
        kind="notebook",
        content="",
        reads=["data/train.csv"],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_missing_input_artifacts(tmp_path, [artifact])

    assert findings == []


def test_mutable_remote_input_check_flags_raw_github_branch_url(tmp_path: Path) -> None:
    source_path = tmp_path / "analysis.py"
    url = "https://raw.githubusercontent.com/example/lab-data/main/train.csv"
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=f'df = pd.read_csv("{url}")\n',
        reads=[url],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_mutable_remote_input_artifacts(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC022"
    assert findings[0].severity == "medium"
    assert "main/train.csv" in findings[0].evidence


def test_mutable_remote_input_check_accepts_commit_pinned_url(tmp_path: Path) -> None:
    source_path = tmp_path / "analysis.py"
    url = "https://raw.githubusercontent.com/example/lab-data/0123456789abcdef0123456789abcdef01234567/train.csv"
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=f'df = pd.read_csv("{url}")\n',
        reads=[url],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_mutable_remote_input_artifacts(tmp_path, [artifact]) == []


def test_mutable_remote_input_check_accepts_checksum_context(tmp_path: Path) -> None:
    source_path = tmp_path / "analysis.py"
    url = "https://raw.githubusercontent.com/example/lab-data/main/train.csv"
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=f'# sha256: abc123\ndf = pd.read_csv("{url}")\n',
        reads=[url],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_mutable_remote_input_artifacts(tmp_path, [artifact]) == []


def test_scan_flags_mutable_remote_input_url(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\npython -m pip install -r requirements.txt\npython analysis.py\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "analysis.py").write_text(
        'import pandas as pd\n'
        'df = pd.read_csv("https://raw.githubusercontent.com/example/lab-data/main/train.csv")\n',
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC022")

    assert finding.category == "artifacts"
    assert finding.file_path == "analysis.py"


def test_scan_flags_mutable_remote_input_download_call(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("requests==2.32.3\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\npython -m pip install -r requirements.txt\npython download_data.py\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "download_data.py").write_text(
        'import requests\n'
        'response = requests.get("https://raw.githubusercontent.com/example/lab-data/main/train.csv")\n',
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC022")

    assert finding.category == "artifacts"
    assert finding.file_path == "download_data.py"
    assert "raw.githubusercontent.com/example/lab-data/main/train.csv" in finding.evidence


def test_remote_download_timeout_check_flags_requests_and_urllib(tmp_path: Path) -> None:
    source_path = tmp_path / "download_data.py"
    source_path.write_text(
        "import requests\n"
        "import urllib.request\n"
        "response = requests.get('https://example.com/data/train.csv')\n"
        "urllib.request.urlretrieve('https://example.com/data/labels.csv', 'labels.csv')\n",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_remote_download_without_timeout(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC047"
    assert findings[0].severity == "medium"
    assert findings[0].category == "artifacts"
    assert "requests.get" in findings[0].evidence
    assert "urllib.request.urlretrieve" in findings[0].evidence


def test_remote_download_timeout_check_accepts_explicit_timeout(tmp_path: Path) -> None:
    source_path = tmp_path / "download_data.py"
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=(
            "import requests\n"
            "import urllib.request\n"
            "response = requests.get('https://example.com/data/train.csv', timeout=30)\n"
            "handle = urllib.request.urlopen('https://example.com/data/labels.csv', timeout=30)\n"
        ),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_remote_download_without_timeout(tmp_path, [artifact]) == []


def test_remote_download_timeout_check_handles_notebook_shell_lines(tmp_path: Path) -> None:
    notebook_path = tmp_path / "analysis.ipynb"
    artifact = SourceArtifact(
        path=notebook_path,
        kind="notebook",
        content=(
            "!curl https://example.com/data/train.csv -o data/train.csv\n"
            "!wget --timeout 30 https://example.com/data/labels.csv\n"
        ),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_remote_download_without_timeout(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC047"
    assert "curl https://example.com/data/train.csv" in findings[0].evidence
    assert "labels.csv" not in findings[0].evidence


def test_remote_artifact_checksum_check_flags_stable_remote_artifact(tmp_path: Path) -> None:
    source_path = tmp_path / "analysis.py"
    url = "https://example.com/releases/v1/train.csv"
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=f'df = pd.read_csv("{url}")\n',
        reads=[url],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_remote_artifact_without_checksum(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC050"
    assert findings[0].severity == "medium"
    assert findings[0].category == "artifacts"
    assert "without visible checksum" in findings[0].evidence


def test_remote_artifact_checksum_check_accepts_hash_context(tmp_path: Path) -> None:
    source_path = tmp_path / "analysis.py"
    url = "https://example.com/releases/v1/train.csv"
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=f'# sha256: abc123\ndf = pd.read_csv("{url}")\n',
        reads=[url],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_remote_artifact_without_checksum(tmp_path, [artifact]) == []


def test_remote_artifact_checksum_check_skips_mutable_url_already_covered(tmp_path: Path) -> None:
    source_path = tmp_path / "analysis.py"
    url = "https://raw.githubusercontent.com/example/lab-data/main/train.csv"
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=f'df = pd.read_csv("{url}")\n',
        reads=[url],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_remote_artifact_without_checksum(tmp_path, [artifact]) == []


def test_scan_flags_remote_download_without_timeout(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("requests==2.32.3\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\npython -m pip install -r requirements.txt\npython download_data.py\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "download_data.py").write_text(
        "import requests\nresponse = requests.get('https://example.com/data/train.csv')\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC047")

    assert finding.category == "artifacts"
    assert finding.file_path == "download_data.py"
    assert "requests.get" in finding.evidence


def test_scan_flags_remote_artifact_without_checksum(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\npython -m pip install -r requirements.txt\npython analysis.py\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "analysis.py").write_text(
        "import pandas as pd\n"
        "df = pd.read_csv('https://example.com/releases/v1/train.csv')\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC050")

    assert finding.category == "artifacts"
    assert finding.file_path == "analysis.py"
    assert "example.com/releases/v1/train.csv" in finding.evidence


def test_huggingface_revision_check_flags_unpinned_artifacts(tmp_path: Path) -> None:
    source_path = tmp_path / "hf_assets.py"
    source_path.write_text(
        """
import datasets as ds
from transformers import AutoModel, pipeline
from huggingface_hub import hf_hub_download

data = ds.load_dataset("squad")
model = AutoModel.from_pretrained("bert-base-uncased")
classifier = pipeline("text-classification", model="distilbert-base-uncased")
weights = hf_hub_download("org/model", filename="pytorch_model.bin")
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_unpinned_huggingface_revisions(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC042"
    assert findings[0].severity == "medium"
    assert findings[0].category == "artifacts"
    assert "load_dataset('squad'" in findings[0].evidence
    assert "AutoModel.from_pretrained('bert-base-uncased'" in findings[0].evidence
    assert "hf_hub_download('org/model'" in findings[0].evidence


def test_huggingface_revision_check_accepts_revision_pins_and_local_paths(tmp_path: Path) -> None:
    source_path = tmp_path / "hf_assets.py"
    source_path.write_text(
        """
from datasets import load_dataset
from transformers import AutoTokenizer
from huggingface_hub import snapshot_download

data = load_dataset("squad", revision="6c1f3f4")
local_data = load_dataset("csv", data_files="data/train.csv")
tokenizer = AutoTokenizer.from_pretrained("models/tokenizer")
snapshot = snapshot_download("org/model", revision="v1.0.0")
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_unpinned_huggingface_revisions(tmp_path, [artifact]) == []


def test_huggingface_revision_check_handles_notebook_magic_lines(tmp_path: Path) -> None:
    notebook_path = tmp_path / "analysis.ipynb"
    artifact = SourceArtifact(
        path=notebook_path,
        kind="notebook",
        content="%%time\nfrom datasets import load_dataset\ndata = load_dataset('glue')\n",
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_unpinned_huggingface_revisions(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC042"


def test_scan_flags_huggingface_revision_gap(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("datasets==2.20.0\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\npython -m pip install -r requirements.txt\npython analysis.py\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "analysis.py").write_text(
        "from datasets import load_dataset\n"
        "data = load_dataset('squad')\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC042")

    assert finding.category == "artifacts"
    assert finding.file_path == "analysis.py"


def test_data_versioning_check_flags_undocumented_dvc_restore_steps(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Run `python train.py` to reproduce results.\n", encoding="utf-8")
    (tmp_path / "data.dvc").write_text("outs:\n  - md5: abc\n    path: data/train.csv\n", encoding="utf-8")

    findings = check_missing_data_versioning_restore_steps(tmp_path, list(tmp_path.rglob("*")))

    assert len(findings) == 1
    assert findings[0].check_id == "LC018"
    assert findings[0].severity == "low"
    assert findings[0].file_path == "README.md"
    assert "DVC metadata" in findings[0].evidence
    assert "dvc pull" in findings[0].suggested_fix


def test_data_versioning_check_flags_undocumented_git_lfs_restore_steps(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Run `python train.py` to reproduce results.\n", encoding="utf-8")
    (tmp_path / ".gitattributes").write_text("data/*.csv filter=lfs diff=lfs merge=lfs -text\n", encoding="utf-8")

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC018")

    assert finding.severity == "low"
    assert finding.category == "artifacts"
    assert "Git LFS metadata" in finding.evidence
    assert "git lfs pull" in finding.suggested_fix


def test_data_versioning_check_accepts_documented_restore_steps(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "Restore data with `dvc pull` and `git lfs pull` before running notebooks.\n",
        encoding="utf-8",
    )
    (tmp_path / "dvc.yaml").write_text("stages: {}\n", encoding="utf-8")
    (tmp_path / ".gitattributes").write_text("models/*.pt filter=lfs diff=lfs merge=lfs -text\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert "LC018" not in {finding.check_id for finding in report.findings}


def test_data_versioning_check_accepts_module_and_hyphenated_restore_commands(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "Restore artifacts with `python -m dvc pull` and `git-lfs pull` before training.\n",
        encoding="utf-8",
    )
    (tmp_path / "dvc.yaml").write_text("stages: {}\n", encoding="utf-8")
    (tmp_path / ".gitattributes").write_text("models/*.pt filter=lfs diff=lfs merge=lfs -text\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert "LC018" not in {finding.check_id for finding in report.findings}


def test_data_versioning_check_accepts_makefile_restore_wrapper(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Run `make data` before `python train.py`.\n", encoding="utf-8")
    (tmp_path / "Makefile").write_text("data:\n\tdvc pull data/raw\n", encoding="utf-8")
    (tmp_path / "data.dvc").write_text("outs:\n  - md5: abc\n    path: data/raw\n", encoding="utf-8")

    findings = check_missing_data_versioning_restore_steps(tmp_path, list(tmp_path.rglob("*")))

    assert findings == []


def test_data_versioning_check_accepts_package_script_restore_wrapper(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Run `npm run fetch-data` before tests.\n", encoding="utf-8")
    (tmp_path / "package.json").write_text(
        '{"scripts": {"fetch-data": "git lfs pull"}}\n',
        encoding="utf-8",
    )
    (tmp_path / ".gitattributes").write_text("data/*.csv filter=lfs diff=lfs merge=lfs -text\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert "LC018" not in {finding.check_id for finding in report.findings}


def test_data_versioning_check_accepts_shell_script_restore_wrapper(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "Restore data with `bash scripts/restore-data.sh` before running notebooks.\n",
        encoding="utf-8",
    )
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "restore-data.sh").write_text("dvc pull\ngit lfs pull\n", encoding="utf-8")
    (tmp_path / "dvc.yaml").write_text("stages: {}\n", encoding="utf-8")
    (tmp_path / ".gitattributes").write_text("models/*.pt filter=lfs diff=lfs merge=lfs -text\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert "LC018" not in {finding.check_id for finding in report.findings}


def test_data_versioning_check_does_not_accept_unimplemented_restore_wrapper(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("Run `make data` before `python train.py`.\n", encoding="utf-8")
    (tmp_path / "Makefile").write_text("train:\n\tpython train.py\n", encoding="utf-8")
    (tmp_path / "data.dvc").write_text("outs:\n  - md5: abc\n    path: data/raw\n", encoding="utf-8")

    findings = check_missing_data_versioning_restore_steps(tmp_path, list(tmp_path.rglob("*")))

    assert [finding.check_id for finding in findings] == ["LC018"]


def test_missing_input_artifacts_do_not_treat_parent_escape_as_repo_artifact(tmp_path: Path) -> None:
    outside_data = tmp_path.parent / "labcheck-outside-data.csv"
    outside_data.write_text("value\n1\n", encoding="utf-8")
    try:
        notebook_path = tmp_path / "analysis.ipynb"
        notebook_path.write_text("{}", encoding="utf-8")
        artifact = SourceArtifact(
            path=notebook_path,
            kind="notebook",
            content="",
            reads=[f"../{outside_data.name}"],
            writes=[],
            uses_randomness=False,
            seeds_randomness=False,
        )

        findings = check_missing_input_artifacts(tmp_path, [artifact])

        assert len(findings) == 1
        assert outside_data.name in findings[0].evidence
    finally:
        outside_data.unlink(missing_ok=True)


def test_gitignored_input_artifact_check_flags_existing_ignored_file(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("data/\n", encoding="utf-8")
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "train.csv").write_text("value\n1\n", encoding="utf-8")
    script_path = tmp_path / "analysis.py"
    artifact = SourceArtifact(
        path=script_path,
        kind="python",
        content="",
        reads=["data/train.csv"],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_gitignored_input_artifacts(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC053"
    assert findings[0].severity == "high"
    assert findings[0].category == "artifacts"
    assert "data/train.csv" in findings[0].evidence
    assert ".gitignore pattern" in findings[0].evidence


def test_gitignored_input_artifact_check_flags_existing_ignored_glob_dir(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("/data/raw/\n", encoding="utf-8")
    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)
    (raw_dir / "batch.csv").write_text("value\n1\n", encoding="utf-8")
    script_path = tmp_path / "analysis.py"
    artifact = SourceArtifact(
        path=script_path,
        kind="python",
        content="from pathlib import Path\nfiles = list(Path('data/raw').glob('*.csv'))\n",
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_gitignored_input_artifacts(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC053"
    assert "data/raw" in findings[0].evidence


def test_gitignored_input_artifact_check_accepts_unignored_exception(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("data/*\n!data/fixture.csv\n", encoding="utf-8")
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "fixture.csv").write_text("value\n1\n", encoding="utf-8")
    artifact = SourceArtifact(
        path=tmp_path / "analysis.py",
        kind="python",
        content="",
        reads=["data/fixture.csv"],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_gitignored_input_artifacts(tmp_path, [artifact]) == []


def test_gitignored_input_artifact_check_flags_negated_file_below_ignored_parent(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("data/\n!data/fixture.csv\n", encoding="utf-8")
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "fixture.csv").write_text("value\n1\n", encoding="utf-8")
    artifact = SourceArtifact(
        path=tmp_path / "analysis.py",
        kind="python",
        content="",
        reads=["data/fixture.csv"],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_gitignored_input_artifacts(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC053"
    assert "data/fixture.csv" in findings[0].evidence


def test_scan_flags_gitignored_input_artifact(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("data/\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\npython -m pip install -r requirements.txt\npython analysis.py\n```\n",
        encoding="utf-8",
    )
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "train.csv").write_text("value\n1\n", encoding="utf-8")
    (tmp_path / "analysis.py").write_text(
        "import pandas as pd\ndf = pd.read_csv('data/train.csv')\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC053")

    assert finding.file_path == "analysis.py"
    assert finding.category == "artifacts"
    assert "data/train.csv" in finding.evidence


def test_missing_globbed_input_paths_flags_absent_data_globs(tmp_path: Path) -> None:
    script_path = tmp_path / "analysis.py"
    source = (
        "from glob import glob\n"
        "import os\n"
        "csv_files = glob('data/raw/*.csv')\n"
        "image_files = os.listdir('images')\n"
    )
    artifact = SourceArtifact(
        path=script_path,
        kind="python",
        content=source,
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_missing_globbed_input_paths(tmp_path, [artifact])

    assert [finding.check_id for finding in findings] == ["LC036", "LC036"]
    assert findings[0].severity == "high"
    assert "data/raw/*.csv" in findings[0].evidence
    assert "data/raw" in findings[0].evidence
    assert "images" in findings[1].evidence


def test_missing_globbed_input_paths_flags_pathlib_globs(tmp_path: Path) -> None:
    script_path = tmp_path / "analysis.py"
    source = (
        "from pathlib import Path\n"
        "records = list(Path('datasets').rglob('*.jsonl'))\n"
    )
    artifact = SourceArtifact(
        path=script_path,
        kind="python",
        content=source,
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_missing_globbed_input_paths(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC036"
    assert "datasets/*.jsonl" in findings[0].evidence


def test_missing_globbed_input_paths_accepts_existing_input_dir(tmp_path: Path) -> None:
    (tmp_path / "data" / "raw").mkdir(parents=True)
    script_path = tmp_path / "analysis.py"
    artifact = SourceArtifact(
        path=script_path,
        kind="python",
        content="import glob\nfiles = glob.glob('data/raw/*.csv')\n",
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_missing_globbed_input_paths(tmp_path, [artifact]) == []


def test_missing_globbed_input_paths_ignores_non_input_globs(tmp_path: Path) -> None:
    script_path = tmp_path / "analysis.py"
    artifact = SourceArtifact(
        path=script_path,
        kind="python",
        content="from pathlib import Path\nmodules = list(Path('src').glob('*.py'))\n",
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_missing_globbed_input_paths(tmp_path, [artifact]) == []


def test_scan_flags_missing_globbed_input_path(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\npython -m pip install -r requirements.txt\npython analysis.py\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "analysis.py").write_text(
        "from pathlib import Path\nfiles = list(Path('data/raw').glob('*.csv'))\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC036")

    assert finding.category == "artifacts"
    assert finding.file_path == "analysis.py"


def test_unsorted_file_discovery_flags_existing_data_globs(tmp_path: Path) -> None:
    (tmp_path / "data" / "raw").mkdir(parents=True)
    (tmp_path / "images").mkdir()
    script_path = tmp_path / "analysis.py"
    source = (
        "from glob import glob\n"
        "import os\n"
        "csv_files = glob('data/raw/*.csv')\n"
        "image_files = os.listdir('images')\n"
    )
    artifact = SourceArtifact(
        path=script_path,
        kind="python",
        content=source,
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_unsorted_file_discovery_order(tmp_path, [artifact])

    assert [finding.check_id for finding in findings] == ["LC038", "LC038"]
    assert findings[0].severity == "medium"
    assert findings[0].category == "determinism"
    assert "data/raw/*.csv" in findings[0].evidence
    assert "images" in findings[1].evidence


def test_unsorted_file_discovery_flags_pathlib_globs(tmp_path: Path) -> None:
    (tmp_path / "datasets").mkdir()
    script_path = tmp_path / "analysis.py"
    source = (
        "from pathlib import Path\n"
        "records = list(Path('datasets').rglob('*.jsonl'))\n"
    )
    artifact = SourceArtifact(
        path=script_path,
        kind="python",
        content=source,
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_unsorted_file_discovery_order(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC038"
    assert "datasets/*.jsonl" in findings[0].evidence


def test_unsorted_file_discovery_accepts_sorted_calls_and_in_place_sort(tmp_path: Path) -> None:
    (tmp_path / "data" / "raw").mkdir(parents=True)
    (tmp_path / "images").mkdir()
    script_path = tmp_path / "analysis.py"
    source = (
        "from glob import glob\n"
        "from pathlib import Path\n"
        "import os\n"
        "csv_files = sorted(glob('data/raw/*.csv'))\n"
        "records = list(sorted(Path('data/raw').glob('*.jsonl')))\n"
        "image_files = os.listdir('images')\n"
        "image_files.sort()\n"
    )
    artifact = SourceArtifact(
        path=script_path,
        kind="python",
        content=source,
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_unsorted_file_discovery_order(tmp_path, [artifact]) == []


def test_unsorted_file_discovery_ignores_missing_and_non_input_paths(tmp_path: Path) -> None:
    script_path = tmp_path / "analysis.py"
    source = (
        "from pathlib import Path\n"
        "missing = list(Path('data/raw').glob('*.csv'))\n"
        "modules = list(Path('src').glob('*.py'))\n"
    )
    artifact = SourceArtifact(
        path=script_path,
        kind="python",
        content=source,
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_unsorted_file_discovery_order(tmp_path, [artifact]) == []


def test_scan_flags_unsorted_file_discovery_order(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\npython -m pip install -r requirements.txt\npython analysis.py\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "data" / "raw").mkdir(parents=True)
    (tmp_path / "analysis.py").write_text(
        "from pathlib import Path\nfiles = list(Path('data/raw').glob('*.csv'))\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC038")

    assert finding.category == "determinism"
    assert finding.file_path == "analysis.py"


def test_set_derived_order_flags_list_set_conversion(tmp_path: Path) -> None:
    script_path = tmp_path / "analysis.py"
    artifact = SourceArtifact(
        path=script_path,
        kind="python",
        content="labels = list(set(raw_labels))\n",
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_set_derived_order(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC056"
    assert findings[0].severity == "medium"
    assert findings[0].category == "determinism"
    assert "list(set(raw_labels))" in findings[0].evidence


def test_set_derived_order_flags_loop_and_comprehension_over_set(tmp_path: Path) -> None:
    artifact = SourceArtifact(
        path=tmp_path / "analysis.py",
        kind="python",
        content=(
            "for label in set(raw_labels):\n"
            "    print(label)\n"
            "encoded = [label for label in set(raw_labels)]\n"
        ),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_set_derived_order(tmp_path, [artifact])

    assert len(findings) == 2
    assert all(finding.check_id == "LC056" for finding in findings)


def test_set_derived_order_accepts_sorted_set_and_shadowed_set(tmp_path: Path) -> None:
    artifact = SourceArtifact(
        path=tmp_path / "analysis.py",
        kind="python",
        content=(
            "labels = sorted(set(raw_labels))\n"
            "def set(values):\n"
            "    return values\n"
            "ordered = list(set(raw_labels))\n"
        ),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_set_derived_order(tmp_path, [artifact]) == []


def test_scan_flags_set_derived_order(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\npython -m pip install -r requirements.txt\npython analysis.py\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "analysis.py").write_text(
        "raw_labels = ['b', 'a', 'b']\nlabels = list(set(raw_labels))\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC056")

    assert finding.category == "determinism"
    assert finding.file_path == "analysis.py"


def test_python_hash_usage_flags_hash_based_split(tmp_path: Path) -> None:
    artifact = SourceArtifact(
        path=tmp_path / "analysis.py",
        kind="python",
        content="bucket = hash(user_id) % 10\nsplit = 'test' if bucket == 0 else 'train'\n",
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_python_hash_usage(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC057"
    assert findings[0].severity == "medium"
    assert findings[0].category == "determinism"
    assert "hash(user_id)" in findings[0].evidence


def test_python_hash_usage_accepts_hashlib_and_dunder_hash(tmp_path: Path) -> None:
    artifact = SourceArtifact(
        path=tmp_path / "analysis.py",
        kind="python",
        content=(
            "import hashlib\n"
            "stable = hashlib.sha256(user_id.encode()).hexdigest()\n"
            "class Label:\n"
            "    def __hash__(self):\n"
            "        return hash((self.name, self.version))\n"
        ),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_python_hash_usage(tmp_path, [artifact]) == []


def test_python_hash_usage_accepts_shadowed_hash(tmp_path: Path) -> None:
    artifact = SourceArtifact(
        path=tmp_path / "analysis.py",
        kind="python",
        content="def hash(value):\n    return value\nstable = hash(user_id)\n",
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_python_hash_usage(tmp_path, [artifact]) == []


def test_scan_flags_python_hash_usage(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\npython -m pip install -r requirements.txt\npython analysis.py\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "analysis.py").write_text(
        "bucket = hash(user_id) % 10\nsplit = 'test' if bucket == 0 else 'train'\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC057")

    assert finding.category == "determinism"
    assert finding.file_path == "analysis.py"


def test_timestamped_output_paths_flags_datetime_derived_write(tmp_path: Path) -> None:
    script_path = tmp_path / "analysis.py"
    source = (
        "from datetime import datetime\n"
        "stamp = datetime.now().strftime('%Y%m%d')\n"
        "df.to_csv(f'outputs/report_{stamp}.csv')\n"
    )
    artifact = SourceArtifact(
        path=script_path,
        kind="python",
        content=source,
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_timestamped_output_paths(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC037"
    assert findings[0].severity == "medium"
    assert "outputs/report_{}.csv" in findings[0].evidence


def test_timestamped_output_paths_flags_direct_current_time_in_path(tmp_path: Path) -> None:
    script_path = tmp_path / "analysis.py"
    source = (
        "import datetime\n"
        "with open(f'outputs/run_{datetime.datetime.utcnow():%Y%m%d}.txt', 'w') as handle:\n"
        "    handle.write('ok')\n"
    )
    artifact = SourceArtifact(
        path=script_path,
        kind="python",
        content=source,
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_timestamped_output_paths(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC037"


def test_timestamped_output_paths_accepts_stable_outputs_and_non_output_timestamps(tmp_path: Path) -> None:
    script_path = tmp_path / "analysis.py"
    source = (
        "from datetime import datetime\n"
        "print(datetime.now())\n"
        "df.to_csv('outputs/report.csv')\n"
    )
    artifact = SourceArtifact(
        path=script_path,
        kind="python",
        content=source,
        reads=[],
        writes=["outputs/report.csv"],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_timestamped_output_paths(tmp_path, [artifact]) == []


def test_scan_flags_timestamped_output_path(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\npython -m pip install -r requirements.txt\npython analysis.py\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "outputs").mkdir()
    (tmp_path / "analysis.py").write_text(
        "from datetime import datetime\n"
        "stamp = datetime.now().strftime('%Y%m%d')\n"
        "df.to_csv(f'outputs/report_{stamp}.csv')\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC037")

    assert finding.category == "artifacts"
    assert finding.file_path == "analysis.py"


def test_current_time_usage_flags_date_cutoff(tmp_path: Path) -> None:
    script_path = tmp_path / "analysis.py"
    source = (
        "from datetime import date\n"
        "cutoff = date.today()\n"
        "recent = df[df['created_at'] >= cutoff]\n"
    )
    artifact = SourceArtifact(
        path=script_path,
        kind="python",
        content=source,
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_current_time_usage(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC055"
    assert findings[0].severity == "medium"
    assert findings[0].category == "determinism"
    assert "date.today" in findings[0].evidence


def test_current_time_usage_flags_time_based_seed(tmp_path: Path) -> None:
    script_path = tmp_path / "analysis.py"
    artifact = SourceArtifact(
        path=script_path,
        kind="python",
        content="import time\nseed = int(time.time())\n",
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_current_time_usage(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC055"
    assert "time.time" in findings[0].evidence


def test_current_time_usage_ignores_logging_and_timestamped_output_path(tmp_path: Path) -> None:
    script_path = tmp_path / "analysis.py"
    artifact = SourceArtifact(
        path=script_path,
        kind="python",
        content=(
            "from datetime import datetime\n"
            "print(datetime.now())\n"
            "stamp = datetime.now().strftime('%Y%m%d')\n"
            "df.to_csv(f'outputs/report_{stamp}.csv')\n"
        ),
        reads=[],
        writes=["outputs/report.csv"],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_current_time_usage(tmp_path, [artifact]) == []


def test_scan_flags_current_time_usage(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\npython -m pip install -r requirements.txt\npython analysis.py\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "analysis.py").write_text(
        "import pandas as pd\nfrom datetime import date\ncutoff = date.today()\nprint(cutoff)\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC055")

    assert finding.category == "determinism"
    assert finding.file_path == "analysis.py"


def test_provenance_graph_deduplicates_repeated_edges(tmp_path: Path) -> None:
    notebook_path = tmp_path / "analysis.ipynb"
    notebook_path.write_text("{}", encoding="utf-8")
    artifact = SourceArtifact(
        path=notebook_path,
        kind="notebook",
        content="",
        reads=["data/train.csv", "data/train.csv"],
        writes=["out.csv", "out.csv"],
        uses_randomness=False,
        seeds_randomness=False,
    )

    graph = build_provenance_graph(tmp_path, [artifact])

    edge_keys = {(edge.source, edge.target, edge.kind) for edge in graph.edges}
    assert len(graph.edges) == 2
    assert len(edge_keys) == 2


def test_orphan_output_artifacts_flag_committed_outputs_without_producers(tmp_path: Path) -> None:
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    output_path = output_dir / "report.csv"
    output_path.write_text("value\n1\n", encoding="utf-8")
    script_path = tmp_path / "analysis.py"
    script_path.write_text("print('ready')\n", encoding="utf-8")
    artifact = SourceArtifact(
        path=script_path,
        kind="python",
        content="",
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_orphan_output_artifacts(tmp_path, [script_path, output_path], [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC009"
    assert findings[0].file_path == "outputs/report.csv"


def test_orphan_output_artifacts_accept_visible_producers(tmp_path: Path) -> None:
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    output_path = output_dir / "report.csv"
    output_path.write_text("value\n1\n", encoding="utf-8")
    script_path = tmp_path / "analysis.py"
    script_path.write_text("df.to_csv('outputs/report.csv')\n", encoding="utf-8")
    artifact = SourceArtifact(
        path=script_path,
        kind="python",
        content="",
        reads=[],
        writes=["outputs/report.csv"],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_orphan_output_artifacts(tmp_path, [script_path, output_path], [artifact])

    assert findings == []


def test_missing_output_directories_flags_save_to_absent_output_dir(tmp_path: Path) -> None:
    script_path = tmp_path / "analysis.py"
    source = "import joblib\njoblib.dump(model, 'models/model.joblib')\n"
    script_path.write_text(source, encoding="utf-8")
    artifact = SourceArtifact(
        path=script_path,
        kind="python",
        content=source,
        reads=[],
        writes=["models/model.joblib"],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_missing_output_directories(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC035"
    assert findings[0].severity == "high"
    assert findings[0].file_path == "analysis.py"
    assert "models/model.joblib" in findings[0].evidence
    assert "models" in findings[0].evidence


def test_missing_output_directories_accepts_existing_output_dir(tmp_path: Path) -> None:
    (tmp_path / "models").mkdir()
    script_path = tmp_path / "analysis.py"
    artifact = SourceArtifact(
        path=script_path,
        kind="python",
        content="joblib.dump(model, 'models/model.joblib')\n",
        reads=[],
        writes=["models/model.joblib"],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_missing_output_directories(tmp_path, [artifact]) == []


def test_missing_output_directories_accepts_visible_mkdir(tmp_path: Path) -> None:
    script_path = tmp_path / "analysis.py"
    source = (
        "from pathlib import Path\n"
        "output_dir = Path('outputs')\n"
        "output_dir.mkdir(parents=True, exist_ok=True)\n"
        "df.to_csv('outputs/report.csv')\n"
    )
    artifact = SourceArtifact(
        path=script_path,
        kind="python",
        content=source,
        reads=[],
        writes=["outputs/report.csv"],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_missing_output_directories(tmp_path, [artifact]) == []


def test_scan_flags_missing_output_directory(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "```bash\npython -m pip install -r requirements.txt\npython analysis.py\n```\n",
        encoding="utf-8",
    )
    (tmp_path / "analysis.py").write_text(
        "import pandas as pd\npd.DataFrame({'x': [1]}).to_csv('outputs/report.csv')\n",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC035")

    assert finding.category == "artifacts"
    assert finding.file_path == "analysis.py"


def test_orphan_output_artifacts_ignore_data_inputs(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    data_path = data_dir / "train.csv"
    data_path.write_text("value\n1\n", encoding="utf-8")

    findings = check_orphan_output_artifacts(tmp_path, [data_path], [])

    assert findings == []


def test_scan_flags_orphan_output_artifact(tmp_path: Path) -> None:
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    (output_dir / "report.csv").write_text("value\n1\n", encoding="utf-8")
    (tmp_path / "analysis.py").write_text("print('ready')\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert any(finding.check_id == "LC009" for finding in report.findings)


def test_sklearn_random_state_check_flags_seedless_split_and_model(tmp_path: Path) -> None:
    source_path = tmp_path / "train.py"
    source_path.write_text(
        """
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

train, test = train_test_split(rows, test_size=0.2)
model = RandomForestClassifier(n_estimators=20)
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_missing_sklearn_random_state(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC016"
    assert "train_test_split" in findings[0].evidence
    assert "RandomForestClassifier" in findings[0].evidence


def test_sklearn_random_state_check_accepts_seeded_calls(tmp_path: Path) -> None:
    source_path = tmp_path / "train.py"
    source_path.write_text(
        """
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import KFold, train_test_split

train, test = train_test_split(rows, test_size=0.2, random_state=42)
folds = KFold(n_splits=5, shuffle=True, random_state=42)
model = RandomForestClassifier(n_estimators=20, random_state=42)
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_missing_sklearn_random_state(tmp_path, [artifact]) == []


def test_sklearn_random_state_check_only_requires_kfold_state_when_shuffle_true(tmp_path: Path) -> None:
    source_path = tmp_path / "train.py"
    source_path.write_text(
        """
from sklearn.model_selection import KFold

folds = KFold(n_splits=5)
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_missing_sklearn_random_state(tmp_path, [artifact]) == []


def test_scan_flags_sklearn_random_state_gap(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("scikit-learn==1.5.0\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("```bash\npython train.py\n```\n", encoding="utf-8")
    (tmp_path / "train.py").write_text(
        """
from sklearn.cluster import KMeans

model = KMeans(n_clusters=3)
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC016")

    assert finding.severity == "medium"
    assert finding.category == "determinism"
    assert "KMeans" in finding.evidence


def test_pandas_random_state_check_flags_seedless_sample(tmp_path: Path) -> None:
    source_path = tmp_path / "sample.py"
    source_path.write_text(
        """
import pandas as pd

df = pd.read_csv("data/train.csv")
subset = df.sample(frac=0.2)
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_missing_pandas_random_state(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC017"
    assert "sample" in findings[0].evidence


def test_pandas_random_state_check_accepts_seeded_sample(tmp_path: Path) -> None:
    source_path = tmp_path / "sample.py"
    source_path.write_text(
        """
import pandas as pd

df = pd.DataFrame({"value": [1, 2, 3]})
subset = df.sample(n=2, random_state=42)
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_missing_pandas_random_state(tmp_path, [artifact]) == []


def test_pandas_random_state_check_ignores_non_pandas_sample_methods(tmp_path: Path) -> None:
    source_path = tmp_path / "custom.py"
    source_path.write_text(
        """
class Sampler:
    def sample(self):
        return 1

value = Sampler().sample()
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_missing_pandas_random_state(tmp_path, [artifact]) == []


def test_scan_flags_pandas_random_state_gap(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pandas==2.2.2\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("```bash\npython sample.py\n```\n", encoding="utf-8")
    (tmp_path / "sample.py").write_text(
        """
import pandas as pd

df = pd.DataFrame({"value": [1, 2, 3]})
subset = df.sample(n=2)
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC017")

    assert finding.severity == "medium"
    assert finding.category == "determinism"
    assert "sample" in finding.evidence


def test_numpy_default_rng_check_flags_seedless_generator(tmp_path: Path) -> None:
    source_path = tmp_path / "simulate.py"
    source_path.write_text(
        """
import numpy as np

np.random.seed(42)
rng = np.random.default_rng()
values = rng.normal(size=100)
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=True,
        seeds_randomness=True,
    )

    findings = check_missing_numpy_default_rng_seed(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC039"
    assert findings[0].severity == "medium"
    assert "np.random.default_rng" in findings[0].evidence


def test_numpy_default_rng_check_flags_direct_and_random_aliases(tmp_path: Path) -> None:
    source_path = tmp_path / "simulate.py"
    source_path.write_text(
        """
import numpy.random as npr
from numpy.random import default_rng as make_rng

rng_a = npr.default_rng()
rng_b = make_rng(seed=None)
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=True,
        seeds_randomness=False,
    )

    findings = check_missing_numpy_default_rng_seed(tmp_path, [artifact])

    assert len(findings) == 1
    assert "npr.default_rng" in findings[0].evidence
    assert "make_rng" in findings[0].evidence


def test_numpy_default_rng_check_accepts_seeded_generator(tmp_path: Path) -> None:
    source_path = tmp_path / "simulate.py"
    source_path.write_text(
        """
import numpy as np
from numpy.random import default_rng

seed = 42
rng_a = np.random.default_rng(seed)
rng_b = default_rng(seed=123)
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=True,
        seeds_randomness=True,
    )

    assert check_missing_numpy_default_rng_seed(tmp_path, [artifact]) == []


def test_numpy_default_rng_check_ignores_unrelated_default_rng(tmp_path: Path) -> None:
    source_path = tmp_path / "simulate.py"
    source_path.write_text(
        """
class FakeRandom:
    def default_rng(self):
        return 1

random = FakeRandom()
rng = random.default_rng()
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_missing_numpy_default_rng_seed(tmp_path, [artifact]) == []


def test_scan_flags_numpy_default_rng_seed_gap(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("numpy==2.0.0\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("```bash\npython simulate.py\n```\n", encoding="utf-8")
    (tmp_path / "simulate.py").write_text(
        """
import numpy as np

np.random.seed(42)
rng = np.random.default_rng()
values = rng.permutation(rows)
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC039")

    assert finding.severity == "medium"
    assert finding.category == "determinism"
    assert "default_rng" in finding.evidence


def test_pytorch_random_split_check_flags_missing_generator(tmp_path: Path) -> None:
    source_path = tmp_path / "train.py"
    source_path.write_text(
        """
from torch.utils.data import random_split

train_ds, valid_ds = random_split(dataset, [80, 20])
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_missing_pytorch_random_split_generator(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC031"
    assert "random_split" in findings[0].evidence


def test_pytorch_random_split_check_accepts_seeded_generator(tmp_path: Path) -> None:
    source_path = tmp_path / "train.py"
    source_path.write_text(
        """
import torch
from torch.utils import data

generator = torch.Generator().manual_seed(42)
train_ds, valid_ds = data.random_split(dataset, [80, 20], generator=generator)
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_missing_pytorch_random_split_generator(tmp_path, [artifact]) == []


def test_pytorch_random_split_check_ignores_unrelated_function(tmp_path: Path) -> None:
    source_path = tmp_path / "helpers.py"
    source_path.write_text(
        """
def random_split(values, sizes):
    return values[:sizes[0]], values[sizes[0]:]

train, valid = random_split(rows, [80, 20])
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_missing_pytorch_random_split_generator(tmp_path, [artifact]) == []


def test_scan_flags_pytorch_random_split_generator_gap(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("torch==2.4.0\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("```bash\npython train.py\n```\n", encoding="utf-8")
    (tmp_path / "train.py").write_text(
        """
import torch

train_ds, valid_ds = torch.utils.data.random_split(dataset, [80, 20])
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC031")

    assert finding.severity == "medium"
    assert finding.category == "determinism"
    assert "random_split" in finding.evidence


def test_pytorch_dataloader_generator_check_flags_shuffle_without_generator(tmp_path: Path) -> None:
    source_path = tmp_path / "train.py"
    source_path.write_text(
        """
from torch.utils.data import DataLoader

loader = DataLoader(dataset, batch_size=32, shuffle=True)
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_missing_pytorch_dataloader_generator(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC040"
    assert findings[0].severity == "medium"
    assert "DataLoader" in findings[0].evidence


def test_pytorch_dataloader_generator_check_flags_aliases_and_positional_shuffle(tmp_path: Path) -> None:
    source_path = tmp_path / "train.py"
    source_path.write_text(
        """
import torch.utils.data as tud
from torch.utils import data

loader_a = tud.DataLoader(dataset, 32, True)
loader_b = data.DataLoader(dataset, batch_size=64, shuffle=True)
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_missing_pytorch_dataloader_generator(tmp_path, [artifact])

    assert len(findings) == 1
    assert "tud.DataLoader" in findings[0].evidence
    assert "data.DataLoader" in findings[0].evidence


def test_pytorch_dataloader_generator_check_accepts_seeded_or_unshuffled_loader(tmp_path: Path) -> None:
    source_path = tmp_path / "train.py"
    source_path.write_text(
        """
import torch
from torch.utils.data import DataLoader

generator = torch.Generator().manual_seed(42)
loader_a = DataLoader(dataset, batch_size=32, shuffle=True, generator=generator)
loader_b = DataLoader(dataset, batch_size=32, shuffle=False)
loader_c = DataLoader(dataset, batch_size=32)
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_missing_pytorch_dataloader_generator(tmp_path, [artifact]) == []


def test_pytorch_dataloader_generator_check_ignores_unrelated_class(tmp_path: Path) -> None:
    source_path = tmp_path / "not_torch.py"
    source_path.write_text(
        """
class DataLoader:
    pass

loader = DataLoader(dataset, shuffle=True)
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_missing_pytorch_dataloader_generator(tmp_path, [artifact]) == []


def test_scan_flags_pytorch_dataloader_generator_gap(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("torch==2.4.0\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("```bash\npython train.py\n```\n", encoding="utf-8")
    (tmp_path / "train.py").write_text(
        """
import torch

loader = torch.utils.data.DataLoader(dataset, batch_size=32, shuffle=True)
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC040")

    assert finding.severity == "medium"
    assert finding.category == "determinism"
    assert "DataLoader" in finding.evidence


def test_pytorch_dataloader_worker_init_check_flags_num_workers_without_seed_hook(tmp_path: Path) -> None:
    source_path = tmp_path / "train.py"
    source_path.write_text(
        """
from torch.utils.data import DataLoader

loader = DataLoader(dataset, batch_size=32, num_workers=4)
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_missing_pytorch_dataloader_worker_init(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC059"
    assert "num_workers>0" in findings[0].evidence


def test_pytorch_dataloader_worker_init_check_flags_positional_workers_and_persistent_workers(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "train.py"
    source_path.write_text(
        """
import torch.utils.data as tud
from torch.utils import data

loader_a = tud.DataLoader(dataset, 32, False, None, None, 2)
loader_b = data.DataLoader(dataset, batch_size=64, persistent_workers=True)
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_missing_pytorch_dataloader_worker_init(tmp_path, [artifact])

    assert len(findings) == 1
    assert "tud.DataLoader" in findings[0].evidence
    assert "data.DataLoader" in findings[0].evidence


def test_pytorch_dataloader_worker_init_check_accepts_seed_hook_or_single_process(tmp_path: Path) -> None:
    source_path = tmp_path / "train.py"
    source_path.write_text(
        """
import random
import numpy as np
import torch
from torch.utils.data import DataLoader

def seed_worker(worker_id):
    worker_seed = torch.initial_seed() % 2**32
    np.random.seed(worker_seed)
    random.seed(worker_seed)

loader_a = DataLoader(dataset, batch_size=32, num_workers=4, worker_init_fn=seed_worker)
loader_b = DataLoader(dataset, batch_size=32, num_workers=0)
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_missing_pytorch_dataloader_worker_init(tmp_path, [artifact]) == []


def test_scan_flags_pytorch_dataloader_worker_init_gap(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("torch==2.4.0\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("```bash\npython train.py\n```\n", encoding="utf-8")
    (tmp_path / "train.py").write_text(
        """
from torch.utils.data import DataLoader

loader = DataLoader(dataset, batch_size=32, num_workers=4)
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC059")

    assert finding.severity == "medium"
    assert finding.category == "determinism"
    assert "worker_init_fn" in finding.evidence


def test_pytorch_deterministic_backend_flags_cudnn_benchmark_true(tmp_path: Path) -> None:
    source_path = tmp_path / "train.py"
    source_path.write_text(
        """
import torch

torch.backends.cudnn.benchmark = True
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_pytorch_deterministic_backend(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC058"
    assert "torch.backends.cudnn.benchmark = True" in findings[0].evidence


def test_pytorch_deterministic_backend_flags_aliases_and_disabled_algorithms(tmp_path: Path) -> None:
    source_path = tmp_path / "train.py"
    source_path.write_text(
        """
from torch.backends import cudnn
from torch import use_deterministic_algorithms as deterministic_algorithms

cudnn.deterministic = False
deterministic_algorithms(False)
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_pytorch_deterministic_backend(tmp_path, [artifact])

    assert len(findings) == 1
    assert "cudnn.deterministic = False" in findings[0].evidence
    assert "deterministic_algorithms(False)" in findings[0].evidence


def test_pytorch_deterministic_backend_accepts_deterministic_settings(tmp_path: Path) -> None:
    source_path = tmp_path / "train.py"
    source_path.write_text(
        """
import torch

torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True
torch.use_deterministic_algorithms(True)
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_pytorch_deterministic_backend(tmp_path, [artifact]) == []


def test_scan_flags_pytorch_deterministic_backend_gap(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("torch==2.4.0\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("```bash\npython train.py\n```\n", encoding="utf-8")
    (tmp_path / "train.py").write_text(
        """
import torch

torch.backends.cudnn.benchmark = True
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC058")

    assert finding.severity == "medium"
    assert finding.category == "determinism"
    assert "benchmark" in finding.evidence


def test_tensorflow_seed_check_flags_random_call_without_seed(tmp_path: Path) -> None:
    source_path = tmp_path / "train_tf.py"
    source_path.write_text(
        """
import tensorflow as tf

weights = tf.random.normal([4, 4])
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_missing_tensorflow_seed(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC032"
    assert "tf.random.normal" in findings[0].evidence


def test_tensorflow_seed_check_accepts_random_set_seed(tmp_path: Path) -> None:
    source_path = tmp_path / "train_tf.py"
    source_path.write_text(
        """
import tensorflow as tf

tf.random.set_seed(42)
weights = tf.random.uniform([4, 4])
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_missing_tensorflow_seed(tmp_path, [artifact]) == []


def test_tensorflow_seed_check_accepts_keras_set_random_seed(tmp_path: Path) -> None:
    source_path = tmp_path / "train_tf.py"
    source_path.write_text(
        """
import tensorflow as tf

tf.keras.utils.set_random_seed(42)
values = tf.random.shuffle(rows)
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_missing_tensorflow_seed(tmp_path, [artifact]) == []


def test_tensorflow_seed_check_ignores_unrelated_tf_object(tmp_path: Path) -> None:
    source_path = tmp_path / "not_tensorflow.py"
    source_path.write_text(
        """
class FakeRandom:
    def normal(self, shape):
        return shape

class FakeTensorFlow:
    random = FakeRandom()

tf = FakeTensorFlow()
weights = tf.random.normal([4, 4])
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_missing_tensorflow_seed(tmp_path, [artifact]) == []


def test_scan_flags_tensorflow_seed_gap(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("tensorflow==2.16.1\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("```bash\npython train_tf.py\n```\n", encoding="utf-8")
    (tmp_path / "train_tf.py").write_text(
        """
import tensorflow as tf

weights = tf.random.uniform([4, 4])
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC032")

    assert finding.severity == "medium"
    assert finding.category == "determinism"
    assert "tf.random.uniform" in finding.evidence


def test_xgboost_random_state_check_flags_seedless_estimator(tmp_path: Path) -> None:
    source_path = tmp_path / "train_xgb.py"
    source_path.write_text(
        """
import xgboost as xgb

model = xgb.XGBClassifier(n_estimators=100, subsample=0.8)
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_missing_xgboost_random_state(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC033"
    assert "xgb.XGBClassifier" in findings[0].evidence


def test_xgboost_random_state_check_accepts_random_state_or_seed(tmp_path: Path) -> None:
    source_path = tmp_path / "train_xgb.py"
    source_path.write_text(
        """
from xgboost import XGBClassifier, XGBRegressor

classifier = XGBClassifier(random_state=42)
regressor = XGBRegressor(seed=42)
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_missing_xgboost_random_state(tmp_path, [artifact]) == []


def test_xgboost_random_state_check_ignores_unrelated_class(tmp_path: Path) -> None:
    source_path = tmp_path / "not_xgboost.py"
    source_path.write_text(
        """
class XGBClassifier:
    pass

model = XGBClassifier()
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_missing_xgboost_random_state(tmp_path, [artifact]) == []


def test_scan_flags_xgboost_random_state_gap(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("xgboost==2.1.1\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("```bash\npython train_xgb.py\n```\n", encoding="utf-8")
    (tmp_path / "train_xgb.py").write_text(
        """
from xgboost import XGBRegressor

model = XGBRegressor(colsample_bytree=0.8)
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC033")

    assert finding.severity == "medium"
    assert finding.category == "determinism"
    assert "XGBRegressor" in finding.evidence


def test_optuna_sampler_seed_check_flags_default_create_study(tmp_path: Path) -> None:
    source_path = tmp_path / "tune.py"
    source_path.write_text(
        """
import optuna

study = optuna.create_study(direction="maximize")
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_missing_optuna_sampler_seed(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC060"
    assert "create_study" in findings[0].evidence


def test_optuna_sampler_seed_check_flags_unseeded_sampler_alias(tmp_path: Path) -> None:
    source_path = tmp_path / "tune.py"
    source_path.write_text(
        """
from optuna import create_study
from optuna.samplers import TPESampler

sampler = TPESampler(multivariate=True)
study = create_study(sampler=sampler)
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_missing_optuna_sampler_seed(tmp_path, [artifact])

    assert len(findings) == 1
    assert "TPESampler" in findings[0].evidence
    assert "sampler=sampler" in findings[0].evidence


def test_optuna_sampler_seed_check_accepts_seeded_sampler(tmp_path: Path) -> None:
    source_path = tmp_path / "tune.py"
    source_path.write_text(
        """
import optuna

sampler = optuna.samplers.TPESampler(seed=42)
study = optuna.create_study(direction="maximize", sampler=sampler)
other = optuna.samplers.RandomSampler(seed=7)
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_missing_optuna_sampler_seed(tmp_path, [artifact]) == []


def test_scan_flags_optuna_sampler_seed_gap(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("optuna==4.0.0\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("```bash\npython tune.py\n```\n", encoding="utf-8")
    (tmp_path / "tune.py").write_text(
        """
import optuna

study = optuna.create_study(direction="minimize")
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC060")

    assert finding.severity == "medium"
    assert finding.category == "determinism"
    assert "Optuna" in finding.title


def test_jax_prng_key_check_flags_reused_key(tmp_path: Path) -> None:
    source_path = tmp_path / "train_jax.py"
    source_path.write_text(
        """
import jax

key = jax.random.PRNGKey(0)
weights = jax.random.normal(key, (4, 4))
bias = jax.random.uniform(key, (4,))
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_reused_jax_prng_key(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC061"
    assert "uniform" in findings[0].evidence
    assert "key" in findings[0].evidence


def test_jax_prng_key_check_accepts_split_keys(tmp_path: Path) -> None:
    source_path = tmp_path / "train_jax.py"
    source_path.write_text(
        """
from jax import random as jr

key = jr.PRNGKey(0)
key, subkey = jr.split(key)
weights = jr.normal(subkey, (4, 4))
key, subkey = jr.split(key)
bias = jr.uniform(subkey, (4,))
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_reused_jax_prng_key(tmp_path, [artifact]) == []


def test_scan_flags_jax_prng_key_reuse(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("jax==0.4.35\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("```bash\npython train_jax.py\n```\n", encoding="utf-8")
    (tmp_path / "train_jax.py").write_text(
        """
import jax

key = jax.random.PRNGKey(0)
a = jax.random.normal(key, (4,))
b = jax.random.bernoulli(key, 0.5, (4,))
""",
        encoding="utf-8",
    )

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC061")

    assert finding.severity == "medium"
    assert finding.category == "determinism"
    assert "JAX" in finding.title


def test_polars_seed_check_flags_sample_and_shuffle_without_seed(tmp_path: Path) -> None:
    source_path = tmp_path / "train_polars.py"
    source_path.write_text(
        """
import polars as pl

subset = pl.DataFrame({"value": [1, 2, 3]}).sample(n=2)
expr = pl.col("value").shuffle()
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    findings = check_missing_polars_seed(tmp_path, [artifact])

    assert len(findings) == 1
    assert findings[0].check_id == "LC034"
    assert "DataFrame" in findings[0].evidence
    assert "shuffle" in findings[0].evidence


def test_polars_seed_check_accepts_seeded_calls(tmp_path: Path) -> None:
    source_path = tmp_path / "train_polars.py"
    source_path.write_text(
        """
from polars import DataFrame, col

subset = DataFrame({"value": [1, 2, 3]}).sample(n=2, seed=42)
expr = col("value").shuffle(seed=42)
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_missing_polars_seed(tmp_path, [artifact]) == []


def test_polars_seed_check_ignores_unrelated_sample_method(tmp_path: Path) -> None:
    source_path = tmp_path / "not_polars.py"
    source_path.write_text(
        """
class Sampler:
    def sample(self):
        return 1

subset = Sampler().sample()
""",
        encoding="utf-8",
    )
    artifact = SourceArtifact(
        path=source_path,
        kind="python",
        content=source_path.read_text(encoding="utf-8"),
        reads=[],
        writes=[],
        uses_randomness=False,
        seeds_randomness=False,
    )

    assert check_missing_polars_seed(tmp_path, [artifact]) == []


def test_scan_flags_polars_seed_gap(tmp_path: Path) -> None:
    (tmp_path / ".python-version").write_text("3.11\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("polars==1.0.0\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("```bash\npython train_polars.py\n```\n", encoding="utf-8")
    (tmp_path / "train_polars.py").write_text(
        """
import polars as pl

subset = pl.read_csv("data/train.csv").sample(fraction=0.5)
""",
        encoding="utf-8",
    )
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "train.csv").write_text("value\n1\n", encoding="utf-8")

    report = scan_path(str(tmp_path))
    finding = next(finding for finding in report.findings if finding.check_id == "LC034")

    assert finding.severity == "medium"
    assert finding.category == "determinism"
    assert "read_csv" in finding.evidence
