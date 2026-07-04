from __future__ import annotations

from pathlib import Path

from .models import Graph, GraphEdge, GraphNode
from .source_analysis import SourceArtifact


def _node_id(path: str) -> str:
    return path.replace("\\", "/")


def build_provenance_graph(root: Path, artifacts: list[SourceArtifact]) -> Graph:
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []
    edge_keys: set[tuple[str, str, str]] = set()

    def ensure_node(node_id: str, label: str, kind: str) -> None:
        if node_id not in nodes:
            nodes[node_id] = GraphNode(id=node_id, label=label, kind=kind)

    for artifact in artifacts:
        rel_path = artifact.path.relative_to(root).as_posix()
        artifact_id = _node_id(rel_path)
        ensure_node(artifact_id, rel_path, artifact.kind)

        for read_path in artifact.reads:
            read_id = _node_id(read_path)
            ensure_node(read_id, read_path, "input")
            edge_key = (read_id, artifact_id, "reads")
            if edge_key not in edge_keys:
                edge_keys.add(edge_key)
                edges.append(GraphEdge(source=read_id, target=artifact_id, kind="reads"))

        for write_path in artifact.writes:
            write_id = _node_id(write_path)
            ensure_node(write_id, write_path, "artifact")
            edge_key = (artifact_id, write_id, "writes")
            if edge_key not in edge_keys:
                edge_keys.add(edge_key)
                edges.append(GraphEdge(source=artifact_id, target=write_id, kind="writes"))

    return Graph(nodes=list(nodes.values()), edges=edges)
