# Runbook — Continue A-Sunday Conductor Zero-Relay across the Mac -> Windows handoff

Status: ACTIVE OPERATIONAL RUNBOOK / WINDOWS RETURN PREPARED
Applies to: home macOS recovery host and the next Windows 11 primary-host resume
Related: Issue #233, WO-P1-168, WO-P1-169

## Purpose

Continue the highest-priority GPT <-> GLM Zero-Relay work safely from repository source
without requiring Serena, Sunday Worker 1-5, ZCode, or an installed A-Conductor desktop app.

This runbook does not grant mutation authority. Repository/claim/worktree gates still apply.

## 1. Recovery sequence

Always start with:

1. read `00-AGENT-ENTRY.md`;
2. read `PROJECT-GRAPH.yaml`;
3. read `AGENTS.md`;
4. fetch origin;
5. verify repo/worktree/branch/HEAD/dirty state;
6. inspect active worktrees and claims;
7. read the active WO and relevant Issue #233 checkpoints;
8. classify scope overlap before mutation.

Actual Git/GitHub/runtime state outranks chat memory and stale global projections.

## 2. Current ownership split

### WO-P1-168 — R4 frozen corrective lane

R0 candidate `654e36d...` merged as `577d948...`, then later real-host security evidence
reopened the compatibility/settings boundary. R1/R2/R3 are frozen CHANGES_REQUIRED
history. Current successor is draft PR #242 / candidate
`7d0fd83bb5608a4ab025d5000203cbad2a31831f` in
`/Users/aase7en/Desktop/A-Wiki-Conductor-wo168-r4`.

R4 preserves provider isolation and project/local deny rules, closes the bounded filesystem
identity boundary, rejects duplicate decoded JSON keys, and bounds Windows command-line
quoting. Exact-head CI `34440601328` is SUCCESS across Windows/full, Ubuntu and macOS.
The remaining R3 gate is a truly independent exact-SHA reviewer; Codex/Astra and a fresh
Codex reviewer are currently quota-blocked. Do not merge or open WO170 source mutation
until that review passes and post-main verification completes.

### WO-P1-169 — GPT-5.6 Sol

Documentation/continuity only:
- this runbook;
- Mac host migration incident record;
- WO169 checkpoint.

### GPT integrator

Retains:
- trust/architecture adjudication;
- exact-SHA independent acceptance;
- merge/release;
- Zero-Relay milestone truth.

GLM is not yet automatically dispatched on this Mac.

## 3. What is NOT required yet

Do not install these merely to repair or review the current source compatibility problem:
- Serena;
- Sunday Worker fleet;
- ZCode;
- full A-Conductor desktop application.

They may become later deployment/runtime tasks, but they are not prerequisites for
repository-level WO168 work.

## 4. Secret contract

Private key role:
`A-Wiki-Data/secrets/global.env`

Credential reference:
`secret-ref:awiki-env/COINTH_GLM_AUTH_TOKEN`

Runtime mapping:
`ANTHROPIC_AUTH_TOKEN`

Endpoint:
`https://cointh.com/glm/anthropic`

Model:
`glm-5.3`

Rules:
- never print/read back the value for diagnosis;
- never put it in argv/prompt/task/result/Git/GitHub/logs;
- use presence/identity/hash-safe checks only;
- use the existing A-Wiki environment reference resolver at the execution boundary;
- historical exposed key material is invalid for production use.

## 5. Gate A — Claude invocation compatibility — R4 FROZEN / REVIEW_BLOCKED

Required before any live provider task:
- current WO168 defect reproduced deterministically;
- repaired invocation accepted by installed CLI;
- no automatic fallback to a weaker security profile;
- customization isolation proven;
- read-only/plan/tool restrictions preserved;
- task packet/system binding preserved;
- settings/user override defect does not regress;
- secret/base-url binding unchanged;
- exact SHA frozen and independently reviewed.

Do not accept a timeout as GREEN.

## 6. Gate B — supervised process portability

After Gate A, re-check actual production call path.

Current main evidence shows the canonical supervised native adapter resolver constructs
Windows-specific process/observer/PowerShell components. Until a macOS/POSIX equivalent
is accepted, do not claim that the full production A-Conductor supervision stack runs on
this Mac.

