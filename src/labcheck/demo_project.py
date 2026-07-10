from __future__ import annotations

import json
from pathlib import Path


DEMO_FILES: dict[str, str] = {
    "README.md": """# Demo Lab

This tiny repository is intentionally broken so `labcheck` has something useful to find.

Run the workflow:

```bash
python scripts/train.py
```

Expected input: `data/train.csv`.
""",
    "requirements.txt": """pandas
scikit-learn
""",
}


def _script_source() -> str:
    input_path = "data" + "/" + "train.csv"
    output_path = "outputs" + "/" + "report.csv"
    return f"""from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split


def main() -> None:
    frame = pd.read_csv({input_path!r})
    train, test = train_test_split(frame, test_size=0.2)
    Path({output_path!r}).write_text(f"train={{len(train)}}, test={{len(test)}}\\n", encoding="utf-8")


if __name__ == "__main__":
    main()
"""


def _demo_notebook() -> str:
    input_path = "data" + "/" + "train.csv"
    output_path = "outputs" + "/" + "report.csv"
    notebook = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": 1,
                "metadata": {},
                "outputs": [],
                "source": ["import pandas as pd\n", "from pathlib import Path\n"],
            },
            {
                "cell_type": "code",
                "execution_count": 5,
                "metadata": {},
                "outputs": [],
                "source": [f"df = pd.read_csv({input_path!r})\n"],
            },
            {
                "cell_type": "code",
                "execution_count": 3,
                "metadata": {},
                "outputs": [],
                "source": ["clean = external_state + 1\n"],
            },
            {
                "cell_type": "code",
                "execution_count": 4,
                "metadata": {},
                "outputs": [],
                "source": [f"Path({output_path!r}).write_text('demo\\n')\n"],
            },
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "pygments_lexer": "ipython3",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    return json.dumps(notebook, indent=2) + "\n"


def write_demo_repo(output_dir: Path, force: bool = False) -> list[Path]:
    """Create a tiny intentionally broken repo for first-run demos."""
    destination = output_dir.expanduser()
    if destination.exists() and not destination.is_dir():
        raise FileExistsError(f"Output path exists and is not a directory: {destination}")
    if destination.exists() and any(destination.iterdir()) and not force:
        raise FileExistsError(f"Output directory is not empty: {destination}. Use --force to overwrite demo files.")

    files = {**DEMO_FILES, "scripts/train.py": _script_source(), "notebooks/analysis.ipynb": _demo_notebook()}
    written: list[Path] = []
    for relative_path, content in files.items():
        path = destination / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written
