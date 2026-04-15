param(
    [string]$WorkspaceRoot = "workspace",
    [string]$RequestFile = "input\request.txt",
    [string]$OutputFile = "output\run.log",
    [ValidateSet("batch", "line-by-line")]
    [string]$CommandPresentation = "batch",
    [switch]$PromptForCommands
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path $PSScriptRoot -Parent
$workspacePath = Join-Path $PSScriptRoot $WorkspaceRoot
$requestPath = Join-Path $PSScriptRoot $RequestFile
$outputPath = Join-Path $PSScriptRoot $OutputFile
$outputDir = Split-Path $outputPath -Parent
$batchLogRoot = Join-Path $outputDir "batch_logs"
$sessionTraceDir = Join-Path $outputDir "session_trace"
$sessionLogDir = Join-Path $outputDir "session_logs"
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
$pythonCommand = if (Test-Path $pythonExe) { $pythonExe } else { "python" }
$orchestratorStdoutPath = Join-Path $outputDir "orchestrator.stdout.log"
$orchestratorStderrPath = Join-Path $outputDir "orchestrator.stderr.log"
$requirementsStdoutPath = Join-Path $outputDir "requirements.stdout.log"
$requirementsStderrPath = Join-Path $outputDir "requirements.stderr.log"
$previousPythonPath = $env:PYTHONPATH
$previousTraceExportDir = $env:MCP_TRACE_EXPORT_DIR
$previousTraceLogDir = $env:MCP_TRACE_LOG_DIR
$previousCommandPresentation = $env:MCP_COMMAND_PRESENTATION
$previousAllowOfflineFallback = $env:MCP_ALLOW_OFFLINE_FALLBACK
$runLogSections = @()

function Get-LogText {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        return ""
    }

    $content = Get-Content -Path $Path -Raw
    if ($null -eq $content) {
        return ""
    }

    return $content.TrimEnd()
}

