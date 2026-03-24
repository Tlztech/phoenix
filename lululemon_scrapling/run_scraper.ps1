$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$archiveRoot = Join-Path $scriptDir "scheduled_runs"
$runOutputDir = Join-Path $archiveRoot $timestamp
$alertDir = Join-Path $scriptDir "alerts"
$candidatePythonExes = @(
    (Join-Path $scriptDir ".venv\Scripts\python.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe")
)

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCommand) {
    $candidatePythonExes += $pythonCommand.Source
}

foreach ($candidate in $candidatePythonExes | Select-Object -Unique) {
    if (-not $candidate -or -not (Test-Path $candidate)) {
        continue
    }

    try {
        & $candidate -c "import openpyxl, scrapling" 1>$null 2>$null
        if ($LASTEXITCODE -eq 0) {
            $pythonExe = $candidate
            break
        }
    }
    catch {
    }
}

if (-not $pythonExe -or -not (Test-Path $pythonExe)) {
    throw "No usable Python found. Checked project venv, user-local Python 3.12, and PATH for openpyxl + scrapling."
}

New-Item -ItemType Directory -Path $archiveRoot -Force | Out-Null
New-Item -ItemType Directory -Path $alertDir -Force | Out-Null

$forwardArgs = @()
$hasOutputDir = $false
foreach ($arg in $args) {
    $forwardArgs += $arg
    if ($arg -eq "--output-dir") {
        $hasOutputDir = $true
    }
}

if (-not $hasOutputDir) {
    $forwardArgs += @("--output-dir", $runOutputDir)
}

$mainScript = Join-Path $scriptDir "main.py"

try {
    & $pythonExe $mainScript @forwardArgs
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        throw "Scraper exited with code $exitCode."
    }
}
catch {
    $errorMessage = $_.Exception.Message
    $alertPath = Join-Path $alertDir "scraper_failure_$timestamp.txt"
    $alertBody = @(
        "time=$timestamp"
        "script=$mainScript"
        "output_dir=$runOutputDir"
        "error=$errorMessage"
    ) -join [Environment]::NewLine
    Set-Content -Path $alertPath -Value $alertBody -Encoding UTF8

    try {
        $wshell = New-Object -ComObject WScript.Shell
        $null = $wshell.Popup(
            "Lululemon scraper failed at $timestamp.`n$errorMessage`nAlert file: $alertPath",
            0,
            "Lululemon Scraper Failed",
            16
        )
    }
    catch {
    }

    throw
}
