# ZCode `config.json` lock recovery runbook

Use this runbook when ZCode reports errors such as:

- `EPERM: operation not permitted, rename ...tmp -> ...\.zcode\v2\config.json`
- `Timed out ... waiting for the ZCode file lock`
- `EEXIST ... config.json.lock`
- provider/model/session refresh repeatedly fails or reconnects

## Confirm before changing anything

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\diagnose_zcode_config_lock.ps1
```

The script is read-only. It never prints `config.json` contents and never kills a process.

## Incident proven on 2026-09-03

ZCode itself was not the only process touching the file. Windows Restart Manager identified a Desktop Commander Node.js process as the active holder of `%USERPROFILE%\.zcode\v2\config.json`. A broad Desktop Commander content search had traversed the live `.zcode\v2` directory while ZCode was performing atomic provider-config writes.

That combination caused this sequence:

1. external tool holds `config.json`;
2. ZCode writes `config.json.<pid>.<nonce>.tmp`;
3. Windows refuses the atomic rename to `config.json` with `EPERM`;
4. concurrent ZCode calls wait on `config.json.lock` and eventually time out;
5. provider/session UI appears degraded or reconnecting.

## Safe recovery order

1. Stop or finish any broad search/read operation targeting `.zcode\v2`.
2. Run the diagnostic script and record the exact locking PID(s).
3. Identify the PID before any stop. If it is Desktop Commander, verify its executable/process identity; stop only that exact child PID. Never broad-kill `node.exe`.
4. Re-run the diagnostic. Require `ZCODE_CONFIG_LOCK=UNLOCKED` before touching any stale lock/temp artifact.
5. Validate JSON without printing it:

```powershell
Get-Content "$HOME\.zcode\v2\config.json" -Raw | ConvertFrom-Json | Out-Null
```

6. Check the current ZCode log for new `EPERM`, `config.json.lock`, or file-lock timeout errors.
7. Only if all ZCode processes are intentionally closed and ownership is proven absent may an actually stale `config.json.lock` directory or orphan temp file be removed. Never delete these blindly while ZCode is running.

## Prevention rule

**Do not use recursive/broad content-search tooling on `%USERPROFILE%\.zcode\v2` while ZCode is running.** This includes Desktop Commander search operations over the whole directory.

For diagnostics, prefer one of these bounded patterns:

- read a single known log/config file directly;
- use `Select-String` against one known log file;
- copy the needed file to a temporary snapshot and search the snapshot;
- use `scripts/diagnose_zcode_config_lock.ps1` to identify file ownership.

Never search or index the whole live ZCode state directory merely to find one key/value. Avoid exposing credential-bearing config content in tool output, logs, commits, or chat.

## Verification from the 2026-09-03 repair

After the exact Desktop Commander child was stopped:

- exclusive `ReadWrite` + `FileShare.None` open succeeded;
- no `config.json.lock` directory remained;
- no `config.json.*.tmp` files remained;
- JSON parsing passed;
- no new lock/rename errors were seen in the following verification window.

See `docs/work-orders/WO-P1-153-zcode-config-lock-incident.md` and `DEFECT_LESSONS.md` lesson #51.
