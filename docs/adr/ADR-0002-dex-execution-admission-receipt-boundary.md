# ADR-0002 — DEX execution admission and receipt boundary across A-Sunday Conductor and SunDayRemoteMCP

Date: 2026-09-19
Status: ACCEPTED ARCHITECTURE DIRECTION / RUNTIME IMPLEMENTATION GATED BEHIND WO-P1-259 + WO-P1-260 ACCEPTANCE
Issue: #348
Author packet: DEX-ARCH-1 (docs branch `docs/dex-arch-1-contract-freeze`)
Normative contract: `docs/contracts/execution-admission-receipt-v1.md`

Extends (does not supersede): `ADR-0001-mcp-gateway-deferred.md` (control-plane /
execution-substrate split), `docs/agent-collab/TOOL_AND_FAST_PATH_ROUTING.md`
(repo-role topology single definition home), `docs/contracts/resilient-execution-supervisor.md`,
`docs/agent-collab/EXECUTION_LIVENESS_PROTOCOL.md`.

## Context

The DEX defect class (WO-P1-250, Issue #339): a ChatGPT turn/context ends while
dispatched Kilo/GLM processes outlive the observer. Governing invariants
`CHAT/TURN LOSS != EXECUTION FAILURE` and `NEW SESSION != NEW TASK` are already
accepted, and DEX-0/DEX-1 policy (durable dispatch pointer, A-FastTask entry
recovery) landed via PR #345. Cross-repo binding semantics (authority repo vs
execution substrate repo, exact-SHA compatibility sets) were frozen by WO-P1-251.

The remaining unfrozen boundary is the delegated-execution seam itself: when
A-Sunday Conductor dispatches physical execution onto the SunDayRemoteMCP (SRM)
substrate, who admits an attempt, who supervises the live process, who collects
evidence, who receipts it, and who may authorize retry. Without a frozen answer,
each side can silently grow the other's authority (substrate accepting tasks,
control plane supervising foreign processes, or neither owning reconciliation).

## Decision

The cross-repo authority boundary for delegated execution is:

1. **A-Sunday Conductor (A-Conductor) is the sole control plane.** It owns
   canonical task/work-order/claim authority, execution admission decisions,
   reconciliation, evidence receipt, retry authorization, review, and
   acceptance.
2. **SunDayRemoteMCP (SRM) owns physical execution supervision and immutable
   collection evidence only.** It launches, supervises, observes, quiesces, and
   collects the processes it hosts, and records immutable evidence about them.
   It never decides task or attempt admission, task completion, retry, review,
   or acceptance, and it is never a source of accepted task state.
3. **A-FastTask routes and binds only.** It selects and invokes existing
   authorities; it owns no execution lifecycle state (unchanged from WO-P1-250).
4. **Substrate collection markers are advisory, never acceptance.** Any
   SRM-side terminal marker, result file, or status flag is evidence awaiting a
   Conductor receipt. A task is accepted/completed only through Conductor
   authority.
5. **Transport/session loss != process failure.** The resilient-supervisor
   invariant carries across the repo boundary unchanged: loss of the
   MCP/tunnel/chat session never classifies the physical process.
6. **Outcome-known != retry-authorized.** Even a verified terminal outcome of
   one attempt never authorizes replay by itself; retry requires Conductor
   reconciliation under claim-generation and replay-safety authority.
7. **Repo drift is asymmetric.** Old terminal evidence may be collected
   (read-only harvest) even when the worktree HEAD/dirty state drifted after
   dispatch; granting any *new* mutation under drift remains fail-closed.
8. **Cross-repo interface acceptance binds an exact SHA pair/set.** A DEX
   interface release is accepted only as a WO-P1-251 compatibility set
   `{A-Wiki-Conductor@SHA_AUTH, SunDayRemoteMCP@SHA_EXEC}`; any member head
   drift invalidates the set until re-pin and focused review.
9. **No raw secret-bearing argv/env in durable evidence.** Durable admission,
   supervision, collection, and receipt evidence carries allowlisted credential
   references and bounded/redacted command shape only.
10. **Threat model: trusted-local-process MVP.** The v1 boundary assumes the
    local executor/shim is trusted. Hardening against a hostile local executor
    is a future explicit threat-model decision; it must not be assumed as an
    implicit property of v1.

## Rejected alternatives

- **SRM owning receipt/task truth** — turns the execution substrate into a
  second control plane and second SSoT; violates ADR-0001's substrate-only
  rule and the repository no-second-authority rule.
- **Chat/session state as execution truth** — chat memory is never the bridge
  between dispatch and harvest (WO-P1-250); sessions end while processes live.
- **Broad PID/process heuristics** — ownership and liveness decisions from
  name/pattern-scanning processes are forbidden; only exact process creation
  identity with PID-reuse defense qualifies, and broad kill remains forbidden.
- **Blind retry** — replaying a dispatch because a response was lost or a
  session ended can duplicate durable mutation; replay requires explicit
  replay-safety classification plus Conductor retry authority.

## Consequences

- DEX-2 splits into DEX-2a (SRM physical supervision; WO-P1-259,
  `EXECUTION_SUBSTRATE_ONLY`) and DEX-2b (Conductor reconciliation + receipt;
  WO-P1-260, `CONTROL_PLANE_ONLY`).
- `docs/contracts/resilient-execution-supervisor.md` and
  `docs/contracts/fault-injection.md` reference the normative
  admission/receipt contract instead of duplicating it.
- DEX-6 deterministic fault coverage moves earlier and runs continuously as a
  prerequisite gate for DEX-2a/2b rather than a late E2E step.
- No new scheduler, task DB, claim store, receipt/completion authority beyond
  the Conductor seam, project SSoT, or secret store is created by this ADR.
