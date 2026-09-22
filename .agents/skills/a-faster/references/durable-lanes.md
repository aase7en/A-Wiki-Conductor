# A-Faster reference — durable lane identity / cross-chat recovery

This reference is an A-FastTask/A-Faster routing projection only. It adds
identity/evidence conventions for delegated lanes. It grants no mutation,
dispatch, retry, provider, review, merge, or acceptance authority, and it
creates no scheduler, database, task/claim/lease store, review system, or
completion state machine. All task/claim/lease/execution authority remains
with the existing work-order, claim, and execution authorities exactly as
A-FastTask and `docs/agent-collab/EXECUTION_LIVENESS_PROTOCOL.md` bind them.

Problem this solves: a delegated lane can outlive the chat/turn/session that
launched it. A fresh session on the same or another device must be able to
answer "which lane, which attempt, which binding, what happened, is it safe
to continue?" from durable evidence instead of chat memory, without
inventing a second control plane.

## 1. Identity overlay

Four fields overlay every A-Faster delegated lane. They label and bind
evidence; they are never authority.

### LANE_REF — stable routing label

- Format: `lane:<TASK_ID>:<role>:<ordinal>`
  - `<TASK_ID>`: work-order id, e.g. `WO-P1-374`;
  - `<role>`: lane role segment, e.g. `author`, `review`, `verify`;
  - `<ordinal>`: small integer distinguishing same-role lanes.
- Example: `lane:WO-P1-374:author:1`
- Stable across device, harness, and chat/session/attempt changes for the
  life of the lane. A new attempt on the same lane keeps the same LANE_REF.
- Never task authority: holding or guessing a LANE_REF grants nothing.
  The claim/lease/work-order authorities decide ownership, always.

### DELEGATED_RUN_ID — unique attempt identity

- Format: `run:<TASK_ID>:<role>:<ordinal>:a<attempt>:<random-id>`
  - `<attempt>`: the attempt number (see ATTEMPT);
  - `<random-id>`: lowercase CSPRNG hex, historically 8 chars and currently
    observed as 12 chars in durable dispatch evidence; both 8 and 12 are
    accepted canonical forms for recovery. New generators should preserve the
    exact random suffix they mint rather than truncate or reinterpret it.
- Example: `run:WO-P1-374:author:1:a1:352051cd`
- Uniquely identifies one dispatch attempt for observation, logging,
  recovery, and harvest. Never task authority: a run id says "this attempt
  happened", not "this task is owned/done/accepted".
- Recovery-only legacy aliases (WO-P1-480 P1 repair): real pre-MSP0
  durable pointers also contain proven pre-grammar alias shapes, e.g.
  `run:WO-P1-478:r3-review:a1:2933deb345c2` (ordinal segment absent)
  and `run:WO-P1-475:flash-architecture:acfa39d:a1:16b32a2f6ea9`
  (non-decimal token in the ordinal position). These are accepted ONLY
  when recovering an existing attempt directory from
  `pointer.md`/`execution-pointer.json` evidence: the entire original
  string is preserved verbatim as the immutable recovery identity, only
  the trailing `a<attempt>` and 8/12-hex suffix are bound to the
  physical directory (exact suffix agreement on suffixed directories,
  attempt agreement on legacy unsuffixed ones), and they are never
  valid for new minting or physical path generation — the canonical
  parser and `attempt_dir_name()` stay strictly canonical. Dual pointer
  sources must agree on the exact full string; any mismatch, ambiguity,
  or malformed value fails closed with stable code-only errors.

### ATTEMPT — evidence-local attempt counter

- Monotonic only within the lane evidence directory
  (`runs/<WO>/<lane>/`): 1, 2, 3 ... rendered as `attempt-0001`,
  `attempt-0002`, ...
