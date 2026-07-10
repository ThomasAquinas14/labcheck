from __future__ import annotations

from pathlib import Path

from labcheck.models import NotebookDocument
from labcheck.source_analysis import (
    analyze_python_file,
    analyze_readme,
    find_hidden_state_issues,
    readme_has_dependency_setup_instructions,
    readme_has_run_instructions,
)


def _notebook(*sources: str) -> NotebookDocument:
    return NotebookDocument(
        path=Path("analysis.ipynb"),
        code_cell_count=len(sources),
        execution_counts=[index for index, _ in enumerate(sources, start=1)],
        sources=list(sources),
    )


def test_hidden_state_ignores_function_definition_internals() -> None:
    notebook = _notebook(
        """
def save_fig(fig_id, tight_layout=True, fig_extension="png", resolution=300):
    path = f"images/{fig_id}.{fig_extension}"
    if tight_layout:
        plt.tight_layout()
    plt.savefig(path, format=fig_extension, dpi=resolution)
"""
    )

    assert find_hidden_state_issues(notebook) == []


def test_hidden_state_flags_use_before_assignment_in_same_cell() -> None:
    notebook = _notebook(
        """
print(external_state)
external_state = 3
"""
    )

    issues = find_hidden_state_issues(notebook)

    assert len(issues) == 1
    assert issues[0].names == ["external_state"]


def test_hidden_state_allows_names_defined_in_earlier_cells() -> None:
    notebook = _notebook(
        "external_state = 3",
        "print(external_state)",
    )

    assert find_hidden_state_issues(notebook) == []


def test_hidden_state_ignores_comprehension_target_names() -> None:
    notebook = _notebook(
        """
dataset = [1, 2, 3]
items = [value for value in dataset if value > 0]
paths = [path.upper() for path in ["a", "b"]]
"""
    )

    assert find_hidden_state_issues(notebook) == []


def test_hidden_state_learns_assignments_after_cell_magic() -> None:
    notebook = _notebook(
        """
%%time
prepared_rows = [1, 2, 3]
""",
        "print(prepared_rows)",
    )

    assert find_hidden_state_issues(notebook) == []


def test_hidden_state_ignores_line_magic_and_shell_setup_lines() -> None:
    notebook = _notebook(
        """
%matplotlib inline
!pip install pandas
import pandas as pd
frame = pd.DataFrame({"value": [1]})
""",
        "print(frame)",
    )

    assert find_hidden_state_issues(notebook) == []


def test_hidden_state_learns_ipython_shell_assignment_names() -> None:
    notebook = _notebook(
        """
files = !ls data
""",
        "print(files)",
    )

    assert find_hidden_state_issues(notebook) == []


def test_hidden_state_allows_common_notebook_display_helpers() -> None:
    notebook = _notebook(
        """
frame = {"value": 1}
display(frame)
get_ipython()
"""
    )

    assert find_hidden_state_issues(notebook) == []


def test_source_analysis_does_not_treat_path_open_mode_as_read_path(tmp_path: Path) -> None:
    source = tmp_path / "extract.py"
    source.write_text(
        """
from pathlib import Path

destination = Path("out.bin")
with archive.open(member) as source, destination.open("wb") as target:
    target.write(source.read())
""",
        encoding="utf-8",
    )

    artifact = analyze_python_file(source)

    assert artifact.reads == []
    assert artifact.writes == []


def test_source_analysis_distinguishes_builtin_open_read_and_write_modes(tmp_path: Path) -> None:
    source = tmp_path / "io.py"
    source.write_text(
        """
input_path = "data/train.csv"
output_path = "outputs/report.csv"

with open(input_path, "r") as source:
    rows = source.readlines()
with open(output_path, "wb") as target:
    target.write(b"ready")
""",
        encoding="utf-8",
    )

    artifact = analyze_python_file(source)

    assert artifact.reads == ["data/train.csv"]
    assert artifact.writes == ["outputs/report.csv"]


def test_source_analysis_extracts_remote_download_reads_from_python_calls(tmp_path: Path) -> None:
    source = tmp_path / "download_data.py"
    source.write_text(
        """
import requests
import urllib.request
import wget

requests.get("https://raw.githubusercontent.com/example/lab-data/main/train.csv")
urllib.request.urlretrieve("https://example.com/latest/labels.csv", "labels.csv")
wget.download("https://github.com/example/repo/raw/main/features.csv")
""",
        encoding="utf-8",
    )

    artifact = analyze_python_file(source)

    assert artifact.reads == [
        "https://raw.githubusercontent.com/example/lab-data/main/train.csv",
        "https://example.com/latest/labels.csv",
        "https://github.com/example/repo/raw/main/features.csv",
    ]


def test_source_analysis_extracts_remote_download_reads_from_notebook_shell_lines() -> None:
    notebook = _notebook(
        """
!wget -O data/train.csv https://raw.githubusercontent.com/example/lab-data/main/train.csv
!curl -L https://example.github.io/latest/data.csv -o data.csv
"""
    )

    from labcheck.source_analysis import analyze_notebook

    artifact = analyze_notebook(notebook)

    assert artifact.reads == [
        "https://raw.githubusercontent.com/example/lab-data/main/train.csv",
        "https://example.github.io/latest/data.csv",
    ]


