# WO-P1-575 — A-Sidecar Phase 2 synthetic-envelope hardening

Issue: #575
Predecessor: #573 / PR #574
Topology: CONTROL_PLANE_ONLY
Risk: R3
Status: GENERATION-2 IMPLEMENTED / EXACT-HEAD REVIEW AND CI PENDING
Claim: WO-P1-575-SIDECAR-HARDENING-MAC-001
Worktree: /Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo575-sidecar-hardening-g2
Branch: feat/wo-p1-575-sidecar-hardening-g2
Base HEAD: 100c94b0308ba33101e00929d7016443f3f7331f

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

## 3. Historical generation-1 lane identity (superseded by §13)

- repository: aase7en/A-Wiki-Conductor
- worktree: /Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo575-sidecar-hardening
- branch: feat/wo-p1-575-sidecar-hardening
- base: 6c4bcdfebfde29990f92b7b76670830009ba6753
- claim: WO-P1-575-SIDECAR-HARDENING-MAC-001

This is the original generation-1 tuple and is historical only. The generation-2
replacement binding is authoritative before mutation and is recorded in §13 and
Issue #575 comments `5950579896` and `5950598814`. Any active
repo/worktree/branch/HEAD/claim mismatch fails closed before mutation.

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
  (user-directed Desktop-binding recovery lesson and orchestration-mode
  supervision-contract projection; documentation only, no authority expansion)

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

## 11. Synthetic-boundary reproduction — 2026-10-01

- Binding recheck: repo `aase7en/A-Wiki-Conductor`; worktree `/Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo575-sidecar-hardening`; branch `feat/wo-p1-575-sidecar-hardening`; HEAD and remote branch both `91d57dcd3df39093b1d41b9556f706763d045b33`; claim remains `WO-P1-575-SIDECAR-HARDENING-MAC-001`.
- A bounded in-memory Python reproducer ran with `PYTHONDONTWRITEBYTECODE=1`; it imported the existing bridge/tests, created synthetic envelopes via `dataclasses.replace`, and wrote no files.
- `_invalid_evidence_ref` currently accepts all three probe classes: unsafe Unicode (`Cf`), PEM-marker text, and secret-shaped token text.
- `recover_checkpoint` lets raw `TypeError` escape for a non-string `CREATED_AT` and for mixed naive/aware timestamps; neither is a typed `RelayCarrierError`.
- `select_steer_candidate` lets raw `ValueError` escape for malformed synthetic `CREATED_AT`; it is not a typed `RelayCarrierError`.
- This is direct behavior evidence for WO §5/§6 gaps, not acceptance. No source/test files or A-Wiki state changed; no full pytest suite, provider, or dispatch was run. Worktree remains clean for tracked files; preserve `.kilo/`.
- The R3 source gate remains `HUMAN_REQUIRED` pending current accepted WIP admission and release/reconciliation of the #498-owned continuity paths. Do not treat this reproducer or the prior plan-only GLM execution as mutation authority.

## 12. Post-merge dependency and binding recheck — 2026-10-01 04:13 UTC

- PR #574 / WO-P1-573 is now merged and post-main verified. `origin/main` is
  `6c4bcdfebfde29990f92b7b76670830009ba6753`; exact-head and post-main CI
  succeeded, and Issue #573 records `ACCEPTED / POST_MAIN_VERIFIED / COMPLETE`.
  The #575 predecessor dependency is satisfied.
- Live #575 binding: repository `aase7en/A-Wiki-Conductor`; worktree
  `/Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo575-sidecar-hardening`;
  branch `feat/wo-p1-575-sidecar-hardening`; local HEAD and remote branch both
  `855d2f2da74a497bf7f3aac4b688d538cc160309`. Tracked files are clean. Preserve
  the existing untracked `.kilo/` directory.
- SundayMCP recovery reports 215 executions, all terminal and replay-safe
  (153 completed, 20 failed, 42 cancelled); lane list is empty. The previous
  #575 GLM run remains terminal `PLAN_ONLY`; do not replay it.