function Copy-WorkspaceSnapshot {
    param(
        [string]$SourceRoot,
        [string]$DestinationRoot
    )

    if (-not (Test-Path $SourceRoot)) {
        return @()
    }

    if (Test-Path $DestinationRoot) {
        Remove-Item -Recurse -Force $DestinationRoot
    }

    New-Item -ItemType Directory -Force -Path $DestinationRoot | Out-Null

    $allowedExtensions = @(".py", ".md", ".txt", ".toml", ".json", ".ps1")
    $copiedFiles = @()
    Get-ChildItem -Path $SourceRoot -Recurse -File |
        Where-Object {
            $_.Extension -in $allowedExtensions -and $_.FullName -notmatch "\\__pycache__(\\|$)"
        } |
        Sort-Object FullName |
        ForEach-Object {
            $relativePath = $_.FullName.Substring($SourceRoot.Length).TrimStart([char]'\', [char]'/')
            $destinationPath = Join-Path $DestinationRoot $relativePath
            New-Item -ItemType Directory -Force -Path (Split-Path $destinationPath -Parent) | Out-Null
            Copy-Item -Path $_.FullName -Destination $destinationPath -Force
            $copiedFiles += $relativePath
        }

    $indexPath = Join-Path $DestinationRoot "source_index.txt"
    if ($copiedFiles.Count -gt 0) {
        $copiedFiles | Set-Content -Path $indexPath
    }
    else {
        "" | Set-Content -Path $indexPath
    }

    return $copiedFiles
}

function Copy-DirectoryContents {
    param(
        [string]$SourceRoot,
        [string]$DestinationRoot
    )

    if (-not (Test-Path $SourceRoot)) {
        return
    }

    New-Item -ItemType Directory -Force -Path $DestinationRoot | Out-Null
    Get-ChildItem -Path $SourceRoot -Force | ForEach-Object {
        Copy-Item -Path $_.FullName -Destination $DestinationRoot -Recurse -Force
    }
}

function Copy-DirectoryTree {
    param(
        [string]$SourceRoot,
        [string]$DestinationRoot
    )

    if (-not (Test-Path $SourceRoot)) {
        return
    }

    if (Test-Path $DestinationRoot) {
        Remove-Item -Recurse -Force $DestinationRoot
    }

    New-Item -ItemType Directory -Force -Path $DestinationRoot | Out-Null
    Get-ChildItem -Path $SourceRoot -File | ForEach-Object {
        Copy-Item -Path $_.FullName -Destination $DestinationRoot -Force
    }
}

if (-not (Test-Path $requestPath)) {
    throw "Missing request file: $requestPath"
}

New-Item -ItemType Directory -Force -Path $workspacePath | Out-Null
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
New-Item -ItemType Directory -Force -Path $batchLogRoot | Out-Null
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $sessionTraceDir
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $sessionLogDir
New-Item -ItemType Directory -Force -Path $sessionTraceDir | Out-Null
New-Item -ItemType Directory -Force -Path $sessionLogDir | Out-Null
Get-ChildItem -Path $outputDir -File -Filter *.log | Remove-Item -Force

Push-Location $repoRoot
try {
    if ([string]::IsNullOrWhiteSpace($previousPythonPath)) {
        $env:PYTHONPATH = $repoRoot
    }
    else {
        $env:PYTHONPATH = "$repoRoot;$previousPythonPath"
    }
    $env:MCP_TRACE_EXPORT_DIR = $sessionTraceDir
    $env:MCP_TRACE_LOG_DIR = $sessionLogDir
    $env:MCP_COMMAND_PRESENTATION = $CommandPresentation
    $env:MCP_ALLOW_OFFLINE_FALLBACK = "0"

    $requestArg = (Resolve-Path $requestPath).Path
    Push-Location $workspacePath
    try {
        $orchestratorProcess = Start-Process -FilePath $pythonCommand -ArgumentList @(
            "-m",
            "mcp_apps.orchestrator.app.main",
            "--request-file",
            $requestArg
        ) -WorkingDirectory $workspacePath -NoNewWindow -PassThru -RedirectStandardOutput $orchestratorStdoutPath -RedirectStandardError $orchestratorStderrPath -Wait
    }
    finally {
        Pop-Location
    }

    if (Test-Path $orchestratorStdoutPath) {
        $stdoutText = Get-LogText -Path $orchestratorStdoutPath
        if (-not [string]::IsNullOrWhiteSpace($stdoutText)) {
            $runLogSections += $stdoutText
        }
    }
    if (Test-Path $orchestratorStderrPath) {
        $stderrText = Get-LogText -Path $orchestratorStderrPath
        if (-not [string]::IsNullOrWhiteSpace($stderrText)) {
            $runLogSections += $stderrText
        }
    }

    if ($orchestratorProcess.ExitCode -ne 0) {
        throw "Orchestrator run failed with exit code $($orchestratorProcess.ExitCode)"
    }

    if ($PromptForCommands) {
        $terminalCommandsPath = Join-Path $sessionTraceDir "planner\terminal_commands.txt"
        if (Test-Path $terminalCommandsPath) {
            $plannedCommands = Get-Content -Path $terminalCommandsPath | Where-Object { $_ -match '^[0-9]+\. ' }
            foreach ($plannedCommand in $plannedCommands) {
                Write-Host "Planned command: $plannedCommand"
                $confirmation = Read-Host "Continue to the next planned command? (y/n)"
                if ($confirmation -notin @("y", "Y", "yes", "YES")) {
                    throw "Command approval declined by the user"
                }
            }
        }
    }

    "`n=== Requirement tests ===" | Tee-Object -FilePath $outputPath -Append
    $requirementsProcess = Start-Process -FilePath $pythonCommand -ArgumentList @(
        "-m",
        "unittest",
        "discover",
        "-s",
        "tests",
        "-t",
        "."
    ) -WorkingDirectory $workspacePath -NoNewWindow -PassThru -RedirectStandardOutput $requirementsStdoutPath -RedirectStandardError $requirementsStderrPath -Wait

    if (Test-Path $requirementsStdoutPath) {
        $runLogSections += "=== Requirement tests ==="
        $stdoutText = Get-LogText -Path $requirementsStdoutPath
        if (-not [string]::IsNullOrWhiteSpace($stdoutText)) {
            $runLogSections += $stdoutText
        }
    }
    if (Test-Path $requirementsStderrPath) {
        $stderrText = Get-LogText -Path $requirementsStderrPath
        if (-not [string]::IsNullOrWhiteSpace($stderrText)) {
            $runLogSections += $stderrText
        }
    }

    if ($requirementsProcess.ExitCode -ne 0) {
        throw "Requirement tests failed with exit code $($requirementsProcess.ExitCode)"
    }
}
finally {
    Pop-Location
    $env:PYTHONPATH = $previousPythonPath
    $env:MCP_TRACE_EXPORT_DIR = $previousTraceExportDir
    $env:MCP_TRACE_LOG_DIR = $previousTraceLogDir
    $env:MCP_COMMAND_PRESENTATION = $previousCommandPresentation
    $env:MCP_ALLOW_OFFLINE_FALLBACK = $previousAllowOfflineFallback

    if ($runLogSections.Count -gt 0) {
        $runLogSections -join "`r`n`r`n" | Set-Content -Path $outputPath -Encoding utf8
    }

    $archiveStamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
    $archivePath = Join-Path $batchLogRoot $archiveStamp
    $archiveLogsPath = Join-Path $archivePath "logs"
    $archiveTracePath = Join-Path $archivePath "trace"
    $archiveWorkspacePath = Join-Path $archivePath "workspace_snapshot"
    $archiveOrchestratorPath = Join-Path $archiveLogsPath "orchestrator"
    $archiveRequirementsPath = Join-Path $archiveLogsPath "requirements"
    New-Item -ItemType Directory -Force -Path $archiveLogsPath | Out-Null
    New-Item -ItemType Directory -Force -Path $archiveTracePath | Out-Null
    New-Item -ItemType Directory -Force -Path $archiveWorkspacePath | Out-Null
    New-Item -ItemType Directory -Force -Path $archiveOrchestratorPath | Out-Null
    New-Item -ItemType Directory -Force -Path $archiveRequirementsPath | Out-Null

    @(
        "timestamp=$archiveStamp"
        "request=$requestPath"
        "workspace=$workspacePath"
        "output=$outputDir"
        "command_presentation=$CommandPresentation"
        "prompt_for_commands=$PromptForCommands"
        "offline_fallback_enabled=0"
    ) | Set-Content -Path (Join-Path $archivePath "manifest.txt")

    if (Test-Path $requestPath) {
        Copy-Item -Path $requestPath -Destination (Join-Path $archivePath "request.txt") -Force
    }

    if (Test-Path $outputPath) {
        Copy-Item -Path $outputPath -Destination (Join-Path $archivePath "run.log") -Force
        Copy-Item -Path $outputPath -Destination (Join-Path $archiveLogsPath "combined.log") -Force
    }
    if (Test-Path $orchestratorStdoutPath) {
        Copy-Item -Path $orchestratorStdoutPath -Destination (Join-Path $archiveOrchestratorPath "stdout.log") -Force
    }
    if (Test-Path $orchestratorStderrPath) {
        Copy-Item -Path $orchestratorStderrPath -Destination (Join-Path $archiveOrchestratorPath "stderr.log") -Force
    }
    if (Test-Path $requirementsStdoutPath) {
        Copy-Item -Path $requirementsStdoutPath -Destination (Join-Path $archiveRequirementsPath "stdout.log") -Force
    }
    if (Test-Path $requirementsStderrPath) {
        Copy-Item -Path $requirementsStderrPath -Destination (Join-Path $archiveRequirementsPath "stderr.log") -Force
    }

    Copy-DirectoryContents -SourceRoot $sessionLogDir -DestinationRoot $archiveLogsPath
    Copy-DirectoryContents -SourceRoot $sessionTraceDir -DestinationRoot $archiveTracePath
    Copy-WorkspaceSnapshot -SourceRoot $workspacePath -DestinationRoot $archiveWorkspacePath | Out-Null

    Get-ChildItem -Path $outputDir -File -Filter *.log | Remove-Item -Force
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $sessionTraceDir
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $sessionLogDir
}
