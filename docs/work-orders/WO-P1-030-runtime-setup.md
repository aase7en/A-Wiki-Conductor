# WO-P1-030: Runtime Setup Service + Desktop Dialog

Status: in_progress
Lane/files: `src/a_conductor/runtime_setup.py`, `src/a_conductor/desktop_control.py`, `src/a_conductor/desktop_ui.py`, `src/a_conductor/__init__.py`, `tests/test_runtime_setup.py`, `tests/test_desktop_ui.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-030-runtime-setup.md`
Branch: main
Model tier: high

## Goal

Provide a safe Runtime Setup workflow for each A-Worker and its assigned project. Persist only non-secret runtime paths/ports/opaque refs, register local reference-file metadata without reading its content, and capture exact Git branch/HEAD read-only for project identity.

## Acceptance

- tests first / RED before implementation;
- setup view shows CONFIGURED/UNCONFIGURED without reading reference values;
- worker defaults propose isolated `a-worker-01..03` roots and health ports 18011..18013 but do not persist until Save;
- Save Worker Setup persists `SerenaWorkerConfig` with worker-owned home/run/log paths under selected instance root;
- optional tunnel reference stores opaque reference ID + local file path + allowed root only;
- setup service never reads tunnel/reference file content;
- exact Git identity capture uses fixed read-only Git runner and stores exact root/branch/HEAD binding;
- explicit NO_GIT binding is available for non-Git projects;
- lifecycle readiness requires assignment + worker config + project binding + registered tunnel ref metadata when tunnel is required;
- desktop adds Setup button/dialog; no secret/tunnel value field exists;
- desktop lifecycle Start is disabled when selected stopped worker is not setup-ready;
- setup dialog exposes paths/port/reference IDs only and supports Save + Capture Exact Project Identity;
- no process/tunnel provisioning is triggered by Setup;
- full suite + compileall + diff/static secret-field scan pass.

## Forbidden

- No tunnel ID/API key/credential value field in UI.
- No reading reference file content in setup service.
- No Git mutation/network.
- No process lifecycle action from Setup dialog.
- No remote/push.

## Checkpoint log

- [2026-08-20] Opened after desktop lifecycle wiring close commit; worktree clean.
