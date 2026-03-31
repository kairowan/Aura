from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


_GENERATOR_PATH = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "public"
    / "drawio-diagrams"
    / "scripts"
    / "generate_drawio.py"
)
_VALIDATOR_PATH = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "public"
    / "drawio-diagrams"
    / "scripts"
    / "validate_drawio.py"
)


def test_generate_drawio_escapes_attribute_text():
    generator = _load_module("generate_drawio", _GENERATOR_PATH)
    validator = _load_module("validate_drawio", _VALIDATOR_PATH)

    xml_content = generator.build_drawio_document(
        {
            "page": "Page-1",
            "nodes": [
                {
                    "id": "api",
                    "label": 'API & Auth <Check> "quoted"',
                    "kind": "process",
                    "x": 80,
                    "y": 120,
                },
                {
                    "id": "db",
                    "label": "数据库",
                    "kind": "data",
                    "x": 320,
                    "y": 120,
                },
            ],
            "edges": [
                {
                    "id": "edge-api-db",
                    "source": "api",
                    "target": "db",
                    "label": "写入 & 校验",
                }
            ],
        }
    )

    assert "&amp;" in xml_content
    assert "&lt;Check&gt;" in xml_content
    validator.validate_drawio_xml(xml_content)


def test_generate_drawio_rejects_missing_edge_nodes():
    generator = _load_module("generate_drawio", _GENERATOR_PATH)

    try:
        generator.build_drawio_document(
            {
                "nodes": [
                    {"id": "start", "label": "开始", "kind": "terminator", "x": 0, "y": 0},
                ],
                "edges": [
                    {"id": "edge-1", "source": "start", "target": "missing"},
                ],
            }
        )
    except ValueError as exc:
        assert "references unknown nodes" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unknown edge target")