- The #498 owner worktree remains dirty at
  `8d2aae705a6d2180fd36abaf7f1ed545355d554c` across 12 tracked paths,
  including `CURRENT-WORK.md`, `handoff.md`, and its claimed source/test
  paths. No release/reconciliation evidence was found. Preserve that state;
  #575 must not edit the two continuity paths.
- The latest accepted A-Faster markers remain the carried values from #547
  comment `5847879995` / #498 comment `5855053210`:
  `FANOUT_TARGET=0`, `UNUSED_SAFE_CAPACITY=1`,
  `AUTO_REFILL_REQUIRED=false`. These do not prove fresh global WIP admission;
  do not recompute utilization or infer permission to start source mutation.
- A-Wiki Issue #58 remains open and PR #67 has two unresolved R3 review
  threads. #551/#549 refill therefore remains fail-closed; this is separate
  from the now-satisfied #574 dependency and does not grant #575 WIP authority.

`SAFE_TO_MUTATE=NO` for the #575 source/test slice until the #498 continuity
ownership is reconciled and current canonical WIP plus the exact-head R3 gate
are re-established. The reproduced defects remain actionable evidence, not
mutation authority. Next safe action: recheck the #498 owner release and
accepted WIP marker, then rerun the #575 identity/scope/A-Audit gates at the
current exact HEAD before any provider request.

This stop was lifted for generation 2 by the gate clearance recorded in §13:
Issue #575 comment `5950579896` (#498 closed/completed/post-main verified,
empty durable lane census, A-Audit `STRONG_IMPLEMENTATION`, and
`SAFE_TO_MUTATE=YES` conditional on a proven clean generation-2 lane) and
comment `5950598814` (exact clean generation-2 worktree/branch/start-HEAD
binding with current main merged, tracked tree clean, and no collision).
§12 remains the historical generation-1 stop; this citation adds no authority.

## 13. Generation-2 implementation checkpoint — 2026-10-02

- Binding: repository `aase7en/A-Wiki-Conductor`; worktree
  `/Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo575-sidecar-hardening-g2`;
  branch `feat/wo-p1-575-sidecar-hardening-g2`; start HEAD
  `42e82cc7217126d9726661bb467bdf6cb536ca12` with current main
  (`100c94b0308ba33101e00929d7016443f3f7331f`) merged into the lane; claim
  `WO-P1-575-SIDECAR-HARDENING-MAC-001` unchanged.
- Gate clearance from the §12 generation-1 stop: Issue #575 comment
  `5950579896` records #498 closed/completed/post-main verified, an empty
  durable lane census, A-Audit `STRONG_IMPLEMENTATION`, and `SAFE_TO_MUTATE=YES`
  conditional on proving the clean generation-2 lane. Comment `5950598814`
  proves that lane at the exact worktree/branch/start HEAD, with current main
  included, tracked tree clean, and no collision. Together these comments are
  the durable clearance for generation 2; §12 remains the historical stop for
  generation 1. No generation-2 source mutation began before this clearance.
- RED first: focused failing tests (42 RED across the §6 matrix) were added
  for secret-token-shaped refs (ghp_/gho_/ghs_/github_pat_/sk-/xoxb-/AKIA/
  AIza shapes), PEM-marker refs, Cc/Cf/Co/Cs unsafe-Unicode refs, non-string
  (int/None/datetime), invalid-ISO, naive, padded, unsafe, and overlong
  CREATED_AT in both checkpoint chronology and steer ordering, mixed
  aware/naive chronology, zero transport calls on preflight validation
  failure, and aware offset-instant ordering determinism.
- Implementation (§5.A): `_invalid_evidence_ref` now delegates the
  sensitive-text verdict to the accepted carrier's own validator via
  `_carrier_text_is_unsafe`, adding unsafe-Unicode, PEM/private-key, and
  credential/secret-token rejection on top of the existing
  URL/padding/length/duplicate rules; the composed `relay-event:` receipt
  ref in `build_ack_receipt` passes the same bridge-side gate before any
  carrier append. The carrier file itself is untouched.
- Implementation (§5.B): `_require_carrier_created_at` gates every CREATED_AT
  consumed by `recover_checkpoint` chronology and `select_steer_candidate`
  ordering through the carrier's typed timestamp validator before any
  comparison or transport call, so non-string, invalid-ISO, naive, padded,
  unsafe, and overlong values — and mixed naive/aware chronology — fail
  closed with the stable `RELAY_ENVELOPE_INVALID` code and no raw
  TypeError/ValueError escapes. Aware offset-instant ordering stays
  deterministic.
