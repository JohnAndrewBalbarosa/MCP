# `mcp_apps/orchestrator/tests/test_researcher_resilience.py`

Source path: `mcp_apps/orchestrator/tests/test_researcher_resilience.py`

Role: Tests resilience and fallback behavior in the research stage.

Responsibilities:

- Verify malformed JSON recovery
- Ensure lifecycle command defaults are filled in
- Protect request normalization around Next.js scaffolding

## Story

This file is a guardrail for the behavior described by the surrounding module docs. Its job is to exercise one narrow slice of logic and fail loudly when a change breaks an assumption the rest of the system depends on.

## Terms

- `module under test`: The file or behavior the test is exercising.
- `assertion`: A condition that must be true for the test to pass.
- `invariant`: A property of the system that should remain stable across changes.

## Mermaid

```mermaid
flowchart TD
    Start["Run researcher resilience tests"] --> Feed["Feed malformed or partial research payloads"]
    Feed --> Recover["Run repair and fallback paths"]
    Recover --> Assert["Assert normalized research brief is still usable"]
    Assert --> Pass["Protect resilience behavior"]
```
