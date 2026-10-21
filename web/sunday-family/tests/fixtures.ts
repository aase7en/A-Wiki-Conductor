import { API_VERSION, type Snapshot } from '../src/api';

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

export function streamResponse(chunks: string[]) {
  const encoder = new TextEncoder();
  return new Response(new ReadableStream({
    start(controller) { chunks.forEach(chunk => controller.enqueue(encoder.encode(chunk))); controller.close(); },
  }), { headers: { 'Content-Type': 'text/event-stream; charset=utf-8' } });
}
