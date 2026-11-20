# WO-P1-659 — allowlist surface reconciliation (strict writes + doctor truth)

Status: DONE — SRM PR #31 merged 2026-10-14 at `d1da117` (pinned-head `c3dc14b`); design challenged pre-implementation (Sol SOUND_WITH_AMENDMENTS) + 3-round review (r1 P1 forged-version row-injection + P2 over-cap display + P3 non-merge gap → r2 P2 raw-count dimension → r3 PASS zero findings); claim released #659 comment 6168010170
Issue: #659
Parent: #495 (overnight P4); predecessors: slice-E installer (`agent-lifecycle.ts`), WO-P1-656 (`allowlist-config.ts`).
Risk: R3 — installer write-path semantics + displayed authorization truth.
Topology: EXECUTION_SUBSTRATE_ONLY. Compatibility: SRM `660ad00` + AWC `5ba505e` (re-pin on drift).

## Design (challenged by GPT-6 Sol pre-implementation: SOUND_WITH_AMENDMENTS — output archived in supervisor .tmp/wo659-challenge)

1. **Canonical surface = installer `config.json` `.allowlist`** (already consumed by shipped probes/canary).
2. **Strict writes**: `initializeSundayInstall` validates entries through the WO-656 rule on the INERT copy (absolute Windows/UNC; traversal/NUL/control-char/ADS/prefix/trailing-dot-space rejected; case-insensitive dedupe; raw-input bound AND 64-unique cap), persisting the normalized deduped result. Read-back unchanged. Reinstall rejection of >64 uniques documented.
3. **Lenient reads (backward compat)**: `persistedInstallValid` UNCHANGED (old-policy installs still read as valid evidence; 1024 cap). Load-bearing invariant (Sol amendment): STRICT validation applies wherever grants are DISPLAYED as usable — the doctor classifies legacy entries failing strict as `invalid-for-use`, never as granted.
4. **Doctor truth**: new install-config section resolving the INSTALLER root (`sundayAgentConfigRoot()`, `--config-root` respected) separately from the Sunday root: installer allowlist row with strict-for-display classification (N granted / M invalid-for-use) + standalone `allowlist.json` labeled NON-CANONICAL, disagreement reported WITHOUT merging grants.
5. **Root unification (installer `~/.desktop-commander-device` vs Sunday `~/.sunday-device`) = DECISION_REQUIRED follow-up** — deliberately NOT changed in this lane (it moves where real installs land; recorded for the operator/architecture lane).

## Forbidden

Standard set; `persistedInstallValid` read semantics untouched; no executor wiring; no real enrollment; no silent root change.

## Checkpoint log (append-only)

- [2026-10-14] WO created. Lane issue #659 verified real BEFORE naming. Sol challenge verdict SOUND_WITH_AMENDMENTS (4 amendments folded: root divergence found real — installer default `.desktop-commander-device` vs Sunday `.sunday-device`, CONFIRMED in source; strict-for-display classification; inert-copy + raw-count bound + persist normalized; disagreement-not-merge labeling). No source mutation yet.
