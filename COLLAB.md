# COLLAB — A-Conductor Multi-Agent Coordination

> Binding coordination standard: A-Wiki `docs/protocols/cross-agent-work-orders.md`.
> Universal entry is `00-AGENT-ENTRY.md` -> `PROJECT-GRAPH.yaml` -> `AGENTS.md`. Read this file when the project graph selects multi-agent coordination, claims, delegation, or handoff.

## Lanes

| Lane | Theme | Owned scope | Must not touch without a separate claim |
|---|---|---|---|
| `WO-P1-022` | ChatGPT / Sunday-Conducter | 2026-08-20 | `src/a_conductor/tunnel_boundaries.py`, `src/a_conductor/owned_process.py`, `src/a_conductor/__init__.py`, `tests/test_tunnel_boundaries.py`, `tests/test_owned_process.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-022-tunnel-preflight-references.md` |
| ARCH | architecture, contracts, ADRs, plans | `PROJECT-PLAN.md`, `docs/contracts/**`, `schemas/**`, architecture ADRs | runtime/UI implementation |
| RUNTIME | worker/runtime/process/Serena adapters | future runtime/process source + runtime tests | UI and architecture hotspot files |
| VERIFY | deterministic verification, evidence, recovery tests | future verifier/test/evidence tooling | product UI and unrelated runtime internals |
| UI | desktop control center | future UI source/assets | runtime/process internals |
| DOCS | continuity, handoff, operator docs | `AGENTS.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/**`, operator docs | architecture decisions unless explicitly claimed |

A single work order may claim multiple lanes only when the scope is explicit and small. Prefer additive/new files over shared-file edits.

## Hotspot files

These are shared coordination surfaces and must be changed by only one active work order at a time:

- `PROJECT-PLAN.md`
- `AGENTS.md`
- `COLLAB.md`
- `CURRENT-WORK.md`
- `handoff.md`
- future dependency manifests / lockfiles
- future central worker/project registries
- future task-state transition tables
- future shared schema index/version registry

## In-progress claims

| Chunk/WO | Agent | Claimed | Scope (files) |
|---|---|---|---|
| `WO-P1-154` fast execution / risk-tier workflow | GPT-5.6 Sol integrator | MERGED / RELEASED via PR #208 on 2026-09-04 | Binding R0-R3 Fast Execution workflow accepted after independent exact-SHA rereview PASS and exact-head CI. Merge commit `25c08c91317a4d3640ce2308e6166edd382bbad7`; shared hotspot claim released to successor work. |
| `WO-P1-157` GLM-first execution / universal entry | GPT-B | ACTIVE / RECOMPOSED_ON_MAIN 2026-09-05 | Docs/process-only successor to PR #208. Current base is merged `main@25c08c9`; preserves universal entry, task-selective project graph, GLM-first/GPT-governance routing, and Zero-Relay transport-only boundary. Includes post-PR208 `CURRENT-WORK.md` / `handoff.md` continuity fold; no product source/tests/runtime/DB/credentials. |
| `WO-P1-155` Zero-Relay Accelerator | GPT-5.6 Sol gate authority; GLM preview/review lanes | PREVIEW / SHAPING EVIDENCE - NOT ACCEPTED 2026-09-04 | ZRA-0 prerequisite migration mechanism/evidence is pre-proven on sacrificial/valid-registry DBs with live DB untouched, but formal ZRA-0 node acceptance remains PENDING after PR208 merge/reconciliation. ZRA-1 preview/transport-harness evidence only; full authorized/admitted production acceptance PENDING (`653eba9` NOT accepted). ZRA-2..4 production acceptance PENDING. Issues #212-#216 are durable shaping claims/evidence, not proof of completed implementation. WO153 hotspot release already satisfied in `68079e3`. |
| `WO-P1-151` service/Terms authorization binding | GPT-5.6 Sol MAX | READY_FOR_INDEPENDENT_REVIEW 2026-09-03 | Exact repair `6b958f2...`; `provider_service_authorization.py`, focused tests, WO151, bounded `COLLAB.md`; pure/no-I/O only; no store/policy/runtime/live AiPASS. |
| `WO-P1-116` / AHA-6B worker supply + elastic capacity | GPT-5.6 Sol integrator | RELEASED 2026-08-31 | PR #157 + closeout PR #158 merged; source lane released. |
| `WO-P1-117` provider dispatch/admission safety | GPT-5.6 Sol integrator | READY_FOR_CLAIM | `parallel_ready_execution.py`, `provider_config_store.py`, focused tests; baseline CI `33357214028` green; claim requires isolated worktree + fresh preflight. |
| `WO-P1-118` provider config generation/policy | unassigned | QUEUED | Shares `provider_config_store.py` with 117; must not start until 117 releases it. |
| `WO-P1-119` provider output persistence safety | GPT-5.6 Sol Ultra proposed | READY_FOR_CLAIM | supervised Claude capture / smallest owned-process boundary + focused tests; disjoint from 117/120. |
| `WO-P1-120` elastic fencing/recovery | GLM-5.3 MAX proposed | READY_FOR_CLAIM | worker lease/candidate/elastic files + focused tests; disjoint from 117/119. |
| North Star integration | GPT integrator + bounded workers | 2026-08-27 | `feat/north-star-runtime-sunday-family`; preserved; current unique file set does not overlap 117/119/120 planned source files. |

