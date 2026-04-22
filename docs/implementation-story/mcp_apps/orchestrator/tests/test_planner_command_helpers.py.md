# `mcp_apps/orchestrator/tests/test_planner_command_helpers.py`

Source path: `mcp_apps/orchestrator/tests/test_planner_command_helpers.py`

Role: Tests planner-side command and graph helper behavior.

Responsibilities:

- Validate command sequencing and deduplication
- Check workspace-aware scaffold skipping
- Protect fallback graph rules and command-first execution

## Story

This file is a guardrail for the behavior described by the surrounding module docs. Its job is to exercise one narrow slice of logic and fail loudly when a change breaks an assumption the rest of the system depends on.

## Terms

- `module under test`: The file or behavior the test is exercising.
- `assertion`: A condition that must be true for the test to pass.
- `invariant`: A property of the system that should remain stable across changes.

## Mermaid

```mermaid
flowchart TD
    Start["Run planner helper tests"] --> Build["Build sample planning scenarios"]
    Build --> Exercise["Exercise command sequencing and helper logic"]
    Exercise --> Assert["Assert graph ordering, scaffold skipping, and fallback behavior"]
    Assert --> Pass["Protect planner helper invariants"]
```
