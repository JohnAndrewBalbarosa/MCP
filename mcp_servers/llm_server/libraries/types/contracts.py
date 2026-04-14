from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderRuntime:
    provider_id: str
    model: str
    api_key: str = ""
    max_output_tokens: int = 1024
    temperature: float = 0.2
    top_p: float = 0.95
    max_parallel_instances: int = 4
    max_context_lines: int = 16

    def public_view(self) -> "ProviderRuntimeView":
        return ProviderRuntimeView(
            provider_id=self.provider_id,
            model=self.model,
            max_output_tokens=self.max_output_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
            max_parallel_instances=self.max_parallel_instances,
            max_context_lines=self.max_context_lines,
        )


@dataclass(frozen=True)
class ProviderRuntimeView:
    provider_id: str
    model: str
    max_output_tokens: int
    temperature: float
    top_p: float
    max_parallel_instances: int
    max_context_lines: int