### Recently closed / released claims

- `WO-P1-148` AIP-1 pure service-authorization contract: semantic Terms identity + UTC-normalized chronology binding now require evidence to be observed on/after the declared Terms effective date without timezone-representation drift. REDs `72592db...` + `f458a4a...`; source repair `78f0fa8...`; current checkpoint `adc1c901...`; GPT rerun focused 47/47 + provider matrix 247/247 PASS. No live/store/policy/admission/runtime mutation. All pre-`adc1c901...` CI/review evidence is historical; fresh exact-SHA review remains required.
- `WO-P1-132` / PR #183 AiPASS roadmap: exact docs head `a84f7a8569846c196ba3000f69d9e83eb473ad96`; exact-head CI `33710739794` SUCCESS; merged as `6e96b773aeb0795807cb65abce93956b7702f33e`; post-main `33712217339` SUCCESS. Roadmap claim released to WO148 AIP-1.
- `WO-P3-144` / PR #195 post-reliability closeout: exact docs head `f2d33ed2d63454e6b7f547a016abb07f058d89be`; exact-head CI `33699856774` SUCCESS; merged `cf2a4e7a57bfd22ec55de79c700ec3e4931dc475`; post-main `33704062299` SUCCESS. Final closeout also corrects the AiPASS section 3.4 evidence: explicit written authorization is the documented exception. Claim released to PR #183 / WO132 reconciliation.
- `WO-P1-143` / PR #194 provider Evidence selection-sync remediation: latest exact candidate `720d0328c02f7068d34cc3a5ae31418a9b1ede4b` preserved all 7 reviewed feature blobs; GLM latest-SHA rereview PASS P0/P1/P2/P3=0; exact-head CI `33680012267` SUCCESS; merged as `272953a366f93a7f7dbd8e1e8060fc0f1bacdb88`; post-main `33681115738` SUCCESS. Source claim released.
- A-Wiki Review Bridge dependency is RELEASED: PR #50 head `b04761d5` independent GLM rereview PASS P0/P1/P2=0, merged `588a9072`, post-main `33704270521` SUCCESS. Future A-Conductor adapter must reuse the existing stable mailbox and approved A-Wiki CLI boundary.
- `WO-P2-140` / PR #193 residual owned-process diagnostics: GPT repaired one P2 unbounded diagnostic sequence after GLM handback using `deque(maxlen=64)`. Final head `2238259e264991e1249d1439b206dc9b252c3051`; exact-head CI `33678036552` SUCCESS; merged `787e9be2f108ce3f323bebc20127eb03c2958bfc`; post-main `33679432865` SUCCESS. Source claim released.

- `WO-P1-115` / PR #155 AHA-6A.1 provider admission + production runtime wiring: exact PR head `7959ff9d8a300b2920a2ef1014c63db64b19518c` passed CI `33312763072`; merged as `a758f9e882db03e988d67a3f04f69862dd9195c2`; post-main CI `33313201851` passed Windows/Ubuntu/macOS including Frozen Setup E2E. GLM review + repair re-review found zero P0/P1/P2 defects. Claim released. Automatic live provider dispatch remains fail-closed until active route + complete reset-bearing 5h quota evidence exist.

