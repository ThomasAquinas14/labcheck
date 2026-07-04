from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(slots=True)
class Finding:
    check_id: str
    title: str
    severity: str
    category: str
    file_path: str
    evidence: str
    why_it_matters: str
    suggested_fix: str


@dataclass(slots=True)
class NotebookErrorOutput:
    cell_index: int
    ename: str
    evalue: str


@dataclass(slots=True)
class NotebookDocument:
    path: Path
    code_cell_count: int
    execution_counts: list[int | None]
    sources: list[str]
    error_outputs: list[NotebookErrorOutput] = field(default_factory=list)
    kernel_name: str = ""
    language_name: str = ""


@dataclass(slots=True)
class ScanSummary:
    target: str
    notebooks: int
    python_files: int
    findings_count: int


@dataclass(slots=True)
class ScoreCard:
    overall_score: int
    environment_rebuildability: int
    notebook_determinism: int
    artifact_availability: int
    portability: int
    onboarding_readiness: int


@dataclass(slots=True)
class GraphNode:
    id: str
    label: str
    kind: str


@dataclass(slots=True)
class GraphEdge:
    source: str
    target: str
    kind: str


@dataclass(slots=True)
class Graph:
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)


@dataclass(slots=True)
class Report:
    summary: ScanSummary
    scores: ScoreCard
    findings: list[Finding] = field(default_factory=list)
    graph: Graph = field(default_factory=Graph)

    def to_dict(self) -> dict:
        return {
            "summary": asdict(self.summary),
            "scores": asdict(self.scores),
            "findings": [asdict(finding) for finding in self.findings],
            "graph": {
                "nodes": [asdict(node) for node in self.graph.nodes],
                "edges": [asdict(edge) for edge in self.graph.edges],
            },
        }