A direct `NativeSubprocessRunner` or raw Claude command may be useful for diagnostics,
but cannot silently replace the accepted production supervision authority for the final
Zero-Relay proof.

If a POSIX adapter is needed, create a separate bounded R3 work order. Reuse the existing:
- execution store;
- supervised execution semantics;
- identity/dedup/recovery contract;
- environment allowlist;
- provider authority.

Do not create a second scheduler, job store, claim/lease authority, retry engine, or
parallel process-lifecycle authority.

## 7. Gate C — isolated authenticated one-shot

Only after invocation + supervision gates are accepted:

Use:
- isolated/sacrificial DB/state;
- synthetic read-only task packet;
- unique deterministic marker;
- no tracked repository writes;
- no patient/hospital/personal data;
- no unnecessary repository source sent to the external provider.

Required evidence:
- exact task ID/SHA;
- exact repo/worktree/HEAD;
- provider profile + endpoint + model identity;
- admission/authority identity where required;
- process identity and terminal cleanup;
- canonical result ID/SHA;
- secret-confinement scan;
- `git status` before/after;
- no live DB mutation.

Success label only if a real authenticated GLM-5.3 turn returns through the accepted path:
`GPT_GLM_ZERO_RELAY_ONE_SHOT = PROVEN`.

## 8. Negative cases before success

Fail closed on at least:
- missing secret reference;
- invalid secret reference;
- endpoint drift;
- model/provider mismatch;
- task SHA mismatch;
- missing task packet;
- result identity mismatch;
- unsupported CLI capability;
- process identity/recovery ambiguity.

Do not burn provider quota on redundant negative tests when a deterministic local test is
sufficient.

## 9. Problem ledger

| Item | State | Authority |
| --- | --- | --- |
| old chat continuity | MITIGATED | Issue #233 + private session memory |
| Mac repo up to date | PROVEN at migration checkpoint | Git |
| Cointh endpoint reachable | PROVEN unauthenticated only | HTTP 401/missing_key |
| rotated secret reference present | PROVEN presence only | private env resolver audit |
| Claude 2.1.152 rejects --safe-mode | PROVEN | real Mac CLI RED |
| WO168 compatibility repair | R4 FROZEN / EXACT-HEAD CI SUCCESS / INDEPENDENT REVIEW BLOCKED | PR #242 + Issue #233 |
| full supervised process path on macOS | OPEN | current-main source audit |
| authenticated GLM turn on Mac | NOT PROVEN | future isolated proof |
| GPT <-> GLM zero human relay | NOT PROVEN | future canonical result proof |
| Serena/Workers/A-Conductor desktop install | DEFERRED | not prerequisite for current source work |

## 10. Closeout discipline

For every completed gate persist:
- work order/status;
- branch/HEAD/worktree;
- changed scope;
- deterministic evidence;
- unresolved defects;
- owner/claim;
- exact next safe action.

Do not hand-edit `CURRENT-WORK.md`, `handoff.md`, or `COLLAB.md` from competing lanes.
Use the accepted single-writer/fold path when it becomes operational.

A model saying DONE is not completion authority.


## 11. Proposed next R3 contract — POSIX/macOS supervised-process portability

Status: SHAPED / BLOCKED_BY_WO168_R4_REVIEW / NO SOURCE AUTHORITY IN THIS DOCS LANE.

Fresh current-main architecture audit after the WO168 merge shows the portability gap is
narrower than a new supervisor:

Reusable authority already exists:
- `OwnedProcessSpec` and the existing process-ownership classifier;
- `SupervisedExecutionService` consumes injected controller/observer protocols;
- durable execution store and execution identity;
- `SupervisedRunCoordinator` dedup/inspect/collect semantics;
- `SupervisedCommandRunner` and Claude provider/task authority above it;
- generic native execution/file safety primitives.

Windows binding is concentrated in:
- process spawner/terminator defaults in `owned_process.py`;
- `WindowsRuntimeObserver`;
- `StrictPowerShellInspectionRunner`;
- `build_supervised_native_adapter_resolver()` production composition.

Therefore the preferred classification is `EXTEND / WRAP`, not NEW.

### Required design invariants

