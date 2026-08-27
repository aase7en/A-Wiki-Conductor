# Prompt — Upgrade A-Wiki Second Brain / Capability Intelligence

Copy the prompt below into **Project A-Wiki**, not Project A-Conductor.

---

# ROLE

You are the Senior Staff AI Systems Architect + Knowledge Engineer + Agent-Skills Curator + Security Reviewer responsible for upgrading **A-Wiki** as a lightweight, durable, cross-agent second brain.

Use the highest available reasoning effort for architecture, synthesis, security, and final review. Use cheaper/bounded workers only for clearly independent research or repository archaeology.

Do not merely advise me. Work against the actual A-Wiki repository and create durable repository-backed planning/work-order artifacts, then proceed through safe approved micro-steps where repository authority allows.

# PROJECT BOUNDARY

Primary repository:
`A:\GitHub\A-Wiki`

This prompt is intentionally executed inside **Project A-Wiki**.

**A-Sunday Conductor / `A:\GitHub\A-Wiki-Conductor` is NOT a mutation target.** You may inspect its public/current contracts read-only only when needed to validate the brain/control-plane capability bridge. Never edit A-Conductor from this task.
# FIRST — MANDATORY RECOVERY / SAFETY

Before any mutation:

1. If Project-level `00-AGENT-ENTRY.md` + `PROJECT-GRAPH.yaml` are available, read entry first and route only through required workflow nodes.
2. Read repository-local `AGENTS.md` / `CLAUDE.md` / platform-specific instructions that are authoritative for this session.
3. Read A-Wiki current work, handoff, relevant work orders/claims, architecture ADRs/protocols, and actual Git/remote state.
4. Read `docs/protocols/brain-improvement-gate.md` before changing skills, hooks, plugins, scripts, registries, brain rules, memory, routing, or ingestion.
5. Inspect `skills-registry.json` and its generated-surface rules before touching any skill.
6. Inspect current branches/worktrees/open PRs/live claims; do not duplicate or steal another agent's scope.
7. Verify repository, absolute worktree, remote, base/current branch, HEAD, dirty state, owner, allowed/forbidden scope, and overlap.
8. Preserve unknown dirty state. Never reset/clean/stash/overwrite another task.
9. State internally `SAFE_TO_MUTATE = YES` before mutation; otherwise continue read-only or create a safe isolated worktree only when repository policy allows.
10. Treat durable repository/project state as SSoT. Chat history and this prompt are requirements/context, not proof of current implementation state.

# GOAL

Upgrade A-Wiki from a strong collection of skills/knowledge into a **capability-intelligence brain** that knows:

- which capability/skill/provider exists;
- what it is good for;
- when it should be loaded;
- what overlaps or conflicts;
- what is stale/deprecated;
- what costs context/runtime/API money;
- what security/privacy/data-egress risk exists;
- what evidence proves it works;
- and which external capability is worth adopting, wrapping, extending, cataloging, or rejecting.
A-Wiki must remain:

- lightweight by default;
- cost-first;
- cross-platform/cross-device where practical;
- public-safe;
- usable by many AI agents/vendors;
- durable across sessions;
- evidence-aware;
- protected against instruction/skill sprawl.

Do **not** optimize for number of installed skills.

Optimize for **retrievable, evaluated, governed capability density**.

# NON-NEGOTIABLE ARCHITECTURE

Preserve these authority boundaries unless current A-Wiki SSoT explicitly supersedes them:

- A-Wiki = brain, policies, reusable procedures, skill intelligence, durable knowledge/memory and lessons.
- A-Sunday Conductor = execution/control-plane authority: worker/runtime/provider observations, scheduling, durable job execution, recovery, evidence and review.
- `skills-registry.json` remains the single source of truth for A-Wiki skill registration if current repo rules still say so.
- External memory engines such as Mem0/Claude-Mem may be retrieval/cache experiments only; they must not silently become canonical truth.
- External agent frameworks or hundreds/thousands of skills are catalogs/candidates until they pass A-Wiki's Brain Improvement Gate.
- Never paste an external CLAUDE.md/AGENTS.md/ruleset over A-Wiki's governing instructions.
- Reuse existing A-Wiki intake/research/index/graph/ledger/claim mechanisms before creating parallel state stores.

For every candidate classify:
`REUSE | WRAP | EXTEND | REPLACE | NEW | CATALOG_ONLY | REJECT | DEFER`

Prefer:
`REUSE -> WRAP -> EXTEND`

Any `REPLACE` or central `NEW` brain primitive requires strong evidence and explicit architecture review.
# PRIOR SURVEY — HYPOTHESES TO VERIFY, NOT AUTHORITY

