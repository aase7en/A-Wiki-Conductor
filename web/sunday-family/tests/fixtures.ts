import { API_VERSION, type MonitorViews, type Snapshot } from '../src/api';

export const snapshot: Snapshot = {
  api_version: API_VERSION,
  generated_at: '2026-10-21T05:00:00Z',
  cockpit: { lanes: [{
    identity: { work_order_ref: 'WO-P1-690', task_ref: null, lane: 'a-worker-01', execution_id: 'exec-690', lease_id: null, provenance: 'OBSERVED' },
    state: 'RUNNING', state_markers: ['OBSERVED'], blocker_code: null,
    next_safe_action: 'OBSERVE', last_activity: null, last_meaningful_progress: null,
    gates: { verification: 'UNKNOWN', review: 'UNKNOWN', merge: 'UNKNOWN', ci: 'UNKNOWN', post_main: 'UNKNOWN', provenance: 'OBSERVED' },
  }] },
  monitor: { error: 'MONITOR_PROJECTION_UNAVAILABLE', gate: 'OPTIONAL_READ_PORT_UNAVAILABLE' },
  stale: false, stale_reason: null, degraded_observability: ['ACTIVITY_READER_UNAVAILABLE'],
  monitor_stream_degraded: false,
};

// WO-P1-750: live monitor-views child (strict-validated union branch).
export const liveMonitor: MonitorViews = {
  health: { degraded: true, counters: {}, conditions: ['MONITOR_BUS_ABSENT'] },
  timeline: [{ event_id: 'e1', event_type: 'OBSERVE', hook_class: 'OBSERVE', occurred_at: '2026-11-13T00:00:00Z', note: 'ok' }],
  stm: [{ partition: 'hooks', state: 'FRESH', rebuild_required: false, record_count: 3 }],
  correlation: { state: 'UNKNOWN' },
  inspector: {
    summary: {
      generated_at: '2026-11-13T00:00:00Z',
      tools: { counts: { READY: 1, UNKNOWN: 1 }, truncated: false, dropped: 0 },
      hooks: { counts: { UNKNOWN: 4 }, truncated: false, dropped: 0 },
      skills: { counts: { AVAILABLE: 2, STALE: 1 }, truncated: false, dropped: 0 },
    },
    tools: [{ name: 'a-worker-01', device: 'windows-local', category: 'connector', source: 'instance.ps1 discovery', phase: 'CONNECTED', state: 'READY', registration_evidence: 'instance.ps1', last_verified: null, last_error: '', next_safe_action: 'Inspect health evidence', provenance: 'probe:readyz' }],
    hooks: [],
    skills: [],
  },
};

export const liveSnapshot: Snapshot = { ...snapshot, monitor: liveMonitor };

export function streamResponse(chunks: string[]) {
  const encoder = new TextEncoder();
  return new Response(new ReadableStream({
    start(controller) { chunks.forEach(chunk => controller.enqueue(encoder.encode(chunk))); controller.close(); },
  }), { headers: { 'Content-Type': 'text/event-stream; charset=utf-8' } });
}
