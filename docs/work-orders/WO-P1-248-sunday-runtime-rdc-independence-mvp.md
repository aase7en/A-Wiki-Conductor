# WO-P1-248 — SunDay Runtime / RDC-independence MVP

Date: 2026-09-17
Status: ACTIVE / R3 / RED-FIRST
Owner: GPT-5.6 Sol / SOL-B
Issue: #333
Base: `origin/main@018779d0d2f5a7a7a21adb277e23a617692c36fd`
Branch: `feat/wo-p1-248-sunday-runtime-rdc-independence`
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo248-sunday-runtime`

## User decision / reorder authority

The user explicitly requested urgent work on 2026-09-17 to reduce dependence on paid Remote Desktop Commander, build an owned RDC-equivalent path, and use GLM-5.3 aggressively. This is the explicit user reorder contemplated by the WO247 activation fence. It does not transfer or overlap WO246 / WO205 / WO227 authority.

A-Sunday Conductor remains the sole control plane. SunDay Runtime is an execution substrate only: `execute / observe / cancel / collect evidence`.

## Current evidence

- Protected root checkout is dirty/stale and is not used for mutation.
- This isolated worktree is clean at exact `origin/main`.
- SOL-A owns WO246 and its source lane; this WO does not touch it.
- WO247 / PR #332 remains a separate docs-only SOL-B lane.
- Default global WIP is now full at 3 mutable lanes; do not open another writer.
- Windows has two concurrently live `@wonderwhy-er/desktop-commander@0.2.50 remote` process trees:
  - old tree started 2026-09-16 15:51 local;
  - new tree started 2026-09-17 10:40 local;
  - both have ESTABLISHED TCP/443 relay connections.
- Persisted Remote Desktop Commander config exposes one device id; secret/session values were not read.
- Dashboard last-seen timing aligns with the new process tree.
- Upstream local DesktopCommanderMCP package `0.2.50` is MIT licensed; hosted Remote Desktop Commander relay implementation is proprietary and must not be copied.

## Goal

Deliver a local-first SunDay Runtime MVP that replaces ordinary Remote MCP file/search/command traffic for A-Conductor while preserving existing Conductor authority and security boundaries.

P0 is local RDC independence. P1 self-hosted remote transport is shaped but not implemented by this source batch.

## Reuse / ownership rules

REUSE:
- `NativeExecutionScope`
- `NativeFileSystem`
- `NativeSubprocessRunner`
- supervised execution / recovery primitives
- Git as exact repo/worktree/branch/HEAD truth

WRAP:
- pinned MIT `@wonderwhy-er/desktop-commander@0.2.50` as optional compatibility adapter only

DO NOT COPY:
- proprietary hosted Remote Desktop Commander service implementation
- hosted billing/account/quota service
- OAuth/session relay internals not present in the MIT repository

DO NOT CREATE:
- scheduler
- task store
- claim/lease authority
- provider registry
- retry/review/completion authority
- global mutable Active Project state

## Exact mutable tracked scope

- `docs/work-orders/WO-P1-248-sunday-runtime-rdc-independence-mvp.md`
- NEW `src/a_conductor/sunday_runtime.py`
- NEW `src/a_conductor/desktop_commander_adapter.py`
- NEW `tests/test_sunday_runtime.py`
- NEW `tests/test_desktop_commander_adapter.py`
- NEW `src/a_conductor/sunday_remote_protocol.py`
- NEW `src/a_conductor/sunday_remote_bridge.py`
- NEW `tests/test_sunday_remote_protocol.py`
- NEW `tests/test_sunday_remote_bridge.py`

P1 expansion was explicitly published in Issue #333 after the P0 freeze; it remains the same mutable WO248 lane and does not increase global mutable WIP.

Everything else is read-only unless a new explicit gate is published.

In particular, this WO forbids mutation of:
- WO246 / WO205 / WO227 owned files;
- `execution_record.py`, `execution_store.py`, `supervised_run_coordinator.py`, `zcode_production_assembly.py`, `zero_relay_repair_materializer.py`;
- scheduler/job/provider/lease/review/GoalCloseout authority;
- shared continuity files;
- Desktop Commander credential/session files;
- proprietary Remote Desktop Commander code;
- merge/deploy/release.

## Runtime contract

### Lane binding

Each runtime request carries immutable:
- repo root;
- worktree root;
- branch;
- exact HEAD;
- claim id.

Before any operation, runtime re-observes actual Git identity. Any mismatch returns fail-closed `CONTEXT_DRIFT` and performs no operation.

### File operations

Use `NativeFileSystem` inside the bound worktree root.
- read/list are allowed when context is valid;
- mutation is allowed only when the caller supplies a scope with mutation authority;
- absolute paths and root escape remain forbidden;
- overwrite keeps existing SHA-256 precondition semantics.

### Search

Use an allowlisted `rg` argv through `NativeSubprocessRunner`.
- no shell;
- cwd is bound to the worktree;
- query is an argv element, not shell text;
- search output is bounded by existing runtime limits;
- broad searches of live `%USERPROFILE%\.zcode\v2` are outside the bound repo and therefore impossible.

### Commands

P0 exposes no generic raw-shell API.
Only explicitly constructed allowlisted argv specs may run through existing native execution primitives.

### DesktopCommander compatibility adapter

The adapter:
- pins package identity to `@wonderwhy-er/desktop-commander@0.2.50`;
- can report whether the pinned local package is available;
- can construct local stdio launch argv for future compatibility use;
- must not select the proprietary hosted `remote` mode by default;
- must fail closed on unexpected package/version/configuration.

P0 intentionally did not implement the remote transport. P1 adds a self-hosted transport owned by this repository; it does not copy the proprietary hosted RDC relay.

### P1 self-hosted remote bridge

The bridge:
- signs every request with HMAC-SHA256 using a caller-supplied secret that is never persisted by the bridge;
- enforces timestamp freshness plus bounded request-id/nonce replay protection;
- exposes typed operations only: context verify, bounded file read/list/create/write, bounded text search, and already-allowlisted argv execution;
- delegates all filesystem/command/context authority to the bound `SunDayRuntime`; it cannot mint mutation authority or bypass `CONTEXT_DRIFT`;
- has no raw-shell operation; unknown operations fail closed;
- provides a standard-library HTTP listener that binds loopback by default; non-loopback plaintext bind requires explicit opt-in because HMAC authenticates but does not encrypt;
- is intended to sit behind a separately-authorized encrypted tunnel/reverse proxy for actual remote-device use;
- owns no scheduler/task/claim/provider/review/retry/completion/merge/project-memory authority.

This establishes the self-hosted RDC-independent transport seam without introducing a second control plane.

## Duplicate Remote-agent incident gate

The old 2026-09-16 process tree may be stopped only after:
1. Issue #333 exists;
2. both old and new exact trees are re-identified;
3. the new tree still has a healthy ESTABLISHED relay connection;
4. only the old root process tree is terminated;
5. new tree is rechecked healthy afterward.

Never broad-kill `node.exe`.

Stopping the duplicate is runtime cleanup, not proof of billing reduction. Tool-call attribution remains an evidence question.

## RED acceptance matrix

1. exact binding accepts matching repo/worktree/branch/HEAD/claim.
2. branch mismatch => `CONTEXT_DRIFT`.
3. HEAD mismatch => `CONTEXT_DRIFT`.
4. worktree mismatch/outside repo => `CONTEXT_DRIFT`.
5. read/list work only inside the bound root.
6. search uses allowlisted `rg`, no shell, bounded cwd.
7. mutation forbidden scope cannot write.
8. DesktopCommander adapter pins exact package/version.
9. adapter local argv never contains `remote`.
10. unexpected package/version fails closed.
11. no touched file outside the exact nine-path WO248 scope (P0 five paths + P1 four new paths).
12. targeted + related tests, compileall, diff-check, UTF-8, secret scan pass.
13. exact candidate receives independent GLM-5.3 read-only review after fresh approved CoinTH quota/readiness preflight.
14. exact-head hosted CI passes.
15. Sol performs final acceptance; author lane does not self-merge without authority.

## GLM offload

`GLM_OFFLOAD_ASSESSMENT=BENEFICIAL`.

Long/mechanical work should route to Kilo + `cointh-glm/glm-5.3` after fresh approved quota/readiness evidence. Before each material dispatch, refresh the five-hour tuple. `QUOTA_UNKNOWN` is not `RATE_LIMITED`; no bypass or silent provider substitution.

## Mutation gate

At claim time:
- task/claim identity exists as Issue #333;
- exact worktree/branch/HEAD is known;
- P0 was frozen before P1; the P1 expansion owns only four new transport source/test paths plus this WO doc, for nine total WO248 paths, with no WO246 overlap;
- protected root is untouched;
- global WIP is at, not above, its 3 mutable lane maximum.

`SAFE_TO_MUTATE_WO248_SCOPE=YES` only for the exact nine paths above under the published P0 + P1 gates.
`SAFE_TO_MUTATE_FOREIGN_SOURCE=NO`.


## P1 security hardening checkpoint

Exact-head adversarial review found a real concurrent replay race because `ThreadingHTTPServer` shared one unlocked replay window. A deterministic two-thread RED test demonstrated duplicate acceptance (`accepted`, `accepted`). The bounded repair makes replay check+record atomic with a lock.

The same hardening batch also:
- rejects non-bytes-like bridge secrets instead of allowing `bytes(32)`-style predictable zero-key coercion;
- bounds request id, nonce, and operation identity text to 128 characters before replay-cache insertion;
- serializes remote mutation operations (`fs.create`, `fs.write`, and mutation-intent allowlisted commands) while retaining parallel read/search execution.

RED evidence: 5 new adversarial cases failed before the repair (3 unbounded identity fields, integer secret coercion, concurrent mutation overlap), plus the concurrent replay race was proven separately. GREEN evidence after repair: 37 WO248 tests passed; 80 related native/supervised/transport regression tests passed; compileall and diff-check passed.

Fresh CoinTH quota preflight through the approved A-Wiki resolver returned HTTP 403 on 2026-09-17. Classify GLM material dispatch as `AUTH_REQUIRED / ENTITLEMENT_MISMATCH`, not rate-limited; do not bypass or silently substitute a provider.