- Physical directory naming (WO-P1-480 / MSP-0): new attempt
  directories are `attempt-NNNN-<random-id>`, where `NNNN` is the
  run's attempt number zero-padded to 4 digits (human-readable
  bookkeeping only, never uniqueness authority) and `<random-id>` is
  exactly the DELEGATED_RUN_ID's accepted 8- or 12-hex random suffix. One delegated
  run maps to exactly one immutable directory; two sessions that
  collide on the same ordinal therefore cannot overwrite each other's
  task/config/pointer/result artifacts. Legacy `attempt-NNNN`
  directories remain readable/recoverable via their pointer and are
  never rewritten in place. The canonical pure helper is
  `src/a_conductor/delegated_run_artifacts.py` (parse/derive/enumerate/
  recover, fail-closed on mismatch/malformed/traversal input).
- Physical injectivity assumes uniqueness of the CSPRNG random suffix.
  The current 12-hex form (48 bits of entropy) is the preferred
  new-minting form; the historical 8-hex form (32 bits) carries a
  residual birthday-bound collision probability across many runs and
  is recovery compatibility, not preferred new minting entropy. New
  generators must not mint 8-hex suffixes.
- Never grants retry authority. Starting attempt N+1 requires the existing
  replay-safety and claim/recovery rules (reconcile side effects and replay
  classification first); the counter only records that a new attempt exists.

### BINDING_DIGEST — drift detection over the safe binding tuple

- SHA-256 over canonical UTF-8 JSON of exactly these fields:
  `schema`, `task_id`, `claim_ref`, `repo`, `worktree`, `branch`,
  `dispatch_head`, `mutable_scope` (sorted list), `device_id`, `host_os`,
  `harness_id`, `model_id`.
- Canonicalization: JSON object serialized with sorted keys and compact
  separators `(",", ":")`, UTF-8 encoded, SHA-256 hex digest. Fixed
  `schema` value: `a-faster.binding.v1`. `worktree` uses forward slashes.
- Purpose: detect binding drift (wrong repo/worktree/branch/HEAD/scope/
  device/harness/model). It is NOT encryption, authentication, or proof of
  integrity against a malicious actor — only a tamper-evidency-free
  equality check between recorded and observed binding facts.

## 2. Canonicalization worked example (verified)

Canonical post-remediation example for the A-Faster durable-lanes task
(WO-P1-374, Issue #374). Input object (field order shown sorted only for
readability; JSON key sorting is enforced by the serializer):

```json
{
  "branch": "docs/wo-p1-374-a-faster-durable-lanes",
  "claim_ref": "WO-P1-374-A-FASTER-DURABLE-LANES-001",
  "device_id": "DESKTOP-7IB57R4",
  "dispatch_head": "ef7d3d15fce0b66ddfdadbc56a3014875aa1bcbd",
  "harness_id": "kilo-code-cli",
  "host_os": "windows",
  "model_id": "cointh-glm/glm-5.3",
  "mutable_scope": [
    ".agents/skills/a-faster/SKILL.md",
    ".agents/skills/a-faster/references/durable-lanes.md",
    "docs/work-orders/WO-P1-374-a-faster-durable-lanes.md"
  ],
  "repo": "aase7en/A-Wiki-Conductor",
  "schema": "a-faster.binding.v1",
  "task_id": "WO-P1-374",
  "worktree": "A:/GitHub/_worktrees/A-Wiki-Conductor-wo374-a-faster-durable"
}
```

Canonical bytes (single line, compact, sorted):

```text
{"branch":"docs/wo-p1-374-a-faster-durable-lanes","claim_ref":"WO-P1-374-A-FASTER-DURABLE-LANES-001","device_id":"DESKTOP-7IB57R4","dispatch_head":"ef7d3d15fce0b66ddfdadbc56a3014875aa1bcbd","harness_id":"kilo-code-cli","host_os":"windows","model_id":"cointh-glm/glm-5.3","mutable_scope":[".agents/skills/a-faster/SKILL.md",".agents/skills/a-faster/references/durable-lanes.md","docs/work-orders/WO-P1-374-a-faster-durable-lanes.md"],"repo":"aase7en/A-Wiki-Conductor","schema":"a-faster.binding.v1","task_id":"WO-P1-374","worktree":"A:/GitHub/_worktrees/A-Wiki-Conductor-wo374-a-faster-durable"}
```

