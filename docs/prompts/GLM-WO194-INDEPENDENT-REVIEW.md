# GLM / ZCode — WO-P1-194 independent exact-SHA review

## /goal

Independently review the frozen WO-P1-194 candidate for the legacy Sunday Worker launcher forensics hardening.

Do not implement, amend, commit, merge, or deploy from this review lane.

The implementation author is GPT-5.6 Sol. You are the independent GLM-5.3 MAX / ZCode reviewer.

## Cold start

Read in this order:

1. `00-AGENT-ENTRY.md`
2. routed task-relevant nodes from `PROJECT-GRAPH.yaml`
3. `AGENTS.md`
4. `docs/work-orders/WO-P1-194-legacy-launcher-forensics-hardening.md`
5. `docs/work-orders/WO-P1-192-worker-runtime-selfheal.md`
6. `docs/work-orders/WO-P1-156-worker-mcp-resilience.md`
7. relevant defect-memory/runbook sources routed by the project graph

Then re-pin actual repository, branch, HEAD, origin/main, dirty state, PR head, CI, ownership/claim state, and review assignment.

The exact candidate SHA is the SHA explicitly assigned in the durable PR/Issue review checkpoint. If the worktree/PR head differs, stop with `CANDIDATE_MOVED` and do not review a moving target.

## Review scope

Primary source/test scope:

- `src/a_conductor/instance_create.py`
- `tests/test_instance_create.py`
- WO194 documentation and this review packet only for contract interpretation

Everything else is read-only unless needed as reference.

Do not mutate:

- live `C:\AI\serena-instances\**`
- Worker processes/PIDs/ports
- live Control Center DB
- credentials/DPAPI/tunnel secrets
- ZRA-3 / WO191
- ZRA-4 product source
- shared continuity files

## Review question

Does the exact candidate safely harden both accepted legacy launcher shapes without corrupting credential/preflight/cleanup semantics or creating a new runtime/recovery authority?

Accepted legacy terminal shapes are:

1. `Wait-Process -Id $RuntimeProcess.Id`
2. the actual Sunday Worker shape:

```powershell
try {
    ...
    $RuntimeProcess.WaitForExit()
    if ($RuntimeProcess.ExitCode -ne 0) {
        Fail 'TUNNEL_START_FAILED' "Tunnel client exited with code $($RuntimeProcess.ExitCode)."
    }
}
finally {
    ...cleanup...
}
```

The candidate should only rewrite a launcher when identity markers are unambiguous.

## Mandatory adversarial checks

Review source and tests, then independently exercise or reason through at least these cases:

1. live method-wait shape hardens;
2. prior Wait-Process shape still hardens;
3. method-wait inside `try/finally` preserves indentation;
4. cleanup lines after the terminal block remain byte/ordering compatible;
5. DPAPI/tunnel/project/doctor/environment content is not replaced or logged;
6. runtime stdout/stderr are archived before a new run can overwrite them;
7. `WaitForExit()` precedes `Refresh()`;
8. exit code is captured once into `$RuntimeExitCode` after terminal wait/refresh;
9. normal exit records `exit_code=0`;
10. failure records the numeric exit code;
11. the old terminal `if ($RuntimeProcess.ExitCode -ne 0)` branch does not survive after hardening;
12. startup-time `HasExited`/preflight logic elsewhere is not accidentally removed;
13. helper is byte-idempotent after first hardening;
14. already-hardened input remains unchanged;
15. missing stdout/stderr/STARTING marker returns unchanged;
16. multiple recognized terminal waits return unchanged;
17. malformed method-wait block returns unchanged rather than partial rewrite;
18. duplicate stdout/stderr assignment ambiguity fails closed;
19. CRLF-normalized input remains compatible with create_instance output;
20. no second watchdog/retry/recovery authority is introduced.

Pay special attention to regex overmatch across nested PowerShell braces and to any path where archive insertion could occur before the terminal seam is proven safe.

## Required verification

At minimum run, without modifying the candidate:

```text
python -m pytest -q tests/test_instance_create.py
python -m pytest -q tests/test_setup_wizard.py tests/test_ps1_encoding_and_quoting.py tests/test_doctor_fixes.py
python -m compileall -q src/a_conductor
git diff --check <base>..<candidate>
```

Also inspect hosted CI for the exact PR head when available.

If useful, perform a read-only in-memory proof against the five current `start.ps1` files, but never write them. Do not print secret/config values; report only boolean structural findings.

## Findings policy

Classify every material finding as P0/P1/P2/P3.

Any P0/P1 => `CHANGES_REQUIRED`.

Do not call a stylistic preference a blocking finding.

A finding must include:

- severity;
- exact file/line or symbol;
- deterministic reproducer or concrete counterexample;
- impact;
- smallest repair direction.

If no blocking defects are found, state why the regex/identity boundary is sufficiently fail-closed and why cleanup/preflight semantics remain protected.

## Result destination

Write the durable review result to:

`runs/WO-P1-194/glm-independent-review.md`

and post a concise verdict checkpoint to the WO194 Draft PR or its durable GitHub issue if one is assigned.

Required final fields:

- `REVIEWED_SHA`
- `BASE_SHA`
- `VERDICT=ACCEPT|CHANGES_REQUIRED|CANDIDATE_MOVED|BLOCKED`
- `P0_COUNT`
- `P1_COUNT`
- `P2_COUNT`
- `P3_COUNT`
- test commands/results
- CI identity/status
- findings with deterministic evidence
- residual risk
- exact next safe action

Do not merge, release, deploy, or self-author a repair from this review packet.
