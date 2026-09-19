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
  - `<TASK_ID>`: work-order id, e.g. `WO-P1-260`;
  - `<role>`: lane role segment, e.g. `author`, `review`, `verify`;
  - `<ordinal>`: small integer distinguishing same-role lanes.
- Example: `lane:WO-P1-260:author:1`
- Stable across device, harness, and chat/session/attempt changes for the
  life of the lane. A new attempt on the same lane keeps the same LANE_REF.
- Never task authority: holding or guessing a LANE_REF grants nothing.
  The claim/lease/work-order authorities decide ownership, always.

### DELEGATED_RUN_ID — unique attempt identity

- Format: `run:<TASK_ID>:<role>:<ordinal>:a<attempt>:<random-id>`
  - `<attempt>`: the attempt number (see ATTEMPT);
  - `<random-id>`: 8 hex chars from a CSPRNG (e.g. `secrets.token_hex(4)`),
    unique per launch.
- Example: `run:WO-P1-260:author:1:a1:352051cd`
- Uniquely identifies one dispatch attempt for observation, logging,
  recovery, and harvest. Never task authority: a run id says "this attempt
  happened", not "this task is owned/done/accepted".

### ATTEMPT — evidence-local attempt counter

- Monotonic only within the lane evidence directory
  (`runs/<WO>/<lane>/attempt-NNNN/`): 1, 2, 3 ... as `attempt-0001`,
  `attempt-0002`, ...
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

Input object (field order shown sorted only for readability; JSON key
sorting is enforced by the serializer):

```json
{
  "branch": "docs/wo-p1-260-a-faster-durable-lanes",
  "claim_ref": "WO-P1-260-A-FASTER-DURABLE-LANES-001",
  "device_id": "DESKTOP-7IB57R4",
  "dispatch_head": "ef7d3d15fce0b66ddfdadbc56a3014875aa1bcbd",
  "harness_id": "kilo-code-cli",
  "host_os": "windows",
  "model_id": "cointh-glm/glm-5.3",
  "mutable_scope": [
    ".agents/skills/a-faster/SKILL.md",
    ".agents/skills/a-faster/references/durable-lanes.md",
    "docs/work-orders/WO-P1-260-a-faster-durable-lanes.md"
  ],
  "repo": "aase7en/A-Wiki-Conductor",
  "schema": "a-faster.binding.v1",
  "task_id": "WO-P1-260",
  "worktree": "A:/GitHub/_worktrees/A-Wiki-Conductor-wo260-a-faster-durable"
}
```

Canonical bytes (single line, compact, sorted):

```text
{"branch":"docs/wo-p1-260-a-faster-durable-lanes","claim_ref":"WO-P1-260-A-FASTER-DURABLE-LANES-001","device_id":"DESKTOP-7IB57R4","dispatch_head":"ef7d3d15fce0b66ddfdadbc56a3014875aa1bcbd","harness_id":"kilo-code-cli","host_os":"windows","model_id":"cointh-glm/glm-5.3","mutable_scope":[".agents/skills/a-faster/SKILL.md",".agents/skills/a-faster/references/durable-lanes.md","docs/work-orders/WO-P1-260-a-faster-durable-lanes.md"],"repo":"aase7en/A-Wiki-Conductor","schema":"a-faster.binding.v1","task_id":"WO-P1-260","worktree":"A:/GitHub/_worktrees/A-Wiki-Conductor-wo260-a-faster-durable"}
```

Digest (reproducible with Python 3 `json.dumps(..., sort_keys=True,
separators=(",", ":"))` → `.encode("utf-8")` → `hashlib.sha256(...)`):

```text
BINDING_DIGEST = cca025dd01a90d0a86f6a86b16e2a4c42f04c618cfd1df62bec160be5fa14d3f
```

## 3. Evidence layout and pointer fields

Per-device lane evidence lives under the gitignored runs directory
(`runs/<WO>/<lane>/attempt-NNNN/`), where `<lane>` is the plain role
segment of LANE_REF (e.g. `author`). Each attempt directory holds the
dispatched task packet and at least one `pointer.md` written before or at
launch and updated at terminal/handoff boundaries:

```text
runs/WO-P1-260/author/attempt-0001/
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
- timing: `started_at`, `finished_at` (ISO-8601 with offset, or `UNKNOWN`);
- destinations: `task_ref`, `result_ref`, `exit_ref`, `log_ref`;
- `replay_safety`: `NOT_STARTED/PARTIAL/COMPLETE_UNVERIFIED/
  COMPLETE_VERIFIED/UNKNOWN` per the liveness protocol projection;
- `expected_completion`: what evidence will prove completion (tests,
  checks, review gates) and where it lands.

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
   outstanding lane refs, latest attempt, and declared result
   destinations. Chat memory is convenience context only, after facts.
2. **Process/session** — check the exact runner/child/session identity
   (PID + verified command identity) recorded in the pointer, when the
   device is reachable. Never broad-kill or assume from a process name.
3. **Result/exit** — read `result_ref`/`exit_ref`/`log_ref` artifacts and
   classify the terminal outcome if present.
4. **Git** — verify actual worktree/branch/HEAD/dirty state against
   `dispatch_head`, `mutable_scope`, and the expected outputs; recompute
   BINDING_DIGEST from observed facts.
5. **Derive state** (per the liveness protocol) and act:

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
   outstanding LANE_REF/DELEGATED_RUN_ID + pointer state, exact next safe
   action — written to the work order checkpoint.
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
     overlap, and only then continue. Digest mismatch never silently
     transfers ownership, and never bypasses the WO/claim authority.

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

- Fresh session finds `lane:WO-P1-260:author:1` attempt-0002 pointer with
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
- [ ] no new scheduler/DB/registry/state machine was introduced
      (router-only boundary intact);
- [ ] recover algorithm disposition recorded for every outstanding lane
      before new READY work was selected;
- [ ] WIP accounting unchanged: 3 mutable + 1 review, global.
