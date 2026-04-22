# `mcp_apps/__init__.py`

Source path: `mcp_apps/__init__.py`

Role: Package marker for the application layer.

Responsibilities:

- Make `mcp_apps` importable as a Python package
- Define the root namespace for app-level modules

## Story

This file is mostly structural rather than procedural. In the story of the codebase, it marks a folder as a real Python package so imports, test discovery, and namespace resolution work the way the rest of the system expects.

## Terms

- `package`: A Python directory that can be imported as a module namespace.
- `namespace`: The import path under which child modules are resolved.
- `import resolution`: The process Python uses to locate and load modules.

## Mermaid

```mermaid
flowchart TD
    Import["Python imports mcp_apps"] --> Mark["Treat folder as package"]
    Mark --> Resolve["Enable child-module resolution"]
    Resolve --> Done["Imports can continue into app modules"]
```
