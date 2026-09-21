# WO-P1-443 — A-Faster cross-device lifecycle pulses and safe takeover

Status: ACTIVE / CLAIMED
Issue: #443
Risk: R2 — binding routing/continuity governance
Topology: CONTROL_PLANE_ONLY

## Binding
- Authority repo: `aase7en/A-Wiki-Conductor`
- Execution repo: `aase7en/A-Wiki-Conductor`
- Device: `Aase7ens-MacBook-Pro.local` / macOS / RDC
- Worktree: `/Users/aase7en/Desktop/_worktrees/A-Wiki-Conductor-wo443-a-faster-liveness`
- Branch: `docs/wo-p1-443-a-faster-cross-device-liveness`
- Base / bootstrap head: `9a37e02ba833004ddf4317fd39cbf5927cf26d58`
- Claim: `WO-P1-443-A-FASTER-CROSS-DEVICE-LIVENESS-001`
- Owner/integrator: GPT-5.6 Sol
- Evidence carrier: Issue #443 + pushed branch/exact-SHA + existing A-Faster local run pointers

## Goal

Make A-Faster communicate lane lifecycle truth across devices/sessions with timestamps and task-specific freshness bounds so another A-Faster invocation can distinguish active work, intentional waiting/stopping, terminal-unharvested work, completion, and a possible stall without relying on chat memory.

This is an EXTEND of the accepted `docs/agent-collab/EXECUTION_LIVENESS_PROTOCOL.md`, A-Faster durable-lane pointers, and Issue/WO checkpoints. It creates no scheduler, task database, claim/lease system, heartbeat daemon, retry engine, global registry, or second execution state machine.

## Exact mutable scope
- `.agents/skills/a-faster/SKILL.md`
- `.agents/skills/a-faster/references/durable-lanes.md`
- `.agents/skills/a-faster/references/multidevice.md`
- `docs/work-orders/WO-P1-443-a-faster-cross-device-liveness.md`

Everything else is read-only unless a separately accepted finding reopens scope.

## Required behavior

1. Every A-Faster entry assumes another device/session may already own a lane and recovers the latest durable pulse before mutation.
2. Material mutable/delegated lanes publish cross-device lifecycle pulses at least at:
   - `STARTED`;
   - material `PROGRESS`;
   - intentional `WAITING` or `STOPPED`;
   - `TERMINAL_UNHARVESTED`;
   - `COMPLETED` / reconciled terminal.
3. A pulse is a projection/checkpoint only. Existing authoritative job/task state and liveness classes remain authoritative.
4. Pulse fields include lane/run/task/claim/device/repo/worktree/branch/HEAD/scope plus `observed_at`, `started_at`, `last_activity_at`, `last_progress_at`, optional `last_heartbeat_at`, typed reason, replay-safety, evidence destination, exact next safe action, and a task/adapter-specific freshness/stall bound.
5. Activity, progress, heartbeat, and completion stay distinct. Polling/identical logs do not count as progress.
6. No global timeout is introduced. Each lane/adaptor declares a bounded expected activity/heartbeat policy as required by the existing liveness protocol.
7. Crossing the declared time bound produces only a `STALLED`/stall-candidate reconciliation trigger. Time alone never grants replay, cancellation, takeover, or mutation authority.
8. Before takeover/help, the receiving device reconciles exact process/session identity, result/exit/log evidence, Git/worktree state, claim/ownership and replay safety. An explicit handoff or proof that the prior mutable owner is no longer active is required.
9. A takeover publishes a new cross-device pulse with old/new device identity and binding-digest delta. A previously stopped/stale device that resumes must census/collision-check first and yield to the valid current owner.
10. GitHub Issue/WO checkpoint is the durable cross-device carrier. Device-local `runs/` remains detailed evidence and must be folded before cleanup. If the carrier is unavailable, record typed `PULSE_CARRIER_UNAVAILABLE`, do not claim publication, and block handoff/takeover/cleanup that depends on the missing fold until it succeeds.
11. Plain ChatGPT is not claimed to self-wake or continuously poll after a turn ends. The next invocation reconstructs truth; an accepted external/runtime heartbeat source may provide evidence but never authority by itself.
12. Global WIP remains `3 mutable + 1 independent read-only review`; `1 MUTABLE HOTSPOT = 1 MUTATION OWNER`.

## Pulse projection vocabulary

Pulse labels are communication events, not a new state machine:

- `STARTED` — lane began or an authorized takeover/continuation started.
- `PROGRESS` — a material task milestone advanced.
- `WAITING` — owner remains known while waiting on a typed dependency.
- `STOPPED` — the current executor/session intentionally ceased work without claiming completion; include replay-safety and next action.
- `TERMINAL_UNHARVESTED` — executor attempt ended and result/evidence still requires harvest.
- `COMPLETED` — accepted/reconciled lane outcome is terminal for the claimed scope.
- `TAKEOVER_STARTED` — new device/session has passed takeover gates and is now the mutable owner.

Each pulse also carries the existing `liveness_class`; the two concepts must not be conflated.

## Freshness / stall projection

