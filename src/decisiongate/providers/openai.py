"""Optional OpenAI Responses API adapter."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from typing import Any


def _openai_strict_schema(json_schema: dict[str, Any]) -> dict[str, Any]:
    """Convert ordinary JSON Schema into the strict subset used by OpenAI.

    Pydantic schemas are valid JSON Schema but may omit ``additionalProperties``
    and may leave fields with defaults out of ``required``. OpenAI Structured
    Outputs with ``strict=True`` requires object schemas to reject extra fields
    and expects every declared property to be required (nullable fields remain
    expressible through their type schema).

    The conversion is provider-local so DecisionGate's core Pydantic models do
    not need OpenAI-specific validation semantics.
    """

    schema = deepcopy(json_schema)

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            properties = node.get("properties")
            if node.get("type") == "object" or isinstance(properties, dict):
                node["additionalProperties"] = False
                if isinstance(properties, dict):
                    node["required"] = list(properties.keys())
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(schema)
    return schema


class OpenAIProvider:
    def __init__(self, model: str | None = None):
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("Install the provider with: pip install 'decisiongate[openai]'") from exc
        self._client = OpenAI()
        self._model = model or os.getenv("DECISIONGATE_OPENAI_MODEL", "gpt-5-mini")

    def complete_json(
        self,
        *,
        purpose: str,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
    ) -> dict[str, Any]:
        response = self._client.responses.create(
            model=self._model,
            instructions=system_prompt,
            input=user_prompt,
            text={
                "format": {
                    "type": "json_schema",
                    "name": purpose,
                    "strict": True,
                    "schema": _openai_strict_schema(json_schema),
                }
            },
        )
        return json.loads(response.output_text)
