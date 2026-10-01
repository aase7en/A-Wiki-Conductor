# WO-P1-575 — A-Sidecar Phase 2 synthetic-envelope hardening

Issue: #575
Predecessor: #573 / PR #574
Topology: CONTROL_PLANE_ONLY
Risk: R3
Status: BOOTSTRAP_BOUND / SOURCE_MUTATION_PENDING_FULL_GATE
Claim: WO-P1-575-SIDECAR-HARDENING-MAC-001
Worktree: /Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo575-sidecar-hardening
Branch: feat/wo-p1-575-sidecar-hardening
Base HEAD: 6c4bcdfebfde29990f92b7b76670830009ba6753

## 1. Goal

Harden the accepted A-Sidecar Phase 2 bridge at synthetic/in-process envelope
boundaries without changing the accepted A-Relay v1 authority model or inventing
new protocol semantics.

The source slice addresses the remaining nonblocking review findings carried
forward from #573:

1. carrier-equivalent evidence-ref rejection for unsafe Unicode categories,
   PEM markers, and secret-token-shaped synthetic refs;
2. typed fail-closed CREATED_AT validation for manually constructed synthetic
   envelopes in checkpoint recovery and steer selection;
3. preserve the intentional ACK-vs-projected v1 limitation without adding a
   marker or completion/approval semantic;
4. reconcile the historical #573 WO checkpoint as documentation only.

## 2. Authority and trust boundary

- A-Conductor remains the only task/claim/WIP/retry/review/merge/completion authority.
- A-Relay remains evidence transport only.
- The bridge remains pure projection/selection/receipt logic over caller-injected
  facts/transport; it does not become a scheduler, store, retry engine, approval
  authority, or completion authority.
- No raw Codex SQLite/session/thread-writer-lock mutation.
- No private IPC dependency.
- No arbitrary command execution.
- No secret-bearing relay payloads.
- Foreign-device paths remain opaque strings; do not normalize them.

## 3. Exact lane identity

- repository: aase7en/A-Wiki-Conductor
- worktree: /Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo575-sidecar-hardening
- branch: feat/wo-p1-575-sidecar-hardening
- base: 6c4bcdfebfde29990f92b7b76670830009ba6753
- claim: WO-P1-575-SIDECAR-HARDENING-MAC-001

Any repo/worktree/branch/HEAD/claim mismatch fails closed before mutation.

## 4. Scope

### 4.1 Bootstrap slice

NEW only:
- docs/work-orders/WO-P1-575-a-sidecar-phase2-hardening.md

Everything else is read-only until this bootstrap is committed and the full
source mutation gate is rerun.

### 4.2 Source slice after full gate

Allowed:
- src/a_conductor/sidecar_codex_bridge.py
- tests/test_sidecar_codex_bridge.py
- docs/work-orders/WO-P1-575-a-sidecar-phase2-hardening.md
- docs/work-orders/WO-P1-573-a-sidecar-phase2-codex-bridge.md
  (docs-only final checkpoint/accepted-main evidence; no source semantics)
- .agents/skills/a-sidecar/SKILL.md
  (user-directed Desktop-binding recovery lesson only; no authority expansion)

Forbidden:
- src/a_conductor/sidecar_relay.py
- docs/contracts/a-sidecar-relay-v1.md
- CURRENT-WORK.md
- handoff.md
- COLLAB.md
- #498/#549/#551/#526 owned hotspots
- provider/config/credential/runtime mutation

Any required edit outside the allowed list is SCOPE_EXPANSION_REQUIRED.

## 5. Failure model / required behavior

### A. Synthetic evidence refs

Bridge-side validation must reject before observe/submit/append:
- unsafe Unicode category text;
- PEM/private-key markers;
- credential/secret-token-shaped refs;
- existing invalid URL/padding/length/duplicate cases.

Use the accepted carrier's validation semantics as the parity source without
weakening the carrier or leaking secret-bearing text into errors. Keep the
existing bridge failure taxonomy unless deterministic evidence proves a
contract mismatch.

### B. Synthetic CREATED_AT

Manually constructed envelopes with malformed CREATED_AT must fail with a typed,
stable relay/bridge validation error before ordering or transport invocation.
No raw TypeError/ValueError may escape from:
- recover_checkpoint chronology/filter paths;
- select_steer_candidate ordering paths;
- the full projection path that consumes those candidates.

Valid aware ISO-8601 timestamps, including different offsets representing
different instants, must remain deterministic.

### C. ACK-vs-projected v1 limitation

No behavior change in this WO. Do not add a new v1 marker, receipt field, or
completion semantic. Record the limitation; a future semantic change requires
an explicit versioned contract decision.

### D. Codex Desktop successor-thread binding

A thread created or read through a separately spawned Codex App Server may be
durable without being loaded into the Codex Desktop conversation runtime. The
observed operational signature is an `ACTIVE` Schedule targeting the correct
thread while Desktop reports
`Conversation state not found conversationId=<thread-id>` and the target
rollout does not progress.