A later R3 implementation should preserve the existing higher-level authority and add only
the minimum POSIX/macOS process facts needed by the same protocols:

1. spawn an exact owned helper without a shell and with a dedicated process/session identity;
2. persist PID metadata atomically through the existing contract;
3. observe PID existence + executable identity + required profile marker from actual OS facts;
4. never signal a PID/process group until ownership is proven;
5. stale PID, reused PID, missing command-line identity or observation failure must fail closed;
6. terminate only the exact owned process/session, with bounded TERM -> verified-exit ->
   narrowly authorized KILL escalation;
7. preserve existing durable execution IDs, CAS/version checks, inspect/collect/recovery,
   output bounds/redaction and environment allowlists;
8. transport loss must never release execution ownership;
9. no second scheduler/store/lease/retry/review/process-lifecycle authority;
10. production assembly selects a platform adapter explicitly and unknown platforms fail closed.

### Minimum RED/fault matrix

Before source repair, independently reproduce:
- current Mac production assembly attempts Windows observer/PowerShell composition;
- stale PID file;
- live foreign PID;
- PID reuse/mismatched executable;
- correct executable but missing profile marker;
- observer cannot prove command line;
- TERM returns but process remains alive;
- process exits between observe and terminate;
- helper exits before PID persistence;
- PID persistence fails after child start;
- restart/reattach to a still-running exact-owned helper;
- descendant-held stdout/stderr handles cannot make terminal result ambiguous;
- no broad kill or name-based kill under any failure.

### Acceptance boundary

A generic `NativeSubprocessRunner` smoke is diagnostic only. The final macOS Zero-Relay
proof must use the canonical supervised execution/identity/recovery path.

Host proof should use a disposable helper and temporary SQLite/runtime directory first.
Real provider credential use is a later gate and is not required to accept POSIX process
ownership itself.

Next durable work item after WO168 R4 closes:
`Mac/POSIX supervised-process adapter + production composition`, R3, isolated worktree,
RED-first, with GPT trust framing and independent exact-SHA review.


## 12. Windows 11 primary-host resume — prepared handoff

The next session should treat Windows 11 as the primary execution host and Sunday-Worker
1-5 as available capacity only after each worker is individually re-pinned. Do not assume
that a worker is free from its name or project alone.

GitHub handoff facts at this checkpoint:
- `origin/main` remains `577d9483720c857a89a5d2c9ea9359f9c0aa50b5`;
- full R4 source is already pushed on `gpt/wo-p1-168-r4-settings-file-boundary`;
- frozen R4 candidate / PR #242 head is `7d0fd83bb5608a4ab025d5000203cbad2a31831f`;
- exact-head CI `34440601328` is SUCCESS on Windows/full, Ubuntu and macOS;
- merge is intentionally blocked only by the independent R3 review requirement.

Windows resume order:
1. enter `A:\GitHub\A-Wiki-Conductor`; read `00-AGENT-ENTRY.md`, `PROJECT-GRAPH.yaml`,
   `AGENTS.md`, actual Git state, `CURRENT-WORK.md`, then Issue #233 + WO168;
2. `git fetch --all --prune`; update local `main` with fast-forward only; preserve any dirty
   or untracked work and stop on unexpected divergence;
3. inspect Sunday-Worker 1-5 actual process/readiness/task/worktree/branch/HEAD/dirty/claim
   state before assigning anything;
4. choose one genuinely free Worker for an independent READ-ONLY exact-SHA review of PR
   #242 at `7d0fd83...`; it must not edit/commit/merge;
5. if the reviewer returns P0=0/P1=0/P2=0 and identity matches, GPT integrator marks the PR
   ready and merges with expected-head fencing; otherwise open only a bounded successor;
6. verify exact merge ancestry/tree and post-main CI; only then pull `main` again on Windows
   and later fast-forward the Mac checkout to converge both hosts;
7. after WO168 closes, resume the Zero-Relay critical path. Because Windows already has the
   accepted Windows supervision stack, re-audit whether the Mac POSIX portability lane is
   still on the immediate critical path before opening it.

Do not delete old Mac worktrees/branches during the host handoff. They are retained as
evidence until accepted merge/closeout proves cleanup is safe.
