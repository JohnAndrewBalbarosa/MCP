const fs = require('fs');
const path = require('path');
const vscode = require('vscode');

function quotePowerShell(value) {
  return `'${String(value).replace(/'/g, "''")}'`;
}

function resolveRepoRoot(context) {
  const candidates = [path.resolve(context.extensionPath, '..')];
  const workspaceFolders = vscode.workspace.workspaceFolders || [];

  for (const folder of workspaceFolders) {
    candidates.push(folder.uri.fsPath);
  }

  for (const candidate of candidates) {
    const scriptPath = path.join(candidate, 'mcp_testbed', 'run_case.ps1');
    if (fs.existsSync(scriptPath)) {
      return candidate;
    }
  }

  return undefined;
}

function buildConsoleLaunchCommand(scriptPath) {
  const quotedScriptPath = quotePowerShell(scriptPath);
  return [
    '$requestText = Read-Host "Enter the request for this run"',
    'if ([string]::IsNullOrWhiteSpace($requestText)) { throw "No request text provided." }',
    '$commandPresentation = Read-Host "Command presentation (batch or line-by-line) [batch]"',
    'if ([string]::IsNullOrWhiteSpace($commandPresentation)) { $commandPresentation = "batch" }',
    'if ($commandPresentation -notin @("batch", "line-by-line")) { throw "Unsupported command presentation: $commandPresentation" }',
    '$commandArgs = @("-RequestText", $requestText, "-CommandPresentation", $commandPresentation)',
    'if ($commandPresentation -eq "line-by-line") { $commandArgs += "-PromptForCommands" }',
    `& ${quotedScriptPath} @commandArgs`,
  ].join(' ; ');
}

async function activate(context) {
  const outputChannel = vscode.window.createOutputChannel('Parallel Coding Assistant');

  context.subscriptions.push(
    vscode.commands.registerCommand('parallelCodingAssistant.run', async () => {
      const repoRoot = resolveRepoRoot(context);
      if (!repoRoot) {
        vscode.window.showWarningMessage('Could not find the MCP repo root for the terminal launcher.');
        return;
      }

      const scriptPath = path.join(repoRoot, 'mcp_testbed', 'run_case.ps1');
      const commandLine = buildConsoleLaunchCommand(scriptPath);

      outputChannel.clear();
      outputChannel.appendLine('Parallel Coding Assistant run started.');
      outputChannel.appendLine(`Repo root: ${repoRoot}`);
      outputChannel.appendLine('Request entry mode: terminal console prompt');
      outputChannel.appendLine('Command presentation: terminal console prompt');
      outputChannel.appendLine(`Command: ${commandLine}`);
      outputChannel.show(true);

      const terminal = vscode.window.createTerminal({
        name: 'Parallel Coding Assistant',
        cwd: repoRoot,
      });
      context.subscriptions.push(terminal);
      terminal.show(true);
      terminal.sendText(commandLine, true);
    })
  );
}

function deactivate() {}

module.exports = {
  activate,
  deactivate,
};