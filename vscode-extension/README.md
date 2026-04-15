# Parallel Coding Assistant Extension

This is a minimal VS Code extension scaffold that launches the existing MCP testbed against any workspace folder.

## What it does
- Prompts for the target workspace folder.
- Prompts for the MCP repo root that contains `mcp_testbed/run_case.ps1`.
- Prompts for the request text.
- Lets you choose `batch` or `line-by-line` command presentation.
- Starts an integrated terminal with the PowerShell command that runs the testbed.

## How to try it
1. Open this `vscode-extension/` folder in VS Code.
2. Install extension dependencies if you package it later, or run it in an Extension Development Host.
3. Set `parallelCodingAssistant.repoRoot` in settings or enter the repo path when prompted.
4. Run the command `Parallel Coding Assistant: Run`.
5. Choose the workspace you want the MCP to modify.

## Why the workspace files have weird comments
The `# mutation_intent` and `# model_response` lines used to be injected by the testbed. The worker has now been changed so future runs keep the source files clean and put trace data in the logs instead.

## Notes
- The extension uses the existing `mcp_testbed/run_case.ps1` script rather than reimplementing the orchestration logic.
- The `line-by-line` mode maps to `-PromptForCommands` in the testbed runner.