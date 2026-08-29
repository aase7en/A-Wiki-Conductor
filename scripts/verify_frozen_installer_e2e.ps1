param(
    [Parameter(Mandatory = $true)][string]$Portable,
    [Parameter(Mandatory = $true)][string]$Setup,
    [Parameter(Mandatory = $true)][string]$ExpectedVersion
)

$ErrorActionPreference = "Stop"
$AppName = "A-Sunday Conductor"
$RegPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$AppName"
$StartLink = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\$AppName\$AppName.lnk"
$DesktopLink = Join-Path $HOME "Desktop\$AppName.lnk"
$TempPattern = "A-Sunday-Conductor-Uninstall-*.exe"

function Assert-Condition([bool]$Condition, [string]$Code) {
    if (-not $Condition) { throw $Code }
}

function Invoke-CheckedNative([string]$FilePath, [string[]]$Arguments, [int[]]$ExpectedCodes) {
    & $FilePath @Arguments
    $code = $LASTEXITCODE
    if ($ExpectedCodes -notcontains $code) {
        throw "NATIVE_EXIT_UNEXPECTED: $FilePath exit=$code expected=$($ExpectedCodes -join ',')"
    }
    return $code
}

$Portable = (Resolve-Path -LiteralPath $Portable).Path
$Setup = (Resolve-Path -LiteralPath $Setup).Path
Assert-Condition (Test-Path -LiteralPath $Portable -PathType Leaf) "PORTABLE_MISSING"
Assert-Condition (Test-Path -LiteralPath $Setup -PathType Leaf) "SETUP_MISSING"

Assert-Condition (-not (Test-Path -LiteralPath $RegPath)) "HOST_REGISTRY_NOT_CLEAN"
Assert-Condition (-not (Test-Path -LiteralPath $StartLink)) "HOST_START_LINK_NOT_CLEAN"
Assert-Condition (-not (Test-Path -LiteralPath $DesktopLink)) "HOST_DESKTOP_LINK_NOT_CLEAN"
Assert-Condition (@(Get-ChildItem -Path $env:TEMP -Filter $TempPattern -File -ErrorAction SilentlyContinue).Count -eq 0) "HOST_TEMP_UNINSTALLER_NOT_CLEAN"

$Root = Join-Path $env:RUNNER_TEMP ("a-sunday-installer-e2e-" + [guid]::NewGuid().ToString("N"))
$Unknown = Join-Path $Root "unknown-nonempty"
$Target = Join-Path $Root "managed-target"
$SmokeDb = Join-Path $Root "installed-smoke.sqlite"
New-Item -ItemType Directory -Path $Unknown -Force | Out-Null
New-Item -ItemType Directory -Path $Target -Force | Out-Null
$Sentinel = Join-Path $Unknown "sentinel.txt"
Set-Content -LiteralPath $Sentinel -Value "keep-me" -NoNewline -Encoding utf8
$SentinelBefore = (Get-FileHash -Algorithm SHA256 -LiteralPath $Sentinel).Hash