- Reuse `last_activity_at`, `last_progress_at`, and optional `last_heartbeat_at` from the liveness protocol.
- Record `stall_policy` in a bounded, task-specific form (for example an expected activity or heartbeat interval); never invent one global timeout.
- When the bound is deterministically computable, record `recheck_after_at` / `stall_candidate_after_at` as convenience projections only.
- Expired freshness means `RECONCILE_REQUIRED`, not `SAFE_TO_TAKEOVER=YES`.
- A bare old timestamp or stale PID is never proof that an owner is gone.

## Current global-WIP / collision checkpoint at bootstrap

- WO433 source candidate has merged to `main@9a37e02ba833004ddf4317fd39cbf5927cf26d58`; post-main verification is in progress but its mutable source lane is no longer authoring.
- WO205 Phase-D §14 has an active Windows R3 source claim on a disjoint source/test scope under Issue #214.
- Windows also has a Kilo review process for the separate ENV project; it is not an A-Sunday Conductor mutable lane.
- This WO443 scope is A-Faster governance/docs only and does not overlap WO205 source paths.
- Mac root checkout is protected/stale with untracked `.kilo/`; this task uses only the isolated worktree above.

## Verification
- exact four-path scope
- `git diff --check`
- strict UTF-8 / no U+FFFD
- A-Faster frontmatter/reference integrity
- `tests/test_work_order_identity.py`
- added-line secret-shaped scan
- adversarial wording check: time breach must not imply replay/takeover authority
- independent exact-SHA R2 review
- exact-head hosted CI
- GPT-5.6 Sol exact-SHA acceptance, expected-head merge, post-main verification

## Replay / continuity safety

Every later device/session must start from Issue #443 + this WO + actual Git/runtime evidence. A stale pulse, missing chat turn, device offline state, or elapsed time never authorizes duplicate mutation. `STALLED`, `INTERRUPTED`, and `UNKNOWN` require existing replay-safety and ownership reconciliation before takeover.

## Initial checkpoint

The user explicitly requested cross-device awareness with start/working/complete/stop timestamps and safe help/takeover after long stalls. Existing liveness authority already defines activity/progress/heartbeat distinctions and STALLED reconciliation, while A-Faster currently does not require these timestamp fields or explicit lifecycle-pulse publication at every lane boundary. This WO fills that routing/projection gap by REUSE -> EXTEND only.

## Author checkpoint

- Author surface: GPT-5.6 Sol direct through macOS RDC in the isolated claimed worktree.
- `GLM_OFFLOAD_ASSESSMENT=NOT_BENEFICIAL` for authorship: the change is a bounded governance projection over already accepted liveness authority; preserve GLM capacity/independence for the required R2 review.
- Added automatic A-Faster lifecycle-pulse recovery/publication at STARTED, material PROGRESS, WAITING/STOPPED, TERMINAL_UNHARVESTED, COMPLETED, and TAKEOVER_STARTED.
- Extended local pointer timing with activity/progress/heartbeat freshness plus task-specific stall policy and derived stall-candidate time.
- Made stale/expired pulses reconciliation triggers only; time never grants retry/cancel/takeover authority.
- Cross-device takeover now requires prior-owner/process/result/Git/claim/replay reconciliation and a TAKEOVER_STARTED pulse; a resumed old device must yield to the valid newer owner.
- Global WIP remains `3 mutable + 1 review`; no scheduler/registry/lease/heartbeat daemon/state-machine authority was added.
- Deterministic author checks: exact four-path scope PASS; `git diff --check` PASS; work-order identity 33 PASS; strict UTF-8/no U+FFFD PASS; frontmatter/reference/required-semantic assertions PASS; added-line secret-shaped scan 0 hits.
- Durable progress pulse: Issue #443 comment `5754040165`.
- Candidate still requires freeze, independent exact-SHA R2 review, exact-head hosted CI, GPT acceptance, expected-head merge, and post-main verification.

## Independent review attempt 1 and P3 repair checkpoint

- Frozen candidate `95eb13b8187adb7dd8ce8f7d9752ca5727532558` received independent Windows Kilo/GLM-5.3 MAX R2 verdict `PASS`, P0/P1/P2/P3 = `0/0/0/3`.
- Exact-head CI #1117 on that SHA = SUCCESS.
- P3-1 repaired: canonical `A-FASTER LANE PULSE v1` template now includes required `started_at`.
- P3-2 repaired: pulse `event` and existing `liveness_class` are explicitly separate projections; overlapping literal names never derive, overwrite, promote, or substitute authoritative liveness/task state.
- P3-3 repaired: carrier outage is explicitly `PULSE_CARRIER_UNAVAILABLE`; local evidence must record the failure, publication must not be claimed, and handoff/takeover/cleanup that depends on the missing cross-device fold remains blocked until durable publication succeeds.
- Local work may continue during carrier outage only when its pre-existing task/claim/ownership/replay-safety gates independently remain valid.
- Current main advanced to `0ce82be15355bf3af782cd488b54d77c475d285b` via WO205/PR #445. The old-base→current-main relevance diff touches none of the four WO443 paths, so the claim remains non-overlapping.
- Repair checks: `git diff --check` PASS; work-order identity 33 PASS; strict UTF-8/no U+FFFD PASS; explicit P3 semantic assertions PASS; exact four-path scope PASS; added-line secret-shaped scan 0 hits.
- Next gate: commit/push repaired candidate, prove current-main merge-tree on committed SHA, then focused independent rereview of P3-1/P3-2/P3-3 plus exact-head hosted CI.
