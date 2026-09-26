# WO-P1-555 — Sunday Family Web/PWA control-surface roadmap

Status: ACTIVE / ROADMAP AUTHORING
Issue: #555
Risk: R1 — planning/architecture only; no runtime or product-source mutation
Task topology: CONTROL_PLANE_ONLY

## Binding

Project: A-Sunday Conductor / Sunday Family

Authority repo: `/Users/aase7en/GitHub/A-Wiki-Conductor`
Execution-substrate reference: `/Users/aase7en/GitHub/SunDayRemoteMCP`
Authority worktree: `/Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo555-sunday-family-web-pwa`
Branch: `docs/wo-p1-555-sunday-family-web-pwa`
Base SHA: `31ec2cd17caf05d93fb1101d0492573dfcc319f8`
Owner / integrator: GPT-5.6 Sol

## Goal

Freeze the long-term Sunday Family operator-surface framework and dependency-ordered migration roadmap so Mac Codex sessions working across A-Wiki-Conductor + SunDayRemoteMCP share one architecture:
- A-Sunday Conductor remains the authority/control plane.
- SunDayRemoteMCP remains headless execution/capability substrate.
- Sunday Family becomes the product/package/operator experience.
- Sunday Family Web/PWA becomes the long-term primary operator UI.
- Tk/Ttk remains the current LOCAL-USABLE-1 shell until explicit Web/PWA parity gates pass.
- Serena Dashboard becomes manual diagnostics only and must not auto-open in normal Sunday Family operation.

## Allowed mutation scope

- NEW `docs/work-orders/WO-P1-555-sunday-family-web-pwa.md`
- NEW `docs/plans/2026-09-26-sunday-family-web-pwa-roadmap.md`
- NEW `docs/contracts/sunday-family-web-runtime-boundary-v1.md`
- MODIFY `PROJECT-PLAN.md` only for framework/roadmap pointers and explicit supersession notes.
- Git branch/commit/PR metadata for this planning slice.

## Forbidden

- no A-Conductor product/runtime implementation;
- no SunDayRemoteMCP mutation;
- no change to active #433/#429 critical-path source ownership;
- no Tk/Ttk deletion or feature removal;
- no Serena installation/removal/config mutation;
- no new task/claim/scheduler/completion authority;
- no browser-to-SunDayRemoteMCP direct mutation path;
- no native installer removal in this slice;
- no secret/token material in frontend state, logs, docs, or fixtures;
- no remote-network exposure enabled by default.

## Acceptance criteria

1. One authoritative Web/PWA roadmap exists under `docs/plans/`.
2. One runtime/UI authority contract exists under `docs/contracts/`.
3. `PROJECT-PLAN.md` says Web/PWA supersedes the old long-term Tk/Ttk-only direction without blocking LOCAL-USABLE-1.
4. Frontend baseline is React + TypeScript + Vite + PWA.
5. Backend boundary is A-Conductor-owned typed HTTP/event APIs; SRM stays headless.
6. Consequential actions remain behind Command Gateway authorization.
7. Serena Dashboard is `AUTO_OPEN = FALSE` and manual diagnostic fallback only.
8. Migration is incremental: Monitor Projection/API -> read-only Web/PWA -> Command Gateway -> packaging -> parity -> optional Tk/Ttk retirement.
9. Windows/macOS/Linux/Pi/Umbrel targets and security defaults are explicit.
10. No current #433/#429 source scope is widened or preempted.
11. Browser-consumed Monitor API/SSE data requires an origin allowlist and local auth/session token even on loopback; deterministic origin/token, CSRF, and DNS-rebinding tests gate browser connection.
12. SRM lifecycle/output/results are execution-local advisory evidence until A-Conductor reconciliation/receipt; Conductor retains task, attempt, completion, retry, review, and acceptance authority.
13. A genuinely required future SRM seam uses a bound CROSS_REPO child WO and exact-SHA compatibility set; no SRM mirror-only mutation.

## Replay safety

Docs-only. Re-read Issue #555, current main, active critical-path ownership, and PROJECT-PLAN overlap before replay. Never treat this plan as permission to mutate active product-source lanes.

## Independent exact-SHA review and repair checkpoint

The independent read-only review of candidate `58c5b1a97984c237970f97ef7352cf53e8d4a875` found:

- P1: local Monitor API/SSE reads did not require the existing Hook/STM local auth/session-token plus origin-validation contract, and lacked an explicit pre-browser CSRF/DNS-rebinding acceptance gate.
- P2: SRM output/status/cancel/harvest/recover wording could be read as authoritative task lifecycle rather than execution-local evidence awaiting A-Conductor reconciliation and receipt.
- Follow-up: state the exact-SHA CROSS_REPO child-WO binding only when an actual required SRM seam cannot be met by existing contracts/capabilities.

These findings are being repaired within the existing docs-only scope. The candidate remains unaccepted until the repaired exact SHA passes deterministic scope/docs checks, hosted CI, and a fresh independent exact-SHA review.

## Next safe action

Freeze the repaired roadmap candidate, run deterministic docs/scope checks, push the new exact SHA, then finish fresh hosted CI and independent review. Merge only with expected-head binding after acceptance; run post-main verification and release/close #555 without interrupting the active LOCAL-USABLE-1 critical path.
