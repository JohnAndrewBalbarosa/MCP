from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SnippetRequest:
    file_path: str
    start_line: int
    end_line: int


@dataclass
class SnippetWriteRequest(SnippetRequest):
    replacement: str