- §5.C: no behavior change; no new v1 marker, receipt field, or
  completion/approval semantic was added. The ACK-vs-projected limitation
  stands as recorded.
- §5.D: the Desktop-binding lesson in `.agents/skills/a-sidecar/SKILL.md`
  was verified present with the required deep-link recovery, writer/runtime
  verification, and `THREAD_DURABLE != DESKTOP_LOADED != SCHEDULE_PROVEN`
  invariant; preserved unchanged.
- Verification on this worktree: `python3 -m pytest -q
  tests/test_sidecar_codex_bridge.py` 141 passed;
  `python3 -m pytest -q tests/test_sidecar_relay.py tests/test_control_events.py
  tests/test_lifecycle_journal.py tests/test_work_order_identity.py` 173
  passed; `python3 -m py_compile` clean for both changed Python files;
  `git diff --check` clean; strict UTF-8/LF, no U+FFFD, no trailing
  whitespace; changed paths are exactly the §4.2 source-slice allowlist
  entries `src/a_conductor/sidecar_codex_bridge.py`,
  `tests/test_sidecar_codex_bridge.py`, and this work order, plus the
  documentation-only reconciliation in
  `docs/work-orders/WO-P1-573-a-sidecar-phase2-codex-bridge.md`. No commit,
  push, merge, or GitHub mutation performed; independent exact-SHA R3 review
  and integrator acceptance pending.

## 14. Orchestration-contract projection and incident/evidence appendix — 2026-10-03

Source of record: Issue #575 comments `5955806357` and `5956054416`.
The GLM-authored patch was generated read-only against generation-2 HEAD
`08618b5d9d59efdc07828e69aafd9591798119e2` (base
`100c94b0308ba33101e00929d7016443f3f7331f`), then mechanically applied by
the Luna integrator. Precommit verification for that head is recorded in Issue
#575 comment `5959102149`; the repair and current-head verification are recorded
in §15. It grants no claim/review/merge/completion authority.

`.agents/skills/a-sidecar/SKILL.md` projects the orchestration activation
("use A-Sidecar"; in-project typo "A-Sidebar") and supervision contract:
Sol/Luna role split, A-FastTask-first composition, parent loop, watchdog,
routing, writer continuity, skill freshness, and binding corrections.
The A-Sidecar authority floor remains unchanged.

Incident/evidence:

- Old Parent `01a0f2dd-eccd-7e61-ae55-8dbc37734662` and watchdog
  `01a0f451-6d13-7f70-a8c2-53b77c897a1e` hit active-writer conflicts on
  supported resume after interrupted turns: queued steer could yield an
  interrupted/empty turn while queue start required resume and resume was
  refused. No raw DB/session/lock repair or broad restart occurred.
- Old checkout `c4d4cf4da830cb313a4569a386edcff0a77266c2` lacked current
  A-Sidecar/A-Audit skills;
  `origin/main@100c94b0308ba33101e00929d7016443f3f7331f` had them.
  Lifecycle hook SHA256
  `eb63c9773aa14c1f58279cf1848e6a97efb575f45d571ad81b83756305d8850a`
  was identical: stale skill visibility, not hook logic. The clean read-only
  snapshot `/Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-codex-supervisor-g2`
  at `100c94b0308ba33101e00929d7016443f3f7331f` exposed
  A-FastTask/A-Faster/A-NightShift/A-Audit/A-Sidecar.
- Successor Parent `01a0fd2f-a479-75a0-bafb-46423c0c0a39` was started
  through the supported API as Luna LOW; recovery-only first turn returned
  `SUCCESSOR_RECOVERY_READY`. The catalog emitted "Exceeded skills context
  budget"; explicitly attaching required skills is the robustness pattern.
- The first successor pass falsely classified CoinTH preflight unavailable
  because it sought a separate visible tool. `~/.codex/hooks.json` and
  `cointh_quota_pretool.py` provide fail-closed PreToolUse admission for
  explicit GLM requests. Credentials were not exposed.
