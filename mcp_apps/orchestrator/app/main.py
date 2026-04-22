from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mcp_apps.orchestrator.app.orchestrator import run_orchestrator

DEFAULT_WORKSPACE_ROOT = REPO_ROOT / "mcp_testbed" / "workspace"
if "MCP_WORKSPACE_ROOT" not in os.environ and DEFAULT_WORKSPACE_ROOT.exists():
    os.environ["MCP_WORKSPACE_ROOT"] = str(DEFAULT_WORKSPACE_ROOT)

def _resolve_request(args: argparse.Namespace) -> str:
    if args.request_file:
        request_path = Path(args.request_file)
        if not request_path.exists():
            raise FileNotFoundError(f"Request file not found: {request_path}")
        return request_path.read_text(encoding="utf-8").strip()

    if args.request:
        return args.request.strip()

    if sys.stdin.isatty():
        try:
            prompt = input("What do you want the orchestrator to build? ").strip()
        except EOFError:
            prompt = ""

        if prompt:
            return prompt

    return "Implement requested feature safely"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the MCP orchestrator")
    parser.add_argument("--request", help="Inline request text", default="")
    parser.add_argument("--request-file", help="Path to a UTF-8 request file", default="")
    args = parser.parse_args()

    run_orchestrator(_resolve_request(args))


if __name__ == "__main__":
    main()
