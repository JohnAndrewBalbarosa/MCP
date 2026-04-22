# `mcp_servers/__init__.py`

Source path: `mcp_servers/__init__.py`

Role: Package marker for the server layer.

Responsibilities:

- Make server modules importable through one namespace
- Support shared imports and test discovery

## Story

This file is mostly structural rather than procedural. In the story of the codebase, it marks a folder as a real Python package so imports, test discovery, and namespace resolution work the way the rest of the system expects.

## Terms

- `package`: A Python directory that can be imported as a module namespace.
- `namespace`: The import path under which child modules are resolved.
- `import resolution`: The process Python uses to locate and load modules.

## Mermaid

```mermaid
flowchart TD
    Start["Python imports mcp_servers"] --> Mark["Treat folder as package"]
    Mark --> Resolve["Resolve filesystem, git, and llm server modules"]
    Resolve --> Done["Server-layer imports succeed"]
```