Digest (reproducible with Python 3 `json.dumps(..., sort_keys=True,
separators=(",", ":"))` → `.encode("utf-8")` → `hashlib.sha256(...)`):

```text
BINDING_DIGEST = e55d20348b88454ebeb8e655afc8c3ddc571e3428560e642d884841699d7db22
```

Historical alias note: the accepted pre-remediation attempt recorded this
binding under the WO-P1-260 identity (task id `WO-P1-260`, claim
`WO-P1-260-A-FASTER-DURABLE-LANES-001`, branch
`docs/wo-p1-260-a-faster-durable-lanes`, digest
`cca025dd01a90d0a86f6a86b16e2a4c42f04c618cfd1df62bec160be5fa14d3f`).
Those historical WO-P1-260 pointers remain valid evidence aliases — LANE_REF
and run ids are observation pointers, not authority — but they are not
canonical task ids after Issue #381 rebound this task to WO-P1-374.

## 3. Evidence layout and pointer fields

Per-device lane evidence lives under the gitignored runs directory
(`runs/<WO>/<lane>/`), where `<lane>` is the plain role segment of
LANE_REF (e.g. `author`). New attempts (WO-P1-480 / MSP-0) use the
collision-proof suffixed form `attempt-NNNN-<random-id>/` whose
`<random-id>` is the DELEGATED_RUN_ID's accepted 8- or 12-hex random suffix; legacy
`attempt-NNNN/` directories stay readable/recoverable and are never
rewritten. Enumeration over mixed legacy/new directories is
deterministic via `src/a_conductor/delegated_run_artifacts.py`, and
recovery maps each suffixed directory back to exactly one delegated
run by name+pointer agreement (mismatch fails closed). Historical/canonical
A-Faster lanes use `pointer.md`; current hardened delegated runners may also
persist `execution-pointer.json`. The canonical helper accepts either recovery
surface and requires exact run-id agreement when both exist. The helper
intentionally treats every `delegated_run_id:`-shaped line in a `pointer.md`
(including lines inside fenced blocks) as pointer evidence, so an extra
example-shaped `delegated_run_id` line that disagrees with the real one
triggers fail-closed `POINTER_RUN_ID_AMBIGUOUS` by design. Keep live
`pointer.md` files to exactly one plain `field: value` `delegated_run_id`
line; keep pointer.md *examples* as plain `field:value` text only inside
fenced examples in documentation, never as extra bare lines in a live
pointer file. Each attempt
directory holds the dispatched task packet and durable pointer evidence written
before or at launch and updated at terminal/handoff boundaries:

```text
runs/WO-P1-374/author/attempt-0001-352051cd/
  task.md       # dispatched packet (input, immutable after dispatch)
  pointer.md    # durable identity/status pointer (this section)
  result.md     # declared result destination (when the attempt declares one)
```

`runs/` is device-local and gitignored. The durable cross-device record is
therefore always: pushed branch + work-order checkpoint (+ Issue/PR where
used). Material pointers/results must be folded into the work order or
another tracked artifact before worktree cleanup, exactly as
`../../a-fasttask/references/closeout.md` requires.

Minimum `pointer.md` fields:

- `lane_ref`, `delegated_run_id`, `attempt`, `binding_digest`;
- `status`: derived liveness class from
  `docs/agent-collab/EXECUTION_LIVENESS_PROTOCOL.md`
  (`STARTING/RUNNING/WAITING/STALLED/TERMINAL_UNHARVESTED/INTERRUPTED/
  TERMINAL/UNKNOWN`) — reuse only, never a second state machine;
- task/claim/topology: `task_id`, `claim_ref`, `topology`
  (`CONTROL_PLANE_ONLY` / `EXECUTION_SUBSTRATE_ONLY` / `CROSS_REPO`,
  defined only in `docs/agent-collab/TOOL_AND_FAST_PATH_ROUTING.md`);
