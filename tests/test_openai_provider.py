from __future__ import annotations

from typing import Any

from decisiongate.analyzer import AnalysisDraft
from decisiongate.providers.openai import _openai_strict_schema


def _object_nodes(node: Any):
    if isinstance(node, dict):
        properties = node.get("properties")
        if node.get("type") == "object" or isinstance(properties, dict):
            yield node
        for value in node.values():
            yield from _object_nodes(value)
    elif isinstance(node, list):
        for value in node:
            yield from _object_nodes(value)


def _dict_nodes(node: Any):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _dict_nodes(value)
    elif isinstance(node, list):
        for value in node:
            yield from _dict_nodes(value)


def test_openai_schema_marks_all_objects_strict_and_fields_required() -> None:
    original = AnalysisDraft.model_json_schema()
    converted = _openai_strict_schema(original)

    assert converted is not original
    object_nodes = list(_object_nodes(converted))
    assert object_nodes

    for node in object_nodes:
        assert node["additionalProperties"] is False
        properties = node.get("properties", {})
        assert node.get("required", []) == list(properties.keys())


def test_openai_schema_removes_defaults_including_ref_siblings() -> None:
    original = AnalysisDraft.model_json_schema()
    assert any("default" in node for node in _dict_nodes(original))

    converted = _openai_strict_schema(original)

    assert all("default" not in node for node in _dict_nodes(converted))
    assert all(
        set(node) == {"$ref"} or "default" not in node
        for node in _dict_nodes(converted)
        if "$ref" in node
    )


def test_openai_schema_conversion_does_not_mutate_input() -> None:
    original = AnalysisDraft.model_json_schema()
    snapshot = AnalysisDraft.model_json_schema()

    _openai_strict_schema(original)

    assert original == snapshot
