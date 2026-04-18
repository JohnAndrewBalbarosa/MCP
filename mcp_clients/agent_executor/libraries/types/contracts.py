from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderRuntimeView:
    provider_id: str
    model: str
    max_output_tokens: int
    temperature: float
    top_p: float
    max_parallel_instances: int
    max_context_lines: int
