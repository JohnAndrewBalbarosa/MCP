Here is the corrected Python file structure with libraries grouped per MCP category.

/root
|
|-- .env                              # Shared defaults used by all MCP categories
|
|-- /mcp_apps
|   |-- .env                          # App-only overrides (not used by clients/servers)
|   |-- /orchestrator                 # Primary model-agnostic orchestrator package
|   |   |-- /app
|   |   |   |-- main.py
|   |   |   |-- researcher.py         # Dedicated research agent entrypoint
|   |   |   |-- planner.py
|   |   |   |-- state_manager.py
|   |   |   `-- orchestrator.py
|   |   `-- /libraries
|   |       |-- /auth                 # Auth adapter abstraction and provider routing
|   |       |-- /config
|   |       |-- /providers            # Research and planner provider selection factories
|   |       `-- /types
|
|-- /mcp_clients
|   |-- .env                          # Client-only overrides and endpoints
|   |-- /agent_executor               # Primary model-agnostic executor package
|   |   |-- /client
|   |   |   |-- agent_factory.py
|   |   |   |-- mcp_router.py
|   |   |   |-- prompt_bounds.py
|   |   |   `-- worker.py
|   |   `-- /libraries
|   |       |-- /config
|   |       |-- /providers            # Executor provider selection factory
|   |       `-- /llm_api_wrappers
|
`-- /mcp_servers
    |-- .env                          # Server-only bind URLs and server config
    |-- /filesystem_server
    |   |-- /server
    |   |   |-- index.py                 # MCP server transport and handlers
    |   |   `-- file_mutator.py          # Deterministic line splice engine
    |   |-- /libraries
    |   |   `-- /types
    |   |       `-- contracts.py
    |   `-- README.md
    |
    `-- /git_server
        |-- /server
        |   `-- index.py                 # MCP git operations wrapper
        |-- /libraries
        |   `-- /types
        |       `-- contracts.py
        `-- README.md

No root-level shared_libraries directory is used in this design.
