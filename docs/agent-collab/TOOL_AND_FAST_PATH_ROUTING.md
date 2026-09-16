# Tool and Fast-Path Routing

Status: BINDING ROUTING ADDENDUM
Introduced by: WO-P1-228
Purpose: keep ChatGPT Project Instructions short while preserving the core execution surfaces and reducing delivery latency without weakening repository authority.

This file extends, but does not replace:

- `00-AGENT-ENTRY.md`
- `AGENTS.md`
- `PROJECT-GRAPH.yaml`
- `docs/agent-collab/FAST_EXECUTION_PROTOCOL.md`
- `docs/agent-collab/COLLAB_PROTOCOL.md`
- `docs/agent-collab/CAPABILITY_MATRIX.md`

If there is conflict, the higher-authority repository policy and actual runtime/Git evidence win.

## 1. Core surfaces ordinary GPT Chat must remember

The compact ChatGPT Project Instruction should explicitly preserve these as the main project execution surfaces:

| Surface | Primary use | Authority limit |
|---|---|---|
| `SunDay-Worker 1`..`SunDay-Worker 5` | scoped implementation, semantic code navigation, symbol/reference work, test generation, repair, read/write local project files when the Worker has a verified project/worktree/claim | Worker output is a claim until reconciled with Git/durable state/tests/review |
| `Remote Desktop Commander` | multi-device filesystem, shell, process, runtime, logs, local builds/tests, repo-wide inspection, fallback local file operations | RDC online does not imply safe repo/Worker/runtime mutation |
| `GitHub` | remote repository truth, branches, PRs, diffs, issues, exact SHAs, Actions/CI, post-merge evidence | GitHub evidence does not override safety, claims, or local dirty-state protection |

These three are CORE. For every substantial project/engineering session, attempt a lightweight READ-ONLY discovery of all three before mutable work. Trivial Q&A and obvious no-routing work bypass this bootstrap. Do not assume previous session mappings are still valid.

### Substantial-session bootstrap rules

- RDC: identify the exact device/runtime before using filesystem, shell, process, log, build/test or local Git evidence. `RDC ONLINE != SAFE_TO_MUTATE`.
- GitHub: refresh the target repo/default branch, relevant Issue/PR, exact remote SHA and CI/review/post-main evidence when material.
- SunDay-Worker 1..5: probe only exposed Workers for minimal readiness/current-project state. Do not activate/rebind/mutate merely for bootstrap.
- Classify unavailable/busy/mismatched surfaces with the existing typed failure vocabulary. A failed tool blocks only dependent work.
- Before any mutation, the normal repo/worktree/branch/HEAD/dirty/task/owner/claim/scope/non-overlap gate still applies.

The future SunDayMCP product may collapse this UX into one facade, but until that implementation is accepted these remain separate core surfaces and the same authority gates apply.

## 2. Conditional accelerator surfaces

Use these only when the task needs them:

| Surface | Use when | Do not use for |
|---|---|---|
| `OpenAI Developers` | OpenAI API, Agents SDK/API, ChatGPT Apps, tool-calling integration, provider-specific OpenAI implementation | project state authority or secret storage |
| `Vercel` | web Control Center preview, branch/PR preview deploys, deployment logs, post-deploy smoke evidence | merge/acceptance authority |
| `PostHog` | runtime observability, product analytics, feature flags, error/log evidence, LLM analytics when explicitly integrated | task/claim/lease authority |
| `Supabase` | approved backend/auth/storage/realtime architecture | second scheduler/job/claim/lease/retry/review authority |
| `Figma/Product Design` | UI/UX/design-system/prototype work | automatic source mutation without repo gate |

Domain plugins such as Bigdata, Elicit, Metricool, Binance, Alpaca, HeyGen and Canva are not ordinary A-Conductor engineering bootstrap tools. Use them only for their domain-specific tasks.

## 2A. GLM labor-offload assessment

For every substantial multi-step task, perform `GLM_OFFLOAD_ASSESSMENT` while GPT-5.6 Sol remains the integrator and continues useful non-overlapping work.

