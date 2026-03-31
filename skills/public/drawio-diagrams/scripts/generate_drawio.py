#!/usr/bin/env python3
"""Generate valid draw.io XML from a JSON spec."""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

DEFAULT_NODE_SIZE = {
    "process": (160, 64),
    "terminator": (160, 56),
    "decision": (140, 90),
    "data": (170, 68),
    "document": (170, 72),
    "text": (180, 32),
    "actor": (60, 90),
    "swimlane": (280, 360),
}

BASE_NODE_STYLES = {
    "process": "rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=14;",
    "terminator": "ellipse;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;fontSize=14;",
    "decision": "rhombus;whiteSpace=wrap;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;fontSize=14;",
    "data": "shape=parallelogram;perimeter=parallelogramPerimeter;whiteSpace=wrap;html=1;fillColor=#f8cecc;strokeColor=#b85450;fontSize=14;",
    "document": "shape=document;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=14;",
    "text": "text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;whiteSpace=wrap;fontSize=14;",
    "actor": "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;outlineConnect=0;fontSize=14;",
    "swimlane": "swimlane;startSize=30;horizontal=0;childLayout=stackLayout;recursiveResize=0;rounded=0;html=1;fillColor=#f5f5f5;strokeColor=#666666;fontSize=14;",
}
DEFAULT_EDGE_STYLE = (
    "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;"
    "html=1;endArrow=classic;strokeColor=#4b5563;fontSize=12;"
)
GRAPH_MODEL_ATTRS = {
    "dx": "1600",
    "dy": "900",
    "grid": "1",
    "gridSize": "10",
    "guides": "1",
    "tooltips": "1",
    "connect": "1",
    "arrows": "1",
    "fold": "1",
    "page": "1",
    "pageScale": "1",
    "pageWidth": "1600",
    "pageHeight": "1200",
    "math": "0",
    "shadow": "0",
}


def _merge_style(base: str, custom: str | None = None, *, fill_color: str | None = None, stroke_color: str | None = None) -> str:
    parts = [base.rstrip(";")]
    if fill_color:
        parts.append(f"fillColor={fill_color}")
    if stroke_color:
        parts.append(f"strokeColor={stroke_color}")
    if custom:
        parts.append(custom.rstrip(";"))
    return ";".join(part for part in parts if part) + ";"


def _node_geometry(node: dict) -> dict[str, str]:
    kind = str(node.get("kind", "process")).lower()
    default_width, default_height = DEFAULT_NODE_SIZE.get(kind, DEFAULT_NODE_SIZE["process"])
    return {
        "x": str(node.get("x", 0)),
        "y": str(node.get("y", 0)),
        "width": str(node.get("width", default_width)),
        "height": str(node.get("height", default_height)),
        "as": "geometry",
    }


def _build_node(root: ET.Element, node: dict) -> None:
    node_id = str(node["id"])
    kind = str(node.get("kind", "process")).lower()
    cell_attrs = {
        "id": node_id,
        "value": str(node.get("label", "")),
        "style": _merge_style(
            BASE_NODE_STYLES.get(kind, BASE_NODE_STYLES["process"]),
            str(node.get("style")) if node.get("style") is not None else None,
            fill_color=node.get("fillColor"),
            stroke_color=node.get("strokeColor"),
        ),
        "vertex": "1",
        "parent": str(node.get("parent", "1")),
    }
    cell = ET.SubElement(root, "mxCell", cell_attrs)
    ET.SubElement(cell, "mxGeometry", _node_geometry(node))


def _build_edge(root: ET.Element, edge: dict) -> None:
    edge_attrs = {
        "id": str(edge["id"]),
        "value": str(edge.get("label", "")),
        "style": _merge_style(DEFAULT_EDGE_STYLE, str(edge.get("style")) if edge.get("style") is not None else None),
        "edge": "1",
        "parent": str(edge.get("parent", "1")),
        "source": str(edge["source"]),
        "target": str(edge["target"]),
    }
    cell = ET.SubElement(root, "mxCell", edge_attrs)
    geometry = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})

    waypoints = edge.get("waypoints") or []
    if waypoints:
        array = ET.SubElement(geometry, "Array", {"as": "points"})
        for point in waypoints:
            ET.SubElement(
                array,
                "mxPoint",
                {
                    "x": str(point["x"]),
                    "y": str(point["y"]),
                },
            )


def validate_spec(spec: dict) -> None:
    nodes = spec.get("nodes")
    edges = spec.get("edges")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("Spec must contain a non-empty 'nodes' list.")
    if not isinstance(edges, list):
        raise ValueError("Spec must contain an 'edges' list (can be empty).")

    node_ids: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            raise ValueError("Each node must be an object.")
        node_id = node.get("id")
        if not node_id:
            raise ValueError("Each node requires a non-empty 'id'.")
        node_id = str(node_id)
        if node_id in {"0", "1"}:
            raise ValueError("Node ids '0' and '1' are reserved.")
        if node_id in node_ids:
            raise ValueError(f"Duplicate node id: {node_id}")
        node_ids.add(node_id)

    edge_ids: set[str] = set()
    for index, edge in enumerate(edges, start=1):
        if not isinstance(edge, dict):
            raise ValueError("Each edge must be an object.")
        edge_id = str(edge.get("id") or f"edge-{index}")
        edge["id"] = edge_id
        if edge_id in edge_ids:
            raise ValueError(f"Duplicate edge id: {edge_id}")
        edge_ids.add(edge_id)
        source = edge.get("source")
        target = edge.get("target")
        if not source or not target:
            raise ValueError(f"Edge {edge_id} requires 'source' and 'target'.")
        if str(source) not in node_ids or str(target) not in node_ids:
            raise ValueError(f"Edge {edge_id} references unknown nodes: {source} -> {target}")


def build_drawio_document(spec: dict) -> str:
    validate_spec(spec)

    mxfile = ET.Element(
        "mxfile",
        {
            "host": "app.diagrams.net",
            "agent": "aura-drawio-generator",
            "version": "24.7.17",
            "type": "device",
        },
    )
    diagram = ET.SubElement(mxfile, "diagram", {"name": str(spec.get("page", "Page-1"))})
    graph_model = ET.SubElement(diagram, "mxGraphModel", GRAPH_MODEL_ATTRS)
    root = ET.SubElement(graph_model, "root")

    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    for node in spec["nodes"]:
        _build_node(root, node)
    for edge in spec["edges"]:
        _build_edge(root, edge)

    tree = ET.ElementTree(mxfile)
    ET.indent(tree, space="  ")
    xml_body = ET.tostring(mxfile, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_body + "\n"


def load_spec(input_path: Path) -> dict:
    try:
        return json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON spec: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a valid draw.io file from JSON.")
    parser.add_argument("--input", required=True, help="Path to the JSON spec file.")
    parser.add_argument("--output", required=True, help="Path to the output .drawio file.")
    args = parser.parse_args(argv)

    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    spec = load_spec(input_path)
    xml_content = build_drawio_document(spec)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(xml_content, encoding="utf-8")
    print(f"Wrote draw.io file to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
