"""Provider-neutral boundary for optional model-assisted analysis."""

from __future__ import annotations

from typing import Any, Protocol


class ModelProvider(Protocol):
    """A model may propose interpretations, but never creates evidence."""

    def complete_json(
        self,
        *,
        purpose: str,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
    ) -> dict[str, Any]: ...

