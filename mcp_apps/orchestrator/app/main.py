from __future__ import annotations

import argparse
from pathlib import Path

from mcp_apps.orchestrator.app.orchestrator import run_orchestrator


def _resolve_request(args: argparse.Namespace) -> str:
    if args.request_file:
        request_path = Path(args.request_file)
        if not request_path.exists():
            raise FileNotFoundError(f"Request file not found: {request_path}")
        return request_path.read_text(encoding="utf-8").strip()

    if args.request:
        return args.request.strip()

    return "Implement requested feature safely"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the MCP orchestrator")
    parser.add_argument("--request", help="Inline request text", default="")
    parser.add_argument("--request-file", help="Path to a UTF-8 request file", default="")
    args = parser.parse_args()

    run_orchestrator(_resolve_request(args))


if __name__ == "__main__":
    main()
