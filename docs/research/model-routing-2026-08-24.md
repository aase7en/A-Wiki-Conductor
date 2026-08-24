# Model Routing Research Snapshot — 2026-08-24

Purpose: evidence for assigning A-Wiki-Conductor work between GLM-5.3 MAX and
GPT-5.6 Sol MAX. This is a dated routing snapshot, not a permanent ranking.
Re-check freshness before major future routing changes.

## Sources checked

1. Z.ai official GLM-5.3 launch (2026-08-14):
   https://z.ai/blog/glm-5.3
2. OpenAI GPT-5.6 launch:
   https://openai.com/index/gpt-5-6/
3. OpenAI GPT-5.6 Sol API model page:
   https://developers.openai.com/api/docs/models/gpt-5.6-sol
4. Artificial Analysis GLM-5.3 (max), current Aug 2026:
   https://artificialanalysis.ai/models/glm-5-3/
5. mattpocock/skills upstream grill-with-docs:
   https://github.com/mattpocock/skills/blob/main/skills/engineering/grill-with-docs/SKILL.md
6. mattpocock/skills release notes v1.1.0:
   https://github.com/mattpocock/skills/releases

## Important comparison caveat

Benchmark scores are harness- and version-sensitive. Z.ai's comparison table is useful because
it reports overlapping models under one published table, but it is still vendor-reported.
Artificial Analysis is independent but its snapshots/benchmark versions can differ from model
launch tables. Use the results as routing evidence, then verify outcomes with repo tests.

## Overlapping coding/agentic evidence from Z.ai launch table

| Benchmark | GLM-5.3 | GPT-5.6 Sol | Routing signal |
|---|---:|---:|---|
| Terminal-Bench 2.1 | 88.2 | 88.8 | essentially tied |
| Terminal-Bench 3.0 | 28.3 | 34.6 | GPT advantage on harder terminal tasks |
| DeepSWE v1.1 | 66.9 | 72.7 | GPT advantage on deep SWE |
| SWE-Marathon v1.1 | 42.5 | 42.5 | tied |
| Toolathlon Verified | 73.0 | 74.9 | close |
| AutomationBench v1.0.6 | 48.2 | 45.8 | GLM advantage |
| Agents' Last Exam ALE-CLI | 28.5 | 28.6 | essentially tied |
| HLE with tools | 62.5 | 64.5 | GPT small advantage |
| GDPval-AA v2 Elo | 1769 | 1730 | GLM advantage in this table |
| CyberGym | 84.5 | 83.6 | GLM small advantage |
| ExploitBench | 54.4 | 76.5 | GPT large advantage |

Z.ai also reports GLM-5.3 Max at 34.5% on its private Code Bench, ~50% improvement over
GLM-5.2, with lower output-token use than GLM-5.2.

## Independent/current signal

Artificial Analysis reports GLM-5.3 (max) Intelligence Index 60 in its Aug 2026 snapshot,
with comparatively low API cost and high verbosity. OpenAI's launch reports GPT-5.6 Sol max
at 58.9 on Artificial Analysis Intelligence Index v4.1, but these are not guaranteed to be
the same dated snapshot/version, so do not treat 60 vs 58.9 as a clean head-to-head win.

OpenAI reports GPT-5.6 Sol as multimodal and optimized for coding, knowledge work, computer
use, science, and design; GLM-5.3 max is text-only in the current Artificial Analysis listing.

## Recommended A-Conductor division of labor

### GPT-5.6 Sol MAX — judgment/integration lane

Use when mistakes are expensive or the task crosses many seams:
- architecture and difficult trade-offs;
- final deep planning;
- UI/UX and visual fidelity judgment;
- multimodal/image-to-implementation tasks;
- cross-cutting bug diagnosis;
- security-sensitive review;
- final code review and integration;
- realistic E2E acceptance and deciding whether evidence is sufficient;
- resolving contradictions between WOs/docs/runtime state.

Reason: stronger reported DeepSWE/Terminal-Bench-3/ExploitBench performance, multimodal
capability, and strong computer-use/design positioning.

### GLM-5.3 MAX — bulk implementation lane

Use for well-specified, bounded tickets with deterministic acceptance:
- implement a clearly defined component/helper;
- repetitive UI label conversion;
- mechanical refactors with tests;
- test generation and coverage expansion;
- CLI/repository exploration;
- documentation synchronization;
- first-pass bug fixing where failures are reproducible;
- long but bounded coding work where cost/quota efficiency matters.

Reason: near-frontier coding/agentic performance, strong AutomationBench/CyberGym/GDPval
signals, and lower public API cost. It is appropriate as the main implementation workhorse
when the spec/test oracle is clear.

### Deterministic tools — zero-model lane

Prefer before either model:
- grep/search/static checks;
- formatting/linting;
- unit/integration tests;
- build/package smoke;
- git identity/diff/status;
- image color histogram/particle-count checks;
- resize geometry assertions.

## No-duplicate protocol

1. Repository SSoT owns task state.
2. Each WO/ticket has one implementation owner at a time.
3. GLM may implement; GPT reviews the resulting commit/diff instead of independently
   rebuilding the same feature.
4. GPT may define acceptance/tests first; GLM implements against them.
5. Parallelism is allowed only for disjoint files/scopes with explicit claims.
6. On transport loss, another worker resumes the same WO only after identity/state gate.
7. A result is DONE only when deterministic evidence passes.

## Engineering loop

`grill-with-docs (upstream freshness) -> brainstorm/reuse gate -> deep plan ->
tests/spec seams -> implement -> review -> debug -> realistic E2E/deep bug hunt ->
report -> defect memory -> PR -> CI/CD -> fetch/merge`

Upstream grill-with-docs freshness checked 2026-08-24. Current upstream still delegates to
the grilling + domain-modeling disciplines; v1.1.0 release notes state grill-with-docs now
builds the domain model inline and depends on domain-modeling/codebase-design vocabulary.
## Freshness re-check — 2026-08-24 15:08 ICT

Official OpenAI GPT-5.6 launch currently reports GPT-5.6 Sol MAX at **80** on the
Artificial Analysis Coding Agent Index v1.1, **88.8%** Terminal-Bench 2.1,
**72.7%** DeepSWE v1.1, and **64.6%** SWE-Bench Pro. OpenAI describes Sol as
its strongest coding model and reports state-of-the-art results on Terminal-Bench 2.1
and DeepSWE at launch. Source: https://openai.com/index/gpt-5-6/

Z.ai's official GLM-5.3 launch (2026-08-14) reports **88.2** Terminal-Bench 2.1,
**28.3** Terminal-Bench 3.0, **66.9** DeepSWE v1.1, **48.2** AutomationBench,
**84.5** CyberGym and **1769** GDPval-AA v2 Elo. The same Z.ai table reports
GPT-5.6 Sol at 88.8 / 34.6 / 72.7 / 45.8 / 83.6 / 1730 respectively.
Source: https://z.ai/blog/glm-5.3

Routing conclusion remains unchanged but is now stronger: use GPT-5.6 Sol MAX for
decomposition, architecture, cross-layer safety decisions, difficult debugging, visual/UX
judgment, and final integration/E2E; use GLM-5.3 MAX as the later bounded implementation
workhorse where acceptance tests and file claims are already explicit. Do not duplicate intent.
