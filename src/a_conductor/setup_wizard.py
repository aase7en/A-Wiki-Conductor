"""Setup Wizard engine — one-stop dependency installer (Windows).

Checks what's installed, downloads/installs missing prerequisites (uv,
Python 3.13, Serena, tunnel-client), and creates the first connector
instance from embedded templates so new users can get running in one flow.
All network/subprocess operations are injectable for testing.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable

from .instance_runtime import _ps_quote

DownloadFn = Callable[[str, str], None]
RunFn = Callable[..., subprocess.CompletedProcess]

UV_GITHUB_API = "https://api.github.com/repos/astral-sh/uv/releases/latest"
TUNNEL_CLIENT_API = "https://api.github.com/repos/openai/tunnel-client/releases/latest"
UV_INSTALL_DIR_NAME = "uv"
TUNNEL_CLIENT_DIR_NAME = "dwb-serena-tunnel-starter"


class SetupWizardError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)


def _default_download(url: str, dest: str) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "A-Sunday-Conductor-Setup"})
    with urllib.request.urlopen(request, timeout=60) as response:
        Path(dest).write_bytes(response.read())


def _default_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=300, **kwargs)


# --- System checks ---------------------------------------------------------


def check_system(
    *,
    tunnel_client_path: Path | None = None,
) -> dict[str, bool]:
    """Check which prerequisites are already installed."""
    result: dict[str, bool] = {}

    # uv: on PATH or in the wizard's install location
    result["uv"] = shutil.which("uv") is not None or _find_uv() is not None

    # Python 3.13: uv can manage it (check via `uv python list` is slow;
    # check the uv-managed python dir instead)
    uv_dir = _uv_install_dir()
    python_dir = uv_dir / "python"
    result["python_313"] = python_dir.is_dir() and any(
        d.name.startswith("3.13") for d in python_dir.iterdir() if d.is_dir()
    ) if python_dir.is_dir() else False

    # Serena: on PATH or via `uv tool list` (fast check: `serena --version`)
    result["serena"] = shutil.which("serena") is not None

    # tunnel-client: at the standard starter path or the given path
    if tunnel_client_path is not None:
        result["tunnel_client"] = tunnel_client_path.is_file()
    else:
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        default_tc = (
            Path(local_app_data) / "Programs" / "A-Conductor" / TUNNEL_CLIENT_DIR_NAME
            / "tunnel-client" / "tunnel-client.exe"
        ) if local_app_data else None
        legacy_tc = Path("C:/AI") / TUNNEL_CLIENT_DIR_NAME / "tunnel-client" / "tunnel-client.exe"
        result["tunnel_client"] = (
            (default_tc is not None and default_tc.is_file()) or legacy_tc.is_file()
        )

    return result


def _uv_install_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        return Path(local_app_data) / "Programs" / UV_INSTALL_DIR_NAME
    return Path.home() / ".local" / UV_INSTALL_DIR_NAME


def _find_uv() -> Path | None:
    candidate = _uv_install_dir() / "uv.exe"
    if sys.platform == "win32" and candidate.is_file():
        return candidate
    posix_candidate = _uv_install_dir() / "uv"
    if posix_candidate.is_file():
        return posix_candidate
    return None


# --- Installer ---------------------------------------------------------------


class Installer:
    """Download and install prerequisites with injectable operations."""

    def __init__(
        self,
        *,
        download_fn: DownloadFn | None = None,
        run_fn: RunFn | None = None,
        uv_path: Path | None = None,
    ) -> None:
        self._download = download_fn or _default_download
        self._run = run_fn or _default_run
        self._uv_path = uv_path or _find_uv()

    def _uv(self) -> Path:
        if self._uv_path is not None and self._uv_path.is_file():
            return self._uv_path
        found = shutil.which("uv")
        if found:
            return Path(found)
        raise SetupWizardError("UV_NOT_FOUND")

    def install_uv(self) -> Path:
        """Download uv.exe from GitHub releases and place it in the install dir."""
        install_dir = _uv_install_dir()
        install_dir.mkdir(parents=True, exist_ok=True)
        dest = install_dir / "uv.exe"

        if dest.is_file():
            return dest

        # Query GitHub API for the latest uv release
        request = urllib.request.Request(
            UV_GITHUB_API, headers={"User-Agent": "A-Sunday-Conductor-Setup"}
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))

        # Find the Windows x86_64 asset
        asset_url = None
        for asset in data.get("assets", []):
            name = asset.get("name", "")
            if "x86_64-pc-windows-msvc" in name and name.endswith(".zip"):
                asset_url = asset.get("browser_download_url")
                break

        if not asset_url:
            raise SetupWizardError("UV_ASSET_NOT_FOUND", "no windows x86_64 zip in latest release")

        zip_path = install_dir / "uv-download.zip"
        self._download(asset_url, str(zip_path))

        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.namelist():
                if member.endswith("uv.exe"):
                    dest.write_bytes(zf.read(member))
                    break

        zip_path.unlink(missing_ok=True)
        if not dest.is_file():
            raise SetupWizardError("UV_INSTALL_FAILED", "uv.exe not found after extraction")
        return dest

    def install_python(self) -> bool:
        """Run `uv python install 3.13`."""
        uv = self._uv()
        result = self._run([str(uv), "python", "install", "3.13"])
        return result.returncode == 0

    def install_serena(self) -> bool:
        """Run `uv tool install -p 3.13 serena-agent`."""
        uv = self._uv()
        result = self._run([str(uv), "tool", "install", "-p", "3.13", "serena-agent"])
        return result.returncode == 0

    def install_nodejs(self) -> Path | None:
        """Install Node.js LTS portable (ZIP, no admin) if not already present.

        Downloads the Windows x64 ZIP from nodejs.org, extracts to
        %LOCALAPPDATA%/Programs/nodejs/, and returns the node.exe path.
        Returns None if Node.js is already on PATH.
        """
        # Check if node is already available
        existing = shutil.which("node")
        if existing:
            return Path(existing)

        install_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "nodejs"
        if not install_dir.parent.exists():
            install_dir = Path.home() / ".local" / "nodejs"

        node_exe = install_dir / "node.exe"
        if node_exe.is_file():
            return node_exe

        # Download the latest LTS Windows x64 ZIP
        # Use the stable URL pattern from nodejs.org
        url = "https://nodejs.org/dist/v22.14.0/node-v22.14.0-win-x64.zip"
        zip_path = install_dir / "node-download.zip"
        install_dir.mkdir(parents=True, exist_ok=True)

        try:
            self._download(url, str(zip_path))
        except SetupWizardError:
            raise
        except Exception as exc:
            raise SetupWizardError("NODEJS_DOWNLOAD_FAILED", str(exc)[:100])

        # Extract and find node.exe
        try:
            import zipfile

            with zipfile.ZipFile(zip_path, "r") as zf:
                for member in zf.namelist():
                    if member.endswith("node.exe"):
                        # Extract the entire tree preserving relative paths
                        zf.extractall(install_dir)
                        # node.exe is inside a versioned subfolder
                        for candidate in install_dir.rglob("node.exe"):
                            if candidate != node_exe:
                                # Move the whole versioned dir contents up
                                versioned_dir = candidate.parent
                                for item in versioned_dir.iterdir():
                                    target = install_dir / item.name
                                    if not target.exists():
                                        shutil.move(str(item), str(target))
                                versioned_dir.rmdir()
                                break
                        break
        except zipfile.BadZipFile:
            raise SetupWizardError("NODEJS_ZIP_INVALID")

        zip_path.unlink(missing_ok=True)

        if not node_exe.is_file():
            raise SetupWizardError("NODEJS_INSTALL_FAILED", "node.exe not found")
        return node_exe

    def check_nodejs(self) -> bool:
        """Quick check: is Node.js available?"""
        return shutil.which("node") is not None or self._find_nodejs() is not None

    def _find_nodejs(self) -> Path | None:
        install_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "nodejs"
        candidate = install_dir / "node.exe"
        if candidate.is_file():
            return candidate
        return None
        return result.returncode == 0

    def install_tunnel_client(
        self, *, target_dir: Path | None = None
    ) -> Path:
        """Download tunnel-client from openai/tunnel-client GitHub releases."""
        if target_dir is None:
            local_app_data = os.environ.get("LOCALAPPDATA", "")
            base = Path(local_app_data) if local_app_data else Path.home()
            target_dir = base / "Programs" / "A-Conductor" / TUNNEL_CLIENT_DIR_NAME / "tunnel-client"
        target_dir.mkdir(parents=True, exist_ok=True)

        exe_path = target_dir / "tunnel-client.exe"
        if exe_path.is_file():
            return exe_path

        # Query GitHub API
        request = urllib.request.Request(
            TUNNEL_CLIENT_API,
            headers={
                "User-Agent": "A-Sunday-Conductor-Setup",
                "Accept": "application/vnd.github+json",
            },
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))

        # Find the Windows amd64 asset
        asset_url = None
        checksums_url = None
        for asset in data.get("assets", []):
            name = asset.get("name", "")
            if "windows-amd64" in name and name.endswith(".zip"):
                asset_url = asset.get("browser_download_url")
            if name == "SHA256SUMS.txt":
                checksums_url = asset.get("browser_download_url")

        if not asset_url:
            raise SetupWizardError(
                "TUNNEL_CLIENT_ASSET_NOT_FOUND", "no windows-amd64 zip in latest release"
            )

        zip_path = target_dir / "tunnel-client-download.zip"
        self._download(asset_url, str(zip_path))

        # Verify SHA256 if checksums available
        if checksums_url:
            checksums_path = target_dir / "SHA256SUMS.txt"
            try:
                self._download(checksums_url, str(checksums_path))
                expected = _find_checksum(checksums_path, zip_path.name)
                if expected:
                    actual = hashlib.sha256(zip_path.read_bytes()).hexdigest()
                    if actual.lower() != expected.lower():
                        zip_path.unlink(missing_ok=True)
                        raise SetupWizardError("TUNNEL_CLIENT_SHA256_MISMATCH")
            except SetupWizardError:
                raise
            except Exception:
                pass  # checksum verification best-effort

        # Extract
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(target_dir)
        zip_path.unlink(missing_ok=True)

        if not exe_path.is_file():
            # Maybe the zip has a subdirectory
            for f in target_dir.rglob("tunnel-client.exe"):
                if f != exe_path:
                    shutil.move(str(f), str(exe_path))
                    break

        if not exe_path.is_file():
            raise SetupWizardError("TUNNEL_CLIENT_INSTALL_FAILED", "exe not found after extraction")
        return exe_path


def _find_checksum(checksums_path: Path, filename: str) -> str | None:
    try:
        for line in checksums_path.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1].lstrip("*") == filename:
                return parts[0]
    except OSError:
        pass
    return None


# --- First Instance Creator ---------------------------------------------------


class FirstInstanceCreator:
    """Create the very first connector instance from embedded templates.

    Unlike instance_create.py (which clones from an existing reference),
    this generates everything from scratch so the FIRST instance can be
    created on a fresh machine with no prior setup.
    """

    def __init__(self, *, instances_root: Path | str) -> None:
        self._root = Path(instances_root).resolve(strict=False)

    def create(
        self,
        *,
        name: str = "sunday-worker-1",
        project_path: Path | str,
        health_port: int = 18011,
        tunnel_client_path: Path | str,
        api_key_file: Path | str,
        backend: str = "serena",
    ) -> Path:
        slug = name.strip().lower()
        if not re.match(r"^[a-z0-9][a-z0-9-]*$", slug):
            raise SetupWizardError("NAME_INVALID", slug)
        target = self._root / slug
        if target.exists():
            raise SetupWizardError("NAME_ALREADY_EXISTS", slug)

        project = Path(project_path)
        if not project.is_absolute() or not project.is_dir():
            raise SetupWizardError("PROJECT_NOT_FOUND", str(project))

        display = slug.title()
        instance_name = f"Sunday-Worker-1"
        profile = f"serena-{slug}"

        for folder in ("profiles", "config", "run", "logs", "serena-home"):
            (target / folder).mkdir(parents=True, exist_ok=True)

        # instance.ps1
        ps1 = "\n".join([
            f"# {instance_name} instance configuration",
            f"$InstanceName = '{_ps_quote(instance_name)}'",
            f"$ProjectPath = '{_ps_quote(str(project))}'",
            f"$SerenaHome = '{_ps_quote(str(target / 'serena-home'))}'",
            f"$HealthListenAddress = '127.0.0.1:{health_port}'",
            f"$TunnelProfileName = '{_ps_quote(profile)}'",
            f"$TunnelClientPath = '{_ps_quote(str(tunnel_client_path))}'",
            f"$LegacySecretPath = '{_ps_quote(str(api_key_file))}'",
        ])
        (target / "instance.ps1").write_text(ps1 + "\n", encoding="utf-8", newline="\r\n")

        # start.ps1 (mirrors the validated layout)
        start = f"""$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
