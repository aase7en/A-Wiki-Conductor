# Capability Fabric Upgrade Plan — A-Sunday Conductor + A-Wiki

Date: 2026-08-27
Status: PLANNED / NO PRODUCTION IMPLEMENTATION IN THIS LANE
Parent: `docs/work-orders/WO-P1-085-capability-upgrade-plan.md`

## 1. Objective

Upgrade the combined A-Sunday system without creating a second brain, scheduler, lifecycle, or skill registry.

Target operating model:

- **A-Wiki** = brain authority: durable knowledge, policy, reusable skills, research/intake intelligence, long-term lessons.
- **A-Sunday Conductor** = control-plane authority: durable task/job identity, capability routing, runtime/provider selection, safety gates, execution, evidence, recovery, verification/review.
- **Runtimes/providers/tools** = replaceable execution or information capabilities only.
- **Bridge** = versioned contracts between brain requirements and Conductor execution capabilities; no direct access to A-Wiki private `.tmp` internals.

The upgrade is called **Capability Fabric v1** in this plan. The name is descriptive, not a new product or separate state machine.

## 2. Safety / actual-state basis

This plan was created in isolated worktree `A:\GitHub\A-Wiki-Conductor-capability-plan-main` from `origin/main@64bc628` on branch `docs/wo-p1-085-capability-upgrade-plan`.
Verified boundaries at planning time:

- shared `A:\GitHub\A-Wiki-Conductor` is stale/dirty and remains read-only;
- PR #102 / GE-005A and PR #104 / GE-6 have separate GLM-owned worktrees and are out of scope;
- North Star N2 runtime-catalog work already exists and must be extended, not recreated;
- North Star N3 Desktop Commander transport has a separately delegated bounded lane and must not be overlapped;
- GE-7 has an accepted durable-dispatch ADR but production dispatch implementation is not assumed complete;
- A-Wiki is HOLD/read-only from this A-Conductor project; A-Wiki mutations must happen separately inside Project A-Wiki.

## 3. Reuse-before-build verdict

| Area | Existing authority | Upgrade classification |
|---|---|---|
| Capability domain | `domain.Capability`, `Runtime`, `Provider`, `Agent`, `Worker` | **EXTEND** |
| Runtime selection | `runtime_catalog.py` / North Star N2 | **EXTEND** |
| Scheduler | GE-6 | **REUSE**, then feed richer snapshots |
| Durable execution | GE-7 + existing job control/dedup/recovery | **REUSE + WRAP** |
| Brain bridge | GE-0005 | **REUSE** |
| A-Wiki skill authority | `skills-registry.json` | **REUSE** |
| A-Wiki brain intake | Brain Improvement Gate | **REUSE + EXTEND** |
| External skills/frameworks | upstream repositories | **CATALOG / CHERRY-PICK**, never bulk-install |

No parallel `CapabilityRegistry` database should be invented merely because the external article used that phrase.
## 4. Capability Fabric v1 model

A capability should be routable only when Conductor can answer, from evidence:

- What stable capability ID is required?
- Which runtime/provider/agent can supply it?
- Is that provider **AVAILABLE** from an explicit observation, not inferred configuration?
- What read/write/network/device authority does it require?
- What risk and human-approval policy applies?
- What direct/usage cost class applies?
- What data may leave the machine?
- Which credentials are required, and where are they securely resolved?
- What dispatch mode applies (`INTERACTIVE_PULL`, `PROGRAMMATIC_PUSH`, or future accepted mode)?
- What deterministic evidence proves the operation/result?
- What fallback is allowed, and what fallback is forbidden?

Recommended optional metadata, added at existing seams rather than a second registry:

```text
capability_id / version
provider/runtime identity + family
availability + observation provenance + observed_at
permission class + mutation intent + approval requirement
cost class + network/data-egress class
credential requirement (reference only)
dispatch mode
verification/evidence type
fallback policy
health/degradation reason
```

Unknown authority, identity, availability, or evidence must fail closed.
## 5. Priority external capability intake

### P0 — highest ROI

1. **Agent-Reach** — research/social capability adapter. Use primary/fallback/doctor ideas, but Conductor remains routing authority.
2. **GitHub MCP Server** — repository provider. Reuse its scoped toolset/read-only/lockdown patterns as input to Conductor permission policy.
3. **Playwright MCP + webapp-testing patterns** — verification provider for browser E2E, console, screenshot, network, and user-journey evidence.
4. **MarkItDown** — A-Wiki ingestion adapter for PDF/DOCX/PPTX/XLSX/HTML normalization under raw-first provenance.
5. **Capability policy metadata** — internal Conductor extension needed before broad provider activation.

