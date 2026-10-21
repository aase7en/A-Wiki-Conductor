# WO-P1-690 — SF-WEB-2: React/TypeScript/Vite read-only Sunday Family shell

Issue: #690
Status: GOVERNANCE_BOOTSTRAP — implementation admitted after this WO + claim
Risk: R2 (new web frontend, read-only, no server mutations)
Topology: CONTROL_PLANE_ONLY (AWC)

## Authority
- Parent: SF-WEB-0 contract (WO-P1-687, merged); SF-WEB-1 API (WO-P1-689, merged)
- Base: AWC main 990c90b9b54942bf94f479f4508b137fb15c6898
- Worktree: A:\GitHub\_worktrees\AWC-wo690-sfweb2, branch feat/wo690-sfweb2-shell

## Scope (exact)
ALL files under web/sunday-family/ (new directory, entirely additive):
- web/sunday-family/package.json (npm manifest, separate from Python project)
- web/sunday-family/vite.config.ts
- web/sunday-family/tsconfig.json
- web/sunday-family/index.html
- web/sunday-family/src/ (all React components, API client, styles)
- web/sunday-family/tests/ (component tests)

Root-level: add a minimal package.json with web:dev and web:build convenience scripts ONLY (no dependencies, no Python changes). This is the ONLY root file change.

## Technical decisions (pre-adjudicated)
1. SSE via authenticated fetch streaming (NOT native EventSource — cannot supply Bearer header)
2. Dev proxy validates incoming Host/Origin before forwarding to 127.0.0.1:8756
3. UI preserves API limitations: connector/activity unavailable states are displayed honestly, never fabricated
4. Token in sessionStorage only (never localStorage, never URL)
5. React 19 + Vite 6 + TypeScript 5 (latest stable)
6. No SSR, no WebSocket, no write/mutation actions, no CORS wildcard

## Acceptance
- npm install && npm run build in web/sunday-family/ exits 0
- Basic component tests pass
- No changes to existing src/, tests/, docs/ (except this WO)
- App renders snapshot data, subscribes to SSE stream, shows health