. (Join-Path $Root 'instance.ps1')

$ConfigDir = Join-Path $Root 'config'
$ProfilesDir = Join-Path $Root 'profiles'
$RunDir = Join-Path $Root 'run'
$LogsDir = Join-Path $Root 'logs'
$TunnelIdPath = Join-Path $ConfigDir 'tunnel-id.txt'
$ProfileTemplate = Join-Path $ProfilesDir '{profile}.yaml.template'
$RuntimeProfile = Join-Path $RunDir '{profile}.yaml'
$PidFile = Join-Path $RunDir 'tunnel-client.pid'
$LogFile = Join-Path $LogsDir ('{slug}-' + (Get-Date -Format 'yyyyMMdd') + '.log')
$RuntimeStdout = Join-Path $LogsDir '{slug}-runtime.stdout.log'
$RuntimeStderr = Join-Path $LogsDir '{slug}-runtime.stderr.log'

function Write-Log([string]$Message) {{
    $line = ('{{0}} [{{1}}] {{2}}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $InstanceName, $Message)
    Write-Host $line
    Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8
}}

function Fail([string]$Code, [string]$Message) {{
    Write-Log ("{{0}}: {{1}}" -f $Code, $Message)
    exit 1
}}

New-Item -ItemType Directory -Force -Path $RunDir, $LogsDir, $SerenaHome | Out-Null

if (-not (Test-Path -LiteralPath $TunnelClientPath -PathType Leaf)) {{
    Fail 'CONFIG_NOT_FOUND' "tunnel-client not found: $TunnelClientPath"
}}
if (-not (Test-Path -LiteralPath $LegacySecretPath -PathType Leaf)) {{
    Fail 'CONFIG_NOT_FOUND' "credential not found: $LegacySecretPath"
}}
if (-not (Test-Path -LiteralPath $ProjectPath -PathType Container)) {{
    Fail 'PROJECT_PATH_NOT_FOUND' $ProjectPath
}}
if (-not (Test-Path -LiteralPath $TunnelIdPath -PathType Leaf)) {{
    Fail 'CONNECTOR_CONFIGURATION_REQUIRED' "Create $TunnelIdPath"
}}

$TunnelId = (Get-Content -Raw -LiteralPath $TunnelIdPath).Trim()
if ($TunnelId -cnotmatch '^tunnel_[0-9a-f]{{32}}$') {{
    Fail 'TUNNEL_ID_MISSING' 'Tunnel ID is missing or invalid.'
}}

$env:CONTROL_PLANE_API_KEY = [System.Text.Encoding]::UTF8.GetString(
    [System.Security.Cryptography.ProtectedData]::Unprotect(
        [System.IO.File]::ReadAllBytes($LegacySecretPath),
        $null,
        [System.Security.Cryptography.DataProtectionScope]::CurrentUser
    )
)

$profileContent = Get-Content -Raw -LiteralPath $ProfileTemplate
$profileContent = $profileContent.Replace('__TUNNEL_ID__', $TunnelId)
[System.IO.File]::WriteAllText($RuntimeProfile, $profileContent, (New-Object System.Text.UTF8Encoding($false)))

Write-Log "STARTING: health=$HealthListenAddress project=$ProjectPath"

$RuntimeProcess = Start-Process -FilePath $TunnelClientPath `
    -ArgumentList @('run', '--profile-file', $RuntimeProfile, '--pid.file', $PidFile) `
    -NoNewWindow -PassThru `
    -RedirectStandardOutput $RuntimeStdout `
    -RedirectStandardError $RuntimeStderr

Write-Log "READY: waiting for tunnel-client"
Wait-Process -Id $RuntimeProcess.Id
"""
        (target / "start.ps1").write_text(start, encoding="utf-8", newline="\r\n")

        # stop.ps1
        stop = f"""$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
. (Join-Path $Root 'instance.ps1')

$PidFile = Join-Path $Root 'run' 'tunnel-client.pid'

if (-not (Test-Path -LiteralPath $PidFile)) {{
    Write-Host "NOT_RUNNING"
    exit 0
}}

$pidText = (Get-Content -Raw -LiteralPath $PidFile).Trim()
$existingPid = 0
if ([int]::TryParse($pidText, [ref]$existingPid)) {{
    $proc = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
    if ($proc) {{
        Stop-Process -Id $existingPid -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }}
}}

Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
Write-Host "STOPPED"
"""
        (target / "stop.ps1").write_text(stop, encoding="utf-8", newline="\r\n")

        # cmd wrappers
        start_cmd = (
            "@echo off\r\n"
            f"title Sunday-works 1 - {display}\r\n"
            "setlocal\r\n"
            "cd /d \"%~dp0\"\r\n"
            "powershell.exe -NoProfile -ExecutionPolicy Bypass -File start.ps1\r\n"
            "if errorlevel 1 (\r\n  echo.\r\n  pause\r\n)\r\n"
        )
        (target / f"Start-{instance_name}.cmd").write_text(start_cmd, encoding="utf-8", newline="")

        stop_cmd = (
            "@echo off\r\n"
            f"title Sunday-works 1 - Stop\r\n"
            "setlocal\r\n"
            "cd /d \"%~dp0\"\r\n"
            "powershell.exe -NoProfile -ExecutionPolicy Bypass -File stop.ps1\r\n"
        )
        (target / f"Stop-{instance_name}.cmd").write_text(stop_cmd, encoding="utf-8", newline="")

        # profile template — backend-aware
        project_fwd = str(project).replace("\\", "/")
        if backend == "filesystem":
            mcp_command = f"npx -y @modelcontextprotocol/server-filesystem {project_fwd}"
        else:
            mcp_command = (
                f"serena start-mcp-server --context chatgpt\n"
                f"      --project {project_fwd}\n"
                f"      --enable-web-dashboard false\n"
                f"      --open-web-dashboard false\n"
                f"      --enable-gui-log-window false"
            )
        template = (
            f"# {instance_name} tunnel profile (backend: {backend})\n"
            f"tunnel_id: __TUNNEL_ID__\n"
            f"api_key: env:CONTROL_PLANE_API_KEY\n"
            f"server:\n"
            f"  listen_addr: 127.0.0.1:{health_port}\n"
            f"mcp:\n"
            f"  commands:\n"
            f"    - >-\n"
            f"      {mcp_command}\n"
        )
        (target / "profiles" / f"{profile}.yaml.template").write_text(
            template, encoding="utf-8", newline="\n"
        )

        # serena_config.yml seed
        serena_config = (
            "language_server:\n"
            "  backend: lsp\n"
            f"projects:\n- '{project}'\n"
        )
        (target / "serena-home" / "serena_config.yml").write_text(
            serena_config, encoding="utf-8", newline="\n"
        )

        return target
