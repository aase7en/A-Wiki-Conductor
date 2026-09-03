param(
    [string]$ConfigPath = (Join-Path $HOME '.zcode\v2\config.json')
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
    Write-Output "ZCODE_CONFIG=NOT_FOUND"
    Write-Output "PATH=$ConfigPath"
    exit 3
}

$unlocked = $false
try {
    $stream = [System.IO.File]::Open(
        $ConfigPath,
        [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::ReadWrite,
        [System.IO.FileShare]::None
    )
    $stream.Close()
    $unlocked = $true
}
catch [System.IO.IOException] {
    Write-Output 'ZCODE_CONFIG_LOCK=LOCKED'
}

if ($unlocked) {
    Write-Output 'ZCODE_CONFIG_LOCK=UNLOCKED'
    try {
        Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json | Out-Null
        Write-Output 'JSON_PARSE=OK'
        exit 0
    }
    catch {
        Write-Output 'JSON_PARSE=FAILED'
        exit 4
    }
}

if ([System.Environment]::OSVersion.Platform -ne [System.PlatformID]::Win32NT) {
    Write-Output 'LOCK_OWNER_LOOKUP=UNSUPPORTED_NON_WINDOWS'
    exit 2
}

$source = @'
using System;
using System.Runtime.InteropServices;

public static class ZCodeLockRestartManager
{
    [StructLayout(LayoutKind.Sequential)]
    public struct RM_UNIQUE_PROCESS
    {
        public int dwProcessId;
        public System.Runtime.InteropServices.ComTypes.FILETIME ProcessStartTime;
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct RM_PROCESS_INFO
    {
        public RM_UNIQUE_PROCESS Process;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 256)] public string strAppName;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 64)] public string strServiceShortName;
        public uint ApplicationType;
        public uint AppStatus;
        public uint TSSessionId;
        [MarshalAs(UnmanagedType.Bool)] public bool bRestartable;
    }

    [DllImport("rstrtmgr.dll", CharSet = CharSet.Unicode)]
    public static extern int RmStartSession(out uint handle, int flags, string key);

    [DllImport("rstrtmgr.dll", CharSet = CharSet.Unicode)]
    public static extern int RmRegisterResources(
        uint handle, uint fileCount, string[] files,
        uint appCount, IntPtr apps, uint serviceCount, string[] services);

    [DllImport("rstrtmgr.dll")]
    public static extern int RmGetList(
        uint handle, out uint needed, ref uint count,
        [In, Out] RM_PROCESS_INFO[] apps, ref uint rebootReasons);

    [DllImport("rstrtmgr.dll")]
    public static extern int RmEndSession(uint handle);
}
'@

if (-not ('ZCodeLockRestartManager' -as [type])) {
    Add-Type -TypeDefinition $source
}

[uint32]$handle = 0
$key = [guid]::NewGuid().ToString()
$startResult = [ZCodeLockRestartManager]::RmStartSession([ref]$handle, 0, $key)
if ($startResult -ne 0) {
    Write-Output "LOCK_OWNER_LOOKUP=RM_START_FAILED_$startResult"
    exit 2
}

try {
    [ZCodeLockRestartManager]::RmRegisterResources(
        $handle, 1, @($ConfigPath), 0, [IntPtr]::Zero, 0, $null
    ) | Out-Null

    [uint32]$needed = 0
    [uint32]$count = 0
    [uint32]$rebootReasons = 0
    [ZCodeLockRestartManager]::RmGetList(
        $handle, [ref]$needed, [ref]$count, $null, [ref]$rebootReasons
    ) | Out-Null

    if ($needed -eq 0) {
        Write-Output 'LOCK_OWNER_LOOKUP=NO_OWNER_REPORTED'
        exit 2
    }

    $apps = New-Object 'ZCodeLockRestartManager+RM_PROCESS_INFO[]' $needed
    $count = $needed
    [ZCodeLockRestartManager]::RmGetList(
        $handle, [ref]$needed, [ref]$count, $apps, [ref]$rebootReasons
    ) | Out-Null

    Write-Output "LOCK_OWNER_COUNT=$count"
    foreach ($app in $apps) {
        $pidValue = $app.Process.dwProcessId
        $process = Get-CimInstance Win32_Process -Filter "ProcessId=$pidValue" -ErrorAction SilentlyContinue
        $isDesktopCommander = $false
        if ($process -and $process.CommandLine) {
            $isDesktopCommander = $process.CommandLine -match '@wonderwhy-er\\desktop-commander'
        }
        [pscustomobject]@{
            PID = $pidValue
            Name = $process.Name
            ParentPID = $process.ParentProcessId
            ExecutablePath = $process.ExecutablePath
            IsDesktopCommander = $isDesktopCommander
        } | Format-List
    }
}
finally {
    [ZCodeLockRestartManager]::RmEndSession($handle) | Out-Null
}

exit 2