def test_source_analysis_ignores_randomness_pattern_literals(tmp_path: Path) -> None:
    source = tmp_path / "catalog.py"
    source.write_text(
        r'''
import re

RANDOM_USAGE_PATTERNS = [
    re.compile(r"\brandom\."),
    re.compile(r"\bnp\.random\."),
]
HELP_TEXT = "Call random.seed(...) before random.random() in experiments."
''',
        encoding="utf-8",
    )

    artifact = analyze_python_file(source)

    assert not artifact.uses_randomness
    assert not artifact.seeds_randomness


def test_source_analysis_detects_actual_randomness_calls(tmp_path: Path) -> None:
    source = tmp_path / "experiment.py"
    source.write_text(
        """
import random

value = random.random()
""",
        encoding="utf-8",
    )

    artifact = analyze_python_file(source)

    assert artifact.uses_randomness
    assert not artifact.seeds_randomness


def test_source_analysis_treats_jax_prngkey_as_visible_seed(tmp_path: Path) -> None:
    source = tmp_path / "experiment.py"
    source.write_text(
        """
import jax

key = jax.random.PRNGKey(0)
value = jax.random.normal(key, (4,))
""",
        encoding="utf-8",
    )

    artifact = analyze_python_file(source)

    assert artifact.uses_randomness
    assert artifact.seeds_randomness


