# WO-P1-697 — SF-WEB-5: Service packaging

Issue: #697
Status: IMPLEMENTATION (root-GLM author after subagent quota exhaustion)
Risk: R2 (additive service configs, no runtime changes)
Topology: CONTROL_PLANE_ONLY (AWC)

## Scope
All files additive under packaging/ (new directory):
- packaging/systemd/sunday-web.service (Linux/Pi systemd unit)
- packaging/launchd/com.a-sunday.conductor.web.plist (macOS launchd)
- packaging/windows/install-service.ps1 (Windows service wrapper script)
- packaging/umbrel/manifest.yaml (Umbrel app manifest)
- packaging/README.md (install instructions per platform)
- tests/test_packaging.py (validate configs)
- docs/work-orders/WO-P1-697-sfweb5-packaging.md (this file)

## Approach
Configuration-only: generate service definition files for each platform.
No runtime code changes. No actual installation (requires per-OS access).
The web API is started via `a-conductor-web web` CLI command on each platform.
