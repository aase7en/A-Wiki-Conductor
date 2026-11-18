# WO-P1-780 — SFU26 card 13: route explanation / UX-3 read-only advice

Identity schema: GITHUB_ISSUE_V1
Issue: #780
Status: R0 DOCS-ONLY BOOTSTRAP; R2 SOURCE IMPLEMENTATION BLOCKED (card 04 merge + integrator acceptance + fresh claim required)
Risk: R0 docs-only; R2 presentation risk per roadmap §13
Topology: CONTROL_PLANE_ONLY
Parent lineage: SFU26 roadmap #744 (`docs/plans/2026-11-13-sunday-family-unified-dashboard-routing-roadmap.md` §8 card 13); evidence audit [#743 c6983659537](https://github.com/aase7en/A-Wiki-Conductor/issues/743#issuecomment-6983659537); operator lane authorization [#771 c6986313480](https://github.com/aase7en/A-Wiki-Conductor/issues/771#issuecomment-6986313480).

## Goal

Bind the accepted card 13 requirements into an executable R2 contract: a read-only
"Why this route?" explanation over existing accepted evidence only, exposed as a child
view of the existing authenticated monitor snapshot. No new router, provider store,
execution pathway, endpoint, approval authority, or inference dependency.

## Dependency state (verified 2026-11-18)