### P1 — targeted brain improvement

6. **Superpowers / Addy agent-skills / Karpathy / gstack** — delta audit only; import genuinely stronger methods, reject duplicated instruction layers.
7. **Impeccable** — evaluate as deterministic/structured design-review delta under A-Wiki `A-Design`.
8. **last30days** — recent/trend research adapter under A-Wiki research; social engagement is a signal, never factual ground truth.
9. **MarketingSkills** — cherry-pick missing CRO/SEO/analytics/experiment capabilities into existing `A-Content` routes.
10. **Charlie social-media-skills** — prioritize `post-scorer`, `voice-builder`, `content-matrix`, `niche-research`, analytics, and reels scripting deltas.

### P2 — optional / experimental

11. **HyperFrames** — deterministic media/video rendering capability; preferable for repeatable automation before opaque hosted generation.
12. **Mem0** — retrieval/cache experiment only; never canonical truth or replacement for A-Wiki durable memory.
### Catalog/fallback/defer rules

- **Apify**: specialized/cost-aware fallback provider, not default research path.
- **NotebookLM / Gemini Notebook**: export/briefing surface; not memory authority.
- **Claude-Mem**: session/retrieval cache candidate only.
- **OpenMontage**: later media pilot after deterministic media seam is stable.
- **OpenCut**: defer until its agent/headless API is mature enough to benchmark.
- **ManyChat / Higgsfield**: optional business/media providers, not core brain dependencies.
- **agency-agents / awesome-claude-skills / wshobson agents / large Claude skill collections**: searchable upstream catalogs only.
- Existing A-Wiki `ui-ux-pro-max`, `taste-skill`, `frontend-slides`, and `social-publisher` are already canonical; do not reinstall or fork them.

## 6. Delivery phases

### C0 — Capability/vocabulary reconciliation [P0, read-only first]

Goal: produce one versioned mapping between A-Wiki required-capability vocabulary and Conductor capability IDs.

Actions:
- inspect current A-Wiki task capability enum + skill registry + Conductor `Capability` strings;
- identify exact duplicates, aliases, missing execution capabilities, and provider-only traits;
- define compatibility/versioning rules;
- explicitly keep brain taxonomy and runtime observation as separate concerns.

Exit: reviewed mapping contract; no scheduler or lifecycle mutation.

### C1 — Conductor capability metadata extension [BLOCKED on North Star integration ownership]

Extend the existing runtime catalog with optional typed metadata/policy references. Do not replace N2.
Acceptance:
- no polling/network/process work merely to build the catalog;
- current runtime selection behavior remains deterministic;
- missing observations remain UNKNOWN/non-selectable;
- metadata can describe permission, risk, cost, egress, dispatch and evidence without vendor-specific scheduler logic.

### C2 — Permission / risk / cost policy seam [after C1]

Define policy that answers whether a capability may execute, not merely whether a provider can perform it.

Minimum policy dimensions:
- read-only vs mutation;
- local filesystem / Git / browser / network / remote-device authority;
- human approval class;
- public/private/sensitive data-egress constraints;
- credential requirement by secure reference;
- free/local/paid cost tier and bounded budget;
- required evidence and fallback constraints.

Start deterministic and configuration-driven. A model may recommend; it must not silently grant itself authority.

### C3 — P0 providers [after policy seam; independent adapters where safe]

Implement/benchmark adapters separately:
- GitHub MCP: bounded repository operations and permission mapping;
- Playwright: VERIFY/E2E evidence provider;
- Agent-Reach: multi-source research/social access with explicit backend/health/fallback observations.

Each adapter must be optional, lazily loaded, independently disable-able, and have typed failure/degradation states.
### C4 — A-Wiki brain intake [separate Project A-Wiki execution]

Run the separate prompt in `docs/prompts/A-WIKI-BRAIN-CAPABILITY-UPGRADE-PROMPT.md` inside Project A-Wiki.

A-Wiki owns:
- MarkItDown/raw-first ingestion experiment;
- research/trend skill deltas;
- A-Design Impeccable delta evaluation;
- A-Content marketing/social analytics delta evaluation;
- external skill catalog/index/scouting workflow;
- upstream freshness/license/security/context-cost evaluation;
- optional retrieval/cache experiments.

A-Conductor does **not** directly edit A-Wiki in this lane.

### C5 — Cross-repo capability bridge [after C0 + compatible brain work]

Define a small versioned bridge contract:

`A-Wiki requirement -> capability ID/version -> Conductor observation/policy -> eligible execution surface -> evidence -> brain-facing result`

