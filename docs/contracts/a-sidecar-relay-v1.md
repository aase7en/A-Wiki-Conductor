# A-Sidecar Relay Contract v1 (A-Relay)

Status: PHASE 0 CONTRACT — specification only, no runtime released
Work order: WO-P1-568 (`docs/work-orders/WO-P1-568-a-sidecar-relay-phase0.md`)
Role: typed durable cross-surface event/receipt transport only — **no authority**

## 1. Purpose

A-Relay is one typed envelope format plus delivery semantics for durable
cross-surface events between ChatGPT sidecar chats, Codex parent/child lanes,
GLM dispatch lanes, JEV advisory seams, and the human operator. It lets a
sidecar chat, a Codex thread, and an integrator exchange bounded facts —
checkpoints, help requests, receipts, pressure warnings, gate notices — as
durable evidence instead of chat-memory relay, without any participant
becoming a second control plane.

Phase 0 defines the contract text only. Any conforming carrier (append-only
file log, hook bus projection, or future service) is a **dumb carrier**: it
moves and stores events and nothing else.

## 2. Non-authority invariant

- An A-Relay event is a receipt/evidence record, never a command. Arrival of
  an event never creates, claims, schedules, dispatches, reviews, merges,
  completes, or unblocks work by itself.
- Consumers verify against the authoritative owner (work order, claim table,
  Git, deterministic checks, accepted protocols) before acting; the event only
  carries references to that authority.
- A-Relay creates no queue authority: no scheduler, task store, claim/lease
  system, retry owner, prioritization engine, review path, or completion state
  machine. Existing Conductor authorities remain the single owners of all of
  those decisions.
- Drop or delay of events must never change task truth; task truth lives in
  durable repositories/runtime state, which the events merely reference.

## 3. Initial event families

| Family | Typical producer → consumer | Meaning |
|---|---|---|
| `SIDECAR_HELP_REQUEST` | sidecar chat → integrator / Codex owner | sidecar needs a decision or fact it cannot recover read-only |
| `SIDECAR_CHECKPOINT` | sidecar chat → durable record | rollover/recovery checkpoint of sidecar state per the A-Sidecar skill |
| `SIDECAR_RESULT_RECEIPT` | sidecar chat → integrator | a companion-work result is terminally stored at its evidence destination |
| `CODEX_STEER_REQUEST` | integrator/sidecar → Codex lane | request the Codex owner consider a steer; advisory to the owner, never a command |
| `GLM_DISPATCH_REQUEST` | integrator → GLM lane | intent to dispatch a bounded GLM task packet (gates still apply) |
| `GLM_RESULT_RECEIPT` | GLM lane → integrator | a GLM execution terminal outcome with durable pointer/exit evidence |
| `JEV_ADVISORY_REQUEST` | any lane → JEV seam | bounded allowlisted advisory decision requested |
| `JEV_ADVISORY_RECEIPT` | JEV seam → requester | advisory result; evidence only, never action authority |
| `GPT_WORK_LIMITED` | GPT surface → durable record | GPT working capacity constrained (usage limit, throttling, entitlement) |
| `CONTEXT_PRESSURE_HIGH` | any surface → durable record | producer session approaching practical context rollover |
| `HUMAN_GATE_REQUIRED` | any lane → human | an approval/authorization/safety gate needs the operator |

Family set is closed in v1: producers must not invent new families; extension
requires a contract revision with its own work order.

## 4. Minimum envelope

Every event carries at least:

```yaml
EVENT_ID: "evt-<producer-surface>-<collision-resistant-id>"   # immutable, globally unique
EVENT_TYPE: "SIDECAR_CHECKPOINT"                              # exactly one family from §3
SOURCE_SURFACE: "chatgpt-sidecar | codex | glm | jev | gpt | human"
SOURCE_THREAD_ID: "<producer thread/session id, or UNKNOWN>"
SOURCE_TURN_ID: "<producer turn/attempt id, or UNKNOWN>"
TASK_ID: "<canonical task/work-order id>"                     # when applicable
CLAIM_ID: "<canonical claim id>"                              # when applicable
REPO: "owner/name"                                            # when applicable
WORKTREE: "/observed/absolute/worktree/path"                  # when applicable
HEAD_SHA: "<full 40-char sha>"                                # when applicable
REQUESTED_CAPABILITY: "read-only-inspect | advisory | review-prep | heavy-author | ..."   # when applicable
PRIORITY: "LOW | NORMAL | HIGH"                               # human-gate/context events default HIGH
EVIDENCE_REFS:                                                # durable pointers only
  - "repo-relative/path or issue/comment ref or run pointer"
CREATED_AT: "ISO-8601 with offset"
```

Rules:

- Fields marked "when applicable" are omitted, not blank-filled, when they do
  not bind; a mutation-relevant event without an exact TASK_ID/CLAIM_ID/
  REPO/WORKTREE/HEAD_SHA binding is malformed and must be ignored.
- `EVIDENCE_REFS` point at durable destinations only — never secrets, logs
  dumps, transcripts, share URLs, or inline payloads of authority.
- Envelopes are data, not code: no executable content, no prompt injection
  surface, no credentials.
- Device-qualified context (producer device/os) may be added as optional
  fields; identity fields above stay device-neutral.

## 5. Idempotency, replay, and ack semantics

Designed so a future runtime can implement delivery without inheriting
authority:

- **Minting.** `EVENT_ID` is producer-minted, collision-resistant, and
  immutable once emitted. Producers never reuse an id after terminal failure
  of the same logical emission; a genuinely new emission gets a new id.
- **Delivery.** At-least-once. Duplicates are expected; every consumer
  deduplicates on `EVENT_ID` before interpretation. Losing events degrades
  observability only, never task truth.
- **Ordering.** No cross-surface total order is guaranteed. Consumers order
  per producer using `(SOURCE_SURFACE, SOURCE_THREAD_ID, CREATED_AT,
  EVENT_ID)` and tolerate out-of-order arrival.
- **Replay safety.** Events are facts-with-references, not commands, so
  replaying the full log can only re-derive observations. Replay can never
  re-create claims, mutations, merges, or completions; those remain owned by
  their authorities. Any consumer whose action would have side effects must
  gate the action on the authority (claim/scope/Git checks), not on event
  arrival.
- **Ack.** `ACK` is an optional receipt referencing the original `EVENT_ID`
  meaning *observed and folded* — never *approved*, never *completed*. There
  is no NAK and no automatic retry-with-authority in v1: an unobserved event
  is recovered by comparing durable state, not by re-sending commands.
- **Retention.** Events are append-only. Correction happens through a new
  event referencing the old `EVENT_ID`; nothing is rewritten or deleted.
- **Runtime constraint.** Any future carrier implementing this contract must
  preserve the above and must not add scheduling, prioritized work creation,
  retries that carry authority, or task state ownership.

## 6. Codex bridge constraints

- Codex state inspection and steer submission go only through supported
  Desktop-managed Codex App Server / native queue APIs that the current
  harness actually exposes and that the exact Codex version supports.
- Never open, read, or mutate Codex local SQLite/session/lock files as
  product behavior — including read-only access. Raw storage mutation is
  additionally a safety violation. An operator's one-off diagnostic is not
  product behavior and must not be codified into the runtime.
- Capability is per-device/per-version: verify the exact surface, else record
  a typed `SURFACE_UNAVAILABLE` blocker and degrade to Git/GitHub/work-order
  evidence.
- **Durable-first-turn:** the first turn of any bridge interaction writes a
  durable pointer (work-order checkpoint or run pointer) before depending on
  in-chat context, so a later surface can recover the bridge state.
- **UTF-8 across devices:** every relay artifact is strict UTF-8, LF-normalized
  on write, validated on read, on both macOS and Windows producers.
- **Device/path handling:** worktree/absolute paths differ per device
  (`/Users/...` on macOS, drive roots on Windows). Envelopes carry repo
  identity plus the producer-observed path tagged with device context; never
  promote one device's path layout to canonical identity, and never resolve a
  foreign-device path locally.
- Workspace-context visibility into a Codex thread never grants mutation
  authority over that thread's task, claim, scope, or schedule.

## 7. GLM-first quota policy projection

Relay events that request or report model work project the accepted GLM-first
policy; they never modify it:

- deterministic facts before model asks;
- A-Audit/JEV advisory seams for bounded semantic triage only;
- GLM-5.3 Flash for bounded read-only reconnaissance only;
- GLM-5.3 MAX as default eligible heavy author/repair/review labor;
- GPT/Luna limited to supervisor/integrator/acceptance roles;
- each eligible R2/R3 task carries exactly one `GLM_OFFLOAD_ASSESSMENT`
  (`DISPATCHED` / `BLOCKED:<typed_reason>` / `NOT_BENEFICIAL:<reason>`) in its
  own work-order/task record, not invented by relay events;
- actual GLM use requires durable execution evidence;
- one fresh accepted CoinTH quota preflight immediately before each material
  dispatch, recorded with the dispatch event; no readiness smokes; no
  manufactured work.

## 8. Phase 0 scope boundary

This contract adds no runtime, no carrier implementation, no schema file, no
hook, and no product code. Implementing a carrier, emitting events from
product code, or extending the family set each require a successor work order
with its own claim and review.