- An earlier #575 bounded GLM repair got explicit upstream HTTP 429 before
  mutation: a typed lane-local provider blocker, never duplicate-writer
  permission.
- Obsolete review `exec-mur476az-cd6bsrps` was CANCELLED/harvested/collected,
  had `claimPresent=false` and `identity.verified=false`, and used an
  incorrectly reconstructed SHA. It is not acceptance evidence.
- Failed `exec-mur4mla1-1mgnulul` was FAILED/harvested/collected with
  `bindingDigest=null` and `identityVerified=false`; no canonical binding
  or accepted mutation resulted. It is not acceptance evidence and must not
  be replayed as success.
- The first read-only GLM authoring dispatch attempt was rejected by connector
  schema validation before execution because `sunday_dispatch args[3]`
  exceeded `maxLength=8000`. No execution or model call was created. Standing
  fix: compact handoff prompts, prefer durable references plus progressive
  disclosure, and keep each material prompt within the connector limit.

Corrections and standing gates:

- SRM `claimPresent=false` means the SRM completion done-claim artifact is
  missing, not that the A-Conductor project claim or WorkerLease is absent.
  Project/WO claim, WorkerLease/mutation admission, and SRM collection
  semantics are separate evidence planes.
- Never fabricate DEX `bindingDigest` or identity fields. If canonical
  `mode=mutate` admission is unavailable on a direct route, do not send
  unbound mutate; read-only patch output remains non-authoritative until
  separately applied and verified.
- Exact full SHAs come from live Git, never reconstructed from a prefix.
  Actual #579 head at authoring was
  `08618b5d9d59efdc07828e69aafd9591798119e2`. Candidate changes invalidate
  earlier exact-head evidence: fresh hosted CI and independent exact-SHA
  review are required before merge.
- A prior Kilo invocation requested permission for `.kilo/plans` and failed
  before accepted mutation. Use the autonomous, sharing-disabled Kilo shape;
  do not write plans or expose credentials.


## 15. Exact-head review findings and repair disposition — 2026-10-03

- Read-only GLM-5.3 MAX review execution `exec-murbg90k-l9sc037t` completed at
  candidate `15ca95ae997b5ecc2d6c3c413dcb0119b49af779` with exit 0. Its review
  worktree was detached, clean, and bound to that exact SHA. Sunday reports
  `identity.verified=false`, `claimPresent=false`, and empty structured scopes;
  the output is therefore recorded as advisory findings, not acceptance.
- The review found a P2 audit-trail gap from §12 to §13. Exact Issue #575
  comments `5950579896` and `5950598814` have now been verified live and are
  cited in §13 as the #498 release/A-Audit/WIP clearance and clean g2 binding.
  This closes the documentation traceability gap without creating authority.
- The review's precise lane-identity, cross-reference, verification-pointer,
  full-SHA/fence, and model-tier naming findings were mechanically corrected
  within the existing two-file amendment scope.
- This review covered the two-file documentation amendment but does not satisfy
  the whole-candidate review requirement for the bridge source/tests. The new
  candidate requires fresh hosted CI and an independent exact-SHA R3 review
  over the full five-file PR diff; no acceptance is claimed.

## 16. Residual review-finding repair and disposition — 2026-10-03

- Review comment `5959278288` (P2 + 5 P3) was partially repaired at
  `a272125ac4066019fce9dee2951d5c66089e29f6`; the lane-identity,
  verification-pointer, #573-checkpoint-location, fence, and model-tier
  findings were closed there and re-verified read-only at this worktree.
- This amendment closes the remainder: §12 now cites the §13 generation-2
  gate clearance (Issue #575 comments `5950579896` / `5950598814` and the
  #498 release evidence they record), and the §14 snapshot reference uses
  the exact full SHA `100c94b0308ba33101e00929d7016443f3f7331f` resolved
  from live Git. `.agents/skills/a-sidecar/SKILL.md` needs no change; its
  model-tier naming is already canonical there.
- No authority is created and no acceptance is claimed; the §15 hosted-CI
  and independent exact-SHA R3 review requirements apply unchanged to the
  resulting candidate.
