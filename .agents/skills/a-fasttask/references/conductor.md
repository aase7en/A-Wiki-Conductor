# A-FastTask reference — conductor roles, WIP capacity, executor fallbacks

Pointer file only (WO-P1-245; session-routing fold WO-P1-247). Authority lives
in the referenced files; this reference adds none. On any conflict,
`00-AGENT-ENTRY.md`, `AGENTS.md`, `PROJECT-GRAPH.yaml`,
`docs/agent-collab/CAPABILITY_MATRIX.md`, and
`docs/agent-collab/TOOL_AND_FAST_PATH_ROUTING.md` win.

The canonical generic A-FastTask skill is owned by A-Wiki. This file is the
A-Sunday Conductor repo-specific binding/projection, not a global policy fork.

## Role binding (routing preferences, never authority)

| Role | Default route | Boundary |
|---|---|---|
| GPT-5.6 Sol (integrator) | planning, task packets, authority/failure framing, integration, adjudication, continuity, acceptance, authorized merge/release | current claim and risk-tier evidence govern; Sol keeps useful non-overlapping work while delegated lanes run |
| GLM-5.3 via accepted Kilo CLI / Claude Code CLI | bounded implementation, fixtures, targeted tests, mechanical edits, root-cause reproduction, repair batches | exact scope/result destination; no autonomous merge, policy change, or claim transfer |
| SundayWorker / Serena | local semantic navigation, bounded repository tools | Worker output is a claim until reconciled with Git/durable evidence |
| GPT-6 Astra / Codex (exceptional specialist) | narrow decision/review after one recorded Sol escalation | return implementation to Sol/GLM; not a routine worker or mandatory gate |
| RDC / GitHub / deterministic native tools | filesystem/shell/process evidence, remote truth, exact SHAs, CI, hashes, tests, builds | no mutation or acceptance authority by themselves |

No model, provider, tool, or plugin name is an authority. Routing identity never
transfers claim, mutation, provider, or acceptance authority.

## Substantial-session read-only bootstrap

Before mutable work in a substantial project/engineering session, attempt:
1. RDC — discover exact device/runtime and use it for filesystem/shell/process,
   logs, local Git, builds and tests. `RDC ONLINE != SAFE_TO_MUTATE`.
2. GitHub — refresh repository/default branch, relevant Issue/PR, exact remote
   SHA, CI/review/post-main truth when material.
3. Exposed SunDay-Worker 1..5 — discover minimal readiness/current-project
   state without activating, rebinding or mutating merely for bootstrap.

Do not block unrelated safe work because one surface is unavailable. Reuse the
typed failure vocabulary from `TOOL_AND_FAST_PATH_ROUTING.md`, including
`PLUGIN_NOT_EXPOSED_TO_CHAT`, `WORKER_BUSY`, `ACTIVE_PROJECT_MISMATCH`,
`DEVICE_OFFLINE`, `TRANSPORT_FAILURE`, and `RUNTIME_UNVERIFIED`.

Trivial Q&A and obvious no-routing work bypass this bootstrap.

## GLM labor-offload assessment

Every substantial multi-step task records whether useful bounded independent
labor exists. Preferred current routing order:

1. Kilo CLI + CoinTH GLM-5.3 when exact executable/provider/model, liveness,
   authorization, permission profile and quota/readiness evidence are eligible.
2. Claude Code CLI + GLM-5.3 only after the exact route/model/auth/liveness is
   proven on the current runtime.
3. SundayWorker/Serena for lightweight semantic/local repository operations.
4. deterministic/native tools when model inference is unnecessary.
5. GPT-5.6 Sol directly when it is the best eligible executor or external
   routes are blocked.
6. GPT-6 Astra only for material unresolved architecture/trust ambiguity,
   contradictory high-impact findings, or difficult repeated failures.

For Kilo, prefer the exact installed executable and `kilo roll-call` as a
practical liveness probe. Before material dispatch, resolve the CoinTH quota
credential from an approved secret source: an existing environment binding, or
an approved global secret file/resolver when the environment is empty. The
current live-proven secret name is `COINTH_GLM_AUTH_TOKEN`; pass its value only
as `x-api-key` to `GET https://cointh.com/glm/api/quota`. Never print, log, or
persist the key. HTTP 401/403 is auth/entitlement evidence, not quota exhaustion;
missing/stale/malformed evidence remains `UNKNOWN`. Never silently substitute
another or paid model/provider.

Record one compact disposition:
`GLM_OFFLOAD = DISPATCHED | NOT_BENEFICIAL | BLOCKED`, with reason, safe
harness/provider/model/quota-readiness facts, task/claim/scope and result
destination when material. This record routes work; it does not create a new
provider/job/task authority.

### Dispatch-first / harvest-later discipline

For a substantial task, Sol should form the dependency DAG early and bind as
many independent READY lanes as the existing WIP/provider gates permit. Launch
eligible GLM lanes as soon as their exact scope/result destination is bound;
do not wait for lane A merely because lane B is independent. Sol continues its
own non-overlapping architecture/integration/verification work and may bind the
next independent lane while GLM runs. Harvest and reconcile result packets at
material fan-in points, not after every dispatch.

This is aggressive pipeline filling, not unbounded spawning. Never exceed WIP,
quota/capacity, cost approval, or ownership gates; never create overlapping
writers. Do not optimize for token minimization when current authorized quota is
available, but avoid redundant prompts/rereads that do not increase accepted
throughput. Before every material GLM dispatch, refresh approved quota evidence.
If the five-hour tuple is unavailable, record `QUOTA_UNKNOWN`; do not report
`RATE_LIMITED` unless exhaustion is actually observed.

Kilo/Claude Code/ZCode-native slash or goal commands (for example `/goal`,
`/plan`, `/init`) may be used when the exact installed harness supports them.
They can improve long-running execution but never grant claim, scope, provider,
merge, or acceptance authority.

## WIP behavior

`PROJECT-GRAPH.yaml` `rules.default_wip` is the capacity authority: up to 3
mutable implementation lanes and 1 independent read-only review lane, with
spare capacity kept for recovery/blocker diagnosis.

- A free mutable lane is filled by claiming non-overlapping scope through the
  existing claim/lease authority — never by creating a parallel task list.
- Parallel GLM work requires independent READY scope, explicit owner, known
  worktree/branch/HEAD, valid claim/lease, result destination and fan-in plan.
- `1 MUTABLE HOTSPOT = 1 MUTATION OWNER`; available models/Workers do not
  justify overlapping writers.
- WIP full => NO new mutable lane. Return the typed blocker, live-lane inventory
  and exact next safe action.
- Review traffic never occupies mutable-lane budget; reviewers read frozen
  exact candidate identities only.

## Executor fallback (failure → next route)

Classify the failure with the codes in
`docs/agent-collab/TOOL_AND_FAST_PATH_ROUTING.md` section 8, then degrade
without widening scope:

1. SundayWorker `PLUGIN_NOT_EXPOSED_TO_CHAT`, `WORKER_BUSY`, or
   `WORKER_STATE_UNKNOWN` => use the next eligible existing route for the same
   bounded task; never wait on an unexposed Worker or build a second queue.
2. GLM route `RATE_LIMITED`, `TRANSPORT_FAILURE`, `AUTH_REQUIRED`, or unverified
   route => use only an explicitly eligible fallback or checkpoint for Sol;
   never silently substitute another model/provider.
3. Unclassifiable failure => `UNKNOWN_FAILURE`: checkpoint through the lane's
   declared result/evidence destination at a material boundary and report the
   exact blocker.

A failed tool blocks only the dependent step; other safe independent work may
continue.