- device/host: `device_id`, `host_os`;
- harness/model: `harness_id`, `model_id`, `model_effort` when applicable;
- repo binding: `repo`, `worktree`, `branch`, `dispatch_head`,
  `mutable_scope`;
- execution identity when known: runner/child/session ids (PID +
  verified command identity, never a broad process class);
- timing: `observed_at`, `started_at`, `last_activity_at`,
  `last_progress_at`, optional `last_heartbeat_at`, and `finished_at`
  (ISO-8601 with offset, or `UNKNOWN`);
- freshness: task/adapter-specific `stall_policy` plus
  `stall_candidate_after_at` when deterministically computable; there is no
  global A-Faster timeout and expiry alone grants no takeover/replay authority;
- latest lifecycle pulse label:
  `STARTED/PROGRESS/WAITING/STOPPED/TERMINAL_UNHARVESTED/COMPLETED/TAKEOVER_STARTED`
  (communication projection only, never a second state machine);
- destinations: `task_ref`, `result_ref`, `exit_ref`, `log_ref`;
- `replay_safety`: `NOT_STARTED/PARTIAL/COMPLETE_UNVERIFIED/
  COMPLETE_VERIFIED/UNKNOWN` per the liveness protocol projection;
- `expected_completion`: what evidence will prove completion (tests,
  checks, review gates) and where it lands.

## 3.1 Cross-device lifecycle pulse

The device-local pointer is detailed recovery evidence. For cross-device
awareness, fold a compact pulse into the active Work Order/Issue at material
lane boundaries. This pulse reuses the pointer and
`EXECUTION_LIVENESS_PROTOCOL.md`; it is not a registry or lease.

Minimum pulse shape:

```text
A-FASTER LANE PULSE v1
event: STARTED|PROGRESS|WAITING|STOPPED|TERMINAL_UNHARVESTED|COMPLETED|TAKEOVER_STARTED
observed_at: <ISO-8601 offset timestamp or UNKNOWN>
started_at: <ISO-8601 offset timestamp or UNKNOWN>
lane_ref: <LANE_REF>
delegated_run_id: <latest run id or NONE>
task_ref: <WO/task>
claim_ref: <claim>
device_id: <verified device>
liveness_class: <existing liveness class>
repo: <repo>
worktree: <absolute worktree>
branch: <branch or DETACHED>
head: <exact SHA>
mutable_scope: <bounded scope>
last_activity_at: <timestamp or UNKNOWN>
last_progress_at: <timestamp or UNKNOWN>
last_heartbeat_at: <timestamp or UNKNOWN>
stall_policy: <task/adapter-specific bounded policy or UNKNOWN>
stall_candidate_after_at: <derived timestamp or UNKNOWN>
replay_safety: <existing projection>
reason: <typed reason/blocker or NONE>
evidence: <result/log/Issue/PR pointer>
next_safe_action: <exact action>
```

Publish at `STARTED`, material `PROGRESS`, truthful `WAITING`/`STOPPED`,
`TERMINAL_UNHARVESTED`, `COMPLETED`, and every valid
`TAKEOVER_STARTED`. The `event` field and `liveness_class` field are independent
projections; overlapping literals never allow the event label to mutate or
substitute for authoritative liveness/task state. `STOPPED` means only that the current executor/session
ceased work; it is not automatically durable CANCELLED/FAILED/TERMINAL.
`COMPLETED` requires accepted/reconciled evidence, never a model DONE claim.

Freshness is advisory routing evidence. If the current time exceeds a
deterministically derived `stall_candidate_after_at`, the next A-Faster
invocation marks the lane `RECONCILE_REQUIRED` / possible `STALLED` and then
checks exact process/session, result/log, Git/worktree, ownership and replay
safety. Time alone never authorizes a new attempt or takeover.

When a receiving device validly takes over, it records the prior device,
new device, prior/latest run identity, and the binding-digest field delta in
the `TAKEOVER_STARTED` pulse. If the prior device later resumes, that session
must recover this pulse and yield to the current owner unless an explicit
subsequent handoff transfers ownership again.

