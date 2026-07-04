from __future__ import annotations

from pathlib import Path

from labcheck.models import NotebookDocument
from labcheck.source_analysis import analyze_python_file, analyze_readme, find_hidden_state_issues, readme_has_run_instructions


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