try {
    $unknownCode = Invoke-CheckedNative $Setup @("--target", $Unknown) @(5)
    Assert-Condition ($unknownCode -eq 5) "UNKNOWN_TARGET_NOT_REJECTED"
    Assert-Condition ((Get-FileHash -Algorithm SHA256 -LiteralPath $Sentinel).Hash -eq $SentinelBefore) "UNKNOWN_TARGET_SENTINEL_CHANGED"
    Assert-Condition (-not (Test-Path -LiteralPath (Join-Path $Unknown ".a-sunday-conductor-install.json"))) "UNKNOWN_TARGET_MARKER_CREATED"

    $installCode = Invoke-CheckedNative $Setup @("--target", $Target) @(0)
    Assert-Condition ($installCode -eq 0) "SETUP_INSTALL_FAILED"
    $Marker = Join-Path $Target ".a-sunday-conductor-install.json"
    $Installed = Join-Path $Target "$AppName.exe"
    $Uninstaller = Join-Path $Target "Uninstall-$AppName.exe"
    Assert-Condition (Test-Path -LiteralPath $Marker -PathType Leaf) "INSTALL_MARKER_MISSING"
    Assert-Condition (Test-Path -LiteralPath $Installed -PathType Leaf) "INSTALLED_PORTABLE_MISSING"
    Assert-Condition (Test-Path -LiteralPath $Uninstaller -PathType Leaf) "FROZEN_UNINSTALLER_MISSING"
    Assert-Condition ((Get-FileHash -Algorithm SHA256 -LiteralPath $Installed).Hash -eq (Get-FileHash -Algorithm SHA256 -LiteralPath $Portable).Hash) "INSTALLED_PORTABLE_HASH_MISMATCH"
    Assert-Condition (Test-Path -LiteralPath $StartLink -PathType Leaf) "START_LINK_MISSING"
    Assert-Condition (Test-Path -LiteralPath $DesktopLink -PathType Leaf) "DESKTOP_LINK_MISSING"
    Assert-Condition (Test-Path -LiteralPath $RegPath) "UNINSTALL_REGISTRY_MISSING"

    $Reg = Get-ItemProperty -LiteralPath $RegPath
    Assert-Condition ($Reg.DisplayVersion -eq $ExpectedVersion) "REGISTRY_VERSION_MISMATCH"
    Assert-Condition ([IO.Path]::GetFullPath($Reg.InstallLocation) -eq [IO.Path]::GetFullPath($Target)) "REGISTRY_TARGET_MISMATCH"
    Assert-Condition (-not [string]::IsNullOrWhiteSpace($Reg.UninstallString)) "UNINSTALL_STRING_MISSING"

    $smokeCode = Invoke-CheckedNative $Installed @("--smoke", "--database", $SmokeDb) @(0)
    Assert-Condition ($smokeCode -eq 0) "INSTALLED_SMOKE_FAILED"
    Assert-Condition (Test-Path -LiteralPath $SmokeDb -PathType Leaf) "INSTALLED_SMOKE_DATABASE_MISSING"

    $directCode = Invoke-CheckedNative $Uninstaller @("--uninstall", "--target", $Target) @(4)
    Assert-Condition ($directCode -eq 4) "DIRECT_UNINSTALL_DID_NOT_FAIL_CLOSED"
    Assert-Condition (Test-Path -LiteralPath $Target -PathType Container) "DIRECT_UNINSTALL_REMOVED_TARGET"
    Assert-Condition (Test-Path -LiteralPath $RegPath) "DIRECT_UNINSTALL_REMOVED_REGISTRY"

    & cmd.exe /d /s /c $Reg.UninstallString
    $registeredCode = $LASTEXITCODE
    Assert-Condition ($registeredCode -eq 0) "REGISTERED_UNINSTALL_FAILED"
    Assert-Condition (-not (Test-Path -LiteralPath $Target)) "UNINSTALL_TARGET_RESIDUE"
    Assert-Condition (-not (Test-Path -LiteralPath $StartLink)) "UNINSTALL_START_LINK_RESIDUE"
    Assert-Condition (-not (Test-Path -LiteralPath $DesktopLink)) "UNINSTALL_DESKTOP_LINK_RESIDUE"
    Assert-Condition (-not (Test-Path -LiteralPath $RegPath)) "UNINSTALL_REGISTRY_RESIDUE"
    Assert-Condition (@(Get-ChildItem -Path $env:TEMP -Filter $TempPattern -File -ErrorAction SilentlyContinue).Count -eq 0) "UNINSTALL_TEMP_RESIDUE"

    Write-Host "FROZEN_INSTALLER_E2E_OK version=$ExpectedVersion"
}
finally {
    if (Test-Path -LiteralPath $Root) {
        Remove-Item -LiteralPath $Root -Recurse -Force -ErrorAction SilentlyContinue
    }
}
