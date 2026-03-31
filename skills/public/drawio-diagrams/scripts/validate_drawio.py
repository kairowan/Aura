#!/usr/bin/env python3
"""Validate basic draw.io XML structure."""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def _strip_namespace(tag: str) -> str:
    return tag.split("}", 1)[-1]


def validate_drawio_xml(xml_content: str) -> None:
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid XML: {exc}") from exc

    if _strip_namespace(root.tag) != "mxfile":
        raise ValueError("Root element must be <mxfile>.")

    diagram = next((child for child in root if _strip_namespace(child.tag) == "diagram"), None)
    if diagram is None:
        raise ValueError("Missing <diagram> element.")

    graph_model = next((child for child in diagram if _strip_namespace(child.tag) == "mxGraphModel"), None)
    if graph_model is None:
        raise ValueError("Missing <mxGraphModel> element.")

    graph_root = next((child for child in graph_model if _strip_namespace(child.tag) == "root"), None)
    if graph_root is None:
        raise ValueError("Missing <root> element inside <mxGraphModel>.")

    cells = [child for child in graph_root if _strip_namespace(child.tag) == "mxCell"]
    cell_ids = {cell.attrib.get("id") for cell in cells}
    if "0" not in cell_ids or "1" not in cell_ids:
        raise ValueError("draw.io file must contain reserved mxCell ids '0' and '1'.")

    known_ids = {cell.attrib["id"] for cell in cells if cell.attrib.get("id")}
    for cell in cells:
        if cell.attrib.get("edge") == "1":
            source = cell.attrib.get("source")
            target = cell.attrib.get("target")
            if source and source not in known_ids:
                raise ValueError(f"Edge {cell.attrib.get('id')} references missing source node: {source}")
            if target and target not in known_ids:
                raise ValueError(f"Edge {cell.attrib.get('id')} references missing target node: {target}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a draw.io XML file.")
    parser.add_argument("path", help="Path to the .drawio file.")
    args = parser.parse_args(argv)

    file_path = Path(args.path).expanduser().resolve()
    xml_content = file_path.read_text(encoding="utf-8")
    validate_drawio_xml(xml_content)
    print("OK")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