The durable recovery lesson in `.agents/skills/a-sidecar/SKILL.md` must require:
- supported Desktop deep-link load/resume via `codex://threads/<thread-id>`;
- no raw SQLite/session/lock edits, lock stealing, or broad process restarts;
- verification that the actual Desktop-managed App Server owns the writer lock;
- verification that rollout activity and intended model/reasoning settings
  survive Desktop resume;
- Goal + Schedule target/cadence revalidation; and
- one real post-idle scheduled heartbeat/continuation before declaring the
  migrated Schedule end-to-end proven.

The invariant is:
`THREAD_DURABLE != DESKTOP_LOADED != SCHEDULE_PROVEN`.

## 6. RED / adversarial matrix

Before implementation, add or confirm focused RED cases covering:
- secret-token-shaped evidence refs;
- PEM marker refs;
- Cc/Cf/Co unsafe Unicode refs;
- malformed CREATED_AT: non-string, invalid ISO, naive timestamp, padded value,
  unsafe text, and overlong input;
- mixed aware/naive checkpoint chronology;
- malformed steer CREATED_AT before transport use;
- transport call count remains zero on preflight validation failure;
- valid safe refs and aware timestamp ordering remain green.

## 7. Verification

During implementation:
- focused RED/GREEN subset first;
- python3 -m pytest -q tests/test_sidecar_codex_bridge.py
- python3 -m pytest -q tests/test_sidecar_relay.py tests/test_control_events.py tests/test_lifecycle_journal.py tests/test_work_order_identity.py
- python3 -m py_compile src/a_conductor/sidecar_codex_bridge.py tests/test_sidecar_codex_bridge.py
- git diff --check
- strict UTF-8 / LF / no U+FFFD / no trailing whitespace
- A-Sidecar skill text contains the Desktop-binding failure signature, supported
  deep-link recovery, writer/runtime verification, and
  `THREAD_DURABLE != DESKTOP_LOADED != SCHEDULE_PROVEN`

Before acceptance:
- exact candidate SHA frozen;
- independent exact-SHA R3 review by a reviewer that did not author the candidate;
- hosted exact-head CI;
- expected-head guarded merge;
- post-main tree/CI verification.

## 8. Routing

GLM_OFFLOAD_ASSESSMENT is recorded once on Issue #575.
Preferred bounded author: GLM-5.3 MAX after the full source gate.
Preferred independent reviewer: a separate GLM-5.3 MAX execution when admitted.

Immediately before every material GLM request:
- perform one fresh CoinTH quota preflight under docs/runbooks/cointh-glm-quota.md;
- no separate provider smoke request;
- preserve durable EXEC_ID evidence;
- recover/harvest before any retry.

GPT/Sol retains trust framing, claim/scope authority, fan-in, acceptance and merge.

## 9. Completion

Complete only when:
- source/test/docs scope is exact;
- deterministic verification is green;
- independent exact-SHA review has no blocking P0/P1/P2;
- hosted CI is green on the accepted head;
- merge tree preserves the accepted candidate;
- post-main CI is green;
- #573 historical checkpoint is reconciled;
- claim is released and #575 is durably closed with exact evidence.

## 10. Supervisor revalidation checkpoint — 2026-10-01

- Live `origin/main` remains `6c4bcdfebfde29990f92b7b76670830009ba6753`; PR #574 is merged and post-main verified.
- Bound lane: `/Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo575-sidecar-hardening`, branch `feat/wo-p1-575-sidecar-hardening`, HEAD `62cd57b860805c3e8cb4aac40cab1720c575e911`.
- Tracked source/test files are unchanged. A local documentation-only correction removed the extra blank line at EOF; `git diff --check <base>` passes for the current worktree. Preserve the pre-existing untracked `.kilo/` directory.
- Sunday recovery found 215 executions, all terminal and harvested (153 COMPLETED, 42 CANCELLED, 20 FAILED); no live or unharvested lane remains. The prior #575 GLM execution is terminal `PLAN_ONLY`, has no identity-verified binding, and produced no source diff. Do not replay it; any later useful request needs a new exact binding and must pass the current pre-dispatch guard.
- The source defects remain visible at `_invalid_evidence_ref`, `recover_checkpoint`, and `select_steer_candidate`; this checkpoint did not modify production source or tests.
- Current A-Audit: `HUMAN_REQUIRED`. The source task is a bounded R3 repair, but current global WIP admission is not proven from a current accepted A-Faster marker, and the mandatory continuity checkpoint paths are owned by another dirty lane. The older `FANOUT_TARGET=0` / `AUTO_REFILL_REQUIRED=false` markers do not authorize a new refill.
- The #498 worktree currently has tracked edits to both `CURRENT-WORK.md` and `handoff.md`; this WO forbids modifying those paths. Repo policy requires checkpointing them before delegating. Do not dispatch or start source mutation until the owner releases those paths or an explicit ownership/scope reconciliation establishes a safe checkpoint path.
- Next safe action: recheck the exact #498 ownership/continuity release and canonical WIP evidence, then rerun the #575 identity/scope gate and task-bound A-Audit. Proceed to a new GLM-5.3 MAX author request only if the continuity and pre-dispatch gates admit it; keep the existing claim, scope, and `.kilo/` material intact.
