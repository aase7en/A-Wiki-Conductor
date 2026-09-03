# WO-P1-153 — ZCode config lock incident recovery

Date: 2026-09-03
Owner: GPT-5.6 Sol / SunDay-Worker 1-2
Status: COMPLETE / VERIFIED
Priority: P1 operational reliability
Repository: `A:\GitHub\A-Wiki-Conductor`
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo153-zcode-config-lock`
Branch: `fix/wo-p1-153-zcode-config-lock`
Base: `origin/main@1ae477f05e597c5027d22fdb2ca4f1496c070db7`

## Incident
ZCode repeatedly failed provider/session refresh with `EPERM` atomic-rename errors and file-lock timeouts on `%USERPROFILE%\.zcode\v2\config.json`.

## Root cause
Windows Restart Manager identified PID 15728, `node.exe`, command identity `@wonderwhy-er/desktop-commander`, as the process holding `config.json` open. A prior broad Desktop Commander content search traversed `.zcode\v2` while ZCode was concurrently writing provider configuration. This created real cross-process file-handle contention; ZCode's temporary-file rename could not replace `config.json`, then its own lock acquisition timed out.

## Recovery performed
- Verified `config.json` was locked by an external process and had no stale `config.json.lock` directory or `.tmp` files at final recovery time.
- Verified PID 15728 identity before stopping only that Desktop Commander child process; no broad Node/ZCode kill was used.
- After stop, exclusive `ReadWrite/None` open of `config.json` succeeded.
- JSON parse succeeded; SHA-256 after recovery: `667D46E834FACE92D2C753788217BA89DB761E6E2AF4684568058C07EABF8D9C`.
- ZCode log showed no new `EPERM` / config-lock errors from 22:10 through the 22:20 verification window.

## Mutable scope
- `AGENTS.md`
- `DEFECT_LESSONS.md`
- `docs/runbooks/zcode-config-lock.md`
- `scripts/diagnose_zcode_config_lock.ps1`
- this work order

## Acceptance
1. Durable root-cause lesson records symptom → cause → fix → prevention → verification.
2. Agent entry rules forbid recursive/broad search over live `.zcode\v2` state.
3. A read-only diagnostic script identifies unlocked/locked state and Windows locking PIDs without printing config contents or secrets.
4. Runbook defines safe targeted recovery and explicitly forbids broad process kills or blind deletion of lock/temp files.
5. Script runs successfully on this host and returns `UNLOCKED` after recovery.

## Forbidden
No ZCode credential/config content may be copied into Git. No broad `node.exe`/`ZCode.exe` termination. No deletion of lock/temp state without proving it is stale. No destructive Git.


## Verification checkpoint — 2026-09-03 22:32 +07:00
- Live diagnostic: `ZCODE_CONFIG_LOCK=UNLOCKED`, `JSON_PARSE=OK`.
- Live ZCode state: `config.json.lock` absent; `config.json.*.tmp` count = 0.
- ZCode log after 22:10: 0 new matches for `EPERM`, `config.json.lock`, or `waiting for the ZCode file lock` through 22:32.
- Synthetic lock test: diagnostic correctly reported `LOCKED`, one exact PowerShell holder, and exited 2 without killing or modifying the file.
- Recovery preserved config content secrecy; only integrity/hash/state evidence was observed.
