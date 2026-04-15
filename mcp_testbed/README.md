# MCP Testbed

Isolated sandbox for testing the MCP stack without putting test inputs or outputs inside `mcp_apps`, `mcp_clients`, or `mcp_servers`.

## Layout
- `input/` holds the request text and any case-specific test artifacts.
- `output/` holds the active run while it is executing, then archives the finished artifacts into `output/batch_logs/<timestamp>/` and clears the active `.log` files for the next run.
- `workspace/` is the disposable working copy the orchestrator mutates during a test run.
- Each archive folder contains `trace/` for planner artifacts, `logs/` for orchestrator/model/API logs, and `workspace_snapshot/` for the generated source files.

## Workflow
1. Activate the virtual environment for the repo and install dependencies from [requirements.txt](../requirements.txt).
2. Put the test request in [input/request.txt](input/request.txt) or create another request file under [input](input).
3. Start the MCP services from the main repo in separate terminals using your normal launch commands.
4. Run [run_case.ps1](run_case.ps1) from the repo root. The runner will use the repo `.venv` when it exists, execute against `workspace/`, and then run the requirement tests.
5. Read the archived execution log from the newest folder under `output/batch_logs/`. The runner keeps the combined run log, separate model/API logs, planner trace files, and a `workspace_snapshot/` of generated source code there, then clears the active log files so the next test starts clean.
6. Replace the request file for the next case, or pass a different file to the runner with the RequestFile parameter.

## Command Modes
- Use the default batch mode to print the planned terminal commands as one grouped section.
- Pass the `-PromptForCommands` switch to step through the planned commands one by one before continuing to the test phase.
- The parallel-coding-assistant planner mode will also emit the planned publish path, including the feature branch checkout and `git push` target.

## Provider Errors
- Live model or API failures now surface directly in the run so quota, auth, or transport issues are visible in the archive and do not get auto-masked by fallback output.

## Rules
- Keep this folder decoupled from the MCP source folders.
- Do not write test artifacts into `mcp_apps`, `mcp_clients`, or `mcp_servers`.
- If you later turn this into a VS Code extension, point the extension at this sandbox folder as the test workspace root.