- `WO-P1-114` / PR #153 AHA-6A automatic provider runtime assembly: exact reviewed head `00d0828816e11110f30299c76d6b5a43e7d5b095` passed CI `33299166993`; merged as `8828f07654746a52110bc89cc359e9e558b2f9e5`; post-main CI `33299559419` passed Windows/Ubuntu/macOS including Frozen Setup E2E. GLM-5.3 MAX review PASS with zero P0/P1/P2 findings. Claim released. Production Drive binding, fresh quota observation and provider-global admission require a new work order before automatic provider dispatch is declared ready.

- `WO-P1-113` / PR #151 AHA-6 parallel READY execution: reviewed feature head `5cc2425580c1724ae34f5f836a2211ee6af06b1d` passed exact-head CI `33293013006`; merged as `7825afa0ae946d0389b5c6b2955a63a8ae36f54b`; post-main CI `33293299053` passed Windows/Ubuntu/macOS including Frozen Setup E2E. GLM repair re-review PASS; implementation claim released. Provider-global batch capacity and automatic CoinTH secret/quota assembly require a new work order.
- `WO-P1-112` / PR #149 + closeout PR #150 AHA-5: durable proposal/result/review/repair bridge merged as `f648e04eba647d3a40b6aaa8353c90714f0a2ea1`; closeout merged as `64b6ef839f16a270295fb2c24649d01e0f54d862`; post-main CI `33286026232` passed Windows/Ubuntu/macOS including Frozen Setup E2E; implementation + closeout worktrees/branches removed after clean tree-equality proof. Claim released to WO-P1-113.
- `WO-P1-111` / PR #147 AHA-4B lease heartbeat + stale-owner recovery: merged as `7f9a16f6dfafe17f3795167da22d4886945611e0`; exact-head and post-main CI passed; claim released to AHA-5.
- PR #108 installer target ownership: merged as `bbb392b1ea459e7e5103232845ec3bd463856dbd`; its old in-progress claim row was reconciled against GitHub and removed on the WO-P1-113 claim checkpoint.
- `WO-P1-102` / PR #131 AHA-4A worker lease broker: final head `9abee8baa7388077f81379e4a909155ad0ebb72a` passed exact-head CI `33251145108`; merged as `b7a2149cb5e40c596ae6934506e1a360263ecc3d`; post-main CI `33256317010` passed Windows/Ubuntu/macOS including Frozen Setup E2E; worktree/local branch removed after clean/no-child merge proof. Claim released to WO-P1-111.

- `WO-P1-100` / PR #130 durable supervised Claude backend assembly: exact head `d3890820174c6a3a59331a30cd97ba1b9d42fe3e` passed Windows/Ubuntu/macOS CI run `33183355995` including Windows packaging/frozen/Portable smoke and merged as `08369ade59206cbe2bc80a314d49d3daa50038b7`; claim released to WO-P1-102.

