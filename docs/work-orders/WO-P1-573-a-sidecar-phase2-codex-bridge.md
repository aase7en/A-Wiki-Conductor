# WO-P1-573 — A-Sidecar Phase 2 Codex Bridge

Issue: #573
Parent: #568 / PR #569 (Phase 0 contract) + #570 / PR #571 (Phase 1 carrier)
Topology: CONTROL_PLANE_ONLY (bootstrap slice and later source slice)
Risk: R3
Status: BOOTSTRAP DOC BOUND / SOURCE_MUTATION_PENDING_FULL_GATE
Claim: WO-P1-573-SIDECAR-BRIDGE-MAC-001
Worktree: /Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo573-sidecar-phase2-impl
Branch: feat/wo-p1-573-sidecar-codex-bridge
Base HEAD: e6eea89fc363c9eaff9e53d8c9a01659997ae25a
Shaping evidence: exec-munygh9a-f1j5jfmc (GLM-5.3 Flash, exit 0, harvested)
A-Audit disposition: STRONG_REVIEW

## 1. Goal

Make the accepted Phase 0 contract/skill and Phase 1 carrier practically usable
together as the smallest executable integration: a fresh ordinary ChatGPT
session invokes `Use A-Sidecar`, recovers durable A-Relay events, and through
supported Desktop-managed Codex App Server/native queue APIs projects one
eligible `CODEX_STEER_REQUEST` as a pointer-only steer or reads one
result/checkpoint, then emits a typed receipt — with no new authority.

The bridge is a pure projection/receipt module. A-Conductor remains sole
task/claim/WIP/mutation/review/merge/completion authority; A-Relay remains
evidence transport only.

## 2. Topology and risk

- CONTROL_PLANE_ONLY for both slices: this bootstrap (docs) and the later
  source slice stay inside A-Wiki-Conductor. No SunDayRemoteMCP mutation.
- R3 because the bridge touches durable receipt state, replay/idempotency
  semantics, steer-projection fail-closed behavior, and cross-device evidence.
- Loss/corruption of bridge artifacts degrades observability only. Canonical
  task/claim/Git/execution truth stays with existing authorities.
- Accepted integrator decisions folded from shaping (exec-munygh9a-f1j5jfmc)
  are binding for this WO and listed throughout.

## 3. Predecessors (proven base — do not rebuild)

