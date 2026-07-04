from __future__ import annotations

import json
from pathlib import Path

from .models import NotebookDocument, NotebookErrorOutput


def parse_notebook(path: Path) -> NotebookDocument:
    data = json.loads(path.read_text(encoding="utf-8"))
    metadata = data.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    kernelspec = metadata.get("kernelspec", {})
    if not isinstance(kernelspec, dict):
        kernelspec = {}
    language_info = metadata.get("language_info", {})
    if not isinstance(language_info, dict):
        language_info = {}
    code_cells = [cell for cell in data.get("cells", []) if cell.get("cell_type") == "code"]
    execution_counts: list[int | None] = []
    sources: list[str] = []
    error_outputs: list[NotebookErrorOutput] = []

    for index, cell in enumerate(code_cells, start=1):
        execution_counts.append(cell.get("execution_count"))
        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(source)
        sources.append(str(source))
        for output in cell.get("outputs", []):
            if output.get("output_type") != "error":
                continue
            error_outputs.append(
                NotebookErrorOutput(
                    cell_index=index,
                    ename=str(output.get("ename") or "Error"),
                    evalue=str(output.get("evalue") or ""),
                )
            )

    return NotebookDocument(
        path=path,
        code_cell_count=len(code_cells),
        execution_counts=execution_counts,
        sources=sources,
        error_outputs=error_outputs,
        kernel_name=str(kernelspec.get("name") or ""),
        language_name=str(language_info.get("name") or ""),
    )