- `WO-P1-098` / PR #124 supervised Claude runner: final head `25cc69478f73a8cfc154de721ae1c48bb8db7fd2` passed exact-head Windows/Ubuntu/macOS CI run `33176757259` including Windows packaging/frozen/Portable smoke and merged as `e933a53c3c32bf0f8126f1602c913c08765d9a8a`; claim released to WO-P1-100.
- `WO-P1-097` / PR #122 connector CR-1 + CR-3: tunnel-client >=0.0.12 floor + forensic launcher hardening merged as `ceee9bb7aa361aef6d0ecfc210c25b564578d552`; WO-P1-096 still blocks v0.7.0 on CR-2/CR-4 + isolated E2E/soak.
- `WO-P1-095` / PR #121 Claude durable backend: exact head `69fffe7aba40f74ac23ea7c04f9b875c76d7f030` passed GPT re-audit + 3-OS CI run `33164201872` and merged as `0e9b93a7c08cb7b284f2234af61ec6a96b16a2ea`.
- `WO-P1-094` / PR #119 durable graph-dispatch core: final head `70e80c1d958b08137bf5c70a44cca369ac4aadac` passed Windows/Ubuntu/macOS CI run `33159443742` including Windows packaging/frozen smoke and merged as `5cc417c92450eba796fa9af1cf3da037663b1eea`.
- PR #104 / GE-6 deterministic scheduler: exact head `694b8dee053e48d805596b527525cada875848a4` passed GPT re-audit + 3-OS CI and merged as `023c7b65026b0ff536cd1d802d6010e381a4447a`; worktree/local/remote branch removed after ancestry proof.
- `WO-P1-092` / PR #117 harness phase transition: merged as `8db32269f3b1e55a7a551a5a98f6c93b8a30158d`; claim released to AHA-4.
- `WO-P1-091` / PR #116 AHA-3 Claude Code harness adapter: merged as `ab28dc7` on 2026-08-28 after exact-head Windows/Ubuntu/macOS CI green; clean worktree/local/remote branch removed after ancestry verification.
- `WO-P1-090` / PR #114 AHA-2 provider configuration + observation: merged as `ca4cd98` on 2026-08-28 after exact-head Windows/Ubuntu/macOS CI green; clean worktree/local/remote branch removed after ancestry verification.
- `WO-P1-087` / PR #111 priority plan: merged as `457f974` on 2026-08-28; worktree/branch removed after ancestry verification.
- `WO-P1-088` / PR #112 AHA-1 provider/harness contracts: merged as `c3ca84c` on 2026-08-28; AHA-2 consumes this accepted contract.
- `WO-P1-086` / PR #110 capability vocabulary C0: merged as `6487cb2` on 2026-08-28; clean feature worktree/local/remote branch removed after ancestry verification; accepted contract remains on `main`.
- `WO-P1-063`: implementation/release complete; v0.6.0 published from `c870525`; future work leaves this WO.
- `WO-GE-001` decision fan-in: D1-D5 accepted via PR #86; decision claim released. GE-1a is the next implementation slice and must be claimed by its actual implementer before mutation.
- `docs/repo-health-sync`: merged/closed before release integration; no live claim remains.
- `fix/brain-restart-note` / PR #82: merged/closed; no live claim remains.
- `fix/gpu-context-ui-repaint`: superseded by corrective release PR #87; no live claim remains.

> Git remote `origin` = `https://github.com/aase7en/A-Wiki-Conductor.git` (public since 2026-08-22 by explicit user decision — originally created private 2026-08-20). Pull/reconcile before commit/push; record branch/HEAD in checkpoints.

## Rules

1. **Claim before work.** A chunk must have a work order and claim before touching shared scope.
2. Before significant work, run the **A-Wiki reuse-before-build gate** in `AGENTS.md`/`PROJECT-PLAN.md`; inspect GitHub/work orders/live claims when duplicate-work risk exists.
3. Once Git is initialized, pull/reconcile before commit/push and record branch/HEAD in checkpoints.
4. Never edit a file owned by another live claim.
5. Never use destructive Git (`reset --hard`, `checkout -- .`, `clean`) on shared user work; never delete another worktree/branch.
6. Every chunk uses `docs/work-orders/<id>.md`; append a checkpoint whenever stopping, delegating, or changing execution surface.
7. Scope belongs to the work order, not to a vendor/model. Another agent may resume the same WO after verifying state.
8. Additive-first: prefer new bounded files; shared hotspots require explicit ownership.

## Fast execution / risk-tier binding

`docs/agent-collab/FAST_EXECUTION_PROTOCOL.md` is the binding delivery-speed policy introduced by WO154. Use the shortest R0/R1/R2/R3 loop that truthfully matches risk; safety/ownership/secret gates remain mandatory. Default WIP is at most 3 mutable implementation lanes + 1 independent read-only review lane. Freeze a candidate SHA before independent review, batch adversarial findings before review where practical, and avoid repeated full-suite/hosted-CI runs on intermediate SHAs unless risk or failure evidence justifies them.

One logical WO should normally produce one feature PR. Extra RED/adversarial/repair PRs require a concrete remote-CI, independent-ownership, or stacked-dependency reason. Throughput is measured at accepted merge/release, not number of active worktrees.

## GLM-first execution / GPT-governance default

For READY bounded implementation, the default routing preference is now:

`GPT frames contract/authority -> GLM/ZCode executes the owned lane -> deterministic evidence -> independent review when required -> GPT accepts/merges`

