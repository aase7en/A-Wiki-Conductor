# A-Sunday Conductor — Impeccable UI Audit + Rust Feasibility

**Owner intent:** improve UX quality and avoid generic AI dashboards; evaluate Rust pragmatically across control-plane components.
**Actual repo basis:** Python `src/a_conductor/` control plane + native Tk GUI; separate React/Vite web subapp `web/sunday-family/`. This is **not** currently a Tauri/Rust product.
**Agent entry:** `00-AGENT-ENTRY.md` → `PROJECT-GRAPH.yaml` → `AGENTS.md` → `CURRENT-WORK.md` → scoped WO/claim.
**Blockers:** SFU26 UI/UX card 04/UX-2 requires owner UX-1 green-light (#743); do not turn this design research into an unauthorized UI lane. New source change needs work order, risk classification, exact-head verification, independent review as applicable.
**Design SSoT:** root `DESIGN.md` — dark CMD/terminal-inspired, calm density, thin borders, semantic color, restrained motion, no glossy/gradient cards.

## UI/UX pilot scope by surface
- **React web:** analyze one isolated operator status table, inspector state, error/empty/loading or activity visualization *after* UX gate and non-overlap. Impeccable CLI source/rendered-page scans apply here.
- **Native Tk GUI:** do **not** assume the CLI detects Tk widgets or Python screen layouts. Use sanitized screenshots + manual `critique` / accessibility/keyboard contrast review; inspect source separately. The browser detector is not a verified Tk accessibility scanner.
- **Domain:** monitor status, worker lease, typed UNKNOWN/STALE/FAILED states, logs, actions requiring authority, reconnection/recovery and focus management. Never turn status aesthetics into fake health or fake completeness.
- Compare 1280×720 and larger desktop windows and keyboard-only operation, non-GPU fallback, high DPI, no extra UI polling/process spawning. Preserve Sunday Family approved header/logo.

## Rust preliminary decision
**Recommendation: partial exploration rather than rewrite.**
- **Potential B:** isolated Rust supervisor/daemon, log/trace parser, queue/event throughput kernel or cross-platform low-overhead local tooling *if* real profiling reveals Python bottlenecks and a stable IPC boundary can isolate the change.
- **No default Rust migration:** mature Python orchestrator already owns job/lease/security semantics and Tk integration. Rewriting the control plane increases state-machine drift, FFI/interprocess failures, Windows packaging/debug/recovery overhead.
- **Optional separate experiment:** Tauri 2 + existing React web UI as a future cross-platform shell, but it would entail architectural migration from Tk/native; first compare size, startup time, memory, accessibility, feature parity, update path, Windows security and recovery. The user's visual preference is not proof Tauri is required.
- **Go/no-go:** parity against accepted state machine and typed telemetry contracts, crash/restart/lock consistency tests, Windows packaged E2E, log diagnostics, benchmark p95 CPU/memory/startup, transparent ownership and rollback.
- Defer any implementation until UX-1 and a new scoped WO are approved.

## Authority and safe execution
- **Status: PROPOSAL / RESEARCH ONLY.** This document records owner-requested intent (2026-11-15); it does **not** claim a mutation lane, authorize implementation/deployment, or override the repository SSoT.
- Start with current `AGENTS.md` and live task/claim records. Verify remote `main`, worktree identity, HEAD, dirty ownership, and active PRs. Create an approved bounded JOB/WO, declare a disjoint scope, and follow existing review gates before any product/source edits.
- Do not replace the existing design system, rewrite the app, install unreviewed packages/hooks, change CI defaults, delete user files, migrate data, or touch Production as part of discovery.
- This proposal intentionally leaves canonical live-status files unchanged; do not treat a draft PR as acceptance or as a claim.

## Impeccable investigation protocol (not yet run)
1. Establish **baseline**: capture representative desktop/tablet/mobile or native-app screens, and user journeys. Record page/commit/device, user goal, a11y, contrast, keyboard flow, motion, performance, screenshots, and known UI defects. Use dummy/sanitized data.
2. Preserve brand identity and existing design tokens; write a concise product/design context from confirmed SSoT (do not allow AI to infer or replace business intent).
3. Review upstream source/license/version before opting into `npx impeccable install` and its hooks. Use a throwaway branch/worktree first. Run `/impeccable init` only with approved product context; compare any generated `PRODUCT.md` or `DESIGN.md` with existing authoritative docs. Never blindly overwrite them.
4. Pilot **one isolated component/flow**: `/impeccable critique` for design hierarchy, `/impeccable audit` for a11y/responsive/performance, and `npx impeccable detect <source-path>` and a local rendered URL where supported. Review detector rules and false positives; `--json` for machine-readable evidence. Detector is a heuristic, not a definitive design score.
5. Triage findings: P0 unusable/accessibility/safety, P1 major task friction/incorrect status representation, P2 inconsistency, P3 aesthetic polish. For each finding record URL/screenshot, rule or rationale, impact, proposed correction, owner, before/after comparison, and verified status.
6. Prototype one reversible change. Compare before/after visually and with automated verification; test keyboard, touch, reduced motion, focus, responsive layouts and real content lengths. No aesthetics-only change that regresses user tasks.
7. Request owner decision on the visual direction and an independently reviewed PR before merging. If no measurable benefit, retain original design.

**Suggested gates (targets, not results):** 0 new P0/P1 accessibility/usability regressions; all existing task workflows pass; WCAG AA contrast where applicable; touch targets meet project-specific standard; mobile/desktop screenshots and E2E pass; no sustained bundle/performance regression versus measured baseline. Document exceptions rather than hiding detector warnings.

## Rust evaluation protocol (separate from UI aesthetic work)
- **Hypothesis, not mandate:** assess Rust only where real profiling shows CPU-bound, memory-safety, binary-distribution, concurrency, or resource-use needs not solved by simpler optimization in the current stack. Rust does not by itself make React/Tk UI visually better.
- Inventory current language/process boundaries, native dependencies, build/release/CI platforms, team proficiency, and integration cost. Profile a baseline with realistic workloads and attributable bottlenecks.
- Compare **A: keep and optimize current stack**, **B: isolated Rust service/library/CLI or WASM proof of concept**, **C: broad rewrite**. Default to A until B demonstrates durable total-cost advantage; C requires separate owner-approved ADR and rollback plan.
- Define 1–2 week *experiment scope only after approval*, plus exact benchmarks: median/p95 latency, memory peak, CPU, startup time, binary size, failure/recovery, CI friction, developer time, dependency/security surface, and parity tests.
- Run identical fixtures for incumbent vs Rust candidate; assess FFI/WASM/IPC data marshaling, portability, debug/observability and cross-platform deployment. Abandon pilot if results are inconclusive or integration burden exceeds measured gain.
- Accept Rust only behind a stable interface, preserving current behavior with compatibility tests and an explicit rollback path. Never migrate all projects or entire frontend solely for language uniformity.

## References (checked 2026-11-15)
- Impeccable upstream: https://github.com/pbakaus/impeccable and https://impeccable.style/
- Tauri architecture (Rust core + webview, **not** automatic Rust frontend): https://v2.tauri.app/concept/architecture/
- Rust language: https://doc.rust-lang.org/book/
- WebAssembly constraints: https://developer.mozilla.org/en-US/docs/WebAssembly/Guides/Concepts

## Deliverables for a future authorized agent
- Baseline evidence matrix with screenshots/sha/device and false-positive review.
- Prioritized UI/UX anti-slop audit, before/after prototype and a11y/responsive/E2E evidence.
- Rust feasibility ADR: measured bottleneck, options A/B/C, costs/risks, go/no-go with human decision.
- A bounded JOB/WO and claim through existing SSoT; independently reviewed PR for *any* source change.