A prior external survey of Charlie Hills' “Claude + 35 Add-Ons” ecosystem suggested the following high-ROI candidates. **Re-check current upstream source/docs/license/maintenance before adopting anything.** External repositories evolve.

## P0 candidates

1. **Microsoft MarkItDown**
   - hypothesis: high-value ingestion normalizer for PDF/DOCX/PPTX/XLSX/HTML -> Markdown;
   - desired fit: A-Wiki raw-first provenance -> deterministic normalization -> indexing/graph/synthesis;
   - verify fidelity, metadata/provenance retention, dependency weight, OCR limitations, security and cross-platform behavior.

2. **Agent-Reach**
   - hypothesis: useful research/social capability layer with backend/fallback/doctor patterns;
   - desired fit: A-Wiki research capability + A-Conductor execution adapter later;
   - verify supported platforms, auth/cookies, ToS/data risk, backend stability, dependencies and health semantics.

3. **last30days**
   - hypothesis: useful recent/trend multi-source research method;
   - desired fit: A-Wiki research specialization;
   - enforce that social engagement/sentiment is a signal, not factual ground truth.

4. **Impeccable**
   - hypothesis: design-language / anti-pattern review delta;
   - desired fit: extend existing `A-Design`, not replace `ui-ux-pro-max` or `taste-skill`.

5. **GitHub MCP / Playwright MCP patterns**
   - A-Wiki should learn permission/evidence semantics and reusable procedures;
   - actual runtime execution ownership stays with A-Conductor or the invoking agent/tool surface.
## P1 delta-audit candidates

6. **obra/superpowers**
7. **Addy Osmani agent-skills**
8. **Karpathy-style coding guidelines/skills**
9. **gstack**

Do not install these wholesale. Diff their current methodology against A-Wiki's existing TDD, debug, grill/spec/ticket, review, verification, claim, handoff, council, and continuous-loop capabilities. Adopt only demonstrably stronger deltas.

10. **MarketingSkills**
   - compare CRO, SEO, analytics, experimentation, pricing, referral and RevOps capabilities against existing `A-Content` routes.

11. **Charlie social-media-skills**
   - prioritize evaluation of `post-scorer`, `voice-builder`, `content-matrix`, `niche-research`, analytics-dashboard and reels/video scripting;
   - focus on the closed learning loop: create -> publish -> measure -> score -> learn -> improve.

## P2 / experiment candidates

12. **HyperFrames** — deterministic/repeatable media rendering skill/provider candidate.
13. **OpenMontage** — later media-pipeline pilot after the basic deterministic media seam is understood.
14. **Mem0** — retrieval experiment only, benchmarked against A-Wiki native FTS/graph/memory-ledger behavior.
15. **Apify** — specialized/cost-aware fallback research/scraping provider; avoid making it default core dependency.

## Catalog-only candidates

Treat `agency-agents`, `awesome-claude-skills`, `wshobson/agents`, `alirezarezvani/claude-skills` and similar large collections primarily as **external searchable catalogs**. Do not import hundreds/thousands of agents or skills into active context.
# KNOWN DUPLICATION RISKS — VERIFY CURRENT REPO

Prior inspection found A-Wiki already had canonical or integrated forms of:

- `ui-ux-pro-max`;
- `taste-skill`;
- `frontend-slides`;
- `social-publisher`;
- `A-Design` composition;
- `A-Content` composition;
- primary-source research skill;
- TDD / debug / verify-before-done / council / claims / handoff / loop primitives.

Re-verify current registry before relying on this list. If still present, do not reinstall/fork merely because an upstream collection contains the same capability.

# REQUIRED CANDIDATE AUDIT MATRIX

For every serious candidate record at minimum:

- exact upstream repository/product and current date/commit/tag where possible;
- purpose and concrete capability gain;
- current A-Wiki equivalent/overlap;
- classification (`REUSE/WRAP/EXTEND/...`);
- license and redistribution implications;
- maintenance activity / maturity / abandonment risk;
- dependency footprint and install complexity;
- context/token footprint if made always-visible;
- CPU/RAM/disk/network/API cost;
- Windows/macOS/Linux support where relevant;
- credential/auth requirements;
- data-egress/privacy/security risk;
- prompt-injection/instruction-file risk;
- deterministic verification/eval method;
- rollback/removal path;
- whether it belongs in repo, private Drive, external config, or catalog only;
- recommendation and evidence strength.
# DESIRED A-WIKI UPGRADE SHAPE

Prefer an architecture like:

```text
External capability catalogs / upstream repos
                 |
                 v
        Scout / candidate discovery
                 |
                 v
        Brain Improvement Gate
                 |
      +----------+-----------+
      |                      |
   REJECT /              ADOPT DELTA
   CATALOG ONLY              |
                             v
                    skills-registry.json
                             |
             +---------------+---------------+
             |                               |
       searchable skill                generated surfaces
       / capability metadata           for supported agents
             |
             v
     eval / verification evidence
             |
             v
       durable lessons / updates
```

