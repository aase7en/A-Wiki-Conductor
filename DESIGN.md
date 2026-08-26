# A-Sunday Conductor — Product UI / Interaction Design SSoT

Last updated: 2026-08-25
Status: APPROVED DIRECTION — implementation authority for WO-P1-063

## 1. Design intent

A-Sunday Conductor should look and behave like a lightweight professional command-center application: minimal, dark, terminal/CMD/CLI-inspired, information-dense, and calm. It is a Windows desktop application, not a web app. Preserve the existing Tk desktop architecture and only use GPU/OpenGL inside the bounded Sunday Family particle logo where it materially improves the effect.

Primary visual reference approved by the user on 2026-08-24: the dark A-Conductor command-center mockup with a compact Sunday Family portrait in the header, restrained borders, monospaced data, small status accents, a Projects sidebar, system overview, worker/connector tables, recent events, and a large terminal/log area.

The user reconfirmed this exact visual direction on 2026-08-25 with the wide near-black command-center reference. Match its hierarchy, density, thin dividers, calm status accents, and horizontal use of space while retaining the product capabilities absent from the static mockup: Add Brain, Assign, Add Connector, Guide, copyable diagnostics, and lifecycle-safe controls.

## 2. Non-negotiable visual rules

- Dark near-black / charcoal / subtle navy surfaces.
- Thin borders; no glossy cards, gradients, glass, large shadows, or decorative chrome.
- Monospaced typography for IDs, paths, state, logs, metrics, and command-like text.
- White / gray text first. Small semantic accents only: green healthy, amber warning, red destructive/error, muted blue informational/selection.
- Color communicates state; it is not decoration.
- Dense but readable spacing; wide windows use horizontal space rather than stacking controls unnecessarily.
- Animation is subtle and optional-looking. No large movement and no animation that steals focus or changes layout geometry.
- Graphs, when useful, use thin low-cost lines / tiny particle-like marks and update at a low frequency. Never spawn PowerShell/cmd/subprocesses from periodic render/monitor paths.

## 3. Sunday Family logo authority

Master source: `assets/sunday-family-particle.png` (1448×1086). This detailed portrait is the visual source of truth. `assets/logo-face.png` is legacy/compact fallback only and must not replace the master portrait.

### Rendering

- Background black.
- Portrait points are white / neutral gray only.
- Eyes may use a very small amber accent only when rendering the interactive logo state. The underlying portrait remains grayscale.
- At small sizes, preserve recognisable face landmarks and silhouette by adaptive sampling rather than by switching to a different family illustration.
- Particle points should be very fine. Prefer many small points over fewer large dots, within the performance budget.
- `Sunday Family` framed badge remains part of the master image when the display size permits it; at very small sizes it may visually simplify naturally through sampling, but the source is never replaced.
- When GPU output cannot be proven visible, the Canvas fallback may resize the exact master portrait once and animate only a bounded image/eye-accent set. Do not approximate the family with thousands of per-frame Canvas ovals merely to preserve the word "particle."

### Pointer motion

The logo may react gently to the pointer:
- eye-centre movement: target maximum about 2–3 px at the normal header size;
- face/head parallax: target maximum about 1–2 px, lower than eye movement;
- use smooth easing / spring return; no snapping;
- no strong head turn, no exaggerated gaze, no uncanny effect;
- movement should decay to neutral when the pointer leaves the application;
- motion must not cause layout movement;
- GPU renderer is preferred when available; Tk/Canvas fallback must remain safe and lightweight.

## 4. Main-screen information architecture

### Header

Left cluster:
1. compact Sunday Family particle portrait;
2. `A-Sunday Conductor` / `A-CONDUCTOR` product title;
3. short tagline: `Orchestrate. Execute. Observe.`;
4. compact status chips (controller/online, workers/connectors, uptime only when real data exists);
5. `Add Brain` is a first-class primary action near the product identity.

Right cluster:
- context-appropriate primary actions, English labels only;
- Guide / Settings remain easy to reach;
- actions should wrap only when width requires it.

### Main workspace

