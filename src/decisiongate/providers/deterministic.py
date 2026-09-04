"""Scripted provider for deterministic tests and integrations."""

from __future__ import annotations

from collections import defaultdict, deque
from copy import deepcopy
from typing import Any


class DeterministicProvider:
    """Return queued responses by purpose without network access."""

    def __init__(self, responses: dict[str, list[dict[str, Any]]] | None = None):
        self._responses = defaultdict(deque)
        for purpose, values in (responses or {}).items():
            self._responses[purpose].extend(deepcopy(values))
        self.calls: list[str] = []

    def complete_json(
        self,
        *,
        purpose: str,
        system_prompt: str,
        user_prompt: str,
        json_schema: dict[str, Any],
    ) -> dict[str, Any]:
        del system_prompt, user_prompt, json_schema
        self.calls.append(purpose)
        if not self._responses[purpose]:
            raise RuntimeError(f"No deterministic response queued for {purpose!r}")
        return self._responses[purpose].popleft()