Do not load the full catalog into every session. Discovery/search should be cheap; detailed candidate content should load on demand.

Consider whether A-Wiki needs a lightweight **external-capability catalog/index** distinct from the canonical installed-skill registry. If so, it must not become a shadow installed-skill SSoT: clearly distinguish `candidate/catalog` from `canonical/installed`, and reuse existing indexing/registry machinery if possible.

# MARKITDOWN / INGESTION TARGET

If MarkItDown survives audit, design it to preserve A-Wiki's existing provenance law:

`source -> raw/ immutable original -> conversion/normalization -> wiki/source metadata -> index/graph -> synthesis`

Never let converted Markdown replace the immutable raw source.

Record converter/version/options and original-file reference so future agents can reproduce or re-convert when parsing improves.
# RESEARCH / TREND TARGET

Build on the existing high-trust primary-source research path rather than replacing it.

Desired split:

- factual/current verification -> primary/authoritative sources first;
- community/trend intelligence -> recent social/web sources with provenance and date;
- social engagement/sentiment -> explicitly labeled signal/inference;
- external scraper/provider -> fallback when native/free retrieval is insufficient and policy permits it.

Research outputs must label `FACT`, `INFERENCE`, `RECOMMENDATION`, and `DECISION` where ambiguity matters.

# DESIGN / CONTENT TARGET

For `A-Design` and `A-Content`, prefer composition:

- existing canonical capability remains the stable interface;
- new external skills become bounded sub-capabilities/detectors/evaluators;
- avoid creating competing top-level routers;
- measure whether the delta improves output or catches defects before keeping it canonical.

For social/content learning, prioritize durable feedback:

`hypothesis -> content -> publication -> metrics -> normalized score -> lesson -> next experiment`

Do not encode platform vanity metrics as universal truth; preserve platform/time/context in evidence.

# MEMORY / RETRIEVAL TARGET

A-Wiki durable files, indexes, knowledge graph, decisions, regression rules and approved memory remain authority.

Any Mem0/Claude-Mem/vector-store experiment must be treated as a derived retrieval layer:

- rebuildable from durable sources where practical;
- provenance-aware;
- scoped to avoid irrelevant memory pollution;
- benchmarked for recall/precision/latency/context savings;
- removable without losing canonical knowledge.
# A-WIKI <-> A-CONDUCTOR BRIDGE REQUIREMENT

A-Wiki should express **what capability a task requires**, while A-Conductor observes **whether/where it is available and authorized to execute**.

Inspect current A-Wiki task capability vocabulary and A-Conductor read-only contracts before proposing changes.

Desired conceptual bridge:

`A-Wiki required capability ID/version -> Conductor capability mapping -> observed runtime/provider eligibility -> policy/gate -> execution -> evidence/result -> brain learning`

Do not make A-Wiki own live runtime readiness. Do not make A-Conductor own A-Wiki's canonical skill/memory registry.

If vocabularies differ, design a small versioned mapping/compatibility seam rather than copying one registry wholesale into the other repo.

# EXECUTION PLAN TO CREATE IN A-WIKI

After recovery/research, create or update repository-native durable artifacts according to A-Wiki's current file-purpose map. Do not create shadow SSoT files.

The plan should be decomposed roughly into:

- **AW-CAP-0:** current capability/skill inventory + duplicate/overlap map;
- **AW-CAP-1:** external capability catalog/intake design;
- **AW-CAP-2:** MarkItDown ingestion pilot;
- **AW-CAP-3:** research/trend adapters (Agent-Reach / last30days audit and safe integration);
- **AW-CAP-4:** A-Design delta (Impeccable if justified);
- **AW-CAP-5:** A-Content marketing/social feedback-loop deltas;
- **AW-CAP-6:** engineering-methodology delta audit (Superpowers/Addy/Karpathy/gstack);
- **AW-CAP-7:** retrieval/cache benchmark (optional, only if C0-C6 justify it);
- **AW-CAP-8:** media capability catalog/pilot (HyperFrames/OpenMontage when useful);
- **AW-CAP-9:** cross-repo capability-ID/version bridge review with A-Conductor contracts;
- **AW-CAP-10:** final eval/security/privacy/context-cost audit and canonicalization decisions.

These are conceptual IDs. Reuse the repository's actual work-order/ticket naming convention rather than forcing these names if it already has a better scheme.
# WORKER / MULTI-AGENT RULE

Use workers/subagents only for independent READY tasks after preflight.

For every delegated task provide a bounded contract containing:

- task ID / one question or one implementation goal;
- owner;
- exact repo/worktree/branch/HEAD;
- allowed and forbidden files/scope;
- authoritative sources;
- acceptance criteria;
- verification command/evidence;
- checkpoint/handoff destination;
- stop condition;
- no uncontrolled nested delegation.

Do not assign several workers the vague task “improve A-Wiki.” Parent/lead owns reconciliation and synthesis.

A worker saying DONE is a claim until actual repo state and deterministic evidence are verified.

# ENGINEERING LOOP

Use safe, bounded, resumable micro-steps:

`RECOVER SSoT -> VERIFY ACTUAL STATE -> RESEARCH/SHAPE -> SPEC/PLAN -> TICKETS -> IMPLEMENT -> REVIEW -> VERIFY -> E2E/AUDIT AS REQUIRED -> DEFECT LEARNING -> CHECKPOINT`

If a gate fails, loop to the earliest responsible stage. Do not advance status merely to finish the plan.

For production behavior changes, follow A-Wiki's current test-first/root-cause rules exactly.

Do not weaken tests or bypass hooks/claims to make an external package fit.

# SECURITY / PRIVACY

Treat external skills, instructions, MCP servers, scrapers and memory systems as supply-chain/trust-boundary inputs.

Before canonical adoption inspect:

- install/postinstall scripts and executable code;
- unexpected network calls/telemetry;
- prompt/instruction files;
- credential handling;
- filesystem/write scope;
- data retention/egress;
- dependency vulnerabilities and update strategy;
- license/attribution requirements.
Secrets, tokens, cookies, private/personal data, raw sensitive files and machine-specific confidential configuration must stay in the repository-approved private/data layer. Never paste them into plans, skills, issues, PRs, logs or public Git.

# CONTEXT / PERFORMANCE RULE

Every always-on instruction costs future context.

Prefer:

- small canonical routers;
- searchable registries/indexes;
- on-demand skill loading;
- generated surfaces from one SSoT;
- local deterministic search before expensive model calls;
- deep modules with small interfaces;
- lazy/optional dependencies;
- zero idle polling for capabilities not in use.

Reject an external capability if its maintenance/context/security burden is larger than the demonstrated gain.

# REQUIRED EVIDENCE BEFORE CANONICAL ADOPTION

For each adopted capability provide applicable evidence:

- exact upstream provenance/version;
- deterministic unit/integration checks;
- before/after eval or regression example;
- privacy/security scan;
- skill registry/schema validation;
- cross-platform check where relevant;
- context/dependency footprint measurement or bounded rationale;
- fallback/removal test;
- documentation of limitations and non-goals.

For ingestion/retrieval/research, include representative realistic samples rather than toy-only examples.

For external-current claims, cite/record primary or authoritative upstream evidence with date. Do not rely on the prior ChatGPT survey as current truth.

# DEFINITION OF DONE

This upgrade is not DONE because many repositories were cloned or many skills were registered.
DONE requires applicable evidence that:

1. current A-Wiki capability/skill authority was mapped before adding new surfaces;
2. duplicated candidates were rejected or cherry-picked rather than reinstalled;
3. adopted deltas clearly improve retrieval, reasoning, research, design, content, ingestion, automation, safety or reusable workflow;
4. new capabilities are lightweight/on-demand by default;
5. public/private/raw boundaries remain correct;
6. canonical skills remain registry-backed and generated surfaces remain generated;
7. external upstream provenance/license/security were checked;
8. tests/evals demonstrate real benefit and guard regressions;
9. A-Wiki remains canonical brain/memory authority;
10. A-Conductor remains a separate control plane and was not mutated by this A-Wiki task;
11. durable work orders/current state/handoff are updated according to actual repo convention;
12. a fresh agent with no access to this conversation can safely resume.

# EXPECTED FINAL REPORT

At the end of the completed safe scope, report:

- actual repository/worktree/branch/HEAD;
- initial vs final status;
- research matrix and canonicalization decisions;
- files added/changed;
- skills/providers accepted, rejected, deferred, catalog-only;
- exact tests/evals/checks and results;
- security/privacy/license findings;
- dependency/context/cost implications;
- unresolved decisions/blockers;
- current claims/ownership that remain active;
- one exact next safe action.

Do not hide failures. Distinguish `FACT`, `INFERENCE`, `RECOMMENDATION`, and `DECISION` where necessary.

# START NOW

Recover A-Wiki's actual SSoT and repository state first. Do not ask me to repeat facts that the repository/tools can retrieve. Then perform the external-capability delta audit, create the durable upgrade plan/tickets in A-Wiki's native structure, and continue through safe independent micro-steps without asking “continue?” after every step.

Stop only for a genuine human decision/action/authorization/safety block.