Wide / normal target:
- left: PROJECTS sidebar/list with filter/search seam;
- right/top: SYSTEM OVERVIEW with small factual counters/status, no invented metrics;
- primary runtime surface: **AI EXECUTION SLOTS — LIVE**, connector/runtime-centric and refreshed from real health + Serena telemetry;
- logical Worker Registry remains available as an **Advanced** scheduler-management surface and is collapsed by default so internal STOPPED/READY lifecycle state cannot be mistaken for live connector health;
- optional RECENT EVENTS region where space permits;
- bottom: command-console-like diagnostics area with tabs or compact sections for Terminal/Status, Logs, Events/Monitor. Existing copyable log behavior must be preserved.

Inline row guidance (added 2026-08-25, WO-P1-066, user request): each table carries a
trailing EDIT column whose cell text `Edit` opens that row's editor, and when a table
has no records at all its only row is a `+ Add ...` accent row that opens the matching
add dialog anywhere it is clicked. ttk.Treeview cannot host real per-cell widgets or
per-cell colors, so the affordance is text-in-cell; the PROJECTS sidebar is a
single-column Treeview (not a Listbox) for the same reason. Existing action bars are
unchanged.

Compact target:
- keep all controls reachable;
- panels may stack vertically;
- primary workflow remains ordered;
- no horizontal clipping of critical actions.

### AI Execution Slot operator model (2026-08-26)

The user-facing mental model is `Project -> AI Execution Slot -> Connection -> Active Project -> Task`.

- `CONNECTION` is live connector health (`/readyz`).
- `ACTIVE PROJECT` is read-only Serena runtime observation from the latest bounded activation-log event. Missing evidence is `UNKNOWN`; never infer.
- `BOUND PROJECT` is the connector launch/config binding and may differ from the active project after a ChatGPT session calls `activate_project`.
- A mismatch is rendered with explicit `[DRIFT]` text so meaning never relies on color alone.
- refresh reuses the existing low-frequency single-flight connector monitor; no periodic subprocess or MCP call is allowed.
- logical Worker Registry remains the scheduler/CRUD model for GE-6 but is Advanced/collapsed by default.
- labels must name the actor (`Start Worker`, `Start Connector`) instead of presenting two unrelated state machines as peers.

## 5. Existing behavior that must survive redesign

- Add Brain primary entry.
- Add Project / Assign / Add Worker / Start action flow.
- Add Connector discoverability.
- English action buttons globally.
- Thai / Simplified Chinese / English localized help/tooltips while button labels stay English.
- confirmed atomic assignment replacement.
- copyable MONITOR and ACTIVITY / LOG while read-only.
- Donate beside Check Update.
- safe worker/connector lifecycle behavior and existing invariants.
- GPU failure fallback.

## 6. Performance budget / lightweight contract

- UI framework remains Tk/Ttk; no Electron, browser, embedded web app, or framework rewrite.
- No new periodic subprocess spawning.
- Default UI update interval should be event-driven or low frequency where practical.
- Particle animation is bounded to the logo region.
- Header particle count adapts to rendered size; do not render the full source-resolution point count.
- Target normal header logo animation >= 30 FPS on ordinary integrated graphics when GPU is available; fallback should remain responsive even if it renders fewer points.
- Resize handlers must be debounced/stable and must not create configure loops.
- Monitoring reads must stay native/file-based and follow `DEFECT_LESSONS.md`.
- GPU readiness requires observable framebuffer output, not merely a created context/buffer or a non-zero particle count. A blank or materially incomplete frame must fall back safely.

### PROJECT DISK magnitude cue (2026-08-26)

- `PROJECT DISK` exact human-readable text remains authoritative.
- A bounded 24-dot monochrome strip may sit beside the number as a visual order-of-magnitude cue.
- The strip uses a deterministic logarithmic magnitude mapping (B/KB/MB/GB/TB); it must never imply `% disk full` or a project quota.
- `—`, `…`, and malformed values render fail-closed/dim.
- The renderer consumes only the already-computed async/cached disk display value: no additional filesystem walk, subprocess, timer, thread, network call, or continuous animation.
- Dots derive from the existing foreground/muted/border palette and must remain usable without color.
- Tooltip/help text must explicitly explain that the dots are relative magnitude and the exact number is authoritative.

