from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GitStatusResponse:
    output: str
