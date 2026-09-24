# Elastic Multi-Agent Leverage Roadmap

Date: 2026-09-07
Status: SHAPING / #537 PURE ELASTIC-WIP + READ-ONLY COCKPIT SLICE AUTHORIZED / NO GENERAL FLEET AUTHORITY
Repository: `aase7en/A-Wiki-Conductor`
Baseline at creation: `origin/main@df5a25f1f9949e6938ea4bbcf0150515e6e5fa85` (PR #221 / ZRA-1 merged)
Final shaping fold re-pinned on 2026-09-12 to `origin/main@cfcb369fe5ab3a50569defa822289f10f2f38aac`. The dependency order at that fold was `ZRA-2 -> ZRA-3 -> ZRA-4` (relative order unchanged by the 2026-09-17 recomposition); Phase B was accepted/post-main and Phase C0 / WO216 was the ZRA-2 implementation frontier at that time.
Recomposed on 2026-09-17 by WO-P1-247 / PR #332 (accepted controlled pivot): the `2026-09-17 SunDay Runtime recomposition` section near the end is the current authoritative sequencing and architecture direction.

## Purpose

Evolve A-Sunday Conductor from a fixed small set of parallel lanes into a provider-neutral, asynchronous, conflict-aware **Elastic Multi-Agent execution fabric** that can use 1, 2, 4, 6, 8, 10+ agents when independent READY work actually exists.

This document does not authorize implementation or reorder the accepted Zero-Relay roadmap. It records the target architecture and acceptance principles so future sessions do not depend on chat memory.

## 2026-09-24 elastic borrowed-lane override — Issue #537

The user explicitly authorized an **elastic claimed-WIP layer** so long external,
CI and provider-cooldown waits do not leave safe compute idle or make the system
appear frozen.

This is an override of older static wording only where “3 mutable” was interpreted
as a hard cap on *all claimed mutable lanes*. It does **not** raise the normal
simultaneous mutation-compute ceiling.

```text
BASE_ACTIVE_MUTATION_LIMIT = 3
BORROWED_LANE_LIMIT        = 2
MUTABLE_CLAIM_LIMIT        = 5
INDEPENDENT_REVIEW_LIMIT   = 1
```

Admission semantics:

1. Borrow capacity exists only for base claims truthfully in an eligible passive
   wait: `WAITING_APPROVAL`, `WAITING_CI`, passive `WAITING_GLM`, `WAITING_JEV`,
   `WAITING_EXTERNAL` or `COOLDOWN`. A `WAITING_GLM` lane with an active delegated
   mutation child is not passive and does not free that mutation slot.
2. A borrowed lane requires real independent `READY` work plus the normal exact
   scope/hotspot, claim/lease, runtime and provider gates.
3. `BLOCKED`, `HUMAN_REQUIRED`, unknown evidence and collisions do not create
   borrowed capacity.
4. Existing parked borrowed work resumes before a new borrowed claim is created.
5. The classifier may report `borrow_target`, `resume_target` or
   `borrowed_to_park`; it never dispatches, claims or mutates by itself.
6. Total active mutation remains `<= 3`; total mutable claims remain `<= 5`;
   review remains separately capped at `1`.

Contraction is deterministic. When a base wait resolves, reserve its active slot
first. If the projected active mutation count would exceed three, enough borrowed
lanes must finish only their current bounded micro-step, checkpoint using existing
authority and transition to `PARKED_CAPACITY` before the returning base lane resumes.
No reset, stash, broad kill, claim duplication or silent redispatch is permitted.

The companion Mission Control roadmap
`docs/plans/2026-09-24-mission-control-agent-digital-twin.md` owns the operator UX:
wait type, reason, last activity, next recheck/countdown, borrowed/parked state and
observed capacity. It consumes durable evidence and creates no monitor state store.

Issue #537 authorizes the pure policy classifier and read-only Cockpit projection
slice. Executable A-Faster consumption remains a bounded successor after #530
ownership releases, so the current implementation does not collide with #530.

## 2026-09-12 priority fence and deep-audit fold

> Historical section (2026-09-12). Its production sequencing — including the
> `ONLY AFTER P0-G` Worker Host/Fleet placement, the `After ZRA-4 baseline
> acceptance` P1 MVP gate, and the direct ZRA-3 -> ZRA-4 path — is superseded
> by the 2026-09-17 SunDay Runtime recomposition section below: the SunDay
> Runtime single-device MVP and its two-lane isolation/recovery proof now sit
> between ZRA-3 and ZRA-4 recomposed acceptance. Retained here as evidence.

### Binding product priority

The latest user instruction reaffirms the highest project priority:

> **Complete GPT <-> GLM Zero-Relay before expanding Sunday Worker/Fleet/MCP production scope.**

Completion means the user no longer copies prompts, results, review findings, repair instructions, or `continue` messages between ChatGPT/GPT and GLM/ZCode for the accepted path. Research/docs may proceed without consuming a critical mutable lane; Worker Host/Fleet implementation may not preempt the ZRA dependency chain.

This is consistent with WO189 / PR #261 (pending priority capture) and does not transfer or supersede any active ZRA ownership.

### Actual-state critical path at final fold

This roadmap was re-pinned on 2026-09-12 against `origin/main@cfcb369fe5ab3a50569defa822289f10f2f38aac`.

Durable Zero-Relay state observed from Git/GitHub/Issue #214:

- **ZRA-2 Phase B is COMPLETE / POST-MAIN VERIFIED / ACCEPTED.** The reviewed no-clobber repair was accepted and folded through PR #291; merge `8700d21887500965ffc33bcbffa1f33602d9c2f6` preserved all six accepted Phase-B paths byte-for-byte and post-main verification reported `321 passed, 1 expected platform skip`.
- **ZRA-2 Phase C0 is the active implementation frontier.** WO216 was explicitly released `NEXT_READY` on the accepted Phase-B base. A later durable coordination checkpoint detected two GLM sessions entering the same WO216 worktree; one session stood down without mutation. Treat that event as evidence that logical claim publication alone is insufficient runtime fencing; do not dispatch another WO216 writer until the current owner is reconciled.
- **ZRA-2 Phase C1 remains blocked** until C0 is independently accepted, merged, post-main verified, and a fresh C1 claim is released.
- **WO208 crash/effect lab is CHANGES_REQUIRED.** Independent review found five P2 evidence defects and published bounded repair packet PR #294. The original lab is not accepted as the WO205 Phase-D prerequisite.
- **ZRA-2 Phase D remains blocked** until C0+C1 are accepted and the repaired WO208 crash/effect evidence is accepted and consumed.
- **ZRA-3 remains dependency-blocked by full ZRA-2 acceptance.**
- **ZRA-4 remains dependency-blocked by ZRA-3 acceptance and Issue #216 release.**

These are dated observations, not permanent projections. Every dependent mutation must re-pin actual state.

### Required execution order

```text
P0-A  ZRA-2 Phase C0 — CURRENT ACTIVE FRONTIER
      WO216 review-task binding/materialization
      -> deterministic exact ResultIdentity -> review TaskPacketFile
      -> trusted route binding; READ_ONLY reviewer contract
      -> no invented mailbox agent_id
      -> no-clobber/replay/collision/identity-drift tests
      -> reconcile duplicate-mutator event before further dispatch
      -> freeze exact SHA -> independent review -> merge -> post-main verify

P0-B  ZRA-2 Phase C1
      WO201 trusted review-evidence composition
      -> reviewer payload cannot mint author/result/attempt/generation authority
      -> bind exact independent reviewer execution
      -> exact author-result/task assignment cross-binding

P0-C  WO208 repair + ZRA-2 Phase D prerequisite
      repair the independent lab findings from PR #294
      -> prove real crash/effect/restart evidence truthfully
      -> accept repaired evidence before Phase-D source release

P0-D  ZRA-2 Phase D
      bind accepted ZRA-1 execution/result/review path + GoalCloseout/durable job state
      -> at-most-once external effect / receipt / reconciliation
      -> UNKNOWN or lost acknowledgement => reconcile, never resend
      -> one review failure => exactly one bounded repair generation
      -> repaired result ingested/verified automatically

P0-E  Full ZRA-2 acceptance E2E
      GPT task -> GLM -> exact result -> verify -> independent review
      -> automatic repair -> GLM -> exact repaired result -> acceptance
      -> human relay actions = 0

P0-F  ZRA-3 acceptance
      automatic NEXT READY
      -> reconcile current WO191/WO195/WO199 stack on accepted ZRA-2
      -> timeout/UNKNOWN never blind-replays

P0-G  ZRA-4 bounded baseline
      first ceiling = 2 mutable lanes
      -> C1 physical workspace identity
      -> C1b write-set canonicalization
      -> C2 deterministic parallel batch identity
      -> two-lane race/restart/partial-failure/fan-in proof
      -> raise toward 3 only from evidence

ONLY AFTER P0-G:
P1    Worker Host / Fleet supervisor
P2    second-machine federation
P3    runtime isolation
P4    evidence-gated 4/6/8/10+ scaling
```

### Open-source lessons admitted into the current Zero-Relay path

The companion deep audit permits only bounded invariant/test adoption on the current critical path:

1. **agentmux delivery receipt:** submitted-but-unverified is an at-most-once recovery fence, never a resend signal.
2. **Agent Orchestrator/Open SWE CI-review reaction:** feedback is bound to exact task/result/reviewer identity and enters the existing ZRA-2 repair path.
3. **OpenAI/MAF handoff discipline:** explicit filtered task context, stable participant/execution identity, accepted vs intermediate output separation.
4. **OpenHands/Open SWE unknown-state rule:** unknown/unreachable workspace/process is recovery/hold, not silent replacement.
5. **Docker gateway collision rule:** dynamic capability names cannot silently shadow one another.
6. **Multi-agent runtime fencing lesson from the live WO216 duplicate-mutator incident:** logical task/claim identity must be composed with exact physical worktree/process ownership before dispatch; duplicate entry is a coordination defect to reconcile, not permission for concurrent mutation.

No new scheduler, queue, graph store, retry store, or review authority is authorized.

### P1 — single-machine Worker Host MVP (Windows first)

After ZRA-4 baseline acceptance, consolidate logical workers behind one background host/supervisor while preserving old endpoints as migration fallback:

```text
ChatGPT / A-Sunday Conductor
           |
      Worker Host API
           |
    +------+------+------+------+
    W1     W2     W3     W4     W5
```

Required:
- stable host identity + authenticated endpoint;
- list/get/health/events for logical workers;
- start/stop/restart/drain through existing LocalInstanceOrchestrator/recovery;
- live reconciliation of process/project/worktree/branch/HEAD/dirty/task/claim/lease;
- background/no-console startup;
- request/response plus streaming event/read model;
- namespace collision rejection;
- **no Worker Host scheduler/task/claim/merge authority**.

Primary references: OpenHands Agent Server, Agent Orchestrator, Docker MCP Gateway, `agents`.

### P2 — Windows + Mac federation

```text
A-Conductor
   +-- Windows Host -> W1..W5
   +-- Mac Host     -> W6..W10
```

Required:
- host identity separate from worker identity;
- OS/capability/resource/latency/last-seen projection;
- `HOST_OFFLINE` distinct from `WORKER_UNHEALTHY`;
- heartbeat/event reconciliation;
- cross-host auth/secret isolation;
- cross-platform exact-SHA verification roles;
- no assumption RDC identity == Worker Host identity.

References: ContextForge federation/OTEL, OpenHands multi-server pattern, Gas Town Witness/Deacon separation.

### P3 — runtime isolation profile

Before high-concurrency mutable lanes that run services/tests:
- deterministic per-lane port ranges;
- per-lane DB/schema and Compose namespace where required;
- env projection without secrets in Git;
- dependency/cache policy;
- exact owned background-process identity;
- setup/teardown hooks;
- stale-allocation reconciliation/doctor.

Allocation is subordinate to physical worktree identity + WorkerLease, never a second scheduler/claim system.

References: workz and falq.

### P4 — evidence-gated fleet scale

- **2 mutable lanes:** ZRA-4 first acceptance target.
- **3 mutable + 1 read-only review:** normal ceiling after 2-lane proof.
- **4–6 lanes:** require READY demand, runtime isolation, review capacity, provider capacity, and measured throughput gain.
- **8 lanes:** additionally require host resource backpressure + restart/partial-failure evidence.
- **10+ registered workers:** allowed as a pool; active mutation remains dynamic and recovery capacity stays free.

Ten registered workers are capacity, not a concurrency target.

### Adoption verdict

| Area | Adopt | Reject |
|---|---|---|
| Zero-Relay transport | agentmux at-most-once receipt invariants | second prompt queue |
| worker host | OpenHands/AO interface patterns | their schedulers/task stores |
| MCP gateway | Docker namespace/lifecycle/security | gateway-owned authority |
| federation/observability | ContextForge/OTEL patterns | ContextForge control plane |
| liveness | `agents` live reconciliation | persisted liveness as truth |
| runtime isolation | workz/falq allocation patterns | unowned global cleanup |
| fleet health | Gas Town Witness/Deacon roles | Beads/Gas Town task DB |
| fan-out/in | MAF API/test patterns | MAF graph/checkpoint store |
| durable semantics | Pydantic/Temporal invariants | durable-engine migration |
| handoff context | OpenAI explicit filters/traces | implicit full-chat handoff |
| swarm scale | Ruflo topology benchmarks | Ruflo memory/router/scheduler |

### Fleet acceptance metrics

A Fleet change is rejected if it increases busyness without accepted delivery:
- human relay actions / accepted external-agent task (**0 after Zero-Relay**);
- accepted work/hour;
- median/p95 lead time and READY->claim latency;
- first-review pass rate and repair loops/task;
- merge/conflict rate and review queue wait;
- CPU/RAM/disk/LSP/process count per host;
- duplicate execution count;
- ambiguous-submit blind replay count (**0**);
- runtime port/DB/Compose collision count;
- recovery success + orphan process/worktree count;
- cost / accepted task.

### Activation rule

The deep audit is complete enough to close the research prerequisite for architecture shaping. It does **not** activate Worker Host/Fleet product work. The next production mutation remains the current Zero-Relay critical path. Worker Host/Fleet becomes `NEXT_READY` only after ZRA-4 baseline acceptance or an explicit future user decision that reorders the roadmap after fresh conflict/authority analysis.


## 2026-09-16 SunDayMCP consumer convergence refinement — WO-P1-247

Status: DOCS-ONLY SHAPING / NO HOST-FACADE-SERVICE-BROWSER SOURCE AUTHORITY

This refinement consumes the user's one-connection consumer goal and the
2026-09-16 GPT-6 Astra architecture challenge. It refines the existing Worker
Host/Fleet roadmap; it does not create a second roadmap, scheduler, task store,
claim/lease system, provider registry, review authority, recovery authority, or
SSoT.

### Actual-state override — 2026-09-16

Current remote main at the WO247 claim is
`018779d0d2f5a7a7a21adb277e23a617692c36fd`. Historical C0/C1 frontier text
above remains evidence only where newer Git/GitHub/Issue truth differs.

Dependency order as of 2026-09-16 — superseded 2026-09-17 by the SunDay
Runtime recomposition section below (which inserts the SunDay Runtime
single-device MVP and the two-lane isolation/recovery proof between ZRA-3
and ZRA-4 recomposed); retained as history:

```text
WO246 durable author-attempt provenance
-> WO205 / full ZRA-2 acceptance
-> ZRA-3 accepted NEXT READY continuation
-> ZRA-4 bounded parallel baseline
-> Worker Host / SunDayMCP implementation
-> consumer hardening and optional federation
```

Issue #330 / WO246 is the current Phase-D provenance blocker. WO189 / PR #261
is an older open draft on a stale base; its Zero-Relay-first intent is retained,
but the branch is not current SunDayMCP architecture authority. Issue #320 /
WO240 owns its two Browser Wake docs and remains useful transport/security
input. Its earlier proposal to place Browser Wake product implementation before
ZRA-4 is not adopted by this refinement after the user's newer one-SunDayMCP
architecture decision. Browser/docs shaping may continue; product mutation stays
behind ZRA-4 unless a later explicit user decision reorders the dependency after
fresh authority/conflict analysis.
Final sequencing reconciliation remains reserved for the ZRA-3 exit per
`docs/runbooks/cost-first-delivery.md`; WO247 records the current user priority
without closing that future evidence gate.

### Consumer North Star

```text
ChatGPT / compatible AI client
            |
            v
one authenticated SunDayMCP connection
            |
            v
thin capability facade
            |
            v
A-Sunday Conductor control / trust / authority plane
   |             |              |                 |
Serena        native         Git/GitHub       Kilo / Claude /
semantic      device         scoped adapter   GLM/provider adapters
adapter       adapter
   \_____________|______________|_________________/
                         |
                    Worker Host
                         |
          existing task / claim / lease /
       execution / review / recovery / evidence
```

A-Wiki remains owner of brain/policy/skills/knowledge/review-policy semantics.
A-Sunday Conductor remains owner of live execution/runtime/admission/recovery
and evidence. SunDayMCP is a user-facing facade over those authorities, not a
replacement authority.

### SMCP dependency refinement

The `SMCP-*` labels below are roadmap phases, not reserved Work Order numbers.
Concrete implementation still requires a fresh bounded WO/claim and exact file
ownership after dependencies pass.

| Phase | Class / risk | Dependency / activation | Product outcome | Acceptance focus |
|---|---|---|---|---|
| `SMCP-0` Contract + ADR | REUSE/EXTEND, R2 docs; auth design R3 | docs shaping now | thin-facade contract, ADR-0001 narrow reopen, no duplicate authority | architecture review, authority map, threat/migration contract |
| `SMCP-1` Worker Host + facade vertical slice | WRAP/EXTEND, R3 | accepted ZRA-4 + SMCP-0 | one authenticated connection can read status and perform one bounded semantic operation through existing lifecycle authority | auth negative cases, namespace collision, two-session/project isolation, reconnect/no duplicate effect, legacy parity |
| `SMCP-2` Native + Git/GitHub capability | EXTEND/WRAP, R3 | SMCP-1 contract frozen | scoped filesystem/Git/log first, then typed exec/process/GitHub operations | traversal/junction/PID-reuse/argv/output limits, GitHub scope/revocation, mutation admission |
| `SMCP-3` Persistent OS lifecycle | WRAP/EXTEND, R3 | Host lifecycle contract frozen | background/no-console startup and supervised availability independent of GUI | reboot, login/logout, crash, manual-stop persistence, orphan/PID reuse, duplicate supervisor rejection, no task replay |
| `SMCP-4` Consumer installer/update/repair | EXTEND, R3 | design now; source after ZRA-4; release consumes SMCP-1..3 | one signed installer provisions approved private runtimes, Host and repair/update path without terminal prerequisites | clean VM, actual signature/hash, interrupted update, repair/uninstall, compatible rollback, data preservation |
| `SMCP-5` Browser Companion | WRAP/NEW adapter boundary, R3 | docs/threat shaping may continue under WO240; product implementation after ZRA-4 + stable Host/auth | opt-in selected-site context and bounded user actions through authenticated user-session bridge | per-origin consent/revoke, injection/secret/session/replay/Terms tests; no page-to-shell/claim authority |
| `SMCP-6` Unified monitor | EXTEND/WRAP, R2 read-only; controls R3 | projections frozen; product after ZRA-4 | one evidence-backed view of device/worker/job/claim/quota/process/blocker state; optional local web view later | UNKNOWN/OFFLINE/BLOCKED distinct, event gaps/restart, read causes no writes, provenance/redaction |
| `SMCP-7` Federation | EXTEND + NEW transport only, R3 | accepted single-host product + elastic P2 gates | second authenticated host/device behind the same product surface | partition/rejoin, revoked pairing, duplicate identity, clock skew, stale capability, no double effect |
| `SMCP-8` Legacy migration + consumer release | EXTEND, R3 | accepted single-host SMCP-1..6; federation optional | one SunDayMCP surface replaces the advertised single-device Worker1..5 + RDC workflow where parity is proven | side-by-side parity, reversible cutover, signed release evidence, no silent legacy deletion |

`SMCP-8` single-device consumer release does not wait for `SMCP-7`; federation
must not block the first useful one-machine product. Any RDC/Worker capability
not yet matched is disclosed rather than hidden behind an unsafe fallback.

### Worker Host / facade boundary

The first accepted Host/facade should provide only the minimum reusable seams:
- stable Host identity and authenticated endpoint;
- logical Worker list/get/health/events and capability projection;
- start/stop/restart/drain by reusing existing lifecycle/recovery authority;
- live reconciliation of process/project/worktree/branch/HEAD/dirty/task/claim/lease;
- collision-rejecting capability namespace and request/session binding;
- background lifecycle plus bounded request/response/event read models;
- legacy endpoint compatibility during migration.

It owns no scheduler, task graph/store, claim/lease system, provider admission,
review lifecycle, retry/dedup/completion authority, merge authority or project
memory. One connection is a UX boundary, never permission to bypass per-action
authorization.

### Zero-knowledge consumer installation target

Ordinary users should not need to understand Python, Node, npm/pip/uv, Serena,
MCP ports, tunnels, PowerShell, worktrees or language-server plumbing.

Reuse the existing installer/setup-wizard/runtime-setup foundation and extend it
toward:
- a signed self-contained bootstrap with an approved artifact manifest;
- private/pinned runtimes and dependency verification rather than ambient PATH;
- OS-protected credential references and separate user consent per provider;
- least-privilege Host lifecycle separated from interactive browser/user-session bridge;
- truthful health states for installed / Host-ready / auth-ready / semantic-ready /
  native-ready / provider-eligible;
- staged update/repair that verifies, drains owned work, switches versions,
  health-checks and rolls back only when state compatibility is proven;
- uninstall that removes only owned installation resources and explicitly
  preserves or removes user data by policy.

"Zero knowledge" means no terminal expertise, not zero consent or hidden account
authorization.

### Browser Companion trust boundary

Browser/site content is untrusted input. The Companion remains an adapter and must not
mint task, claim, lease, provider, review, completion or shell authority. Minimum controls:
- default no-site access; explicit per-origin grants and user-visible revoke;
- authenticated Native Messaging or equivalent user-session bridge with OS ACLs;
- bind browser profile/tab/conversation + user/device/project/execution identity;
- no cookie/session-token scraping and no hidden full-page surveillance;
- treat prompt/page text as data, never as policy or executable authority;
- validate typed message schema, size, path and requested capability again in Conductor;
- separate read/capture/send/write/execute grants and preserve user-action boundaries;
- provider Terms/auth/quotas remain binding; no CAPTCHA/login/access-control bypass;
- reconnect/duplicate delivery consumes existing execution/dedup truth and never blind-replays effects.

Required negative tests include malicious page injection, forged extension/native messages,
stale nonce/session replay, conversation mismatch, path traversal/argv injection, secret-shaped
DOM fields, revoked-origin invocation and duplicate wake/result delivery.

### Consumer acceptance matrix

| Gate | Required proof |
|---|---|
| Fresh Windows install | Supported clean VM with no Python/Node/uv/Serena prerequisite; user launches one signed installer; no manual terminal/port/tunnel editing |
| One connection | One supported SunDayMCP app surface exposes the accepted semantic + scoped native + Git/GitHub capability set through existing authority |
| Safe project | Explicit selected sandbox/project; registration alone creates no hidden repo binding/hook/mutation |
| GLM eligible | Exact Kilo/provider/model/task/worktree/result identity plus fresh route/quota/authorization evidence and deterministic candidate verification |
| GLM unavailable | Typed blocker; independent semantic/native work may continue; no silent model substitution or duplicate paid/model effect |
| Reboot/recovery | Host returns without terminal window, user-bound capabilities wait for the correct session, durable execution identity recovers without false completion/replay |
| Session/worktree isolation | Two sessions/projects plus alias/junction overlap, busy Worker and stale claim; no project leakage or overlapping mutable ownership |
| Browser threat matrix | Chrome/Edge/Firefox adapters are tested independently; only granted origins/data/actions cross the bridge; revoked origin has zero privileged effect |
| Installer failure | Tampered artifact, interrupted download/update, disk-full and incompatible state fail closed and preserve recoverable user data |
| Uninstall | Stops/removes only owned installation resources; unknown repos/worktrees/user data are preserved unless explicitly authorized |
| Monitor truth | OFFLINE / UNKNOWN / BLOCKED / RUNNING remain distinguishable and every state points to existing evidence/provenance |
| Legacy migration | Legacy Workers/RDC may run side-by-side during proof, but admission/dedup prevents duplicate effect; cutover is reversible |
| Release evidence | Actual shipped binary/version/hash/signature matches reviewed source/candidate/CI/post-main evidence; green signing workflow alone is insufficient |

Future macOS/Linux support requires equivalent clean-machine lifecycle/signing/key-storage
acceptance for each explicitly supported OS/distro. Cross-platform smoke alone is not
consumer onboarding proof.

### Migration rule

Migration is additive first: inventory legacy logical Worker/device bindings read-only,
introduce SunDayMCP for a sacrificial project, prove read-only parity, then prove bounded
semantic/native/write paths through the same admission/dedup authorities. Do not shadow-run
two writers or silently fall back to a different connector. Preserve legacy configuration
until user-confirmed retirement; rollback changes routing only and never replays ambiguous
unfinished effects.

### Activation fence

Architecture/docs work under a non-overlapping claim may proceed now. Product mutation for
Worker Host, facade, persistent service, Consumer installer integration, Browser Companion,
unified monitor or federation remains gated after accepted ZRA-4 baseline unless a later
explicit user decision changes dependency order after a fresh authority/overlap analysis.

Superseded 2026-09-17 by the activation fence in the SunDay Runtime
recomposition section below: the Runtime single-device MVP now follows ZRA-3
directly, while facade/persistent-service/installer/browser/monitor/federation
product mutation stays behind ZRA-4 recomposed acceptance and the
isolation/recovery proof.

## 2026-09-17 accepted controlled pivot — SunDay Runtime recomposition (WO-P1-247 / PR #332)

Status: DOCS-ONLY SHAPING / NO RUNTIME, SUPERVISOR, FACADE, OR CONSUMER SOURCE AUTHORITY

This section records the accepted controlled pivot and supersedes the
2026-09-12 and 2026-09-16 production sequencing orders above. Historical text
is retained as evidence; where it conflicts with this section, this section
wins for sequencing and architecture direction.

### Control-plane split

- A-Sunday Conductor remains the **sole control plane** (authority,
  admission, claims/leases, review, acceptance, recovery, evidence).
- The new **SunDay Runtime** is an **execution substrate only**:
  `execute / observe / cancel / collect evidence`. It owns no scheduler,
  task graph/store, claim/lease system, provider admission, review,
  retry/dedup/completion authority, merge authority, or project memory.
- **One Runtime Supervisor per device** supervises separate isolated
  executor processes/contexts per lane. Isolation of process, working
  context, and working set across lanes is a Runtime obligation.
- There is **no mutable global Active Project authority**. Logical Worker
  `1..N` is lane naming only, not a fleet identity.
- Transitional Serena use is **private per lane/worktree and optional**; the
  shared mutable Serena Active Project model is SUPERSEDED (ADR-0001 records
  the supersede and the corrected defect analysis: a request timeout alone
  does not prove a Serena deadlock; project-context drift from global
  activation is the architectural defect).
- The standing rule that every exposed Worker binds to the same Active
  Project is **replaced** by per-lane explicit execution-context binding
  (repo/worktree/branch/HEAD/claim) with fail-closed `CONTEXT_DRIFT` when
  the executor process/context does not match the declared binding.
- Default WIP is preserved: `3 mutable + 1 independent read-only review`
  lanes, spare recovery capacity, and `1 MUTABLE HOTSPOT = 1 MUTATION OWNER`.

### Recomposed dependency order (authoritative)

```text
WO246 provenance design + implementation
-> WO205 / full ZRA-2 acceptance
-> ZRA-3 accepted NEXT READY continuation
-> SunDay Runtime single-device MVP
   (Runtime Supervisor + isolated per-lane executors; substrate only)
-> two-lane multi-project isolation/recovery proof
-> ZRA-4 recomposed bounded-parallel acceptance
-> thin SunDayMCP facade
-> consumer hardening / optional federation
```

The relative `ZRA-2 -> ZRA-3 -> ZRA-4` order is unchanged. The Runtime MVP
and its two-lane multi-project isolation/recovery proof are inserted before
ZRA-4 recomposed acceptance because the bounded-parallel proof now runs on
the Runtime's isolated two-lane substrate; ZRA-4's accepted scope (C1/C1b/C2
identity work, two-lane race/restart/partial-failure/fan-in proof,
ceiling 2 raised toward 3 only from evidence) is retained, not discarded.
Federation (P2 / SMCP-7) stays deferred until the isolation/recovery proof
is accepted; the earlier P2 design text remains shaping history, not an
activation grant.

In the SMCP table above, read every `accepted ZRA-4` dependency as `ZRA-4
recomposed acceptance` under this order, and read `SMCP-7` federation as
additionally requiring the isolation/recovery proof. Read `Worker Host` in
the consumer North Star diagram and in `SMCP-1` as the recomposed SunDay
Runtime Supervisor/substrate: its single-device MVP and the two-lane
isolation/recovery proof precede ZRA-4 recomposed acceptance, while the
facade vertical-slice portion of `SMCP-1` still follows it.

### Recomposition ledger

| Action | Item |
|---|---|
| KEEP | WO246, WO205 / full ZRA-2, ZRA-3, SunDayMCP thin facade |
| RECOMPOSE | ZRA-4, WO247 / PR #332, Worker Host -> Runtime Supervisor |
| SUPERSEDE | shared mutable Serena Active Project binding |
| DEFER | federation until two-lane multi-project isolation/recovery proof |

### Runtime Supervisor boundary (recomposes the P1 Worker Host MVP)

The P1 single-machine Worker Host MVP is recomposed into the SunDay Runtime
single-device MVP. The supervisor may:

- supervise per-lane executor processes/contexts with isolated working
  contexts per lane;
- start/observe/cancel executors and collect their evidence by reusing the
  existing LocalInstanceOrchestrator/supervised-execution/recovery
  authority;
- reconcile live process/lane/worktree/branch/HEAD/dirty/task/claim/lease
  identity per lane;
- project bounded status/events and fail closed on `CONTEXT_DRIFT`.

It must not become a scheduler, task store, claim/lease system, provider
registry, review authority, recovery authority, merge authority, or a
mutation surface beyond typed operations. Executor isolation profiles
(ports/DB/env/secrets per lane) follow the P3 direction subordinate to
physical worktree identity and WorkerLease.

### DesktopCommanderMCP adoption strategy

Adopt DesktopCommanderMCP as a **pinned upstream dependency/adapter** for its
useful filesystem/search/remote-device mechanics — not a whole-repo fork
initially. Existing Conductor supervised execution/process ownership remains
the authority. The DesktopCommanderMCP hosted relay remains an optional
external dependency, never a required control-plane component.

### Security P0 — mutation surface

Autonomous mutation must NOT default to unrestricted raw shell, because a
same-user shell can bypass scope. Until stronger isolation exists, prefer
typed file edits, a patch-apply broker, and allowlisted build/test commands.
This applies to the Runtime executors, the future facade, and any
DesktopCommanderMCP-backed operation alike.

### Semantic transition

The Serena compatibility adapter is **lane-local only**. The long-term
direction is a small semantic interface over LSP + Tree-sitter + bounded
ripgrep. Do not rebuild language servers or a global index initially.

### Activation fence

Docs/research shaping for the SunDay Runtime may proceed in parallel under a
non-overlapping claim without consuming conflicting production mutation
ownership. Product mutation for the Runtime supervisor/executors, facade,
persistent service, consumer installer, browser companion, unified monitor,
or federation remains gated behind the recomposed order above unless a later
explicit user decision reorders it after fresh authority/overlap analysis.

## Existing foundations to reuse

Do not rebuild these authorities:

- `WO-P1-116` Production Worker Supply + Elastic Capacity — RELEASED.
- `WO-P1-120` Elastic Capacity Fencing + Recovery Hardening — RELEASED.
- PR #211 four-lane coordination SSoT — existing lane/ownership shaping; do not duplicate its mutable scope.
- Issue #216 / ZRA-4 bounded parallel Zero-Relay preflight — existing parallel execution/fan-in authority shaping.
- existing TaskGraph / ReadySet / scheduler / WorkerLease / provider admission / durable job / supervised execution / review / recovery primitives.
- ZRA-1 accepted production execution path from PR #221.
- `WO-P1-162` Universal Agent Entry (PR #219, BINDING) + `WO-P1-163` continuity fold (PR #224) — every fabric participant starts from `00-AGENT-ENTRY.md` -> `PROJECT-GRAPH.yaml` -> actual-state verification; no lane may bypass the entry/claim gate.
- A-Wiki ReviewBus accepted review gates — Issue #53 / PR #55 (exact-head verdict/CI invalidation on HEAD rollover) and Issue #54 / PR #56 (blocker findings stay blocking through `open` AND `addressed`; only `verified` releases PASS/READY). These are the acceptance authorities any fabric review/fan-in semantics must reuse; no second review bus.

Classification for this roadmap: `REUSE -> WRAP -> EXTEND`; `NEW` only for a proven gap. No second scheduler, lease store, provider store, task store, review authority, recovery authority, or SSoT.

## Core architecture

```text
USER GOAL
   |
   v
Planning / Control Pool
   |
   v
Durable Task DAG
   |
   v
READY Frontier
   |
   +--> Capability Router
   |
   +--> Conflict / Ownership / Policy / Admission Gates
   |
   v
Elastic Heterogeneous Agent Pool
   |       |       |       |       |       |
  GPT     GLM    Claude  Gemini   Local   Tools ...
   |       |       |       |       |       |
   +-------+-------+-------+-------+-------+
                           |
                    Frozen Candidate
                           |
                  Independent Review
                     /            \
                  ACCEPT         REPAIR
                    |              |
                    v              +--> READY
             Incremental Fan-in
                    |
                    v
               NEXT READY
```

A-Sunday Conductor remains the **control / trust / authority plane**. External models are bounded workers, planners, reviewers, or specialists; they are not authority merely because of vendor or model identity.

## Non-negotiable concurrency rule

```text
1 MUTABLE HOTSPOT = 1 MUTATION OWNER
```

Parallelism is allowed across independent mutable scopes. The same hotspot may have multiple read-only reviewers/verifiers, but never multiple unsynchronized writers.

Examples:

- 10 independent safe scopes may permit up to 10 mutation lanes.
- 10 available agents but only 2 safe independent scopes means at most 2 mutation lanes; remaining capacity may review, test, research, or stay spare.
- equivalent physical worktrees or alias-equivalent write sets must be treated as the same conflict domain.

## Asynchronous DAG — no global barrier

The system must not wait for all lanes to finish before making progress.

If task D depends only on B:

```text
B ACCEPTED -> D READY
```

D may start even while unrelated C is still running.

Synchronization occurs only at real dependency or authority barriers, not at a global "all agents finished" barrier.

## Incremental fan-out / fan-in

- READY independent nodes may fan out immediately subject to lease/provider/policy/capacity gates.
- each lane freezes an exact candidate/result independently.
- independent review runs against a stable exact candidate.
- accepted independent outputs may merge/fold independently where graph semantics allow.
- a successor becomes READY only when its required predecessors reach accepted terminal state.
- partial batch success is preserved; UNKNOWN lanes are not blindly replayed and do not roll back unrelated successful lanes.

## Work stealing

A free agent may claim another independent READY task only after a fresh admission/ownership gate.

A worker in `REVIEW_WAIT`, `CI_WAIT`, or blocked on an unrelated dependency should not reserve mutation capacity unnecessarily when its claim can be safely released/frozen.

Work stealing must never bypass:

- task ownership;
- worktree/write-set conflict checks;
- WorkerLease;
- provider admission;
- capability/policy requirements;
- exact HEAD/task/result identity.

## Capability-first heterogeneous routing

Do not hard-code architecture such as `coding -> GLM` or `planning -> GPT`.

Route from task requirements to an **eligible capability profile**, then choose among currently authorized/ready providers/models.

Candidate dimensions include:

- task/role capabilities;
- long-horizon coding quality;
- architecture/reasoning quality;
- review/adversarial quality;
- multimodal/visual quality;
- Thai-language/Thai-in-image quality where relevant;
- research/retrieval speed;
- context capacity;
- tool/MCP/plugin availability;
- latency;
- cost;
- current provider capacity;
- recent first-review acceptance rate;
- repair-loop rate;
- deterministic tool reliability;
- observed unsupported-claim / hallucination rate;
- privacy/locality/policy constraints.

Capability scores must come from evidence/benchmark/accepted task history where practical, not permanent vendor stereotypes.

High-risk trust/authority decisions remain independently verified and are never delegated solely because a model has a high capability score.

## Elastic capacity policy

The target is not `LANES = 10`. Active parallelism is bounded by actual safe capacity.

Conceptually:

```text
safe_mutation_parallelism <= min(
  independent_READY_nodes,
  non_overlapping_mutable_scopes,
  eligible_worker_leases,
  provider_admission_capacity,
  policy_limit,
  verification/review_capacity
)
```

Reserve recovery capacity where required. Do not saturate every available provider/worker slot if doing so prevents recovery or creates an unbounded review queue.

## Frozen-candidate review barrier

A reviewer evaluates an immutable candidate/result identity, not a branch that continues changing under review.

Typical flow:

```text
CLAIM -> IMPLEMENT -> VERIFY -> FROZEN SHA/RESULT
      -> INDEPENDENT REVIEW
      -> ACCEPT or bounded REPAIR
```

The builder may return to the pool after a safe freeze/release boundary if durable state allows another worker to perform any later repair.

## Model/provider independence

The architecture must permit future combinations such as:

- GPT planner + GLM long-horizon implementer + Claude reviewer;
- Claude planner + Gemini fast research worker + GLM builder;
- GPT multimodal/visual specialist + local model classifier + deterministic verifier;
- any future MCP/plugin-capable provider satisfying the same contracts.

Provider substitution is never silent. A route is eligible only when required facts equivalent to the existing fail-closed contract are true:

`CAPABLE ∧ READY ∧ AUTHORIZED ∧ ADMITTED ∧ POLICY_OK ∧ RESULT_DESTINATION_BOUND`

UNKNOWN blocks or routes to an explicitly authorized fallback; it never means "try another model and hope".

## Scale progression

Scaling is evidence-gated, not a one-step jump.

### Stage 0 — external reuse audit — COMPLETE FOR SHAPING (2026-09-12)

Deep source/license/trust-boundary audit is complete in the companion research document. Production adoption remains separately gated; no upstream framework becomes authority by completing this research.

### Stage 1 — bounded parallel baseline

Use existing ZRA-4 scope: 2–3 independent READY lanes with exact conflict/admission/fan-in proof.

### Stage 2 — dynamic 4–6 lanes

Only after Stage 1 acceptance. Add adaptive capacity and demonstrate that accepted throughput improves without increasing duplicate/ownership violations.

### Stage 3 — dynamic 8 lanes

Require restart/concurrency/partial-failure/CI-review-backpressure tests plus measured benefit over Stage 2.

### Stage 4 — dynamic 10+ lanes

Only if READY frontier, provider capacity, conflict topology, review capacity, and measured accepted throughput justify it. No architectural constant should require exactly ten workers.

This scale progression must not silently reorder the authoritative ZRA-0 -> ZRA-1 -> ZRA-2 -> ZRA-3 -> ZRA-4 -> ZRA-5 dependency chain. Shaping/research may proceed read-only; production mutation obeys current roadmap/claims.

## Issue #216 ZRA-4 findings this roadmap must reconcile

Classified against the accepted durable record in Issue #216 (GPT1 review verdict + GPT2 gate refresh + Q59 host validation). Nothing in this section authorizes implementation.

### CURRENT ACCEPTED (design verdicts already recorded in #216; reuse, do not reinvent)

- **Two-coordinator convergence** — deterministic per-node job identity + store CAS closes the concurrent-coordinator window; no global lock, no second scheduler.
- **Partial-batch preservation** — `ParallelReadyExecutor` returns one typed `ParallelReadyOutcome` per selected node; there is NO batch transaction/rollback semantic, and that absence is correct. Lane A success + lane B UNKNOWN preserves A, retains B's admission/lease, and never blindly replays B.
- **Fan-in by per-node durable state** — successor node C becomes READY only when every required predecessor reaches canonical `DONE`/`SKIPPED`; mid-batch crash preserves already-committed lanes across restart.
- **Lease never auto-released by elapsed time alone**; UNKNOWN external effect routes to reconcile, never replay.
- **First ZRA-4 acceptance ceiling** — `SchedulePolicy.max_parallel = 2`, raised toward 3 only after 2-lane chaos/restart/fan-in proof; independent read-only review lane accounted separately under WO154's `3 mutable + 1 review` ceiling.

### FUTURE SHAPING (mutation-ready packets; NOT implemented — gated on the ZRA chain + a fresh WO161 activation claim)

- **C1 — physical Windows worktree identity** (GPT1 P1-1): `windows_worktree_key` (normcase+normpath only) does not resolve junctions/symlinks or expand 8.3 short paths; the same physical worktree expressed via alias currently yields two lease identities => double mutation lease + mutable-scope-overlap bypass. Accepted repair direction (Q59-validated on the real Windows host): resolve + explicit `\\?\`/UNC-prefix stripping + normcase/normpath, with an alias-matrix RED (case change + trailing separator + `~1` short path => `WORKTREE_PARALLEL_CONFLICT`; genuinely distinct worktrees still pass).
- **P1-2 — mutable-scope alias overlap**: `write_sets_overlap` matching raw scope strings can miss alias-spelled overlap; scope paths must normalize through the same normalized root (same future commit as C1).
- **C2 — deterministic batch identity**: `zb1:<sha256(canonical graph_run_id + sorted selected job_ids)>`; the pure re-form design is validated, deterministic across restart, and creates no new batch store/authority.
- Required REDs before any ZRA-4 implementation: alias-key matrix; deterministic batch_id re-form; executor-level two-coordinator race; mid-batch generation-drop; one-lane TTL expiry.

### EXPERIMENTAL / NOT ACCEPTED

- `WO-P1-161` remains a **reservation only** — no dedicated worktree/branch, no activation claim, `SAFE_TO_MUTATE_WO161 = NO` until the ZRA predecessor chain and the fresh main/worktree/HEAD/dirty/claim/overlap gate pass.
- Every upstream framework candidate in the companion audit is unverified until its per-candidate audit passes; popularity is not evidence.

## SSoT / state projection requirement

The fabric must operate from canonical actual state, not session memory or manually synchronized Markdown.

Desired direction:

```text
Git / GitHub / runtime / lease / provider / durable job state
                    |
                    v
          canonical actual-state projection
                    |
        +-----------+-----------+
        v                       v
 operator/read model      drift detection
                                |
                         reconcile before
                         dependent mutation
```

Markdown remains durable human-readable continuity, not a competing runtime database.

## Test-integrity requirement

A lesson from WO158/PR221 is binding:

```text
CANONICAL AUTHORITY -> REAL RECORD -> PRODUCTION CONSUMER
```

Trust-boundary tests must include records created by the real canonical store/broker where feasible. Hand-written mocks alone are insufficient if they can represent impossible production states.

## Required failure semantics

- transport failure != execution failure;
- UNKNOWN external effect -> reconcile, never blind replay;
- no broad process kill;
- no duplicate execution authority;
- no global batch rollback for independent successful lanes;
- no implicit ownership release from elapsed time alone;
- provider/capacity ambiguity remains fail-closed;
- stale HEAD/lease/provider-generation/result identity blocks acceptance.

## Performance metrics

Optimize **accepted throughput**, not raw agent count.

Track at least:

- accepted work / hour;
- first-review pass rate;
- repair loops / accepted task;
- human relay actions / accepted external-agent task;
- review latency;
- queue wait time;
- lane utilization;
- provider utilization;
- conflict rejection rate;
- duplicate execution count;
- blind replay count;
- escaped blocking defect rate;
- cost / accepted task;
- median and p95 task lead time.

A higher lane count is rejected if coordination/review overhead makes accepted throughput worse.

## Acceptance vision

The long-term architecture is accepted only when a user can submit a goal and A-Sunday Conductor can safely:

1. decompose it into durable dependency-aware work;
2. discover the READY frontier;
3. route each independent task to the best eligible currently authorized agent/tool;
4. execute multiple non-conflicting lanes asynchronously;
5. freeze and independently verify exact results;
6. repair bounded failures without human prompt/result relay;
7. incrementally release successors as dependencies accept;
8. recover across restart/transport ambiguity without duplicate external effects;
9. scale active concurrency up or down from evidence rather than a fixed lane count;
10. leave durable SSoT/evidence so a new session can resume with zero chat history.

## Immediate next design action

Do not implement a new orchestration subsystem from this document.

The companion upstream reuse audit is complete for architecture shaping. At the 2026-09-17 re-pin, the current durable frontier is Issue #330 / WO246 author-attempt provenance, opened from WO205 Phase-D's `DESIGN_GAP_AUTHOR_ATTEMPT_PROVENANCE`. The older C0/C1/WO208 execution details retained above are historical evidence and must not be replayed merely because they remain in this roadmap. Continue only through current owners and claims in this order: `WO246 provenance acceptance -> resume WO205 Phase D + full ZRA-2 acceptance -> ZRA-3 acceptance -> SunDay Runtime single-device MVP -> two-lane multi-project isolation/recovery proof -> ZRA-4 recomposed bounded-parallel acceptance -> thin SunDayMCP facade -> consumer hardening / optional federation`. Re-pin durable Git/GitHub/task truth again at each dependency release rather than treating this dated projection as live authority.

SunDay Runtime product work (recomposed from Worker Host) no longer waits for ZRA-4: its single-device MVP directly follows ZRA-3 acceptance under the recomposed order, and ZRA-4 recomposed acceptance runs on that isolated substrate. Facade, consumer installer, browser companion, unified monitor, and federation product work remains gated behind ZRA-4 recomposed acceptance plus the isolation/recovery proof. Research-derived P0 invariants may be folded into the existing ZRA contracts/tests only through their current owners and claims; this document grants no source mutation authority. Any future SunDay Runtime implementation requires a fresh work order, exact-main re-pin, ownership/non-overlap gate, RED-first acceptance criteria, and independent exact-SHA review.
