# Parallel Coding Assistant Extension

This is a minimal VS Code extension scaffold that launches the existing MCP testbed against any workspace folder.

## What it does
- Automatically locates the local MCP repo that contains `mcp_testbed/run_case.ps1`.
- Opens the request prompt in the disposable terminal console so you can check the request before execution.
- Prompts for `batch` or `line-by-line` command presentation in the same terminal session.
- Starts an integrated terminal with the PowerShell command that runs the testbed.
- The testbed now exposes a command-node queue and asks for approval before each command node executes.

## How to try it
1. Open this `vscode-extension/` folder in VS Code.
2. Run it in an Extension Development Host, or package it with the steps below.
3. Run the command `Parallel Coding Assistant: Run`.
4. Type the request in the terminal prompt that appears after the PowerShell session starts.
5. Choose `batch` or `line-by-line` when the terminal asks for command presentation.

## Why the workspace files have weird comments
The `# mutation_intent` and `# model_response` lines used to be injected by the testbed. The worker has now been changed so future runs keep the source files clean and put trace data in the logs instead.

## Notes
- The extension uses the existing `mcp_testbed/run_case.ps1` script rather than reimplementing the orchestration logic.
- The `line-by-line` mode maps to `-PromptForCommands` in the testbed runner.
- Every request gets a fresh disposable workspace clone under `mcp_testbed/output/workspace_sessions/`.

## Package and Publish
1. Install Node.js if you do not already have it.
2. From this `vscode-extension/` folder, run `npm run package`. That produces a `.vsix` file.
3. Create or sign in to a VS Code Marketplace publisher account.
4. Log in with `npx @vscode/vsce login <publisher-name>`.
5. Publish with `npm run publish` or `npx @vscode/vsce publish`.
6. If you only want to share the extension without publishing to the Marketplace, upload the generated `.vsix` to GitHub Releases or any file host and install it with VS Code's "Install from VSIX" command.

## Important
- Replace the `publisher` field in `package.json` with your real Marketplace publisher id before publishing.
- Keep `.vscodeignore` up to date so you do not upload tests, logs, or workspace artifacts.