Merged on main before this WO:
- explicit A-Sidecar skill (`.agents/skills/a-sidecar/SKILL.md`);
- A-Relay v1 contract (`docs/contracts/a-sidecar-relay-v1.md`);
- stdlib-only carrier `src/a_conductor/sidecar_relay.py` (PR #571);
- user-proven ordinary ChatGPT -> SundayMCP -> Codex Desktop
  Project/Thread/Goal/Turn/Queue path on macOS + Windows;
- native queue steer into an existing Codex Desktop writer;
- mobile/UI visibility.

## 4. Exact identity

- claim_ref: `WO-P1-573-SIDECAR-BRIDGE-MAC-001`
- worktree: `/Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo573-sidecar-phase2-impl`
- branch: `feat/wo-p1-573-sidecar-codex-bridge`
- base HEAD: `e6eea89fc363c9eaff9e53d8c9a01659997ae25a` (= main after PR #571)
- Any mismatch of worktree/branch/HEAD/dirty state stops the lane with
  `SAFE_TO_MUTATE = NO` before mutation.

## 5. Scope

### 5.1 Bootstrap scope (this slice — R0 docs under the R3 WO)

NEW only:
- `docs/work-orders/WO-P1-573-a-sidecar-phase2-codex-bridge.md` (this file)

Everything else is READ ONLY. One commit, message
`docs: bind A-Sidecar Phase 2 bridge work order`.

### 5.2 Later source scope (same claim/worktree; full gate rerun required)

NEW only:
- `src/a_conductor/sidecar_codex_bridge.py`
- `tests/test_sidecar_codex_bridge.py`
- evidence appendix updates to this WO

Do NOT modify `src/a_conductor/sidecar_relay.py`, the Phase 0 contract, or the
Phase 0 skill in this slice. Any required edit outside the three paths above
is `SCOPE_EXPANSION_REQUIRED` and must stop for integrator reconciliation.

## 6. Reuse map (from shaping; source-backed)

- REUSE `src/a_conductor/sidecar_relay.py` — the bridge reads recovers and
  appends events only through the carrier's public functions
  (read/dedupe/order/append). Unmodified; it remains the only durable store.
- REUSE `docs/contracts/a-sidecar-relay-v1.md` — closed 11-family envelope,
  binding model, §5 ACK = observed-and-folded semantics, §6 bridge
  constraints. No contract v1 expansion in this WO.
- REUSE `.agents/skills/a-sidecar/SKILL.md` — recovery steps, bounded-session
  rollover vocabulary, Codex bridge read-only inspection rules, authority
  floor. Unmodified.
- REUSE `docs/contracts/codex-nightshift-resume-adapter-v1.md` — pointer-only
  bounded payload precedent, fail-closed outcome list, forbidden-field list,
  ambiguous-delivery handling (no blind retry), transport-not-retry-engine.
- REUSE `src/a_conductor/control_events.py` — typed-code-only error
  precedent.
- REUSE `src/a_conductor/delegated_run_artifacts.py` — evidence-pointer
  grammar precedent; no new run store.
- REUSE `src/a_conductor/context_rollover_guard.py` — context-pressure
  vocabulary only.
- REUSE `src/a_conductor/zero_relay_review_execution.py` — execution
  identity/binding precedent only.
- WRAP: the bridge wraps the carrier as its durable event store and wraps
  caller-injected supported Codex API handles as its only Codex seam.
- NEW: exactly one module + one test file (§5.2). Dominant classification is
  REUSE/WRAP; no REPLACE of any shared seam.

## 7. Bridge module constraints (binding design)

- Pure projection/receipt only: the module itself performs no socket, HTTP,
  subprocess, or native IPC operations and never opens, reads, or mutates
  Codex SQLite/session/lock files even read-only.
- All Codex interaction goes through caller-injected transport callables that
  represent supported Desktop-managed Codex App Server/native queue APIs the
  current harness actually exposes. The bridge validates inputs, builds
  pointer-only projection payloads, invokes the injected seam, and emits
  typed receipts/failures; it never discovers or probes the surface itself.
- Codex surface compatibility is caller/WO-declared evidence: the caller
  supplies a surface descriptor (surface kind + version string) plus an
  explicit allowlist/prefix set. Initial proven Desktop-managed App Server
  version on authorized macOS + Windows: `0.158.0-alpha.2.1`. The
  implementation must accept any caller-supplied allowlist/prefix set; it
  must not hard-code a timeless version authority and must not probe private
  storage to verify versions.
- Pointer-only steer projection: the projected payload carries only bounded
  pointers (durable evidence refs, WO path, claim id, next-safe-action
  pointer). Executable/free-form steer body stays at the durable evidence
  refs; the bridge never composes prompts or commands.
- v1 ACK encoding (no contract expansion): the ACK for an observed relay
  event is one normal `SIDECAR_RESULT_RECEIPT` envelope whose
  `EVIDENCE_REFS` includes `relay-event:<original EVENT_ID>` (plus the
  durable destination of any harvested result). ACK means observed and
  folded — never approved, never completed.
- No second scheduler, task store, claim/lease system, retry engine with
  authority, review path, merge or completion state machine.
- No foreign-device path normalization or authority: WORKTREE/path values are
  opaque device-tagged evidence, validated as bounded safe text only.

## 8. Bridge lifecycle

`SIDECAR_CHECKPOINT recovery -> candidate select -> revalidate -> surface
descriptor -> pointer projection -> connector observation ->
SIDECAR_RESULT_RECEIPT -> rollover`

1. **Checkpoint recovery** — read the relay log through the carrier; dedupe
   by EVENT_ID; recover the latest `SIDECAR_CHECKPOINT` binding
   (repo/worktree/branch/HEAD/claim) for this lane. Prior-chat memory is
   never evidence.
2. **Candidate select** — from recovered events, select at most one eligible
   `CODEX_STEER_REQUEST` (or one result/checkpoint read) by deterministic
   per-producer order. Selection is transport choice, not prioritization
   authority.
3. **Revalidate** — rebind the candidate against live durable evidence
   (Git/claim/work-order state). A stale or unbound candidate fails closed;
   the event was never a command.
4. **Surface descriptor** — require the caller-declared surface descriptor
   and allowlist/prefix set; verify the declared version is allowlisted.
   Missing/unverified surface records the typed blocker and degrades to
   Git/GitHub/work-order evidence.
5. **Pointer projection** — build and submit the pointer-only steer payload
   through the injected supported-API seam. Idempotent on the original
   EVENT_ID: a repeated projection of the same event fails typed instead of
   double-submitting.
6. **Connector observation** — observe the target Project/Thread/Goal/Turn/
   queue state read-only through the same injected seam; detect active
   writer and non-steerable targets.
7. **SIDECAR_RESULT_RECEIPT** — emit the receipt (ACK encoding above) through
   the carrier, referencing the original EVENT_ID and durable destinations.
8. **Rollover** — on context pressure: `HARVEST -> VERIFY ->
   SIDECAR_CHECKPOINT -> NEXT_READY` per the skill; the successor re-runs
   recovery from durable evidence only.

## 9. Typed failure taxonomy (BRIDGE_*)

Carrier-side failures keep the existing `RELAY_*` codes. Bridge failures are
code-only, never echo field values, and default to fail-closed (no
projection, no receipt, durable typed blocker recorded):

| Code | Meaning | Default action |
|---|---|---|
| `BRIDGE_SURFACE_UNAVAILABLE` | supported App Server/native queue surface not present on this device/harness | typed blocker; degrade to durable evidence |
| `BRIDGE_SURFACE_VERSION_UNVERIFIED` | declared version missing or not in the caller-supplied allowlist/prefix set | typed blocker; no projection |
| `BRIDGE_SURFACE_OFFLINE` | surface present but the App Server/connector is not reachable through the supported API | typed blocker; degrade |
| `BRIDGE_ACTIVE_WRITER` | target thread already has an active writer | refuse projection; observation only |
| `BRIDGE_DUPLICATE_PROJECTION` | the same original EVENT_ID was already projected | refuse re-submission; idempotent no-op receipt allowed |
| `BRIDGE_AMBIGUOUS_TARGET` | target thread/project identity ambiguous or unresolvable from caller evidence | refuse; no blind retry |
| `BRIDGE_NOT_STEERABLE` | surface exists but does not accept steer/queue submission for this target | typed blocker; no projection |
| `BRIDGE_CONTEXT_PRESSURE` | caller session approaching rollover | emit `CONTEXT_PRESSURE_HIGH`; defer projection |
| `BRIDGE_QUOTA_LIMITED` | target lane capacity constrained (usage/throttle/entitlement) | emit `GPT_WORK_LIMITED`; defer projection |
| `BRIDGE_POINTER_INVALID` | steer candidate lacks the required durable evidence pointers | refuse projection |

An ambiguous projection delivery is never blindly retried; recover durable
thread/execution evidence first (resume-adapter precedent).

## 10. Security boundaries

- No raw Codex SQLite/session/lock access as product behavior, including
  read-only. No arbitrary command execution. No prompt/steer body
  composition — pointers only.
- No secrets, tokens, share URLs, transcripts, argv, or credentials in any
  bridge artifact; carrier sensitive-content rejection stays in force.
- Caller-injected transports are the only executable seam and must correspond
  to supported Desktop-managed APIs; the bridge treats them as untrusted
  I/O and validates all returned text.
- Workspace-context visibility into a Codex thread never grants authority
  over that thread's task, claim, scope, or schedule.
- The bridge adds no provider/config/credential mutation path.

## 11. Mac/Windows, UTF-8, version, durable-first-turn rules

- Every bridge artifact is strict UTF-8, LF-normalized on write, validated on
  read, on both macOS and Windows producers.
- Path values are opaque, device-tagged evidence; never promote one device's
  layout to canonical identity; never resolve a foreign-device path locally.
- Version authority is the caller-supplied allowlist/prefix set per §7;
  initial proven version `0.158.0-alpha.2.1` is recorded as WO evidence, not
  hard-coded truth; no private-storage probing.
- Durable-first-turn: the first turn of any bridge interaction writes a
  durable pointer (work-order checkpoint or run pointer) before depending on
  in-chat context.

## 12. RED/fault matrix (later source slice)

RED-first tests written before the module must cover at least:

1. checkpoint recovery + dedupe by EVENT_ID through the carrier;
2. candidate selection order; at most one projection target per turn;
3. stale/unbound candidate revalidation fails closed;
4. missing descriptor -> `BRIDGE_SURFACE_UNAVAILABLE`;
5. version not allowlisted -> `BRIDGE_SURFACE_VERSION_UNVERIFIED`;
6. connector unreachable -> `BRIDGE_SURFACE_OFFLINE`;
7. active writer -> `BRIDGE_ACTIVE_WRITER`, no projection;
8. repeat projection of same EVENT_ID -> `BRIDGE_DUPLICATE_PROJECTION`;
9. ambiguous thread identity -> `BRIDGE_AMBIGUOUS_TARGET`;
10. non-steerable target -> `BRIDGE_NOT_STEERABLE`;
11. context pressure -> `BRIDGE_CONTEXT_PRESSURE` + `CONTEXT_PRESSURE_HIGH`
    event;
12. quota constrained -> `BRIDGE_QUOTA_LIMITED` + `GPT_WORK_LIMITED` event;
13. steer without durable pointers -> `BRIDGE_POINTER_INVALID`;
14. ACK receipt references original EVENT_ID via EVIDENCE_REFS entry;
15. projection payload is pointer-only (no free-form/executable body);
16. module performs no socket/HTTP/subprocess/native IPC and no raw storage
    access (AST/structural test);
17. no authority-named API surface (AST/structural test);
18. strict UTF-8/LF artifacts and opaque cross-device path handling;
19. related `tests/test_sidecar_relay.py` and Phase 1 related suites remain
    green.

## 13. Mutation gates and GLM-first quota policy

- This bootstrap slice is docs-only under the R3 claim; the later source
  slice must rerun the full mutation gate: exact worktree/branch/HEAD/dirty
  verification against this WO, non-overlap with every active mutable scope,
  DEFECT_LESSONS review, then RED-first implementation.
- Routing: deterministic evidence first; GLM-5.3 Flash = bounded read-only
  recon only; GLM-5.3 MAX = implementation author and independent reviewer
  (separate executions); GPT/Luna = integrator acceptance/merge only.
- Exactly one `GLM_OFFLOAD_ASSESSMENT` for the source slice
  (`DISPATCHED` / `BLOCKED:<typed_reason>` / `NOT_BENEFICIAL:<reason>`).
- One fresh accepted CoinTH quota preflight immediately before each material
  dispatch; no readiness smokes; no manufactured work. Actual GLM use
  requires durable execution evidence (pointer, result, exit state).
- A-Audit disposition: STRONG_REVIEW — independent exact-SHA review is
  mandatory before integrator acceptance.

## 14. Acceptance sequence

1. docs bootstrap: this WO committed alone (exact one-path delta, hygiene
   checks green);
2. full mutation gate rerun for the source slice (identity/overlap/RED plan);
3. RED-first GLM-5.3 MAX author: `tests/test_sidecar_codex_bridge.py`
   written before `src/a_conductor/sidecar_codex_bridge.py`;
4. deterministic tests green: targeted + related (`test_sidecar_relay.py`,
   `test_control_events.py`, `test_lifecycle_journal.py`,
   `test_work_order_identity.py`);
5. freeze exact candidate SHA;
6. independent separate GLM-5.3 MAX read-only review on the frozen SHA;
7. exact-head CI on the frozen SHA;
8. GPT integrator acceptance;
9. expected-head merge (merge only if candidate SHA is unchanged);
10. post-main verification and WO closeout.

## 15. Forbidden / collision scope

Do not modify (any hit stops the lane):
- `src/a_conductor/sidecar_relay.py` and all Phase 0 surfaces
  (`docs/contracts/a-sidecar-relay-v1.md`,
  `.agents/skills/a-sidecar/SKILL.md`, `docs/work-orders/WO-P1-568*`);
- #498 hotspots: `src/a_conductor/pre_dispatch_guard.py`,
  `src/a_conductor/control_hook_adapter.py`, `CURRENT-WORK.md`, `handoff.md`;
- #549/#550 A-Faster auto-refill surfaces;
- #551/#552 claim-reader/task-binding surfaces;
- #526 admission/multi-device surfaces;
- `.codex/hooks/**`; reserved `hook_bus.py` / `hook_stm.py`;
- `control_events.py`, `lifecycle_journal.py`, `worker_lease.py`,
  provider/admission stores, `zero_relay*.py`;
- A-Wiki or SunDayRemoteMCP;
- any live Codex SQLite/session/lock state (read or write).

## 16. Bootstrap verification (this slice)

- only `docs/work-orders/WO-P1-573-a-sidecar-phase2-codex-bridge.md` added;
- strict UTF-8; no CR; LF final newline; no trailing whitespace;
- `git diff --check` clean;
- no secrets/share URLs;
- Issue #573 / claim / base identifiers correct as in §4.

## Checkpoint log (append-only)

- [2026-09-30] GLM-5.3 MAX (Kilo/CoinTH, bootstrap author lane): WO bound
  from Issue #573 + shaping evidence exec-munygh9a-f1j5jfmc; single-file
  docs commit on base e6eea89fc363c9eaff9e53d8c9a01659997ae25a; source
  slice NOT started; full gate rerun required before any source mutation.
- [2026-10-02] WO-P1-575 generation-2 hardening (worktree
  `A-Wiki-Conductor-wo575-sidecar-hardening-g2`, claim
  `WO-P1-575-SIDECAR-HARDENING-MAC-001`) reconciled this historical
  checkpoint as documentation only: the #573 bridge module/tests received
  the #575 §5/§6 synthetic-boundary repairs (carrier-parity evidence-ref
  rejection, typed fail-closed synthetic CREATED_AT validation) inside the
  #575 lane under its own claim. No #573 semantic expansion, no reopen of
  the accepted #573 review, and no further #573 source work is authorized
  here; #573 remains ACCEPTED / POST_MAIN_VERIFIED / COMPLETE.
