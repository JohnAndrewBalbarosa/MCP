param(
    [string]$WorkspaceRoot = "workspace",
    [string]$RequestFile = "input\request.txt",
    [string]$OutputFile = "output\run.log"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path $PSScriptRoot -Parent
$workspacePath = Join-Path $PSScriptRoot $WorkspaceRoot
$requestPath = Join-Path $PSScriptRoot $RequestFile
$outputPath = Join-Path $PSScriptRoot $OutputFile
$outputDir = Split-Path $outputPath -Parent
$batchLogRoot = Join-Path $outputDir "batch_logs"
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
$pythonCommand = if (Test-Path $pythonExe) { $pythonExe } else { "python" }
$orchestratorStdoutPath = Join-Path $outputDir "orchestrator.stdout.log"
$orchestratorStderrPath = Join-Path $outputDir "orchestrator.stderr.log"
$requirementsStdoutPath = Join-Path $outputDir "requirements.stdout.log"
$requirementsStderrPath = Join-Path $outputDir "requirements.stderr.log"
$previousPythonPath = $env:PYTHONPATH

if (-not (Test-Path $requestPath)) {
    throw "Missing request file: $requestPath"
}

New-Item -ItemType Directory -Force -Path $workspacePath | Out-Null
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
New-Item -ItemType Directory -Force -Path $batchLogRoot | Out-Null
Get-ChildItem -Path $outputDir -File -Filter *.log | Remove-Item -Force

Push-Location $repoRoot
try {
    if ([string]::IsNullOrWhiteSpace($previousPythonPath)) {
        $env:PYTHONPATH = $repoRoot
    }
    else {
        $env:PYTHONPATH = "$repoRoot;$previousPythonPath"
    }

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
        Get-Content -Path $orchestratorStdoutPath -Raw | Set-Content -Path $outputPath -Encoding utf8
    }
    if (Test-Path $orchestratorStderrPath) {
        Get-Content -Path $orchestratorStderrPath -Raw | Add-Content -Path $outputPath -Encoding utf8
    }

    if ($orchestratorProcess.ExitCode -ne 0) {
        throw "Orchestrator run failed with exit code $($orchestratorProcess.ExitCode)"
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
        Get-Content -Path $requirementsStdoutPath -Raw | Add-Content -Path $outputPath
    }
    if (Test-Path $requirementsStderrPath) {
        Get-Content -Path $requirementsStderrPath -Raw | Add-Content -Path $outputPath
    }

    if ($requirementsProcess.ExitCode -ne 0) {
        throw "Requirement tests failed with exit code $($requirementsProcess.ExitCode)"
    }
}
finally {
    Pop-Location
    $env:PYTHONPATH = $previousPythonPath

    $archiveStamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
    $archivePath = Join-Path $batchLogRoot $archiveStamp
    New-Item -ItemType Directory -Force -Path $archivePath | Out-Null

    @(
        "timestamp=$archiveStamp"
        "request=$requestPath"
        "workspace=$workspacePath"
        "output=$outputDir"
    ) | Set-Content -Path (Join-Path $archivePath "manifest.txt")

    if (Test-Path $requestPath) {
        Copy-Item -Path $requestPath -Destination (Join-Path $archivePath "request.txt") -Force
    }

    Get-ChildItem -Path $outputDir -File -Filter *.log | ForEach-Object {
        Copy-Item -Path $_.FullName -Destination $archivePath -Force
    }

    Get-ChildItem -Path $outputDir -File -Filter *.log | Remove-Item -Force
}