### Embedded beginner Guide (2026-08-26)

- The Guide remains a native Tk `Toplevel`; it is not a browser/app rewrite.
- `docs/USER-GUIDE.md` and `docs/USER-GUIDE-EN.md` are the content source of truth. HTML is generated in memory from them.
- Primary renderer is local TkinterWeb `HtmlFrame`; no Chromium/WebView/Electron and no JavaScript requirement.
- Guide rendering must not fetch remote CSS/fonts/images/scripts or send analytics. External web URLs open only after an explicit click.
- The Guide presents six local sections: Start Here, First Setup, Daily Use, Add Chat, Terms, Troubleshooting, with a visible `Step n / 6` marker.
- Start Here explains the operator model as `ChatGPT -> Tunnel -> Connector -> Project` and distinguishes live `ACTIVE PROJECT` from connector `BOUND PROJECT`.
- Repeated Guide clicks reuse/lift the existing singleton window.
- If the HTML renderer/import/load path fails, fall back to the existing read-only Markdown `tk.Text` viewer with clickable URLs.
- No continuous animation. Accessibility and reduced-motion behavior are the default.
- Frozen builds must explicitly collect TkinterWeb/Tkhtml runtime packages and include their licenses/notices.

## 7. Responsive rules

- COMPACT `< 900px`: wrap controls, stack secondary regions if necessary.
- STANDARD `900–1279px`: horizontal primary workflow; compact panels.
- WIDE `>= 1280px`: use width aggressively; primary actions in one row where practical; major monitoring/log regions side-by-side or tabbed without wasted vertical stacking.
- Layout is based on actual available widget width, not screen resolution.
- At the minimum compact height, prefer shorter terminal captions such as `WORKERS`, `CONNECTORS`, and `STATE` over adding overview rows that hide selectable Worker rows. Values and meaning must remain complete and unambiguous.

## 8. Accessibility / interaction

- keyboard focus order follows operator workflow;
- selected/active state must not rely on color alone;
- all diagnostics remain selectable/copyable;
- destructive actions remain visually distinct and confirmed where appropriate;
- pointer animation is decorative/assistive only; it never blocks clicking or keyboard operation;
- future reduced-motion preference must be possible without redesigning the renderer.

## 9. Design verification

A redesign is not accepted from screenshots alone. Verify:
- 700-ish compact, 900-ish standard, 1280+, and maximized layouts;
- all primary actions reachable;
- no unintended button-language change after TH/zh-CN/EN switching;
- Add Brain and Add Connector visible/discoverable;
- Sunday Family portrait recognisable at actual header size;
- eye/face motion subtle under real pointer movement;
- app close cleans animation callbacks/context;
- GPU-disabled fallback remains usable;
- copy logs, assignment replacement, worker/connector operations still work;
- build/package contains all assets and renderer dependencies;
- fresh installed application is visually verified, preventing source-vs-installed drift.

## 10. Cross-agent rule

This file is the visual/interaction authority for the redesign. Agents must not independently invent a second visual direction. Implementation details may change after test/review evidence, but changes to the approved design intent must be recorded here and in the active work order before code diverges.

## 11. Real system monitoring contract

`SYSTEM OVERVIEW` may show CPU, RAM, and app uptime only when they come from real runtime measurements. Never invent values to imitate a mockup.

- CPU = real machine CPU utilisation sampled from native OS counters / kernel data; unavailable -> `—`.
- RAM = real physical memory used / total; unavailable -> `—`.
- Uptime = elapsed lifetime of the current A-Sunday Conductor process/session using a monotonic clock.
- Project/Worker/Connector counters remain derived from the actual service snapshot and connector health state.
- Monitoring must not spawn PowerShell, cmd, shell utilities, or any other subprocess on a periodic path.
- Prefer native Windows API on Windows and file/native fallbacks on other supported systems. Unsupported metrics degrade to `—` rather than guessed numbers.
- Default refresh should be low frequency (about 2–5 seconds) and UI-only. It must stop cleanly during app shutdown.
- A tiny CPU history/sparkline is allowed only from the same real samples; keep at most a small bounded history and draw with a thin line/particle-like mark.