def test_readme_analysis_finds_fenced_commands(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
Run the training script:

```bash
python scripts/train.py --epochs 2
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    assert len(references) == 1
    assert references[0].command == "python scripts/train.py"
    assert references[0].referenced_path == "scripts/train.py"


def test_readme_analysis_finds_make_targets(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
Reproduce the paper:

```bash
make reproduce
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    assert len(references) == 1
    assert references[0].command == "make reproduce"
    assert references[0].referenced_path == "Makefile"
    assert references[0].make_target == "reproduce"


def test_readme_analysis_finds_python_module_commands(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
Reproduce the experiment:

```bash
python -m demo_lab.train --seed 7
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    assert len(references) == 1
    assert references[0].command == "python -m demo_lab.train"
    assert references[0].module_name == "demo_lab.train"


def test_readme_analysis_finds_uv_run_python_entrypoints(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
Reproduce the experiment:

- uv run python scripts/train.py --seed 7
- uv run python -m demo_lab.report
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    assert len(references) == 2
    assert references[0].command == "uv run python scripts/train.py"
    assert references[0].referenced_path == "scripts/train.py"
    assert references[1].command == "uv run python -m demo_lab.report"
    assert references[1].module_name == "demo_lab.report"


def test_readme_analysis_finds_uv_project_script_aliases(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
Reproduce the experiment:

```bash
uv run train-model --seed 7
uv run pytest
uv run ruff check .
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    assert len(references) == 1
    assert references[0].command == "uv run train-model"
    assert references[0].referenced_path == "pyproject.toml"
    assert references[0].package_manager == "uv"
    assert references[0].project_script == "train-model"


def test_readme_analysis_finds_pixi_nox_and_taskipy_aliases(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
Reproduce the experiment:

```bash
pixi run reproduce --fast
nox -s tests
nox --session docs
task train
uv run task report
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    assert [(reference.command, reference.package_manager, reference.package_script) for reference in references] == [
        ("pixi run reproduce", "pixi", "reproduce"),
        ("nox -s tests", "nox", "tests"),
        ("nox --session docs", "nox", "docs"),
        ("task train", "taskipy", "train"),
        ("uv run task report", "taskipy", "report"),
    ]


def test_readme_analysis_finds_invoke_aliases(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
Reproduce the experiment:

```bash
invoke reproduce --fast
inv report
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    assert [(reference.command, reference.package_manager, reference.package_script) for reference in references] == [
        ("invoke reproduce", "invoke", "reproduce"),
        ("inv report", "invoke", "report"),
    ]


def test_readme_analysis_finds_tox_and_rake_aliases(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
Reproduce the experiment:

```bash
tox -e py311,lint
tox run -e docs
rake reproduce
bundle exec rake data:build
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    assert [(reference.command, reference.package_manager, reference.package_script) for reference in references] == [
        ("tox -e py311,lint", "tox", "py311,lint"),
        ("tox run -e docs", "tox", "docs"),
        ("rake reproduce", "rake", "reproduce"),
        ("bundle exec rake data:build", "rake", "data:build"),
    ]


def test_readme_analysis_finds_snakemake_targets(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
Reproduce the workflow:

```bash
snakemake --cores 4 all
snakemake --use-conda results/summary.csv
snakemake -n
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    assert [(reference.command, reference.package_manager, reference.package_script) for reference in references] == [
        ("snakemake --cores 4 all", "snakemake", "all"),
        ("snakemake --use-conda results/summary.csv", "snakemake", "results/summary.csv"),
    ]


def test_readme_analysis_finds_local_nextflow_run_metadata(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
Run the workflow:

```bash
nextflow run main.nf -profile docker,test -entry align_reads
nextflow run nf-core/rnaseq -profile test,docker
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    assert len(references) == 1
    assert references[0].command == "nextflow run main.nf -profile docker,test -entry align_reads"
    assert references[0].package_manager == "nextflow"
    assert references[0].nextflow_pipeline == "main.nf"
    assert references[0].nextflow_profiles == ("docker", "test")
    assert references[0].nextflow_entry == "align_reads"


def test_readme_analysis_finds_local_cromwell_run_metadata(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
Run the workflow:

```bash
java -jar cromwell.jar run workflows/main.wdl --inputs inputs/demo.json --workflow-root workflows
cromwell run https://example.org/workflow.wdl --inputs inputs/remote.json
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    assert len(references) == 1
    assert references[0].command == (
        "java -jar cromwell.jar run workflows/main.wdl --inputs inputs/demo.json --workflow-root workflows"
    )
    assert references[0].package_manager == "cromwell"
    assert references[0].wdl_workflow == "workflows/main.wdl"
    assert references[0].wdl_inputs == ("inputs/demo.json",)
    assert references[0].wdl_workflow_root == "workflows"


def test_readme_analysis_finds_local_cwl_run_metadata(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
Run the workflow:

```bash
cwltool --outdir results workflows/main.cwl inputs/demo.yml
cwl-runner https://example.org/workflow.cwl inputs/remote.yml
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    assert len(references) == 1
    assert references[0].command == "cwltool --outdir results workflows/main.cwl inputs/demo.yml"
    assert references[0].package_manager == "cwl"
    assert references[0].cwl_workflow == "workflows/main.cwl"
    assert references[0].cwl_job == "inputs/demo.yml"


def test_readme_analysis_finds_local_papermill_parameter_files(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
Run the notebook:

```bash
papermill --log-output notebooks/input.ipynb reports/output.ipynb -f params/demo.yaml
papermill s3://bucket/input.ipynb s3://bucket/output.ipynb
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    assert len(references) == 1
    assert references[0].command == (
        "papermill --log-output notebooks/input.ipynb reports/output.ipynb -f params/demo.yaml"
    )
    assert references[0].package_manager == "papermill"
    assert references[0].papermill_input == "notebooks/input.ipynb"
    assert references[0].papermill_parameter_files == ("params/demo.yaml",)


def test_readme_analysis_finds_local_dvc_targets(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
```bash
dvc repro train
dvc pull data/raw
dvc repro
dvc pull --remote storage models/latest
dvc pull s3://bucket/data
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    assert [(reference.command, reference.dvc_command, reference.dvc_targets) for reference in references] == [
        ("dvc repro train", "repro", ("train",)),
        ("dvc pull data/raw", "pull", ("data/raw",)),
        ("dvc pull --remote storage models/latest", "pull", ("models/latest",)),
    ]
    assert all(reference.package_manager == "dvc" for reference in references)


def test_readme_analysis_finds_local_quarto_render_targets(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
```bash
quarto render paper.qmd --to html
quarto render notebooks/demo.ipynb
quarto render docs
quarto render
quarto render --to html
quarto render https://example.org/paper.qmd
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    assert [(reference.command, reference.quarto_target) for reference in references] == [
        ("quarto render paper.qmd --to html", "paper.qmd"),
        ("quarto render notebooks/demo.ipynb", "notebooks/demo.ipynb"),
        ("quarto render docs", "docs"),
    ]
    assert all(reference.package_manager == "quarto" for reference in references)


def test_readme_analysis_finds_local_jupytext_sync_targets(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
```bash
jupytext --sync notebooks/demo.ipynb
jupytext --set-formats ipynb,py:percent --sync notebooks/pair.py
jupytext --sync --pipe black notebooks/clean.ipynb
jupytext --sync notebooks/*.ipynb
jupytext --to py notebooks/demo.ipynb
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    assert [(reference.command, reference.jupytext_targets) for reference in references] == [
        ("jupytext --sync notebooks/demo.ipynb", ("notebooks/demo.ipynb",)),
        (
            "jupytext --set-formats ipynb,py:percent --sync notebooks/pair.py",
            ("notebooks/pair.py",),
        ),
        ("jupytext --sync --pipe black notebooks/clean.ipynb", ("notebooks/clean.ipynb",)),
    ]
    assert all(reference.package_manager == "jupytext" for reference in references)


def test_readme_analysis_finds_kedro_pipeline_targets(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
```bash
kedro run --pipeline data_science
kedro run --pipelines=data_engineering,data_science
kedro run -p reporting
kedro run
kedro run --env local
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    assert [(reference.command, reference.kedro_pipelines) for reference in references] == [
        ("kedro run --pipeline data_science", ("data_science",)),
        ("kedro run --pipelines=data_engineering,data_science", ("data_engineering", "data_science")),
        ("kedro run -p reporting", ("reporting",)),
    ]
    assert all(reference.package_manager == "kedro" for reference in references)


def test_readme_analysis_finds_prefect_deployment_flow_names(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
```bash
prefect deployment run train-flow/prod
uv run prefect deployment run data_flow/daily --param date=2026-01-01
prefect deployment run --id abc123
prefect deployment run train-flow
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    assert [(reference.command, reference.prefect_flow, reference.prefect_deployment) for reference in references] == [
        ("prefect deployment run train-flow/prod", "train-flow", "prod"),
        ("uv run prefect deployment run data_flow/daily --param date=2026-01-01", "data_flow", "daily"),
    ]
    assert all(reference.package_manager == "prefect" for reference in references)


def test_readme_analysis_finds_mlflow_project_entry_points(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
```bash
mlflow run . -e train
uv run mlflow run experiments/model --entry-point evaluate -P alpha=0.1
mlflow run scripts -e train.py
mlflow run .
mlflow run https://github.com/example/project -e train
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    assert [(reference.command, reference.mlflow_project, reference.mlflow_entry_point) for reference in references] == [
        ("mlflow run . -e train", ".", "train"),
        ("uv run mlflow run experiments/model --entry-point evaluate -P alpha=0.1", "experiments/model", "evaluate"),
        ("mlflow run scripts -e train.py", "scripts", "train.py"),
    ]
    assert all(reference.package_manager == "mlflow" for reference in references)


def test_readme_analysis_finds_dbt_model_selectors(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
```bash
dbt run --select orders
dbt test -s path:models/marts/customers.sql
uv run dbt build --cache-selected-only --models staging.orders,staging.customers --target prod
dbt ls --selector nightly
dbt run --select tag:daily
dbt run
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    dbt_references = [reference for reference in references if reference.package_manager == "dbt"]

    assert [(reference.command, reference.dbt_selectors) for reference in dbt_references] == [
        ("dbt run --select orders", ("orders",)),
        ("dbt test -s path:models/marts/customers.sql", ("path:models/marts/customers.sql",)),
        (
            "uv run dbt build --cache-selected-only --models staging.orders,staging.customers --target prod",
            ("staging.orders", "staging.customers"),
        ),
        ("dbt ls --selector nightly", ("selector:nightly",)),
    ]


def test_readme_analysis_finds_great_expectations_checkpoints(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
```bash
great_expectations checkpoint run daily
gx checkpoint run --checkpoint-name weekly
uv run gx checkpoint run --context-root-dir gx nightly
great_expectations checkpoint list
gx suite list
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    gx_references = [reference for reference in references if reference.package_manager == "great_expectations"]

    assert [(reference.command, reference.gx_checkpoint) for reference in gx_references] == [
        ("great_expectations checkpoint run daily", "daily"),
        ("gx checkpoint run --checkpoint-name weekly", "weekly"),
        ("uv run gx checkpoint run --context-root-dir gx nightly", "nightly"),
    ]


def test_readme_analysis_finds_dagster_job_and_asset_targets(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
```bash
dagster job execute -f definitions.py -j train_model
dg launch --job daily_assets --assets target/main/raw_customers,feature_table
uv run dagster asset materialize --select target/main/raw_customers
dg launch --assets '*'
dagster job list
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    dagster_references = [reference for reference in references if reference.package_manager == "dagster"]

    assert [
        (reference.command, reference.dagster_jobs, reference.dagster_assets)
        for reference in dagster_references
    ] == [
        ("dagster job execute -f definitions.py -j train_model", ("train_model",), ()),
        (
            "dg launch --job daily_assets --assets target/main/raw_customers,feature_table",
            ("daily_assets",),
            ("target/main/raw_customers", "feature_table"),
        ),
        ("uv run dagster asset materialize --select target/main/raw_customers", (), ("target/main/raw_customers",)),
    ]


def test_readme_analysis_finds_ploomber_task_targets(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
```bash
ploomber task --status load_data
ploomber build --partially train_model
uv run ploomber build --entry-point pipeline.yaml --partially imported_task
ploomber build --partially fit-*
ploomber build
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    ploomber_references = [reference for reference in references if reference.package_manager == "ploomber"]

    assert [(reference.command, reference.ploomber_tasks) for reference in ploomber_references] == [
        ("ploomber task --status load_data", ("load_data",)),
        ("ploomber build --partially train_model", ("train_model",)),
        ("uv run ploomber build --entry-point pipeline.yaml --partially imported_task", ("imported_task",)),
    ]


def test_readme_analysis_finds_luigi_task_targets(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
```bash
luigi --module workflows.tasks TrainModel --local-scheduler --date 2026-01-01
uv run luigi --module workflows.tasks experiments.NamespacedTask --scheduler-host localhost
luigi --module workflows.tasks --local-scheduler
luigi --help
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    luigi_references = [reference for reference in references if reference.package_manager == "luigi"]

    assert [(reference.command, reference.luigi_module, reference.luigi_task) for reference in luigi_references] == [
        (
            "luigi --module workflows.tasks TrainModel --local-scheduler --date 2026-01-01",
            "workflows.tasks",
            "TrainModel",
        ),
        (
            "uv run luigi --module workflows.tasks experiments.NamespacedTask --scheduler-host localhost",
            "workflows.tasks",
            "experiments.NamespacedTask",
        ),
    ]


def test_readme_analysis_finds_meltano_job_targets(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
```bash
meltano run daily-load
uv run meltano --environment=prod run nightly-sync --dry-run
meltano run tap-gitlab target-postgres
meltano run dbt-postgres:run
meltano job start legacy-backfill
meltano job list daily-load
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    meltano_references = [reference for reference in references if reference.package_manager == "meltano"]

    assert [(reference.command, reference.meltano_jobs) for reference in meltano_references] == [
        ("meltano run daily-load", ("daily-load",)),
        ("uv run meltano --environment=prod run nightly-sync --dry-run", ("nightly-sync",)),
    ]


def test_readme_analysis_finds_flyte_workflow_and_task_targets(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
```bash
flyte run --local workflows/train.py train_model --epochs 2
uv run pyflyte run --remote workflows/train.py scoring_workflow --name smoke
pyflyte --config config.yaml run --remote workflows/train.py package_model --image ghcr.io/acme/flyte:latest
flyte run deployed-task project.domain.task
flyte run python-script scripts/train.py
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    flyte_references = [reference for reference in references if reference.package_manager == "flyte"]

    assert [(reference.command, reference.flyte_script, reference.flyte_target) for reference in flyte_references] == [
        ("flyte run --local workflows/train.py train_model --epochs 2", "workflows/train.py", "train_model"),
        (
            "uv run pyflyte run --remote workflows/train.py scoring_workflow --name smoke",
            "workflows/train.py",
            "scoring_workflow",
        ),
        (
            "pyflyte --config config.yaml run --remote workflows/train.py package_model --image ghcr.io/acme/flyte:latest",
            "workflows/train.py",
            "package_model",
        ),
    ]


def test_readme_analysis_finds_argo_workflow_targets(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
```bash
argo submit workflows/train.yaml --entrypoint train
uv run argo submit --entrypoint=score workflows/train.yaml -p split=test
argo submit workflows/default.yaml
argo submit --from workflowtemplate/cluster-template
argo submit https://example.com/workflow.yaml --entrypoint remote
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    argo_references = [reference for reference in references if reference.package_manager == "argo"]

    assert [(reference.command, reference.argo_workflow, reference.argo_entrypoint) for reference in argo_references] == [
        ("argo submit workflows/train.yaml --entrypoint train", "workflows/train.yaml", "train"),
        ("uv run argo submit --entrypoint=score workflows/train.yaml -p split=test", "workflows/train.yaml", "score"),
        ("argo submit workflows/default.yaml", "workflows/default.yaml", ""),
    ]


def test_readme_analysis_finds_tekton_pipeline_and_task_targets(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
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

    references = analyze_readme(readme)

    tekton_references = [reference for reference in references if reference.package_manager == "tekton"]
    taskipy_references = [
        reference for reference in references if reference.package_manager == "taskipy"
    ]

    assert [
        (reference.command, reference.tekton_kind, reference.tekton_name, reference.tekton_file)
        for reference in tekton_references
    ] == [
        ("tkn pipeline start build-and-test", "pipeline", "build-and-test", ""),
        ("uv run tkn task start unit-test --param image=python:3.11", "task", "unit-test", ""),
        ("tkn pipeline start -f tekton/pipeline.yaml", "pipeline", "", "tekton/pipeline.yaml"),
        ("tkn task start --filename=tekton/task.yaml unit-test", "task", "unit-test", "tekton/task.yaml"),
    ]
    assert not taskipy_references


def test_readme_analysis_finds_ray_job_entrypoints(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
```bash
ray job submit --address http://127.0.0.1:8265 -- python scripts/train.py --epochs 2
uv run ray job submit --working-dir . -- uv run python -m demo.jobs.train --smoke
ray job submit -- bash scripts/train.sh
ray job submit -- python -c "print('hi')"
ray job submit -- python https://example.com/train.py
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    ray_references = [reference for reference in references if reference.package_manager == "ray"]

    assert [
        (reference.command, reference.ray_script, reference.ray_module)
        for reference in ray_references
    ] == [
        (
            "ray job submit --address http://127.0.0.1:8265 -- python scripts/train.py --epochs 2",
            "scripts/train.py",
            "",
        ),
        (
            "uv run ray job submit --working-dir . -- uv run python -m demo.jobs.train --smoke",
            "",
            "demo.jobs.train",
        ),
    ]


def test_readme_analysis_finds_dagger_call_targets(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
```bash
dagger call build-image --source=.
uv run dagger -m ./ci call lint --src=.
dagger --mod ./ci call test --json
dagger -m github.com/dagger/hello-dagger call hello
dagger call --help
dagger -M call container
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    dagger_references = [reference for reference in references if reference.package_manager == "dagger"]

    assert [
        (reference.command, reference.dagger_module, reference.dagger_function, reference.referenced_path)
        for reference in dagger_references
    ] == [
        ("dagger call build-image --source=.", "", "build-image", "dagger.json"),
        ("uv run dagger -m ./ci call lint --src=.", "ci", "lint", "ci/dagger.json"),
        ("dagger --mod ./ci call test --json", "ci", "test", "ci/dagger.json"),
    ]


def test_readme_analysis_finds_bazel_targets(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
```bash
bazel build //src:train //...
uv run bazel test --config=ci //tests:unit
bazel run --platforms //tools:linux //apps:serve -- --port 8000
bazel build @rules_python//python:defs.bzl
bazel query //src:train
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    bazel_references = [reference for reference in references if reference.package_manager == "bazel"]

    assert [
        (reference.command, reference.bazel_command, reference.bazel_targets)
        for reference in bazel_references
    ] == [
        ("bazel build //src:train //...", "build", ("//src:train", "//...")),
        ("uv run bazel test --config=ci //tests:unit", "test", ("//tests:unit",)),
        (
            "bazel run --platforms //tools:linux //apps:serve -- --port 8000",
            "run",
            ("//apps:serve",),
        ),
    ]


def test_readme_analysis_finds_pants_target_specs(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
```bash
pants test src/python:: tests:unit
./pants run src/python/app.py -- --port 8000
uv run pants --changed-since=HEAD lint src/python:lib
pants package @external//:target
pants help goals
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    pants_references = [reference for reference in references if reference.package_manager == "pants"]

    assert [
        (reference.command, reference.pants_goal, reference.pants_specs)
        for reference in pants_references
    ] == [
        ("pants test src/python:: tests:unit", "test", ("src/python::", "tests:unit")),
        ("./pants run src/python/app.py -- --port 8000", "run", ("src/python/app.py",)),
        ("uv run pants --changed-since=HEAD lint src/python:lib", "lint", ("src/python:lib",)),
    ]


def test_readme_analysis_finds_nix_flake_outputs(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
```bash
nix flake check
nix flake check .
nix build .#labcheck .#dockerImage
nix run .#cli -- --help
uv run nix build path:./nix#tool
nix build nixpkgs#hello
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    nix_references = [reference for reference in references if reference.package_manager == "nix"]

    assert [
        (reference.command, reference.nix_command, reference.nix_installables)
        for reference in nix_references
    ] == [
        ("nix flake check", "flake check", (".",)),
        ("nix flake check .", "flake check", (".",)),
        ("nix build .#labcheck .#dockerImage", "build", (".#labcheck", ".#dockerImage")),
        ("nix run .#cli -- --help", "run", (".#cli",)),
        ("uv run nix build path:./nix#tool", "build", ("path:./nix#tool",)),
    ]


def test_readme_analysis_finds_docker_compose_services(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
```bash
docker compose up -d api worker
docker compose -f compose.dev.yml run --rm api pytest -q
docker compose --env-file .env.demo up -d
docker compose --env-file config/dev.env run api pytest -q
docker-compose --env-file=.env.local restart db
docker compose --project-directory deploy up -d
docker compose --project-directory=./ops run api pytest -q
docker-compose --project-directory stacks/dev logs db
docker compose --profile obs logs -f grafana
docker compose --profile gpu run trainer pytest -q
docker-compose --profile=debug --profile qa up worker
docker-compose restart db
docker compose --env-file $COMPOSE_ENV up -d
docker compose --project-directory $COMPOSE_PROJECT_DIR up -d
docker compose --profile $COMPOSE_PROFILE up -d
docker compose down
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    compose_references = [
        reference for reference in references if reference.package_manager == "docker_compose"
    ]

    assert [
        (
            reference.command,
            reference.docker_compose_command,
            reference.docker_compose_files,
            reference.docker_compose_env_files,
            reference.docker_compose_project_dirs,
            reference.docker_compose_profiles,
            reference.docker_compose_services,
        )
        for reference in compose_references
    ] == [
        ("docker compose up -d api worker", "up", (), (), (), (), ("api", "worker")),
        ("docker compose -f compose.dev.yml run --rm api pytest -q", "run", ("compose.dev.yml",), (), (), (), ("api",)),
        ("docker compose --env-file .env.demo up -d", "up", (), (".env.demo",), (), (), ()),
        ("docker compose --env-file config/dev.env run api pytest -q", "run", (), ("config/dev.env",), (), (), ("api",)),
        ("docker-compose --env-file=.env.local restart db", "restart", (), (".env.local",), (), (), ("db",)),
        ("docker compose --project-directory deploy up -d", "up", (), (), ("deploy",), (), ()),
        ("docker compose --project-directory=./ops run api pytest -q", "run", (), (), ("./ops",), (), ("api",)),
        ("docker-compose --project-directory stacks/dev logs db", "logs", (), (), ("stacks/dev",), (), ("db",)),
        ("docker compose --profile obs logs -f grafana", "logs", (), (), (), ("obs",), ("grafana",)),
        ("docker compose --profile gpu run trainer pytest -q", "run", (), (), (), ("gpu",), ("trainer",)),
        ("docker-compose --profile=debug --profile qa up worker", "up", (), (), (), ("debug", "qa"), ("worker",)),
        ("docker-compose restart db", "restart", (), (), (), (), ("db",)),
    ]


def test_readme_analysis_finds_docker_build_targets(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
```bash
docker build --target runtime -t demo .
docker build -f docker/Dockerfile --target=prod .
docker image build --file Dockerfile.worker --target worker .
docker buildx build --platform linux/amd64 --target release .
docker build .
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    build_references = [
        reference for reference in references if reference.package_manager == "docker_build"
    ]

    assert [
        (
            reference.command,
            reference.docker_build_file,
            reference.docker_build_target,
        )
        for reference in build_references
    ] == [
        ("docker build --target runtime -t demo .", "Dockerfile", "runtime"),
        ("docker build -f docker/Dockerfile --target=prod .", "docker/Dockerfile", "prod"),
        ("docker image build --file Dockerfile.worker --target worker .", "Dockerfile.worker", "worker"),
        ("docker buildx build --platform linux/amd64 --target release .", "Dockerfile", "release"),
    ]


def test_readme_analysis_finds_helm_chart_paths(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
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

    references = analyze_readme(readme)

    helm_references = [reference for reference in references if reference.package_manager == "helm"]

    assert [
        (reference.command, reference.helm_command, reference.helm_chart_paths)
        for reference in helm_references
    ] == [
        ("helm template ./charts/api -f values/dev.yaml", "template", ("./charts/api",)),
        ("helm install api ./charts/api --namespace demo", "install", ("./charts/api",)),
        ("helm upgrade api charts/api --install", "upgrade", ("charts/api",)),
        ("helm lint charts/api charts/worker", "lint", ("charts/api", "charts/worker")),
        ("uv run helm package ./charts/worker", "package", ("./charts/worker",)),
    ]


def test_readme_analysis_finds_kustomize_paths(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
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

    references = analyze_readme(readme)

    kustomize_references = [
        reference for reference in references if reference.package_manager == "kustomize"
    ]

    assert [
        (reference.command, reference.kustomize_command, reference.kustomize_paths)
        for reference in kustomize_references
    ] == [
        ("kustomize build overlays/dev", "build", ("overlays/dev",)),
        ("kustomize build --enable-helm ./overlays/prod", "build", ("./overlays/prod",)),
        ("kubectl apply -k overlays/dev", "kubectl apply", ("overlays/dev",)),
        ("kubectl diff --kustomize=overlays/prod", "kubectl diff", ("overlays/prod",)),
        ("kubectl kustomize ./base", "kubectl kustomize", ("./base",)),
    ]


def test_readme_analysis_finds_kubernetes_manifest_paths(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
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

    references = analyze_readme(readme)

    kubernetes_references = [
        reference for reference in references if reference.package_manager == "kubernetes"
    ]

    assert [
        (
            reference.command,
            reference.kubernetes_command,
            reference.kubernetes_manifest_paths,
        )
        for reference in kubernetes_references
    ] == [
        ("kubectl apply -f manifests/app.yaml", "kubectl apply", ("manifests/app.yaml",)),
        ("kubectl diff --filename deploy/", "kubectl diff", ("deploy/",)),
        (
            "uv run kubectl apply --filename=manifests/db.json",
            "kubectl apply",
            ("manifests/db.json",),
        ),
        (
            "kubectl delete -f deploy/api.yaml -f deploy/job.yml",
            "kubectl delete",
            ("deploy/api.yaml", "deploy/job.yml"),
        ),
        (
            "kubectl apply -f manifests/app.yaml,deploy/worker.yaml",
            "kubectl apply",
            ("manifests/app.yaml", "deploy/worker.yaml"),
        ),
    ]


def test_readme_analysis_finds_terraform_working_dirs(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
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

    references = analyze_readme(readme)

    terraform_references = [
        reference for reference in references if reference.package_manager == "terraform"
    ]

    assert [
        (reference.command, reference.terraform_command, reference.terraform_working_dirs)
        for reference in terraform_references
    ] == [
        ("terraform -chdir=infra plan", "plan", ("infra",)),
        ("terraform -chdir deploy apply -auto-approve", "apply", ("deploy",)),
        ("terraform -chdir=infra fmt -check", "fmt", ("infra",)),
        ("uv run terraform -chdir=envs/dev validate", "validate", ("envs/dev",)),
        ("terraform -chdir=./stack/test test", "test", ("./stack/test",)),
    ]


def test_readme_analysis_finds_pulumi_project_dirs(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
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

    references = analyze_readme(readme)

    pulumi_references = [
        reference for reference in references if reference.package_manager == "pulumi"
    ]

    assert [
        (reference.command, reference.pulumi_command, reference.pulumi_project_dirs)
        for reference in pulumi_references
    ] == [
        ("pulumi -C infra preview", "preview", ("infra",)),
        ("pulumi --cwd deploy up --yes", "up", ("deploy",)),
        ("pulumi preview --cwd=envs/dev --stack dev", "preview", ("envs/dev",)),
        ("uv run pulumi install -C ./stacks/prod", "install", ("./stacks/prod",)),
        ("pulumi -C./stacks/test refresh", "refresh", ("./stacks/test",)),
    ]


def test_readme_analysis_finds_ansible_playbook_and_inventory_paths(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
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

    references = analyze_readme(readme)

    ansible_references = [
        reference for reference in references if reference.package_manager == "ansible"
    ]

    assert [
        (reference.command, reference.ansible_playbooks, reference.ansible_inventories)
        for reference in ansible_references
    ] == [
        ("ansible-playbook playbooks/site.yml -i inventory.ini", ("playbooks/site.yml",), ("inventory.ini",)),
        (
            "ansible-playbook -i inventories/dev playbooks/deploy.yaml --tags app",
            ("playbooks/deploy.yaml",),
            ("inventories/dev",),
        ),
        (
            "uv run ansible-playbook playbooks/check.yml --inventory=inventories/prod.yml",
            ("playbooks/check.yml",),
            ("inventories/prod.yml",),
        ),
        (
            "ansible-playbook -iinventory/hosts.yml playbooks/site.yml",
            ("playbooks/site.yml",),
            ("inventory/hosts.yml",),
        ),
    ]


def test_readme_analysis_finds_packer_template_paths(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
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

    references = analyze_readme(readme)

    packer_references = [
        reference for reference in references if reference.package_manager == "packer"
    ]

    assert [
        (reference.command, reference.packer_command, reference.packer_templates)
        for reference in packer_references
    ] == [
        ("packer init templates/web.pkr.hcl", "init", ("templates/web.pkr.hcl",)),
        (
            "packer validate -var-file vars/dev.pkrvars.hcl templates/",
            "validate",
            ("templates/",),
        ),
        (
            "uv run packer build -only amazon-ebs.web images/web.pkr.hcl",
            "build",
            ("images/web.pkr.hcl",),
        ),
        ("packer fmt templates images/db.pkr.hcl", "fmt", ("templates", "images/db.pkr.hcl")),
        ("packer inspect ./templates/web.pkr.hcl", "inspect", ("./templates/web.pkr.hcl",)),
    ]


def test_readme_analysis_finds_airflow_dag_and_task_targets(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
```bash
airflow dags test -B local demo_dag
airflow tasks test --task-params params.json demo_dag train 2026-01-01
uv run airflow tasks run --ship-dag demo_dag evaluate 2026-01-01
airflow dags list
airflow tasks list demo_dag
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    airflow_references = [reference for reference in references if reference.package_manager == "airflow"]

    assert [
        (reference.command, reference.airflow_dag_id, reference.airflow_task_id)
        for reference in airflow_references
    ] == [
        ("airflow dags test -B local demo_dag", "demo_dag", ""),
        ("airflow tasks test --task-params params.json demo_dag train 2026-01-01", "demo_dag", "train"),
        ("uv run airflow tasks run --ship-dag demo_dag evaluate 2026-01-01", "demo_dag", "evaluate"),
    ]


def test_readme_analysis_finds_metaflow_resume_steps(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
```bash
python flow.py resume train_model
uv run python flow.py resume --origin-run-id 42 evaluate
python flow.py run
python flow.py resume --origin-run-id 42
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    metaflow_references = [reference for reference in references if reference.package_manager == "metaflow"]

    assert [
        (reference.command, reference.metaflow_script, reference.metaflow_step)
        for reference in metaflow_references
    ] == [
        ("python flow.py resume train_model", "flow.py", "train_model"),
        ("uv run python flow.py resume --origin-run-id 42 evaluate", "flow.py", "evaluate"),
    ]


def test_readme_analysis_finds_hatch_and_pdm_aliases(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
Reproduce the experiment:

```bash
hatch run reproduce
hatch run docs:build
pdm run report
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    assert [(reference.command, reference.package_manager, reference.package_script) for reference in references] == [
        ("hatch run reproduce", "hatch", "reproduce"),
        ("hatch run docs:build", "hatch", "docs:build"),
        ("pdm run report", "pdm", "report"),
    ]


def test_readme_analysis_finds_just_and_doit_aliases(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
Reproduce the experiment:

```bash
just reproduce
doit report
doit list
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    assert [(reference.command, reference.package_manager, reference.package_script) for reference in references] == [
        ("just reproduce", "just", "reproduce"),
        ("doit report", "doit", "report"),
    ]


def test_readme_analysis_finds_npm_run_scripts(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
Build the report:

```bash
npm run reproduce
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    assert len(references) == 1
    assert references[0].command == "npm run reproduce"
    assert references[0].referenced_path == "package.json"
    assert references[0].package_manager == "npm"
    assert references[0].package_script == "reproduce"


def test_readme_analysis_finds_pnpm_and_yarn_scripts(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
Build the reports:

```bash
pnpm run dashboard
yarn report
yarn run figures
```
""",
        encoding="utf-8",
    )

    references = analyze_readme(readme)

    assert [(reference.package_manager, reference.package_script) for reference in references] == [
        ("pnpm", "dashboard"),
        ("yarn", "report"),
        ("yarn", "figures"),
    ]


def test_readme_analysis_does_not_treat_package_install_commands_as_scripts(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
```bash
npm install
pnpm install
yarn install
```
""",
        encoding="utf-8",
    )

    assert analyze_readme(readme) == []


def test_readme_analysis_does_not_treat_python_m_pip_as_repo_module(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
```bash
python -m pip install -r requirements.txt
```
""",
        encoding="utf-8",
    )

    assert analyze_readme(readme) == []


def test_readme_analysis_ignores_inline_example_commands(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        "- Example README drift: `python scripts/train.py` is documented, but that file does not exist\n",
        encoding="utf-8",
    )

    assert analyze_readme(readme) == []


def test_readme_run_instruction_detection_accepts_fenced_quickstart(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
Quick start:

```bash
python -m pip install -r requirements.txt
jupyter notebook analysis.ipynb
```
""",
        encoding="utf-8",
    )

    assert readme_has_run_instructions(readme)


def test_readme_run_instruction_detection_ignores_inline_examples(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        "This tool can catch stale commands such as `python scripts/train.py` in a README.\n",
        encoding="utf-8",
    )

    assert not readme_has_run_instructions(readme)


def test_readme_dependency_setup_detection_accepts_common_install_steps(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
Quick start:

```bash
uv sync
jupyter notebook analysis.ipynb
```
""",
        encoding="utf-8",
    )

    assert readme_has_dependency_setup_instructions(readme)


def test_readme_dependency_setup_detection_ignores_run_only_readme(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        """
Quick start:

```bash
python train.py
```
""",
        encoding="utf-8",
    )

    assert not readme_has_dependency_setup_instructions(readme)
