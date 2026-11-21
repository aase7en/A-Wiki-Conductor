# SundayFamily — Color E-Ink Manga Design System
**Status:** OPERATOR-APPROVED VISUAL DIRECTION (2026-11-17); repository adoption and implementation remain gated by WO-P1-769 / Issue #769 and UX-1 Issue #743.
**Scope:** SundayFamily unified **web/PWA/operator management experience** across all screens, not the existing Tk desktop implementation or authority/safety protocols.
**Evidence:** Operator explicit preference; privately supplied Gemini Carbon 109-page v1.0.0-rc1 draft. Its screenshot measurements, 12-screen inventory and hypothetical routes are proposals until checked against current code. The 109-page DOCX is **not committed** here.
**Governance:** Existing `DESIGN.md` remains authoritative for current Tk desktop design/behavior; this document governs the approved *visual target* for SundayFamily web after review/merge. The web runtime boundary contract always governs permissions and execution.

## 1. Non-negotiable visual direction
- **Muted Color E-Ink / hand-inked manga:** warm archival-paper surfaces, charcoal ink strokes, soft desaturated pigment accents. No neon, glossy gradients, glassmorphism or generic SaaS visual filler.
- **Brand continuity:** preserve exact family portrait source `assets/sunday-family-particle.png` and respectful SundayFamily wordmark; optimized derivatives may be used for the web only after asset review.
- **Manga artwork in margins:** refined fine-line black pen, crosshatching, stippling and gentle rural/family motifs in brand header, onboarding, useful empty states and selected spot illustrations. Never put hatching or portraits behind data grids, logs, charts, input text or evidence.
- **Ink defines structure; pigment communicates supplementary meaning.** Readability and clear focus win over decorative fidelity. Use restrained rounded corners, no oversized soft shadows.
- **Thai-first bilingual, evidence-first:** Thai comprehension labels plus precise English technical terms. Status meaning requires label + shape/icon + timestamp/source, not color alone. All screenshot counts/hosts/percentages are SAMPLE, never production evidence.
- **Low-cost rendering:** static SVG/WebP/AVIF, no full-screen continuously animated stipple or heavy canvas effects; honor reduced-motion and low-spec Windows/macOS hardware.

## 2. Candidate tokens (design values, not measured runtime facts)
| Token | Candidate value | Meaning |
|---|---|---|
| `--sf-bg-canvas` | `#F4EFE6` | warm paper |
| `--sf-bg-surface` | `#F9F6EE` | readable panels |
| `--sf-bg-surface-alt` | `#ECE6D9` | muted header / row treatment |
| `--sf-bg-elevated` | `#FCFBF7` | modal / popup |
| `--sf-bg-brand-ink` | `#222523` | dark portrait/brand block |
| `--sf-text-primary` | `#1E2220` | charcoal text |
| `--sf-text-secondary` | `#464C48` | secondary text |
| `--sf-text-muted` | `#5C635E` | helper text; contrast test required |
| `--sf-border-ink` | `#323734` | crisp visible structure |
| `--sf-border-subtle` | `#D8D1C4` | non-essential dividers |
| `--sf-focus-ring` | `#234B66` | keyboard-visible focus |
| `--sf-status-verified-bg` | `#D6E3D4` | dusty sage |
| `--sf-status-running-bg` | `#D2E2DF` | faded teal |
| `--sf-status-waiting-bg` | `#F1E1B8` | pale mustard |
| `--sf-status-degraded-bg` | `#F2D5B3` | muted amber clay |
| `--sf-status-blocked-bg` | `#ECCAC2` | washed terracotta |
| `--sf-status-info-bg` | `#D7E1E8` | soft slate blue |
- Use sufficiently dark semantic foreground/borders (draft pairs: verified `#23422B`, running `#1F443E`, waiting `#523C0A`, degraded `#59300B`, blocked `#5A1E15`, info `#233B4D`). Verify every actual text/UI contrast combination in the rendered application.
- Suggested structural sizes: 4px spacing unit; 8/12/16/24/32px steps; compact/standard card padding 12–16px; visible 1–1.5px ink borders; radius 4/6/8/12px; desktop sidebar approx 220px, collapsed rail approx 68px; non-binding until UX implementation evidence.
- Typography candidates: `IBM Plex Sans Thai` / `Noto Sans Thai` for Thai, matching Latin sans; `JetBrains Mono` / `IBM Plex Mono` for IDs, SHAs and logs. Preserve Thai vowel/tone marks with approx 1.5–1.6 body line-height. Exact fonts and asset licenses need verification before loading.
- Illustration candidates: foreground pen line ~1.5px and light detail ~0.85px; paper grain at most subtle ~2.5% outside operational data regions. Static print effect, not runtime shader.

