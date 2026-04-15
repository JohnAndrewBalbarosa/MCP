const fs = require('fs/promises');
const os = require('os');
const path = require('path');
const vscode = require('vscode');

function quotePowerShell(value) {
  return `'${String(value).replace(/'/g, "''")}'`;
}

async function resolveWorkspaceRoot() {
  const folders = vscode.workspace.workspaceFolders || [];
  if (folders.length === 1) {
    return folders[0].uri.fsPath;
  }

  if (folders.length > 1) {
    const choice = await vscode.window.showQuickPick(
      folders.map((folder) => ({
        label: folder.name,
        description: folder.uri.fsPath,
        value: folder.uri.fsPath,
      })),
      {
        placeHolder: 'Choose the workspace to run the assistant against',
      }
    );

    return choice ? choice.value : undefined;
  }

  const entered = await vscode.window.showInputBox({
    prompt: 'Enter the absolute path to the workspace to run against',
    placeHolder: 'C:\\path\\to\\another-workspace',
  });

  return entered ? entered.trim() : undefined;
}

async function resolveRepoRoot(context) {
  const config = vscode.workspace.getConfiguration('parallelCodingAssistant');
  const stored = context.globalState.get('repoRoot') || config.get('repoRoot') || '';
  if (stored && String(stored).trim()) {
    return String(stored).trim();
  }

  const entered = await vscode.window.showInputBox({
    prompt: 'Enter the absolute path to the MCP repo root that contains mcp_testbed/run_case.ps1',
    placeHolder: 'C:\\Users\\Drew\\Desktop\\MCP',
  });

  if (!entered) {
    return undefined;
  }

  const normalized = entered.trim();
  await context.globalState.update('repoRoot', normalized);
  return normalized;
}

async function resolveRequestText(context) {
  const config = vscode.workspace.getConfiguration('parallelCodingAssistant');
  const defaultRequest = config.get('defaultRequest') || 'Build a coding assistant MCP with built-in parallelism.';
  const entered = await vscode.window.showInputBox({
    prompt: 'Enter the request to send to the assistant',
    value: String(defaultRequest),
    placeHolder: 'Build a coding assistant MCP with built-in parallelism.',
  });

  if (!entered) {
    return undefined;
  }

  const requestText = entered.trim();
  await context.globalState.update('lastRequestText', requestText);
  return requestText;
}

async function resolveCommandPresentation() {
  const config = vscode.workspace.getConfiguration('parallelCodingAssistant');
  const defaultMode = config.get('defaultCommandPresentation') || 'batch';
  const choice = await vscode.window.showQuickPick(
    [
      {
        label: 'Batch',
        description: 'Show the planned commands as a grouped list',
        value: 'batch',
      },
      {
        label: 'Line by line',
        description: 'Pause before each planned command',
        value: 'line-by-line',
      },
    ],
    {
      placeHolder: 'Choose how commands should be presented',
      title: `Default is ${defaultMode}`,
    }
  );

  return choice ? choice.value : undefined;
}

async function writeTemporaryRequestFile(requestText) {
  const tempRoot = path.join(os.tmpdir(), 'parallel-coding-assistant');
  await fs.mkdir(tempRoot, { recursive: true });
  const requestPath = path.join(tempRoot, `request-${Date.now()}.txt`);
  await fs.writeFile(requestPath, `${requestText}\n`, 'utf8');
  return requestPath;
}

async function activate(context) {
  const outputChannel = vscode.window.createOutputChannel('Parallel Coding Assistant');

  context.subscriptions.push(
    vscode.commands.registerCommand('parallelCodingAssistant.run', async () => {
      const workspaceRoot = await resolveWorkspaceRoot();
      if (!workspaceRoot) {
        vscode.window.showWarningMessage('No workspace folder selected.');
        return;
      }

      const repoRoot = await resolveRepoRoot(context);
      if (!repoRoot) {
        vscode.window.showWarningMessage('No MCP repo root selected.');
        return;
      }

      const requestText = await resolveRequestText(context);
      if (!requestText) {
        vscode.window.showWarningMessage('No request text provided.');
        return;
      }

      const commandPresentation = await resolveCommandPresentation();
      if (!commandPresentation) {
        vscode.window.showWarningMessage('No command presentation mode selected.');
        return;
      }

      const promptForCommands = commandPresentation === 'line-by-line';
      const requestFile = await writeTemporaryRequestFile(requestText);

      const scriptPath = path.join(repoRoot, 'mcp_testbed', 'run_case.ps1');
      const commandParts = [
        'Set-Location',
        quotePowerShell(repoRoot),
        ';',
        '&',
        quotePowerShell(scriptPath),
        '-WorkspaceRoot',
        quotePowerShell(workspaceRoot),
        '-RequestFile',
        quotePowerShell(requestFile),
        '-CommandPresentation',
        quotePowerShell(commandPresentation),
      ];

      if (promptForCommands) {
        commandParts.push('-PromptForCommands');
      }

      const commandLine = commandParts.join(' ');

      outputChannel.clear();
      outputChannel.appendLine('Parallel Coding Assistant run started.');
      outputChannel.appendLine(`Workspace root: ${workspaceRoot}`);
      outputChannel.appendLine(`Repo root: ${repoRoot}`);
      outputChannel.appendLine(`Request file: ${requestFile}`);
      outputChannel.appendLine(`Command mode: ${commandPresentation}`);
      outputChannel.appendLine(`Command: ${commandLine}`);
      outputChannel.show(true);

      const terminal = vscode.window.createTerminal('Parallel Coding Assistant');
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