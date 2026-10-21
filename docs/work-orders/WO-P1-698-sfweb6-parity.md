# WO-P1-698 — SF-WEB-6: Web/Tk Parity Checklist

Issue: #698
Status: FIRST SLICE (parity analysis document)
Risk: R0 docs (analysis only, no code changes)
Topology: CONTROL_PLANE_ONLY

## Parity Matrix: Tk Desktop App vs Web Shell

| Feature | Tk Desktop | Web Shell | Gap | Priority |
|---|---|---|---|---|
| Worker list + status | ✅ WORKERS bar | ✅ SnapshotView | None | — |
| Connector list + status | ✅ CONNECTORS bar | ✅ SnapshotView | None | — |
| Start/Stop connector | ✅ buttons | ✅ ControlPanel (SF-WEB-4) | None | — |
| + Worker button | ✅ | ❌ | **P1** | High |
| + Connector button | ✅ wizard | ❌ | **P1** | High |
| Rename/Delete connector | ✅ | ❌ | **P2** | Medium |
| Assign project | ✅ dropdown | ✅ ControlPanel assign | None | — |
| MONITOR panel (log tail) | ✅ 5s refresh | ✅ LiveStream SSE | None | — |
| Real CPU/RAM metrics | ✅ system_metrics | ❌ | **P2** | Medium |
| Settings dialog | ✅ (language, toggles) | ❌ | **P3** | Low |
| Setup wizard (first run) | ✅ 7-step | ❌ | **P3** | Low |
| Donate dialog | ✅ | ❌ | **P4** | Low |
| Language switch (TH/EN/ZH) | ✅ i18n | ❌ | **P3** | Low |
| App close = stop all | ✅ toggle | N/A (web) | — | — |
| Particle logo animation | ✅ GPU canvas | ❌ | **P4** | Low |

## Summary
- **Already at parity**: 5 core features (worker/connector status, start/stop, assign, live monitor)
- **P1 gaps (must-have for retirement)**: Worker CRUD, Connector create wizard
- **P2 gaps (important)**: Rename/Delete, CPU/RAM metrics
- **P3/P4 gaps (nice-to-have)**: Settings, wizard, i18n, donate, logo

## Recommendation
Tk retirement is NOT ready until P1 gaps close. P2 gaps should follow.
P3/P4 can be deferred indefinitely (Tk keeps them if web doesn't).
