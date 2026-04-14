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


def load_layered_env() -> Dict[str, str]:
    here = Path(__file__).resolve()
    root_env = here.parents[4] / ".env"
    category_env = here.parents[3] / ".env"

    merged: Dict[str, str] = {}
    merged.update(_parse_env_file(root_env))
    merged.update(_parse_env_file(category_env))
    merged.update(os.environ)
    return merged