from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from mcp_apps.orchestrator.app.orchestrator import run_orchestrator


@contextmanager
def _temp_env(**kwargs: str) -> Generator[None, None, None]:
    """Temporarily set environment variables, restoring originals on exit."""
    old: dict[str, str | None] = {k: os.environ.get(k) for k in kwargs}
    os.environ.update(kwargs)
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_WORKSPACE_ROOT = REPO_ROOT / "Workspace"
DEFAULT_SCENARIO_NAME = "parallel_scheduler_demo"


def _scenario_root(workspace_root: Path) -> Path:
    return workspace_root / DEFAULT_SCENARIO_NAME


def _request_path(workspace_root: Path) -> Path:
    return workspace_root / "scenarios" / DEFAULT_SCENARIO_NAME / "request.txt"


def _trace_root(workspace_root: Path) -> Path:
    return workspace_root / "traces" / DEFAULT_SCENARIO_NAME


def _target_files(workspace_root: Path) -> list[Path]:
    scenario_root = _scenario_root(workspace_root)
    return [
        scenario_root / "node_models.py",
        scenario_root / "prerequisite_counter.py",
        scenario_root / "fork_report.py",
        scenario_root / "demo_runner.py",
    ]


def prepare_parallel_scheduler_demo(workspace_root: Path | None = None) -> dict[str, Path]:
    root = (workspace_root or DEFAULT_WORKSPACE_ROOT).resolve()
    scenario_root = _scenario_root(root)
    request_path = _request_path(root)
    trace_root = _trace_root(root)

    scenario_root.mkdir(parents=True, exist_ok=True)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    if trace_root.exists():
        shutil.rmtree(trace_root)
    trace_root.mkdir(parents=True, exist_ok=True)

    for target in _target_files(root):
        if target.exists():
            target.unlink()

    cache_dir = scenario_root / "__pycache__"
    if cache_dir.exists():
        for cached in cache_dir.iterdir():
            if cached.is_file():
                cached.unlink()
        cache_dir.rmdir()

    if not request_path.exists():
        request_path.write_text(
            (
                "Build a parallel scheduler demo in Python that uses one fork node, "
                "two parallel branches, and one merge prerequisite node. "
                "The result must report generated and deleted agent counts per fork "
                "and summarize compaction events."
            ),
            encoding="utf-8",
        )

    return {
        "workspace_root": root,
        "scenario_root": scenario_root,
        "request_path": request_path,
        "trace_root": trace_root,
    }


def _mock_env(workspace_root: Path, trace_root: Path) -> dict[str, str]:
    """Build the environment variable dict needed to run the orchestrator in mock mode."""
    return {
        "MCP_WORKSPACE_ROOT":          str(workspace_root),
        "MCP_TRACE_EXPORT_DIR":        str(trace_root),
        "MCP_COMMAND_PRESENTATION":    "batch",
        "MCP_IMPLICIT_LAYERED_DESIGN": "1",
        "MCP_LLM_REQUEST_DELAY_SECONDS": "0",
        "RESEARCH_PROVIDER":           "mock",
        "PLANNER_PROVIDER":            "mock",
        "EXECUTOR_PROVIDER":           "mock",
        "RESEARCH_MODEL":              os.environ.get("RESEARCH_MODEL", "mock-local-v1"),
        "PLANNER_MODEL":               os.environ.get("PLANNER_MODEL",  "mock-local-v1"),
        "EXECUTOR_MODEL":              os.environ.get("EXECUTOR_MODEL",  "mock-local-v1"),
    }


def run_parallel_scheduler_demo(workspace_root: Path | None = None) -> dict[str, object]:
    paths = prepare_parallel_scheduler_demo(workspace_root)
    root = paths["workspace_root"]
    request_path = paths["request_path"]
    trace_root = paths["trace_root"]
    scenario_root = paths["scenario_root"]

    request = request_path.read_text(encoding="utf-8").strip()

    with _temp_env(**_mock_env(root, trace_root)):
        run_orchestrator(request)

        try:
            completed = subprocess.run(
                [sys.executable, str(scenario_root / "demo_runner.py")],
                cwd=str(scenario_root),
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                f"demo_runner.py exited with code {exc.returncode}.\n"
                f"stderr: {exc.stderr.strip()}"
            ) from exc

    payload = json.loads(completed.stdout)
    return {
        "request": request,
        "workspace_root": str(root),
        "scenario_root": str(scenario_root),
        "trace_root": str(trace_root),
        "generated_files": [str(path) for path in _target_files(root)],
        "demo_output": payload,
    }


def main() -> None:
    result = run_parallel_scheduler_demo()
    print("\n=== Sample Workspace Demo ===")
    print(f"workspace_root: {result['workspace_root']}")
    print(f"scenario_root: {result['scenario_root']}")
    print(f"trace_root: {result['trace_root']}")
    print("generated_files:")
    for path in result["generated_files"]:
        print(f"- {path}")
    print("demo_output:")
    print(json.dumps(result["demo_output"], indent=2))


if __name__ == "__main__":
    main()
