# install_task.ps1 -- start a (new) scrape job:
#   1) archive any previous result workbooks/summaries into output\history\
#      (so the monitor won't mistake an OLD file for "this run is done"),
#   2) register the "every 10 minutes" monitor task, 3) trigger it once.
# Run: right-click -> "Run with PowerShell", or:  .\install_task.ps1
# Keep this file ASCII-only.
$ErrorActionPreference = "Stop"
$TaskName   = "PatagoniaScraperMonitor"
$Monitor    = Join-Path $PSScriptRoot "monitor.ps1"
$ProjectDir = Split-Path -Parent $PSScriptRoot
$OutputDir  = Join-Path $ProjectDir "output"
$HistoryDir = Join-Path $OutputDir "history"
$LastStart  = Join-Path $ProjectDir "monitor_last_start.txt"

if (-not (Test-Path $Monitor)) { Write-Host "monitor.ps1 not found"; exit 1 }

# If a scrape is already in progress (checkpoint present), do not start a new one.
$ckpt = Get-ChildItem $OutputDir -Filter ".checkpoint_*.jsonl" -Force -ErrorAction SilentlyContinue | Select-Object -First 1
if ($ckpt) {
    Write-Host "A checkpoint exists -> a job is in progress or was interrupted."
    Write-Host "The monitor task will resume it automatically; not starting a new run."
    Write-Host "For a fresh scrape, delete output\.checkpoint_* first, then run this again."
}

# 1) archive previous results (final workbooks + summaries, but not *_part*)
if (Test-Path $OutputDir) {
    $olds = Get-ChildItem $OutputDir -File -ErrorAction SilentlyContinue | Where-Object {
        ($_.Name -like "patagonia_output_*.xlsx" -or $_.Name -like "patagonia_output_*_summary.txt") -and ($_.Name -notlike "*_part*")
    }
    if ($olds) {
        New-Item -ItemType Directory -Force -Path $HistoryDir | Out-Null
        foreach ($f in $olds) {
            $dest = Join-Path $HistoryDir $f.Name
            if (Test-Path $dest) { Remove-Item $dest -Force -ErrorAction SilentlyContinue }
            Move-Item $f.FullName $dest -Force -ErrorAction SilentlyContinue
        }
        Write-Host ("Archived " + $olds.Count + " previous result file(s) to output\history\")
    }
}

# reset the last-start marker so the monitor treats this as a fresh job
Remove-Item $LastStart -Force -ErrorAction SilentlyContinue

# 2) register the task (every 10 min; runs only while the user is logged on so Chrome can show).
# Use Register-ScheduledTask (robust quoting) + -WindowStyle Hidden so the check runs without a window.
$argStr    = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Monitor`""
$action    = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argStr
$trigger   = New-ScheduledTaskTrigger -Once -At (Get-Date)
$trigger.Repetition = (New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 10)).Repetition
$principal = New-ScheduledTaskPrincipal -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive
$settings  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Write-Host "Task created: $TaskName (checks every 10 minutes)"

# 3) trigger once to begin now
Start-ScheduledTask -TaskName $TaskName
Write-Host "Triggered. Watch progress:  Get-Content .\monitor.log -Wait   (in the project root)"
