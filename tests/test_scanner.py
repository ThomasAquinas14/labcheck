from __future__ import annotations

import json
from pathlib import Path
import zipfile

from labcheck.checks import (
    check_absolute_paths,
    check_missing_input_artifacts,
    check_missing_notebook_kernel_metadata,
    check_missing_pandas_random_state,
    check_missing_sklearn_random_state,
    check_orphan_output_artifacts,
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


def test_scan_accepts_pyproject_python_runtime(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nrequires-python = ">=3.11"\ndependencies = ["pandas==2.2.2"]\n',
        encoding="utf-8",
    )
    (tmp_path / "analysis.py").write_text("print('ready')\n", encoding="utf-8")

    report = scan_path(str(tmp_path))

    assert "LC012" not in {finding.check_id for finding in report.findings}


def test_scan_rejects_invalid_disabled_checks_config(tmp_path: Path) -> None:
    config_path = tmp_path / "custom.toml"
    config_path.write_text('disabled_checks = "LC010"\n', encoding="utf-8")

    try:
        scan_path(str(tmp_path), config_path=str(config_path))
    except ValueError as exc:
        assert "disabled_checks must be a list of strings" in str(exc)
    else:
        raise AssertionError("Expected invalid disabled_checks config to fail")


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
    catalog_path.write_text('detects="Hardcoded paths such as C:\\\\Users\\\\..., /Users/..., or /home/...."\n', encoding="utf-8")

    findings = check_absolute_paths(tmp_path, [source_path, catalog_path])

    assert findings == []


def test_absolute_path_check_flags_literal_machine_path(tmp_path: Path) -> None:
    notebook_path = tmp_path / "analysis.ipynb"
    notebook_path.write_text('"C:\\\\Users\\\\researcher\\\\Desktop\\\\data.csv"', encoding="utf-8")

    findings = check_absolute_paths(tmp_path, [notebook_path])

    assert len(findings) == 1
    assert findings[0].check_id == "LC006"


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
