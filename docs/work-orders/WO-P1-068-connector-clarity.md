# WO-P1-068 — Connector clarity & close safety (Rescan incident)

Created: 2026-08-26
Owner: GLM 5.3 Max (user-reported incident; textual/behavioral scope, records per standing takeover pattern)
Status: implementation on `fix/connector-clarity-safety`, PR pending
Base: `origin/main` `333750e` (post-v0.6.0-complete)

## Incident (user report, 2026-08-26)

While GPT chat sessions worked through plugins Sunday-Worker-1..4, pressing **Rescan** appeared to "close instances that had no connector in the Workers table", disconnecting all chats ("server on the PC died"). The user was also confused about how to "configure the connector column" in Workers and how tunnel IDs pair with the GPT account.

## Investigation (code-level, evidence in session + this WO)

- `rescan_instances` = log + rediscover + probe + re-render. **No stop semantics** — verified against every process-terminating path in the codebase (Stop button, close-time stop-all, close-only wrapper reaper, worker lifecycle). Nothing selects instances by absence of Workers-table registration.
- Real killer: **close-time stop-all** (`shutdown_stops_instances`, default ON since v0.2.2) stops every discovered connector when the window closes; the CONNECTORS table did not live-refresh, so dead sessions kept displaying READY until Rescan revealed them.
- Workers-table CONNECTOR (?) column is a **derived display** (exact project-path equality via `connector_name_for_project`) — not a registration, no link button exists by design.

## Changes (this branch)

1. **Close-time confirm:** when the stop-on-close preference is ON and the last known state has RUNNING connectors, closing asks once ("จะหยุด N ตัว… แชทจะถูกตัด — หยุดเลย / ปิดโดยไม่หยุด"); declining skips stop+reap for that close only (preference untouched).
2. **Rescan summary:** the poll logs `RESCAN พบ N ตัวเชื่อม: X READY, Y STOPPED`.
3. **Live CONNECTORS refresh:** 15 s single-flight state refresh mirroring the monitor tick; cancelled in `_stop_instance_monitor`.
4. **Masked tunnel pairing:** `LocalInstance.tunnel_suffix` (last 4 chars) from `tunnel-id.txt`; TUNNEL column shows `...e3f1` (or `Y`/`-`); Edit-connector dialog shows "ปัจจุบัน: ...xxxx". Full IDs are credentials and are never displayed (AGENTS safety rule).
5. **Guides §4.6 updated** (TH+EN): tunnel-column matching, CONNECTOR(?) is derived-not-registration, CONNECTORS table is the tunnel source of truth.

## Handed to GPT (design lane, not attempted here)

- First-run "pair my tunnel IDs" wizard / any GPT-account-level default binding (OpenAI requires the user to create tunnels; interaction design needed).
- Changing the default of `shutdown_stops_instances` (product decision).
- True real-time "active project per chat" view (overlaps GE-10 operator visualization).

## Tests

`tests/test_connector_clarity.py` (8 tests): close-asks/decline-skips, close-silent-when-idle, rescan summary, masked suffix in table (+dash case), discovery suffix extraction, edit-dialog masked hint, periodic tick scheduled+cancelled. Suite reruns handle the known transient uv-Tk skip.
