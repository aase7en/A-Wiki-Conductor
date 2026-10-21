# WO-P1-694 — SF-WEB-4: Command Gateway controls

Issue: #694
Status: IMPLEMENTATION (root-GLM author after subagent quota exhaustion)
Risk: R3 (first mutation authority on web surface)
Topology: CONTROL_PLANE_ONLY (AWC)

## Scope
Server: src/a_conductor/web_api.py (extend with mutation endpoints)
Client: web/sunday-family/src/components/ControlPanel.tsx (new)
Client: web/sunday-family/src/api.ts (extend with mutation calls)
Tests: tests/test_web_api_mutations.py (new)
Tests: web/sunday-family/src/__tests__/control-panel.test.tsx (new)
Root: no changes needed

## Mutation endpoints
POST /api/v1/workers/{worker_id}/command
Body: {"action": "start"|"stop"|"assign", "project": "path" (for assign only)}
Headers: Authorization Bearer + X-Confirm: {nonce}
Rate limit: 1/second per endpoint (in-memory)
Audit: bounded list (last 100 mutations)

## Typed errors
WORKER_NOT_FOUND, WORKER_ALREADY_RUNNING, INVALID_PROJECT_PATH, RATE_LIMITED, CONFIRMATION_REQUIRED