If the active Work Order/Issue carrier cannot be written, record
`PULSE_CARRIER_UNAVAILABLE` in the device-local pointer/evidence and do not
claim cross-device publication succeeded. Continue local work only when its
existing authority/ownership/replay-safety gates remain independently valid;
block cross-device handoff/takeover and cleanup that depends on the missing
fold until the carrier is restored and the pulse is published.

## 4. Secret safety

Pointers, logs, run ids, and evidence must NEVER contain secret values,
raw credential-bearing environment blocks or argv, cookies, or
share/session URLs. Allowed: redacted values (`sk-...abcd` → last 4),
digests, secret names/resolver references, non-secret endpoints. If a
credential-bearing command line must be referenced, record the command
with the credential replaced by `<REDACTED:<SECRET_NAME>>`. Apply the same
rule to pasted tool output folded into evidence.

## 5. Recover algorithm (fresh session / fresh device)

`NEW SESSION != NEW TASK`. Before selecting new READY work or any
redispatch/takeover, reconcile every outstanding LANE_REF for the task:

1. **Issue/WO pointer** — read the active work order/Issue checkpoint for
   outstanding lane refs, latest attempt, latest lifecycle pulse/freshness
   timestamps, and declared result destinations. Chat memory is convenience
   context only, after facts.
2. **Process/session** — check the exact runner/child/session identity
   (PID + verified command identity) recorded in the pointer, when the
   device is reachable. Never broad-kill or assume from a process name.
3. **Result/exit** — read `result_ref`/`exit_ref`/`log_ref` artifacts and
   classify the terminal outcome if present.
4. **Git** — verify actual worktree/branch/HEAD/dirty state against
   `dispatch_head`, `mutable_scope`, and the expected outputs; recompute
   BINDING_DIGEST from observed facts.
5. **Freshness check** — compare trustworthy activity/progress/heartbeat
   timestamps with the lane's declared task/adapter-specific stall policy.
   If its derived bound is exceeded, mark `RECONCILE_REQUIRED` / stall
   candidate; do not infer interruption/ownership loss from time alone.
6. **Derive state** (per the liveness protocol) and act:

| Derived state | Disposition |
|---|---|
| `RUNNING` | never redispatch; attach/observe or continue non-overlapping work |
| `TERMINAL_UNHARVESTED` | harvest and verify the declared result first; blocks redispatch and conflicting mutation |
| `STALLED` | reconcile per the stall contract; a timeout is never replay authority |
| `INTERRUPTED` | replay-safety + side-effect reconciliation before any takeover |
| `UNKNOWN` | fail closed; checkpoint typed blocker; no duplicate mutable attempt |

A new attempt (`attempt+1`, new DELEGATED_RUN_ID) is only created under
the existing claim/recovery authorities after this reconciliation, never
automatically from the counter.

## 6. Cross-device handoff

A device handoff is a lane handoff, not a new task, and not an automatic
transfer:

1. **Checkpoint** on the sending device: task/claim/scope, current SHA,
   outstanding LANE_REF/DELEGATED_RUN_ID + pointer state, latest freshness
   timestamps, truthful `WAITING`/`STOPPED` pulse, and exact next safe action
   — written to the work order/Issue checkpoint.
2. **Push durable state**: push the branch; fold material evidence out of
   `runs/` into the work order/Issue (runs/ is gitignored and does not
   travel with the repo).
3. **Re-pin on the receiving device**: verify actual
   repo/worktree/branch/HEAD/dirty/claim state, then recompute
   BINDING_DIGEST from observed facts.
4. **Compare digests**:
   - equal → same binding continued; recover per Section 5;
   - different → `CONTEXT_DRIFT`. Device-bound fields (`device_id`,
     `host_os`, `worktree`, and possibly `harness_id`) normally differ on
     a handoff, so a mismatch is expected and must be resolved by an
     explicit re-pin: record the field-level delta in a new attempt
     pointer, reconcile the prior attempt per Section 5, prove no mutable
     overlap, publish `TAKEOVER_STARTED` with the old/new device identity
     and field-level digest delta, and only then continue. Digest mismatch
     never silently transfers ownership, and never bypasses the WO/claim
     authority.

