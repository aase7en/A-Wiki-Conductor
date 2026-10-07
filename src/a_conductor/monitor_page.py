"""WO-P1-599: UI-1 read-only monitor page — constant self-contained bytes.

The page is a compile-time constant: no server-side interpolation, no
external origins (strict CSP), no build toolchain. The per-boot token is
read once from the URL fragment, stripped from the address bar, held in
memory only, and sent exclusively in the Authorization header to the same
origin. Truth semantics are explicit: UNKNOWN, STALE, and DEGRADED render
as labeled badges — never as healthy/current/success — and the page issues
GET requests only.
"""

_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>A-Sunday Monitor (read-only)</title>
<meta http-equiv="Content-Security-Policy"
      content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'">
<style>
 body{font-family:Consolas,monospace;background:#111;color:#ddd;margin:2rem}
 h1{font-size:1.1rem} h2{font-size:1rem;margin-top:1.4rem;color:#9cf}
 .badge{display:inline-block;padding:0.15rem 0.6rem;border:1px solid;border-radius:4px;font-size:0.8rem;margin-right:0.4rem}
 .ok{color:#8f8;border-color:#8f8} .unknown{color:#fc6;border-color:#fc6}
 .stale{color:#f96;border-color:#f96} .degraded{color:#f66;border-color:#f66}
 table{border-collapse:collapse;margin-top:0.4rem}
 td,th{border:1px solid #444;padding:0.25rem 0.7rem;font-size:0.85rem;text-align:left}
 #state{margin:1rem 0;padding:0.6rem;border:1px solid #666;min-height:1.2rem}
 .err{color:#f66} .quiet{color:#888}
</style>
</head>
<body>
<h1>A-Sunday Monitor — read-only</h1>
<div id="state" class="quiet">loading…</div>
<h2>Health</h2><div id="health"></div>
<h2>Timeline</h2><div id="timeline"></div>
<h2>STM partitions</h2><div id="stm"></div>
<h2>Correlation</h2><div id="corr"></div>
<script>
"use strict";
var token = "";
function readToken() {
  var m = /^#token=(.+)$/.exec(location.hash);
  if (m) { token = decodeURIComponent(m[1]); }
  history.replaceState(null, "", location.pathname);
}
function badge(label, cls) {
  return '<span class="badge ' + cls + '">' + esc(label) + '</span>';
}
function esc(s) {
  return String(s).replace(/[&<>"']/g, function (c) {
    return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c];
  });
}
function setState(text, cls) {
  var el = document.getElementById("state");
  el.className = cls || "";
  el.textContent = text;
}
function renderHealth(h) {
  var out = [];
  if (!h) { out.push(badge("UNKNOWN", "unknown"), "no health evidence"); }
  else {
    out.push(h.degraded ? badge("DEGRADED", "degraded")
                        : badge("OK", "ok"));
    var counters = Object.keys(h.counters || {});
    if (counters.length) {
      out.push("<table><tr><th>counter</th><th>value</th></tr>");
      counters.forEach(function (k) {
        out.push("<tr><td>" + esc(k) + "</td><td>" + esc(h.counters[k]) + "</td></tr>");
      });
      out.push("</table>");
    }
    (h.conditions || []).forEach(function (c) {
      out.push('<div class="err">' + esc(c) + "</div>");
    });
  }
  document.getElementById("health").innerHTML = out.join(" ");
}
function renderTimeline(rows) {
  if (!rows || !rows.length) {
    document.getElementById("timeline").innerHTML =
      badge("UNKNOWN", "unknown") + " no recent events";
    return;
  }
  var out = ["<table><tr><th>event</th><th>class</th><th>when</th></tr>"];
  rows.forEach(function (r) {
    out.push("<tr><td>" + esc(r.event_id || "UNKNOWN") + "</td><td>" +
             esc(r.hook_class || "UNKNOWN") + "</td><td>" +
             esc(r.occurred_at || "UNKNOWN") + "</td></tr>");
  });
  out.push("</table>");
  document.getElementById("timeline").innerHTML = out.join("");
}
function renderStm(states) {
  if (!states || !states.length) {
    document.getElementById("stm").innerHTML =
      badge("UNKNOWN", "unknown") + " no partition evidence";
    return;
  }
  var out = ["<table><tr><th>partition</th><th>state</th><th>rebuild</th><th>records</th></tr>"];
  states.forEach(function (s) {
    var cls = s.state === "FRESH" ? "ok" :
              s.state === "STALE" ? "stale" : "unknown";
    out.push("<tr><td>" + esc(s.partition) + "</td><td>" +
             badge(s.state || "UNKNOWN", cls) + "</td><td>" +
             (s.rebuild_required ? badge("rebuild_required", "degraded") : "—") +
             "</td><td>" + esc(s.record_count) + "</td></tr>");
  });
  out.push("</table>");
  document.getElementById("stm").innerHTML = out.join("");
}
function renderCorrelation(c) {
  if (!c || c.state === "UNKNOWN") {
    document.getElementById("corr").innerHTML =
      badge("UNKNOWN", "unknown") + " no correlation evidence";
    return;
  }
  // Only an explicitly known-good state renders green; anything the
  // projection did not enum-clamp stays visibly neutral, never success.
  var cls = c.state === "OBSERVED" ? "ok" : "unknown";
  var out = [badge(c.state, cls)];
  var entries = c.entries || [];
  if (entries.length) {
    out.push("<table><tr><th>field</th><th>value</th></tr>");
    entries.forEach(function (e) {
      Object.keys(e).forEach(function (k) {
        out.push("<tr><td>" + esc(k) + "</td><td>" + esc(e[k]) + "</td></tr>");
      });
    });
    out.push("</table>");
  }
  document.getElementById("corr").innerHTML = out.join(" ");
}
function render(views) {
  renderHealth(views.health);
  renderTimeline(views.timeline);
  renderStm(views.stm);
  renderCorrelation(views.correlation);
}
function haltOnForbidden(message) {
  if (pollTimer !== null) { clearTimeout(pollTimer); pollTimer = null; }
  setState(message, "err");
}
function poll() {
  if (!token) {
    haltOnForbidden("FORBIDDEN — token missing. Append #token=<monitor token> to the address and reload.");
    return;
  }
  fetch("/snapshot", {headers: {"Authorization": "Bearer " + token}})
    .then(function (r) {
      if (r.status === 403) { throw {fatal: true, message: "FORBIDDEN — token rejected; polling halted. Reload with a valid #token=."}; }
      if (r.status === 503) { throw new Error("PROJECTION UNAVAILABLE — monitor degraded"); }
      if (!r.ok) { throw new Error("HTTP " + r.status); }
      return r.json();
    })
    .then(function (views) {
      setState("live (snapshot polling)", "quiet");
      backoffDelay = 2000;  // healthy again: reset the poll interval
      render(views);
    })
    .catch(function (e) {
      if (e && e.fatal) { haltOnForbidden(e.message); throw e; }  // fatal: skip reschedule
      backoffDelay = Math.min(backoffDelay * 2, 30000);  // grow on 503/error
      setState(String(e.message || e), "err");
    })
    .then(function () {
      if (pollTimer !== null) { clearTimeout(pollTimer); }
      pollTimer = setTimeout(poll, backoffDelay);
    })
    .catch(function () {});  // swallow the expected fatal rejection
}
var pollTimer = null;
var backoffDelay = 2000;  // doubles on 503/error up to 30s; resets on success
readToken();
poll();
</script>
</body>
</html>
"""

MONITOR_PAGE_BYTES: bytes = _PAGE.encode("utf-8")


def monitor_page_bytes() -> bytes:
    """Return the constant page bytes (identical object every call)."""
    return MONITOR_PAGE_BYTES
