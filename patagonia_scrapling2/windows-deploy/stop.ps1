# stop.ps1 -- stop monitoring: delete the task and kill the running main.py / debug Chrome.
# The checkpoint is kept, so re-running install_task.ps1 later will resume.
# Keep this file ASCII-only.
$TaskName = "PatagoniaScraperMonitor"
schtasks /Delete /TN $TaskName /F 2>$null | Out-Null
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like "*main.py*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" |
    Where-Object { $_.CommandLine -like "*remote-debugging-port=922*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Write-Host "Stopped monitor task and scraper. Checkpoint kept; re-run install_task.ps1 to resume."