## 3. Canonical UX behavior and data semantics
- Present a **read-only-first** operational surface. Browser/PWA is NOT a second control plane or project SSoT. No direct browser-to-SunDayRemoteMCP mutation; changes, when separately admitted, go via A-Conductor Command Gateway with authorization/claim/replay checks and authoritative receipt.
- Distinguish `REGISTERED`, `STARTED`, `CONNECTED`, `READY`, plus `STALE` and `UNKNOWN` device states; don't infer runtime readiness from Git registration or successful tunnel alone.
- Work states `READY`, `RUNNING`, `WAITING`, `DEGRADED`, `BLOCKED`, `VERIFIED` must use actual evidence and timestamps. `ACCEPTED` is not `EXECUTED` or `COMPLETED`. Unknown metrics are `N/A`, never 0.
- Keep effective security/agent policies read-only on Settings unless a real permissioned backend mutation contract exists; never depict a toggle as saved from local browser state. Jev remains advisory/read-only.
- All API providers discovered in A-Wiki are `CATALOG_ONLY` until separately verified/admitted. Never show a marketplace listing as a live working tool. No secrets, tunnel identifiers or PHI in client payloads.
- Real data panels must show source, observed-at/freshness, reason code and expandable provenance. If projection becomes stale, retain only clearly-watermarked cached data and disclose the stale state; never fabricate success or totals.

