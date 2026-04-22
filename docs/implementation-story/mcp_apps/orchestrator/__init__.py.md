# `mcp_apps/orchestrator/__init__.py`

Source path: `mcp_apps/orchestrator/__init__.py`

Role: Package marker for the orchestrator app.

Responsibilities:

- Make orchestrator modules importable through a stable package path
- Keep app-level imports consistent across the repo

## Story

This file is mostly structural rather than procedural. In the story of the codebase, it marks a folder as a real Python package so imports, test discovery, and namespace resolution work the way the rest of the system expects.

## Terms

- `package`: A Python directory that can be imported as a module namespace.
- `namespace`: The import path under which child modules are resolved.
- `import resolution`: The process Python uses to locate and load modules.

## Mermaid

```mermaid
flowchart TD
    Import["Python imports orchestrator package"] --> Mark["Register package namespace"]
    Mark --> Resolve["Resolve app, libraries, and tests modules"]
    Resolve --> Done["Callers can import orchestrator submodules"]
```
