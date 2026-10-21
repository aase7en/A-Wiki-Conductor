# WO-P1-693: SF-WEB-3 PWA / Installable Shell

Issue: #693

## Contract

- Role: AUTHOR; risk R2; topology CONTROL_PLANE_ONLY.
- Base: `570a722a50f6080bb0709f85c1dd0bbd3308ba6f`.
- Worktree: `A:\GitHub\_worktrees\AWC-wo693-sfweb3`.
- Branch: `feat/wo693-sfweb3-pwa`.
- Claim: `WO693-SFWEB3-AUTHOR`; post on driving issue before source mutation.
- Implementation scope: additive files and additive integration edits under
  `web/sunday-family/` only. This bootstrap WO is the sole docs exception.
- Preserve existing shell behavior; no Python, root package, external assets,
  backend authority, credential persistence, or shared continuity edits.
- Reuse React/Vite shell; manual service worker, no PWA dependency required.

## Acceptance

Manifest and local SVG icons; production-only SW registration; subtle install
button handling deferred prompt, dismissal and appinstalled; versioned bounded
static cache, cleanup on activation, offline navigation shell. API requests are
network-only (network-first with no cache fallback or storage), including failures.
Never cache API payloads, arbitrary responses, authenticated data or external URLs.
Install must precache built JS/CSS alongside index, not merely lazy-cache them.

Run npm install, npm run build, existing 34 tests plus new manifest, registration,
install UI and SW lifecycle/routing tests. Check diff/scope and freeze exact SHA.
Commit and push branch only; no PR, merge or issue posts beyond initial claim.
Independent review/CI/acceptance belongs to integrator, not this author lane.

## Checkpoint

Bootstrap created before source mutation. Evidence: native command results and
final author report; integrator owns shared CURRENT-WORK/handoff fold-back.

AUTHOR verification 2026-10-21: npm install exit 0 (0 vulnerabilities), npm test
exit 0 (55/55: existing 34 plus 21 new), npm run build exit 0 (TypeScript + Vite).
Generated precache includes index, manifest, two icons and hashed JS/CSS (6 entries).
SW install/activate, API exclusion, static hits/misses, navigation fallback and
64-entry admission bound verified by executable worker tests. Manifest JSON,
SVG dimensions, production-only registration, install lifecycle and real Vite
bundle output verified. Initial manifest test used a Vite-transformed file URL;
corrected to a filesystem path and full suite reran green.
Browser smoke not performed: integrated browser reported project/directory
session mismatch; preview process stopped. No real installation claim is made.
RDC discovery returned TOOL_NOT_FOUND; authorized local native tools used instead.
Claim comment: https://github.com/aase7en/A-Wiki-Conductor/issues/693#issuecomment-6309309909
Next: integrator exact-SHA independent review and required CI; no author acceptance.
