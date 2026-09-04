"""Optional OpenAI Responses API adapter."""

from __future__ import annotations

import json
import os
from typing import Any


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
                    "schema": json_schema,
                }
            },
        )
        return json.loads(response.output_text)

