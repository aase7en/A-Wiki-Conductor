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
- Repair round 1 (2026-11-18): resolved P2 DTO-placement ambiguity + 2 P3s from
  independent review [PR #781 c6988121321](https://github.com/aase7en/A-Wiki-Conductor/pull/781#issuecomment-6988121321)
  — pinned `snapshot.monitor.route`, placeholder/error typed-unavailable law, finite
  bounds (32/16, fail-closed), `MAX_FRAME_BYTES` naming, per-file R2 allowlist.
- Repair round 2 (2026-11-18): resolved typed-reason/byte-bound contradictions + row-12
  test scope from [PR #781 c6994695148](https://github.com/aase7en/A-Wiki-Conductor/pull/781#issuecomment-6994695148)
  — `ROUTE_EVIDENCE_OVER_LIMIT` added to the `unavailable_reason` union; three-tier
  over-limit law (`ROUTE_EVIDENCE_OVER_LIMIT` projection tier / `MONITOR_PAYLOAD_TOO_LARGE`
  child tier per `monitor_live_provider.py:171-172` / `MONITOR_FRAME_OVERSIZED` whole-frame
  tier per `web_api.py:94-98`); `MONITOR_CHILD_UNAVAILABLE` pinned as UI-side-only;
  `tests/test_web_api.py` pinned as run-only with amendment-before-mutation rule.

## R2 successor contract (implementation-ready; blocked until card 04 merges AND the integrator accepts this section AND a fresh R2 claim exists)

### Deliverable

1. Read-only route child view at the pinned path **`snapshot.monitor.route`** — a key
   inside the existing live-monitor child object, composed by the accepted
   `monitor_live_provider` seam (`{"mode": "live", "monitor": views}` →
   `views["route"]`), which `web_api.WebFeed.read()` already injects verbatim as
   `view["monitor"]`. Served unchanged by the existing authenticated
   `/api/v1/snapshot` + `/api/v1/monitor/snapshot` aliases and the stream feed.
   **NO top-level `snapshot.route` sibling** (that would require a new composition
   seam in `web_api.py`, which this WO does not admit). NO new endpoint. When
   `monitor` is the typed placeholder (`{error, gate}`) or the typed live-projection
   error child, the `route` key is ABSENT and the UI MUST render route as typed
   `UNAVAILABLE` with reason `MONITOR_CHILD_UNAVAILABLE` — never coerce a
   placeholder into live `MonitorViews` and never fabricate route rows.
2. UX-3 drawer in the existing Jev/route-detail section slot of the card 04 shell,
   following the accepted SundayFamily Color E-Ink design system. ADVISORY ONLY:
   no Approve/Retry/Auto-accept controls.
3. Pure projection module (new `src/a_conductor/route_explanation_projection.py`,
   or extension of an existing accepted projection if the integrator prefers):
   injects-only, no clock/network/store I/O, mirroring the card 05/06 projection laws.

### DTO (minimal contract; root path pinned as `snapshot.monitor.route` — MonitorViews branch only)

```
monitor.route: {            // present ONLY in the live MonitorViews union branch;
                            // absent in the MonitorPlaceholder / error child, where
                            // the UI renders UNAVAILABLE/MONITOR_CHILD_UNAVAILABLE
  state: AVAILABLE | UNAVAILABLE,
  unavailable_reason?: SELECTION_RESULT_ABSENT | SEMANTIC_TELEMETRY_ABSENT | RECEIPT_ROW_ABSENT | PRODUCER_NOT_DEPLOYED | ROUTE_EVIDENCE_OVER_LIMIT,
  attempts: [ ≤ 32 rows, dedup by (execution_id, attempt_id): {
    execution_id, attempt_id, request_id?,
    selection?: { outcome, reason_code, selected_provider_id, selected_model_id,
                  expected_configuration_generation,
                  shortlist: [ ≤ 16 rows: { provider_id, model_id, stage, eligible, reason_code,
                                expected_configuration_generation } ] },
    usage_state, input_usage?, output_usage?,
    latency_ms? + clock label, started_at_wall?, finished_at_wall?,
    fallback_reason?, disposition?, receipt_status, accepted,
    duplicate_of?: int (0-based index into this same attempts[] pointing at the
                       first row carrying this identity; absent on first-of-identity —
                       same semantics as route_telemetry_projection.duplicate_of),
    cost: { label: OBSERVED | ESTIMATED | UNKNOWN, reason, amount?, currency? },
    source_freshness?: { state, age_seconds?, drift_notes[] },
    context_digest_ref? } ],
  advice?: { state: AVAILABLE | UNAVAILABLE, unavailable_reason?, disposition?,
             primitive, probability?, model_version_pin }   // ADVISORY ONLY, never a decision authority
}
```

Over-limit and byte-bound law — three DISTINCT tiers, fail-closed, never silent
truncation (codes cross-checked against the accepted production paths):

1. **Route evidence over-limit (projection tier):** attempts > 32 or a shortlist > 16
   rows → the whole `monitor.route` child is `UNAVAILABLE` with reason
   `ROUTE_EVIDENCE_OVER_LIMIT` (member of the `unavailable_reason` union above);
   no partial row sets, no fabricated truncation accounting.
2. **Monitor child encoded over-limit (child-byte tier):** if the serialized live
   monitor child (including `route`) exceeds `MAX_FRAME_BYTES`, the accepted
   `monitor_live_provider` guard (`monitor_live_provider.py:171-172`) replaces the
   WHOLE child with the typed error marker `{"error": "MONITOR_PAYLOAD_TOO_LARGE",
   ...}` — `route` is then absent and the UI renders route
   `UNAVAILABLE/MONITOR_CHILD_UNAVAILABLE`.
3. **Whole-frame encoded over-limit (frame tier):** if the entire snapshot/stream
   frame exceeds `MAX_FRAME_BYTES = 262_144`, the accepted `web_api.encode_frame`
   raises typed `MONITOR_FRAME_OVERSIZED` (`web_api.py:94-98`) exactly as today —
   unchanged by this WO.

`MONITOR_CHILD_UNAVAILABLE` is a **UI-side derived reason only** (rendered when the
monitor child is a placeholder, a live-projection error, or a monitor-wide error
marker such as `MONITOR_PAYLOAD_TOO_LARGE`); it is never serialized inside any
placeholder/error JSON. Frontend contract: extend
`web/sunday-family/src/api.ts` — `MonitorViews` gains the `route` key and
`parseSnapshot`/`isLiveMonitor` validate the child (bounds + typed fields) when
present; the `MonitorPlaceholder` branch stays byte-identical with `route` absent.

Cost mapping law: card-06 `KNOWN` (measured usage × injected pricing) → `ESTIMATED`;
`UNKNOWN` stays `UNKNOWN` + reason. `OBSERVED` is reserved for a future accepted
billing-evidence source and must never be emitted by this WO's code.

### Traceability matrix

| # | ACCEPTED REQUIREMENT (roadmap §13 / §7.1) | EXISTING SOURCE (accepted, on main) | DATA GAP | REQUIRED DTO FIELD | TEST | ALLOWED R2 FILE SCOPE |
|---|---|---|---|---|---|---|
| 1 | Route/attempt identity | `route_telemetry_projection.RouteAttemptInput` (execution_id/attempt_id/request_id) | no production producer | `attempts[].{execution_id,attempt_id,request_id}` | dedup + duplicate_of validator test | NEW `src/a_conductor/route_explanation_projection.py`, its test file |
| 2 | Eligible candidates + exclusion codes | `provider_fallback_policy` reason vocabulary (15 codes) via `RouteSelectionSummary.shortlist` | zero runtime events | `monitor.route.attempts[].selection.shortlist[].reason_code` (verbatim, never invented) | absent→`UNAVAILABLE/SELECTION_RESULT_ABSENT`; verbatim-reason test | same + `monitor_live_provider.py` composition hook |
| 3 | Selected/rejected reason | `RouteSelectionSummary.{outcome,reason_code}` | same | `attempts[].selection.{outcome,reason_code}` | reason-code passthrough test | same |
| 4 | Provider/model provenance | `provider_operator_view.ProviderOperatorRow` (models, trust_class, egress, generation, provenance, quota) | web DTO absent | provenance fields on attempt rows / provider sub-block | provenance truthfulness test | same |
| 5 | Policy/registry revisions | `expected_configuration_generation` chain (policy + observability) | web DTO absent | `selection.expected_configuration_generation` + drift note | stale-generation label test | same |
| 6 | Evidence timestamp/freshness | `model_artifact_freshness_projection` (AVAILABLE/STALE/UNKNOWN + drift) + observation age in operator row | web DTO absent | `source_freshness` | fresh/stale/unknown propagation test | same |
| 7 | Observed/estimated/unknown cost | `RouteTelemetryCost` KNOWN/UNKNOWN chain (USAGE_ABSENT→PRICING_ABSENT→CURRENCY_ABSENT) | no OBSERVED source; pricing unwired | `cost.{label,reason,amount?,currency?}` | 3-way label test; KNOWN→ESTIMATED mapping test; never-0-fabrication test | same |
| 8 | Usage measured | usage_state MEASURED/typed-unavailable | producer absent | `usage_state,input_usage?,output_usage?` | typed-unavailable test | same |
| 9 | Authorization/quota constraints | `AdmissionEvidence` lifecycle + QUOTA_*/PAID_SUBSTITUTION_NOT_AUTHORIZED codes | web DTO absent | admissions/quota fields, deny-by-default | unauthorized-candidate hidden/denied test | same |
| 10 | No-advice honesty (optional Jev) | `semantic_decision.py` typed core (NOUL forbids confidence semantics; typed provider errors) | 12J not started — advice stays UNAVAILABLE with reason | `monitor.route.advice.{state,unavailable_reason,primitive,probability?}` | no-advice vs provider-error vs low-confidence tests; NOUL-probability-not-confidence label test | precise per-file allowlist (see Security §R2 allowed files): `api.ts` + NEW drawer component + NEW tests |
| 11 | Context digest reference | `EvidencePack.digest/fingerprint` (card 07) | unwired to attempts | `context_digest_ref?` (digest string only, never pack content) | digest-ref-is-string-only test | same |
| 12 | Reuse snapshot, no new endpoint | `monitor_live_provider` child seam (`{"mode","monitor"}` shape consumed verbatim by `web_api.WebFeed.read()`); card-01 14-route method-surface contract | — | `monitor.route` child only; no top-level sibling; no `web_api.py` change | route-surface completeness test stays exact (no new route added); placeholder/error child → UI typed `UNAVAILABLE/MONITOR_CHILD_UNAVAILABLE` test | `tests/test_web_api.py` is an existing read-only suite to RUN as-is (surface contract must pass unmodified); editing it requires an explicit successor-claim amendment with integrator approval BEFORE mutation — it is not part of the seven-file R2 allowlist |

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
10. Over-limit/byte-bound three-tier truth: (a) attempts > 32 or shortlist > 16 → `monitor.route` = `UNAVAILABLE/ROUTE_EVIDENCE_OVER_LIMIT`, no truncation; (b) monitor child encoded > `MAX_FRAME_BYTES` → accepted guard yields the `MONITOR_PAYLOAD_TOO_LARGE` error child, `route` absent, UI renders `UNAVAILABLE/MONITOR_CHILD_UNAVAILABLE`; (c) whole frame encoded > `262_144` → existing typed `MONITOR_FRAME_OVERSIZED` behavior unchanged.
11. Monitor child absent or monitor-wide error → placeholder (`{error,gate}`), live-projection error child, and `MONITOR_PAYLOAD_TOO_LARGE` marker all render route `UNAVAILABLE/MONITOR_CHILD_UNAVAILABLE` (UI-side reason); placeholder is never coerced into `MonitorViews` and `MONITOR_CHILD_UNAVAILABLE` never appears in serialized JSON.

### Security & authority constraints

- Existing bearer-authenticated read-only snapshot only; no new endpoint, no CORS/CSP change.
- No provider client in the browser; advisory data only if an accepted server-side seam supplies it.
- No selection-event producer wiring (belongs to canary lineage / separate accepted WO).
- No pricing/billing source invention; cost stays ESTIMATED/UNKNOWN.
- Read DEFECT_LESSONS.md before any `src/a_conductor/` mutation (repo law).
- R2 allowed files — **precise per-file allowlist, no whole-tree claims**: NEW
  `src/a_conductor/route_explanation_projection.py`; NEW `tests/test_route_explanation_projection.py`;
  `src/a_conductor/monitor_live_provider.py` (route-child composition only);
  `web/sunday-family/src/api.ts` (MonitorViews/parseSnapshot route branch);
  NEW `web/sunday-family/src/RoutePanel.tsx` (drawer); NEW
  `web/sunday-family/tests/route-panel.test.tsx`; NEW
  `web/sunday-family/tests/route-dto.test.ts`. If the merged card-04 tree requires
  touching one additional existing section host component (e.g. the Jev/route-detail
  section), the successor claim MUST enumerate that exact file by name from the merged
  tree, and the accepted WO may be amended with integrator approval BEFORE mutation —
  never a `src/**`/`tests/**` glob. UX-2 files remain GPT-owned until PR #776 merges
  and the claim handoff is recorded.

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