No accepted remote/source on the receiving device remains
`SOURCE_UNAVAILABLE / SAFE_TO_MUTATE=NO`.

## 7. Invariants preserved

- Global WIP stays `3 mutable + 1 independent read-only review` lanes
  across every device/harness/repo — never multiplied per device.
- `1 MUTABLE HOTSPOT = 1 MUTATION OWNER`.
- A-FastTask stays router-only; A-Faster stays a routing overlay. Neither
  gains execution lifecycle authority from this reference.
- No global lane registry: LANE_REF strings are discoverable from the
  active work order/Issue checkpoints and lane evidence directories only;
  there is no central registry service, file index, or database.
- Identity fields never substitute for claims: a lane with a perfect
  LANE_REF/DELEGATED_RUN_ID/BINDING_DIGEST and no valid claim is still
  `SAFE_TO_MUTATE = NO`.

## 8. Examples

Safe:

- Fresh session finds `lane:WO-P1-374:author:1` attempt-0002 pointer with
  `status: TERMINAL_UNHARVESTED` and a `result.md`; it harvests and
  verifies the result before any new dispatch on that hotspot.
- Mac takeover of a Windows lane: checkpoint pushed, receiving device
  re-pins HEAD, recomputed digest differs in `device_id`/`host_os`/
  `worktree` only → `CONTEXT_DRIFT` resolved by explicit re-pin + Section 5
  reconciliation + recorded delta, then continues under the same claim.
- Redispatch after `INTERRUPTED`: replay-safety shows `PARTIAL` with
  commits already on the branch; the takeover verifies the delta against
  `mutable_scope` before continuing instead of replaying the packet.

Unsafe:

- Fresh chat sees no result in context and silently re-dispatches the same
  packet (duplicate mutable attempt; violates harvest-first).
- `STALLED` for 40 minutes → kill and relaunch without process/result/Git
  reconciliation (timeout is not replay authority).
- An old `STARTED` pulse crosses `stall_candidate_after_at` → declare the old
  owner dead and mutate the same hotspot without exact runtime/Git/claim
  reconciliation (freshness breach is only a stall candidate).
- Copying a pointer from the other device and continuing without
  re-pinning HEAD (digest mismatch ignored).
- A pointer logging `Authorization: Bearer <raw token>` or a Kilo share
  URL (secret-safety violation; redact/replace with name/digest).
- Treating `attempt-0007` existing as license to retry (counter is not
  authority).

## 9. Validation checklist

Before freezing a lane that uses this overlay, verify deterministically:

- [ ] every material delegated dispatch has `pointer.md` with all Section 3
      minimum fields before or at launch;
- [ ] LANE_REF/DELEGATED_RUN_ID match the defined formats and the active
      work order's lane/claim;
- [ ] BINDING_DIGEST recomputation over the observed binding tuple equals
      the recorded digest (same device) or the delta is fully explained and
      recorded (cross-device);
- [ ] `mutable_scope` in the digest equals the work order's allowed mutable
      scope, sorted;
- [ ] pointer/evidence files contain no secret values, credential-bearing
      argv/env, cookies, or share URLs (pattern scan);
- [ ] attempt directories are strictly monotonic, one per actual dispatch;
      new directories carry the run's exact accepted 8- or 12-hex random suffix
      (`attempt-NNNN-<random-id>`, WO-P1-480) so the ordinal is never
      uniqueness authority, and legacy `attempt-NNNN` recovery still works;
- [ ] proven pre-grammar legacy pointer aliases (WO-P1-480 P1 repair seam)
      recover pointer-only with the original string preserved verbatim and
      never mint paths; dual pointer sources agree on the exact full
      `delegated_run_id` string;
- [ ] no new scheduler/DB/registry/state machine was introduced
      (router-only boundary intact);
- [ ] recover algorithm disposition recorded for every outstanding lane
      before new READY work was selected;
- [ ] WIP accounting unchanged: 3 mutable + 1 review, global.