This exploits ZCode goal/skills/long-running execution without spending GPT chat turns on repetitive implementation mechanics.

Rules:
- GLM/ZCode may continue implement/test/debug/repair/retest inside its exact WO without repeated human `continue` prompts.
- GPT owns dependency order, risk tier, architecture/trust boundaries, claim/scope, cross-lane conflict, SSoT, final defect adjudication, merge and release.
- R3 requires GPT authority/failure-model framing before GLM mutation; GPT is not merely an after-the-fact reviewer.
- The durable WO/task packet is the prompt contract. Prefer one pointer command over regenerated long prompts.
- Automatic Zero-Relay is optional transport acceleration. Until accepted, the human relays one pointer command; the integrator reads result/evidence directly from the declared destination.
- Provider/model readiness never grants ownership, secret, destructive, replay or merge authority.

Every new lane/session must enter through `00-AGENT-ENTRY.md` -> `PROJECT-GRAPH.yaml` -> `AGENTS.md` -> actual Git/claim state -> continuity core before mutation.

## Integrator routing + parallel-lane contract

The integrator owns dependency order, lane boundaries, merge adjudication and durable checkpoints. It may route GPT MAX, GLM-5.3 MAX, Ultra or future agents in parallel only when mutable scopes are independent and every lane has an exact worktree/branch/HEAD/task/result contract. Read-only review lanes may overlap source observation but must write only their declared result destination.

Routing sequence is binding: recover SSoT and actual Git/runtime/claim state first; settle only material ambiguity; build the dependency graph; classify each READY node R0/R1/R2/R3; claim only non-overlapping READY nodes; then execute the tier-specific loop in `FAST_EXECUTION_PROTOCOL.md`. Do not mechanically force every node through the heaviest review/full-suite/E2E path. Exact-head CI, independent review, post-merge proof and release E2E remain mandatory when the node's risk tier requires them.

Agent-to-agent continuity is file-first. Each lane reuses `runs/<task-id>/task.md` plus stable `status.json` and `result.md|json` destinations. Agents update those agreed files in place; they do not create a new handoff/result file for every exchange. The integrator reads them directly and folds only verified conclusions into tracked SSoT.

If the product cannot yet dispatch an external agent automatically, the human acts only as a transport for one pointer command such as `GLM-5.3 MAX: Read A:\...\runs\<task-id>\task.md and execute it.` No result copy-back is required. Automatic dispatch is a roadmap capability, not permission to weaken claim/provider/security gates.

## Pause → Resume

Before pausing or delegating:

1. record actual state/evidence;
2. update active WO checkpoint;
3. update `CURRENT-WORK.md`;
4. update `handoff.md`;
5. release/transfer claim when the coordination backend supports it.

Resume sequence:

`00-AGENT-ENTRY.md -> PROJECT-GRAPH.yaml -> AGENTS.md -> actual repository/runtime/Git/claim reconciliation -> CURRENT-WORK.md -> handoff.md -> active work order -> task-relevant graph nodes`

Never blindly repeat a mutation merely because the previous agent/session disappeared.

## Closed claim — AHA-5 multi-agent review/repair loop (2026-08-30)

- Task: `AHA-5 / WO-P1-112` — COMPLETE; PR #149 merged as `f648e04eba647d3a40b6aaa8353c90714f0a2ea1`; post-main CI `33284585961` SUCCESS.
- Integrator owner: GPT-5.6 Sol
- Worktree: `A:\GitHub\A-Wiki-Conductor-aha5-review-repair`
- Branch: `feat/wo-p1-112-aha5-agent-review-repair-loop`
- Base: `7f9a16f6dfafe17f3795167da22d4886945611e0`
- Mutable scope: AHA-5 task/result packet, harness mutation boundary, supervised execution integration, tests, and provider-neutral `docs/agent-collab/*` only.
- Forbidden: live connector/release soak, UI, North Star, credentials, A-Wiki mutation, unrelated scheduler semantics.
- GLM/future-agent mutation requires its own bounded sub-lane + exact lease + non-overlapping scope recorded in WO-P1-112 before edit.
- Agent output is not transferred through chat as authority; task/result/evidence refs in durable repo state are authoritative.
- Merge/release authority remains GPT integrator + deterministic gates.
