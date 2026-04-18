from __future__ import annotations

import os
from pathlib import Path
from typing import Dict


def _parse_env_file(path: Path) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    if not path.exists():
        return parsed

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip()] = value.strip().strip('"').strip("'")
    return parsed


def load_env() -> Dict[str, str]:
    repo_root = Path(__file__).resolve().parents[2]
    root_env = repo_root / ".env"

    merged: Dict[str, str] = {}
    merged.update(_parse_env_file(root_env))
    merged.update(os.environ)
    return merged
