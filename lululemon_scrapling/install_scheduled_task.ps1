$ErrorActionPreference = "Stop"

$taskName = "LululemonScraperWeekly"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$runScript = Join-Path $scriptDir "run_scraper.cmd"
$currentUser = "$env:USERDOMAIN\$env:USERNAME"
$xmlPath = Join-Path $env:TEMP "LululemonScraperWeekly.xml"

if (-not (Test-Path $runScript)) {
    throw "Run script not found: $runScript"
}

$daysUntilTuesday = ([int][DayOfWeek]::Tuesday - [int](Get-Date).DayOfWeek + 7) % 7
if ($daysUntilTuesday -eq 0 -and (Get-Date).TimeOfDay -ge [TimeSpan]::FromHours(3)) {
    $daysUntilTuesday = 7
}
$nextRun = (Get-Date).Date.AddDays($daysUntilTuesday).AddHours(3)
$startBoundary = $nextRun.ToString("yyyy-MM-dd'T'HH:mm:ss")

$taskXml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Author>$currentUser</Author>
    <Description>Run the lululemon scraper every Tuesday at 3:00 AM.</Description>
    <URI>\$taskName</URI>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>$startBoundary</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByWeek>
        <WeeksInterval>1</WeeksInterval>
        <DaysOfWeek>
          <Tuesday />
        </DaysOfWeek>
      </ScheduleByWeek>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>$currentUser</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT12H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>$runScript</Command>
      <WorkingDirectory>$scriptDir</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@

Set-Content -Path $xmlPath -Value $taskXml -Encoding Unicode
schtasks /create /tn $taskName /xml $xmlPath /f | Out-Null
schtasks /query /tn $taskName /fo LIST /v
