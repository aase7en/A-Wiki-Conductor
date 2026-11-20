# SF-WEB-5: Service Packaging

Install the A-Sunday Conductor Web API as a system service on each platform.

## Prerequisites
- A-Sunday Conductor installed (`pip install a-conductor` or packaged installer)
- `a-conductor-web` executable available in PATH

## Linux / Raspberry Pi (systemd)

```bash
sudo cp packaging/systemd/sunday-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sunday-web
sudo systemctl start sunday-web
```

## macOS (launchd)

```bash
sudo cp packaging/launchd/com.a-sunday.conductor.web.plist /Library/LaunchDaemons/
sudo launchctl load /Library/LaunchDaemons/com.a-sunday.conductor.web.plist
```

## Windows (Scheduled Task)

Run PowerShell as Administrator:
```powershell
.\packaging\windows\install-service.ps1
```

To uninstall:
```powershell
.\packaging\windows\install-service.ps1 -Uninstall
```

## Umbrel

Copy `packaging/umbrel/` to your Umbrel apps directory and install via the Umbrel UI.

## Verification

After installation, check: `curl http://127.0.0.1:8756/api/v1/health`

The API binds to 127.0.0.1 only. For remote access, see SF-WEB-7.