Rules:
- A-Wiki plans/policy may require a capability but cannot claim a runtime is actually available;
- Conductor owns current worker/runtime/provider observations and execution authority;
- no direct reads of A-Wiki `.tmp` implementation stores;
- aliases/version drift are explicit and testable;
- unknown/mismatched versions fail closed or require an accepted compatibility rule.

### C6 — End-to-end capability execution proof [after GE-6/GE-7 gates]

Prove one low-risk vertical slice through the existing durable lifecycle:

`goal -> plan/task requirement -> schedule -> capability/policy match -> durable claim/gate -> execute -> evidence -> VERIFYING/REVIEW -> checkpoint -> learning input`
Required C6 failure scenarios:
- provider unavailable after scheduling;
- permission/approval NO-GO before execution;
- transport loss with uncertain execution state;
- duplicate retry/dispatch;
- stale project/runtime identity;
- oversized result requiring bounded evidence storage;
- fallback candidate exists but violates policy;
- verification fails and enters repair rather than false COMPLETE.

### C7 — Media + retrieval experiments [P2]

Only after the core capability path is measurable:
- HyperFrames deterministic media adapter;
- OpenMontage comparison/pilot;
- Mem0 retrieval experiment against A-Wiki native FTS/graph/ledger baselines.

Keep pilots reversible. A retrieval benchmark must prove value before introducing an always-present dependency.

### C8 — Operator UI [last]

Expose capability routing only after semantics are stable:
- selected runtime/provider and why;
- availability/provenance;
- permission/risk/approval;
- cost/network/data-egress class;
- degraded/fallback state;
- evidence link/status.

UI must not become a second control plane or invent READY from configuration.

## 7. Routing policy direction

Default preference should remain **cheapest/safest sufficient capability**, not “most powerful tool every time”:

1. deterministic local/native operation;
2. local index/script/cache;
3. Serena for semantic code intelligence;
4. specialized free/local provider;
5. external/network provider;
6. paid provider or expensive model only when materially justified.

Exact ordering is policy, not hard-coded vendor prestige. Cost must never override required safety, correctness, or capability.
## 8. Dependency / ownership gates

Do not start implementation merely because this plan exists.

- C1 must reconcile with the integrated North Star N2 branch before editing runtime-catalog/domain seams.
- C2/C3 must not overlap WO-P1-080 or any still-live runtime/transport claim.
- Scheduler-facing routing changes wait for GE-005A + GE-6 reconciliation and accepted GE-7 implementation seams.
- Any new shared schema/central registry file is a hotspot and requires an explicit claim.
- A-Wiki changes occur only under A-Wiki's own claim/Brain Improvement Gate in its own project/session.
- No live connector ports 18011–18015 are test targets for destructive lifecycle/E2E work.

Safe parallelism comes from independent adapters/research with separate worktrees and files, not several workers “improving capabilities” broadly.

## 9. Global acceptance criteria

Capability Fabric v1 is acceptable only if all applicable statements are proven:

1. No second scheduler, task/job lifecycle, retry counter, execution store, or skill registry was introduced.
2. Existing Conductor `Capability` / runtime-catalog / GE scheduler/job-control seams remain authoritative.
3. A-Wiki remains brain/memory/policy authority; memory adapters are caches/retrievers only.
4. External skill frameworks are delta-audited rather than bulk-installed.
5. Disabled providers impose near-zero idle CPU/network/process cost.
6. UNKNOWN availability/identity/permission fails closed.
7. Permissions, mutation intent, approval, cost, egress and evidence requirements are explicit.
8. Provider/runtime failures are typed and do not silently masquerade as code/task failure.
9. Duplicate/retry and transport-loss paths reconcile durable state before relaunch.
10. Verification evidence outranks provider/model claims.
11. Capability vocabulary/version mapping is deterministic and tested across the A-Wiki bridge.
12. No secrets, raw credentials, private data, or machine-specific sensitive values enter tracked public files.
13. Relevant Windows/Linux/macOS tests remain green; realistic E2E/audit covers high-risk adapters.
14. A new agent can resume from durable work orders/specs/evidence without this chat.

## 10. Recommended next safe actions

1. Finish/reconcile current North Star / GE / release ownership gates; do not steal their scopes.
2. In A-Conductor, start **C0 read-only vocabulary reconciliation** as the next new capability-engineering slice.
3. In the separate Project A-Wiki, run the saved brain-upgrade prompt and let A-Wiki create its own work orders/claims.
4. Reconcile the two outputs at the small versioned capability bridge before coding C1/C2.
5. Implement one vertical low-risk capability slice before adding a large provider catalog.

The architectural target is not “Claude + many add-ons.” It is a governed capability fabric where the brain knows **what** capability is appropriate and Conductor proves **whether, where, and under what authority** it can safely execute.
