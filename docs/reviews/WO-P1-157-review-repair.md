# WO-P1-157 Review Repair Evidence

Base candidate: `878ec888eccf3f8d7612d230b587ccbf0e13f274`
Review: GitHub review `5119939724`
Repair branch: `fix/wo-p1-157-review-findings`

## Findings addressed

- P1 authority ordering: actual Git/runtime/process/DB state is now explicitly state evidence inside user/safety/binding-policy constraints, not an authority above those constraints.
- P2 bootstrap deadlock: a new task without a work order may create only its bounded docs-only WO/claim in a clean isolated scope; product/source/runtime mutation remains blocked until the gate is rerun.
- P2 progressive context: `CURRENT-WORK.md` remains mandatory; active WO is conditional on existence/claim; `handoff.md` is loaded only for resume/transfer/unclear continuity or an explicit CURRENT-WORK pointer.
- Routing simplification: lifecycle policy now routes to a capability-selected executor by risk/task class/capability/readiness/authorization/cost/availability; GLM/ZCode remains the current preferred candidate rather than a permanent architectural dependency.

## Scope

Repair changes are limited to governance/process docs and do not touch product source, tests, runtime, DB, credentials, or the protected root checkout.

## Verification required

- exact diff against base candidate
- YAML parse/path consistency for `PROJECT-GRAPH.yaml`
- UTF-8/control-character scan
- focused policy consistency review
- exact-head hosted CI
- independent rereview before fold-back/acceptance
