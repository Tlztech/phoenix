# monitor.ps1 -- triggered by Task Scheduler every 10 minutes.
# Keeps the scraper going until finished: if it is not running and the checkpoint
# has been idle for >= CooldownMin, it resumes; when there is no checkpoint but a
# final workbook exists, the job is done. The scraper stops itself when rate-limited.
# NOTE: keep this file ASCII-only so PowerShell parses it under any codepage.
$ErrorActionPreference = "SilentlyContinue"

# ===== Edit if needed: Python path (use full path if not on PATH) =====
$Python = "python"
# Cooldown minutes after a rate-limit stop before resuming.
$CooldownMin = 30
# =====================================================================
$TaskName = "PatagoniaScraperMonitor"   # must match install_task.ps1

$ProjectDir = Split-Path -Parent $PSScriptRoot     # project root (this script lives in windows-deploy)
$OutputDir  = Join-Path $ProjectDir "output"
$LastStart  = Join-Path $ProjectDir "monitor_last_start.txt"
$MonLog     = Join-Path $ProjectDir "monitor.log"

function Log($m) { "$(Get-Date -Format 'MM-dd HH:mm:ss')  $m" | Out-File -Append -Encoding utf8 $MonLog }

Set-Location $ProjectDir

# 1) already running? do nothing
$running = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
           Where-Object { $_.CommandLine -like "*main.py*" }
if ($running) { Log "running, skip"; exit 0 }

# 2) gather checkpoint / final file / last-start time
$ckpt  = Get-ChildItem $OutputDir -Filter ".checkpoint_*.jsonl" -Force |
         Select-Object -First 1
$final = Get-ChildItem $OutputDir -Filter "patagonia_output_*.xlsx" |
         Where-Object { $_.Name -notlike "*_part*" } |
         Sort-Object LastWriteTime -Descending | Select-Object -First 1
$acts = @()
if ($ckpt) { $acts += $ckpt.LastWriteTime }
if (Test-Path $LastStart) { $acts += (Get-Item $LastStart).LastWriteTime }
$lastAct = if ($acts.Count -gt 0) { ($acts | Measure-Object -Maximum).Maximum } else { $null }

# 3) done? no checkpoint AND a final workbook newer than the last start
if (-not $ckpt) {
    if ($final -and $lastAct -and ($final.LastWriteTime -ge $lastAct)) {
        Log ("DONE: " + $final.Name + " -> removing monitor task (job finished)")
        schtasks /Delete /TN $TaskName /F 2>$null | Out-Null   # self-delete: disappears from Task Scheduler
        exit 0
    }
}

# 4) cooldown gate: wait if last activity is less than CooldownMin ago
if ($lastAct -and (((Get-Date) - $lastAct).TotalMinutes -lt $CooldownMin)) {
    $left = [math]::Ceiling($CooldownMin - ((Get-Date) - $lastAct).TotalMinutes)
    Log ("cooling down, ~" + $left + " min left")
    exit 0
}

# 5) start / resume (--resume-max-age-hours 720 so an interrupted job always resumes)
$mode = if ($ckpt) { "resume" } else { "first-start" }
Log ($mode + " -> launching main.py")
Set-Content -Path $LastStart -Value (Get-Date) -Encoding utf8
Start-Process -FilePath $Python -ArgumentList "main.py --resume-max-age-hours 720" `
              -WorkingDirectory $ProjectDir -WindowStyle Hidden
exit 0