- Card 06 route telemetry baseline: MERGED (PR #753 → main `feb3e3c`).
- Card 05 settings read models: MERGED (PR #768 → main `de98268`).
- Card 04 UX-2 shell: IN FLIGHT (PR #776 @ `497c30c`, GPT-owned).
- Card 12J Jev SHADOW: not started — optional for card 13 (deterministic explanation does not wait).
- Root audit finding: `select_pre_attempt_provider` and `project_route_telemetry` have
  ZERO production callers today. A card 13 panel therefore starts honestly typed-UNAVAILABLE
  until a separately-authorized producer exists. Card 13 must NOT wire a producer.

## R0 bootstrap binding

- Repo: aase7en/A-Wiki-Conductor
- Worktree: A:\GitHub\_worktrees\AWC-wo780-card13
- Branch: docs/wo-p1-780-sfu26-card13-route-explanation
- Base: main@bad92f76e8b255b45978606d1e620881f121b2c0
- Owner: Kilo (GLM-5.3) R0 docs-only; R2 owner to be a fresh non-overlapping claim.
- Allowed THIS R0 step: exactly this NEW Work Order file.
- Forbidden THIS R0 step: web/sunday-family/{src,tests}, AGENTS.md, PROJECT-GRAPH.yaml,
  CURRENT-WORK.md, handoff.md, all src/a_conductor/, plans, secrets; PR #776/#779 branches.
- Evidence: exact one-file diff, identity suite green via exact-head CI, independent
  review before merge, no self-merge. Candidate stays DRAFT until independent evidence.

## R2 successor contract (implementation-ready; blocked until card 04 merges AND the integrator accepts this section AND a fresh R2 claim exists)

### Deliverable

1. Read-only `route` child view inside the EXISTING authenticated monitor snapshot
   (`/api/v1/monitor/snapshot` + stream), composed through the accepted
   `monitor_live_provider` child-view seam (inspector precedent). NO new endpoint.
2. UX-3 drawer in the existing Jev/route-detail section slot of the card 04 shell,
   following the accepted SundayFamily Color E-Ink design system. ADVISORY ONLY:
   no Approve/Retry/Auto-accept controls.
3. Pure projection module (new `src/a_conductor/route_explanation_projection.py`,
   or extension of an existing accepted projection if the integrator prefers):
   injects-only, no clock/network/store I/O, mirroring the card 05/06 projection laws.

### DTO (minimal contract)

```
route: {
  state: AVAILABLE | UNAVAILABLE,
  unavailable_reason?: SELECTION_RESULT_ABSENT | SEMANTIC_TELEMETRY_ABSENT | RECEIPT_ROW_ABSENT | PRODUCER_NOT_DEPLOYED,
  attempts: [  bounded, dedup by (execution_id, attempt_id), duplicate_of pointers: {
    execution_id, attempt_id, request_id?,
    selection?: { outcome, reason_code, selected_provider_id, selected_model_id,
                  expected_configuration_generation,
                  shortlist: [{ provider_id, model_id, stage, eligible, reason_code,
                                expected_configuration_generation }] },
    usage_state, input_usage?, output_usage?,
    latency_ms? + clock label, started_at_wall?, finished_at_wall?,
    fallback_reason?, disposition?, receipt_status, accepted, duplicate_of?,
    cost: { label: OBSERVED | ESTIMATED | UNKNOWN, reason, amount?, currency? },
    source_freshness?: { state, age_seconds?, drift_notes[] },
    context_digest_ref? } ],
  advice?: { state: AVAILABLE | UNAVAILABLE, unavailable_reason?, disposition?,
             primitive, probability?, model_version_pin }   // ADVISORY ONLY, never a decision authority
}
```

Cost mapping law: card-06 `KNOWN` (measured usage × injected pricing) → `ESTIMATED`;
`UNKNOWN` stays `UNKNOWN` + reason. `OBSERVED` is reserved for a future accepted
billing-evidence source and must never be emitted by this WO's code.

### Traceability matrix

| # | ACCEPTED REQUIREMENT (roadmap §13 / §7.1) | EXISTING SOURCE (accepted, on main) | DATA GAP | REQUIRED DTO FIELD | TEST | ALLOWED R2 FILE SCOPE |
|---|---|---|---|---|---|---|
| 1 | Route/attempt identity | `route_telemetry_projection.RouteAttemptInput` (execution_id/attempt_id/request_id) | no production producer | `attempts[].{execution_id,attempt_id,request_id}` | dedup + duplicate_of validator test | NEW `src/a_conductor/route_explanation_projection.py`, its test file |
| 2 | Eligible candidates + exclusion codes | `provider_fallback_policy` reason vocabulary (15 codes) via `RouteSelectionSummary.shortlist` | zero runtime events | `attempts[].selection.shortlist[].reason_code` (verbatim, never invented) | absent→`UNAVAILABLE/SELECTION_RESULT_ABSENT`; verbatim-reason test | same + `monitor_live_provider.py` composition hook |
| 3 | Selected/rejected reason | `RouteSelectionSummary.{outcome,reason_code}` | same | `attempts[].selection.{outcome,reason_code}` | reason-code passthrough test | same |
| 4 | Provider/model provenance | `provider_operator_view.ProviderOperatorRow` (models, trust_class, egress, generation, provenance, quota) | web DTO absent | provenance fields on attempt rows / provider sub-block | provenance truthfulness test | same |
| 5 | Policy/registry revisions | `expected_configuration_generation` chain (policy + observability) | web DTO absent | `selection.expected_configuration_generation` + drift note | stale-generation label test | same |
| 6 | Evidence timestamp/freshness | `model_artifact_freshness_projection` (AVAILABLE/STALE/UNKNOWN + drift) + observation age in operator row | web DTO absent | `source_freshness` | fresh/stale/unknown propagation test | same |
| 7 | Observed/estimated/unknown cost | `RouteTelemetryCost` KNOWN/UNKNOWN chain (USAGE_ABSENT→PRICING_ABSENT→CURRENCY_ABSENT) | no OBSERVED source; pricing unwired | `cost.{label,reason,amount?,currency?}` | 3-way label test; KNOWN→ESTIMATED mapping test; never-0-fabrication test | same |
| 8 | Usage measured | usage_state MEASURED/typed-unavailable | producer absent | `usage_state,input_usage?,output_usage?` | typed-unavailable test | same |
| 9 | Authorization/quota constraints | `AdmissionEvidence` lifecycle + QUOTA_*/PAID_SUBSTITUTION_NOT_AUTHORIZED codes | web DTO absent | admissions/quota fields, deny-by-default | unauthorized-candidate hidden/denied test | same |
| 10 | No-advice honesty (optional Jev) | `semantic_decision.py` typed core (NOUL forbids confidence semantics; typed provider errors) | 12J not started — advice stays UNAVAILABLE with reason | `advice.{state,unavailable_reason,primitive,probability?}` | no-advice vs provider-error vs low-confidence tests; NOUL-probability-not-confidence label test | `web/sunday-family/src/*` + `web/sunday-family/tests/*` (drawer, api.ts branch) |
| 11 | Context digest reference | `EvidencePack.digest/fingerprint` (card 07) | unwired to attempts | `context_digest_ref?` (digest string only, never pack content) | digest-ref-is-string-only test | same |
| 12 | Reuse snapshot, no new endpoint | `monitor_live_provider` child seam; card-01 14-route method-surface contract | — | child under existing snapshot/stream | route-surface completeness test stays exact (no new route added) | `tests/test_web_api.py` surface contract touch if strictly needed |

### Test matrix (from roadmap §13, made deterministic)

1. No advice available → typed `advice.unavailable_reason`, drawer renders the reason, never a fake disposition.
2. Low-confidence advisory vs provider error → distinct typed outcomes; advisory visually separated from deterministic result.
3. NOUL primitive → probability label, never "confidence".
4. Stale/mismatched attempt (generation drift, correlation conflict) → labeled, not dropped silently.
5. Unauthorized candidate → hidden/denied, no capability inference.
6. XSS-safe text → reason codes and Thai/English labels escaped code-only; no raw HTML from evidence.
7. No secret reveal/copy → deny-by-default field law (card-05 pattern) proven by validator tests.
8. Absent selection/telemetry/receipt → typed UNAVAILABLE with exact reason code, counts never fabricated.
9. Surface completeness → card-01 exact method-surface contract unchanged (no new endpoints).
10. Snapshot child bound (rows ≤ N, byte budget) per monitor frame law.

### Security & authority constraints

- Existing bearer-authenticated read-only snapshot only; no new endpoint, no CORS/CSP change.
- No provider client in the browser; advisory data only if an accepted server-side seam supplies it.
- No selection-event producer wiring (belongs to canary lineage / separate accepted WO).
- No pricing/billing source invention; cost stays ESTIMATED/UNKNOWN.
- Read DEFECT_LESSONS.md before any `src/a_conductor/` mutation (repo law).
- R2 allowed files (proposal, integrator may amend at acceptance): the projection module + its
  tests, `monitor_live_provider.py` composition, `web/sunday-family/src/**`, `web/sunday-family/tests/**`.
  UX-2 files remain GPT-owned until PR #776 merges and the claim handoff is recorded.

### Rollback

Single-revert: child view + drawer are additive; removing the commit restores the prior
snapshot shape; `api.ts` validator branch removal returns the strict union to its prior shape.

### Owner / reviewer split

- R2 owner: fresh frontend claim, serialized after card 04 merge, non-overlapping with GPT UX-2 repair.
- R2 reviewer: independent UX/privacy reviewer (roadmap §13), not the implementer.
- Integrator (GPT) retains acceptance/merge authority throughout.

## Continuity

Durable evidence lives on issue #780 (claim/checkpoints), the audit (#743), and the roadmap.
This WO grants no execution, provider, or merge authority.