## 4. Navigation and module mapping
**Keep the UX-1 approved baseline of seven Thai-first primary domains until operator answers remaining IA decisions** (Issue #743). The 109-page Gemini prototype's eight-menu proposal is NOT automatically canonical. The proposed 12 screens are a **coverage checklist**, not evidence of 12 live routes:
1. Overview (ภาพรวม); 2. Projects (โครงการ) as a project-level work view/subroute as needed; 3. Work & Lanes (งานและเลน); 4. Fleet (ทีมเครื่อง); 5. Tools / Hooks / Skills (เครื่องมือและการใช้งาน); 6. API & Knowledge (API และความรู้) as an A-Wiki-backed subview; 7. Evidence (หลักฐาน); 8. Reports (รายงาน); 9. Jev advisory (มุมตัดสินใจ); 10. Activity & Logs (บันทึกกิจกรรม); 11. Settings (ตั้งค่า); 12. Global search/drawers/overlays.
- Module grouping, route URLs, sidebar depth, count and tab structure require mapping to actual React routes, existing UX-1 packet and accepted contracts. **Do not create new routes, endpoints, control paths or store implementations from this list without a separate WO.**
- Keep lifecycle stage (PLN/DEV/QA/REL/OPS) orthogonal to functional work lane (Docs/Design/Web/Backend/Data/MCP/Review). Do not reduce one to the other or change authoritative classifications based on a mockup.

## 5. Shared component and state specifications
- Reusable app shell, sidebar, header/banner, page toolbar, status indicator, badges, cards, lane/work tables, fleet machine card, evidence links, log viewer, Jev advisory, search/filter controls, tabs, drawers, modal, inputs, skeleton, empty/error/offline states.
- Each interactive component specifies default/hover/focus/selected/disabled/loading/empty/stale/error, keyboard and accessible names, responsive behavior, provenance and failure behavior; no decorative nonfunctional switches or placeholder proof links.
- Focus indicator visible, text contrast WCAG 2.2 AA target (normal text at least 4.5:1; large text and applicable UI visuals at least 3:1); labels never color-only. Test at 390/768/900/1280/1440/1920px, browser zoom and high-density tables.
- Responsive: preserve high-density desktop operator workflow; collapse side panels into accessible drawers and reflow primary controls on smaller screens. Hide/compact tall art before obscuring content; never rely on downscaled desktop screenshots.
- Performance budgets are proposals, not benchmarks. Prefer SVG/icon reuse, no animated noise/filter over full screen, avoid rapid polling, and ensure stale/error/empty handling works offline.

## 6. Source reconciliation and migration gates
- **Verified from live repository at decision time:** current web React entry `web/sunday-family/src/App.tsx` and `web/sunday-family/src/styles.css` exist; their current CSS begins with dark background `#0c0f13`. UX-1 target packet `docs/design/2026-11-10-sunday-family-ux1-design.md` uses a seven-domain IA. Current Tk design authority `DESIGN.md` remains dark; web runtime authority lives in `docs/contracts/sunday-family-web-runtime-boundary-v1.md`.
- Gemini Carbon source `SundayFamily — Complete UI/UX Design System & Screen Specifications` (109-page private DOCX, v1.0.0-rc1) offers 37 chapters, 12 screen descriptions and 41 component candidates, but it did not inspect current private repository files. Its screenshot dimensions, status counts, routes, API endpoints and accessibility claims are **UNVERIFIED proposals** until independently tested.
- **Delivery sequence:** approved visual direction -> docs adoption/review -> UX-1 remaining navigation/packaging/behavior decisions -> one bounded React component/theme slice -> screenshot/contrast/perf audits -> incremental module parity -> real-device/CI/independent review -> accepted release. Do not replace Tk, rewrite all screens, or start UX-2 merely from this doc.
- **Acceptance for any implementation:** real screenshot comparisons, visual regression against approved art, AA checks, Thai text+keyboard tests, explicit no-secret/no-fake-health probes, target browser/platform smoke, measurable performance, rollback and independent exact-SHA review.

## 7. Decision log / conflicts
- **APPROVED 2026-11-17:** Color E-Ink + manga ink linework is the common SundayFamily web target for all modules; original stippled family portrait remains brand master.
- **REQUIRES SEPARATE DECISION:** seven vs eight top navigation entries, precise routes/IA; UX-1 operator's other five decisions not answered by color preference; packaging/WebView/PWA, mutation privileges, API/knowledge placement and date-display default. Do not represent these as approved.
- **UNCHANGED:** A-Conductor governance, SundayMCP execution substrate, A-Wiki knowledge authority, safe Command Gateway, claim/security/review, Tk carry-over until parity.
- **SUPERSEDED FOR WEB VISUALS ONLY:** monochrome-only exploration (#769 older wording), dark command-center as the target *web visual style*. Historical dark Tk requirements stay for Tk until its own accepted migration.

**Durable anchors:** [UX-1 / visual operator decision #743](https://github.com/aase7en/A-Wiki-Conductor/issues/743), [Design alignment WO #769](https://github.com/aase7en/A-Wiki-Conductor/issues/769), `docs/work-orders/WO-P1-769-sundayfamily-color-eink-design-alignment.md`.

## 8. Proposed SDLC Virtual Flow extension (2026-11-21 / Issue #782)

**Status: PROPOSED / NON-BINDING / NOT IMPLEMENTED.** For SundayFamily UI work specifically involving SDLC visualization, see [SDLC Virtual Flow — UI/UX Integration & Delivery Roadmap](../plans/2026-11-21-sundayfamily-sdlc-virtual-flow-roadmap.md) and [Issue #782](https://github.com/aase7en/A-Wiki-Conductor/issues/782). This is an additive design proposal under the existing SFU26 master program; it does **not** grant UI/source changes or supersede UX-2 Work Order #774 / PR #776.

- Preserve the seven-domain Thai-first IA. Place the proposed read-only Graph/Mind-Map view **inside Work & Lanes**, not as a new primary navigation domain.
- Use pencil-drawn **SVG connectors** with distinct dependency, evidence, feedback and association edge semantics, plus Color E-Ink node cards; reserve manga/landscape art for framing, margins and empty states, never over operational text.
- Prefer normal readable Thai/English typography for task labels, and hand-ink effect on noncritical paths/icons. Do not turn screenshots into runtime/metric proof.
- Animate only brief, evidence-consistent transitions; keep `prefers-reduced-motion`, keyboard accessible list fallback, true 200% zoom and source/freshness/reason visibility.
- Keep SDLC phase, functional lane, runtime status, risk and gate separate. Unknown remains UNKNOWN; no browser-created task, claim, evidence, completion or execution authority.

**Implementation dependency:** reconcile/accept the current UX-2 frontend owner/PR and re-run an independent Work Order + claim + R2 review/CI gate before editing `web/sunday-family/`.