Use the current evidence-based order:
1. Kilo CLI + CoinTH GLM-5.3 when the exact executable/provider/model, readiness, authorization, permission profile and quota evidence are eligible.
2. Claude Code CLI + GLM-5.3 only after exact route/model/auth/liveness is proven on the current runtime.
3. SunDayWorker/Serena for lightweight semantic/local repository operations.
4. deterministic/native tools when inference is unnecessary.
5. GPT-5.6 Sol directly when it is the best eligible executor or external routes are blocked.
6. GPT-6 Astra only for material unresolved architecture/trust ambiguity, contradictory high-impact findings, or difficult repeated failure after root-cause work.

For Kilo, prefer the exact executable and `kilo roll-call` as a practical liveness probe. Use `docs/runbooks/cointh-glm-quota.md` for CoinTH quota checks only through an approved secret resolver. Never expose/persist the API key. HTTP 401/403 is auth/entitlement evidence, not quota exhaustion; missing/stale/malformed quota evidence remains `UNKNOWN`. Never silently substitute a different or paid model/provider.

Parallel GLM lanes require independent READY work, explicit owners, known worktrees/branches/HEADs, valid non-overlapping claims/leases, declared result destinations and a fan-in plan. `1 MUTABLE HOTSPOT = 1 MUTATION OWNER`.

Record one compact routing result: `GLM_OFFLOAD = DISPATCHED | NOT_BENEFICIAL | BLOCKED`, with bounded reason and safe harness/provider/model/quota-readiness/task/scope/result facts when material. This record is routing evidence, not a new task/provider authority.

## 2B. Dispatch-first / harvest-later throughput rule

For substantial work, GPT-5.6 Sol should decompose the dependency DAG early,
bind independent READY lanes through the existing claim/lease authority, and
dispatch eligible GLM-5.3 labor as soon as each lane is safe. Do not serialize
independent lanes merely to read the previous GLM report first. Sol remains an
active integrator: while delegated lanes run, continue non-overlapping
architecture, integration, deterministic verification, blocker diagnosis, and
routing of the next READY lane. Harvest GLM results later at material fan-in
points, reconcile them against Git/runtime/durable evidence, then repair or
integrate in bounded batches.

This rule optimizes accepted throughput, not agent count or token minimization.
Use available authorized quota productively, but never exceed WIP/provider
capacity, paid-cost approvals, claim/scope boundaries, or `1 MUTABLE HOTSPOT =
1 MUTATION OWNER`. Before every material GLM dispatch, refresh the approved
quota/readiness evidence. `QUOTA_UNKNOWN` means evidence is unavailable;
`RATE_LIMITED` requires observed exhaustion and must not be guessed.

Harness-native commands such as `/goal`, `/plan`, `/init`, skills loops, or
similar Kilo/Claude Code/ZCode features may be used when the exact installed
harness proves support. These commands are execution accelerators only; they do
not replace the durable WO/task packet, claim/lease, result destination,
verification, or GPT acceptance authority.

## 3. Fast path principle

Optimize for accepted outcomes, not number of active agents.

Default delivery:

```text
RECOVER MINIMUM STATE
-> CLASSIFY RISK
-> CLAIM NON-OVERLAPPING SCOPE
-> IMPLEMENT IN ONE COHERENT BATCH
-> TARGETED VERIFY
-> FREEZE CANDIDATE
-> PARALLEL REVIEW + CI AS RISK REQUIRES
-> BATCH REPAIR CONFIRMED FINDINGS
-> ACCEPT / MERGE / POST-MAIN VERIFY / CHECKPOINT
```

Do not run the maximum-assurance loop for every task. Use the lowest risk tier that truthfully covers blast radius.

`FAST_EXECUTION_PROTOCOL.md` remains the authority for each risk tier's verification floor. Fast-path routing may remove redundant ceremony, but it must not weaken that floor. In particular, R2 still requires its adversarial batch, frozen exact-SHA independent review, bounded repair/rereview when needed, and exact-head CI before merge.

## 4. Normal fast path

Use for R0/R1/R2 work that does not touch secrets, durable authority, concurrency, process ownership, release/installers, or provider admission.

