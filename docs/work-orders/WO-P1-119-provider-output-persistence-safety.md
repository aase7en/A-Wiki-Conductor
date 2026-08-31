# WO-P1-119 — Provider Output Persistence Safety

Date: 2026-08-31
Proposed owner: GPT-5.6 Sol Ultra
Status: READY_FOR_CLAIM / UNCLAIMED
Repository: `aase7en/A-Wiki-Conductor`
Priority: P1 before any credential-bearing unattended provider canary

## Goal

Ensure provider subprocess output is sanitized before any durable log/artifact persistence. A secret echoed by a child process must never land in raw stdout/stderr files and only then be redacted on return.

## Evidence

Ultra R5 was source-confirmed by the integrator:
- `WindowsProcessSpawner.spawn()` opens durable `stdout_path` / `stderr_path` and gives those handles directly to `subprocess.Popen`;
- `ClaudeCodeSupervisedRunner.run()` resolves credential-bearing environment values, then calls the native/supervised runner;
- `_redact()` is applied only to the returned `NativeCommandResult.stdout/stderr` after the child has already written through the owned-process output files.

Classification: `WRAP + EXTEND` the accepted supervised/owned-process boundary. Do not weaken subprocess ownership, timeout, cancellation or bounded-output guarantees.
## Allowed scope

- `src/a_conductor/claude_code_supervised_runner.py`
- the smallest necessary supervised capture / `owned_process.py` boundary if RED proves it is required
- focused tests for subprocess capture, timeout, cancellation and artifact bytes
- this WO only; shared SSoT remains integrator-owned

## Forbidden scope

- provider config/admission/policy semantics
- worker/elastic files
- broad process lifecycle redesign or broad process termination
- real credentials/live provider probes
- new artifact store or machine-wide environment mutation

## RED-first acceptance

1. A controlled child echoes a fake secret to stdout and stderr; the sentinel is absent from every durable file/artifact and returned diagnostic.
2. Fragmented/chunked secret output, exception/error and timeout paths are also sanitized before persistence.
3. Sanitization never writes plaintext first and scrubs later.
4. Output caps, cancellation, exact descendant/process ownership and crash cleanup remain correct.
5. Non-secret subprocess output remains available with expected forensic fidelity.
6. Focused supervised-runner/owned-process regressions, compileall, diff/scope/secret audit pass.
7. Exact-SHA independent review + 3-OS CI before merge.
## Concurrency

This lane may run in parallel with WO-P1-117 and WO-P1-120 because source ownership is disjoint. If RED requires `supervised_command_runner.py` or another shared lifecycle file, stop and return `SCOPE_REOPEN_REQUIRED` rather than editing outside this contract.
