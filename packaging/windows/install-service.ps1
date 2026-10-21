# SF-WEB-5: Windows service installation script
# Run as Administrator. Creates a scheduled task (no NSSM dependency).
# Usage: .\install-service.ps1 [-Port 8756] [-InstallDir "C:\Program Files\A-Sunday Conductor"]

param(
    [int]$Port = 8756,
    [string]$InstallDir = "C:\Program Files\A-Sunday Conductor",
    [switch]$Uninstall
)

$TaskName = "A-Sunday-Conductor-Web"

if ($Uninstall) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "Service '$TaskName' removed."
    exit 0
}

if (-not (Test-Path $InstallDir)) {
    Write-Error "Install directory not found: $InstallDir"
    Write-Output "Install the application first, then run this script."
    exit 1
}

$exe = Join-Path $InstallDir "a-conductor-web.exe"
if (-not (Test-Path $exe)) {
    $exe = Join-Path $InstallDir "Scripts\a-conductor-web.exe"
}

if (-not (Test-Path $exe)) {
    Write-Error "a-conductor-web executable not found in $InstallDir"
    exit 1
}

$action = New-ScheduledTaskAction -Execute $exe -Argument "web --port $Port"
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force
Write-Output "Service '$TaskName' installed (port $Port)."
Write-Output "Start with: Start-ScheduledTask -TaskName '$TaskName'"