```text
1. Recover only the entry files selected by PROJECT-GRAPH.
2. Verify repo/branch/HEAD/dirty/claim/scope.
3. Assign one executor: GPT, Worker, ZCode/GLM, or native tools.
4. Let the executor continue through safe micro-steps without asking the user for "continue".
5. Run targeted + directly related verification.
6. Run the risk-tier adversarial batch before freeze when required; for R2 this is mandatory.
7. Freeze one candidate SHA.
8. Start independent read-only review and CI in parallel according to the risk-tier floor; for R2, independent exact-SHA review and exact-head CI are mandatory.
9. Batch all confirmed findings into one repair pass.
10. Rereview only changed/high-risk boundaries unless the repair broadens scope.
11. Merge only after exact-SHA evidence satisfies repository policy.
```

## 5. High-risk path

Use R3 when the work affects:

- auth/security/secrets
- process/PID ownership
- concurrency, leases, retries, deduplication, idempotency
- durable job/task/claim/graph/protocol authority
- provider readiness/admission/quota/credentials
- installer/release/update path
- high-blast-radius shared state

R3 keeps the full authority/failure-model framing, independent exact-SHA review, strongest deterministic verification, hosted CI, post-main/live/release proof, and durable closeout.

## 6. Parallel review and CI fan-out/fan-in

After a coherent candidate is frozen:

- run deterministic checks/CI and independent read-only review concurrently where possible;
- bind every result to exact repo, branch, task, commit SHA and changed files;
- do not ask multiple reviewers to review moving intermediate commits;
- collect findings once, deduplicate them, classify severity, then repair in one bounded batch;
- do not rerun broad suites or full rereviews unless the repair changes the trusted boundary.

This follows the repository WIP limit unless the active work order explicitly narrows or expands it:

- up to 3 mutable implementation lanes;
- 1 independent read-only review lane;
- spare capacity kept for recovery/blocker diagnosis.

## 7. Anti-loop / anti-latency rules

Stop repeating slow loops.

- Do not reread large docs not selected by `PROJECT-GRAPH.yaml`.
- Do not ask the user to type `continue` when a safe next micro-step exists.
- Do not run full suites after every trivial edit.
- Do not open a PR for each small adversarial finding by default.
- Do not create fresh long prompts when a durable WO/task packet exists.
- Do not poll CI forever; inspect once, classify, then checkpoint if external.
- Do not retry transport/tool failure as if it were product failure.
- Do not retry the same repair twice without new evidence; switch to root-cause mode.
- Do not maximize Worker count merely because Workers exist.
- Do not update `CURRENT-WORK.md`, `handoff.md`, or `COLLAB.md` after every tiny step; checkpoint them at material boundaries.

## 8. Tool failure classification

Classify accurately:

- `PLUGIN_NOT_EXPOSED_TO_CHAT`
- `PLUGIN_AUTH_REQUIRED`
- `RATE_LIMITED`
- `TRANSPORT_FAILURE`
- `DEVICE_OFFLINE`
- `DEVICE_IDENTITY_UNKNOWN`
- `TARGET_RUNTIME_UNKNOWN`
- `WORKER_BUSY`
- `WORKER_STATE_UNKNOWN`
- `ACTIVE_PROJECT_MISMATCH`
- `CLAIM_CONFLICT`
- `DIRTY_WORKTREE_UNEXPLAINED`
- `PERMISSION_FAILURE`
- `RUNTIME_UNVERIFIED`
- `COST_UNKNOWN`
- `UNKNOWN_FAILURE`

A failed tool blocks only the dependent step. Continue other safe independent work when possible.

## 9. Cost-first routing

Use existing/free capacity first. Before paid usage or plan upgrade:

1. identify whether the free/current tier is enough;
2. estimate benefit and cost where possible;
3. provide a free fallback;
4. require explicit user authorization for paid plans, credits, or material pay-as-you-go usage.

OpenAI API billing is separate from ChatGPT subscription.

## 10. Completion invariant

Tools accelerate execution. They do not replace authority.

```text
MODEL PROPOSES
-> CORE SURFACES EXECUTE
-> TESTS/CI/DIFFS VERIFY
-> INDEPENDENT REVIEW CHALLENGES
-> GPT/INTEGRATOR ACCEPTS
-> DURABLE STATE REMEMBERS
```
