# MCP Workspace Structure

This document reflects the current architecture and naming conventions.

## Top-Level Layout

/root
|
|-- .env                              # single shared configuration source
|-- requirements.txt
|-- pyproject.toml
|-- mcp_design_python.md
|-- mcp_orchestrator_prompt.md
|-- fileStructure.md
|
|-- /mcp_shared
|   `-- /config
|       `-- env_loader.py             # shared root .env loader
|
|-- /mcp_apps
|   `-- /orchestrator
|       |-- README.md
|       |-- /app
|       |   |-- main.py
|       |   |-- orchestrator.py
|       |   |-- planner.py
|       |   |-- researcher.py
|       |   |-- state_manager.py
|       |   `-- trace_exporter.py
|       `-- /libraries
|           |-- /auth
|           |-- /providers
|           `-- /types
|
|-- /mcp_clients
|   `-- /agent_executor
|       |-- README.md
|       |-- /client
|       |   |-- mcp_router.py
|       |   |-- prompt_bounds.py
|       |   `-- worker.py
|       `-- /libraries
|           `-- /types
|       `-- /tools
|           |-- README.md
|           |-- flow_parser.py
|           `-- response_parser.py
|
`-- /mcp_servers
    |-- /filesystem_server
    |   |-- README.md
    |   |-- /server
    |   |   |-- index.py
    |   |   `-- file_mutator.py
    |   `-- /libraries
    |       `-- /types
    |
    |-- /git_server
    |   |-- README.md
    |   |-- /server
    |   |   `-- index.py
    |   `-- /libraries
    |       `-- /types
    |
    `-- /llm_server
        |-- /server
        |   |-- index.py             # compatibility facade
        |   |-- providers.py         # provider selection entry
        |   |-- trace_logger.py
        |   |-- /handlers
        |   |   `-- llm_handler.py   # server handler layer
        |   `-- /agents
        |       |-- entrypoint.py    # server agent entrypoint
        |       |-- /modules         # vendor-neutral agent modules
        |       |   |-- defaults.py
        |       |   |-- runtime_loader.py
        |       |   `-- offline_fallback.py
        |       `-- /vendors         # vendor-specific implementations
        |           |-- registry.py
        |           |-- openai_agent.py
        |           |-- gemini_agent.py
        |           `-- qwen_agent.py
        `-- /libraries
            `-- /types

## LLM Request Path

mcp_clients request -> mcp_servers llm handler -> agent entrypoint -> vendor module

## Configuration Rules

- Use root .env as the single configuration source.
- Process environment variables override root .env values.
- Keep vendor-specific keys and model settings consumed only by server-side code.
