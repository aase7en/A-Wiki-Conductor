# Runbook — Continue A-Sunday Conductor Zero-Relay work on a Mac without installed Workers

Status: ACTIVE OPERATIONAL RUNBOOK
Applies to: home macOS host while primary Windows A-Conductor host is offline
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

### WO-P1-168 — GPT-6 Astra

Owns only the Mac Claude harness compatibility repair and its declared tests/WO/evidence.
Do not edit or reset its worktree.

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

## 5. Gate A — Claude invocation compatibility

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
| WO168 compatibility repair | ACTIVE / UNACCEPTED | WO168 |
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
