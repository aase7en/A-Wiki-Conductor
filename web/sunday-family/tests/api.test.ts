import { afterEach, describe, expect, it, vi } from 'vitest';
import { getSnapshot, parseSnapshot, streamSnapshots } from '../src/api';
import { snapshot, streamResponse } from './fixtures';

afterEach(() => vi.unstubAllGlobals());

describe('authenticated monitor client', () => {
  it('sends the bearer in a header, never URL or cookies', async () => {
    const fetch = vi.fn().mockResolvedValue(Response.json(snapshot));
    vi.stubGlobal('fetch', fetch);
    const signal = new AbortController().signal;
    expect(await getSnapshot('test-only-token', signal)).toEqual(snapshot);
    expect(fetch).toHaveBeenCalledWith('/api/v1/snapshot', expect.objectContaining({
      headers: { Authorization: 'Bearer test-only-token', Accept: 'application/json' },
      credentials: 'omit', redirect: 'error', cache: 'no-store', signal,
    }));
  });

  it('parses fragmented SSE, CRLF, comments, and multiple frames', async () => {
    const frame = `event: snapshot\r\ndata: ${JSON.stringify(snapshot)}\r\n\r\n`;
    const fetch = vi.fn().mockResolvedValue(streamResponse([
      ': heartbeat\n\n', frame.slice(0, 35), frame.slice(35, -1), frame.slice(-1),
      `event: update\ndata: ${JSON.stringify({ ...snapshot, stale: true })}\n\n`,
    ]));
    vi.stubGlobal('fetch', fetch);
    const received = vi.fn();
    await streamSnapshots('test-only-token', new AbortController().signal, received);
    expect(received).toHaveBeenCalledTimes(2);
    expect(received.mock.calls[1][0].stale).toBe(true);
    expect(fetch.mock.calls[0][1].headers.Authorization).toBe('Bearer test-only-token');
  });

  it('preserves UTF-8 split across bytes', async () => {
    const bytes = new TextEncoder().encode(`data: ${JSON.stringify({ ...snapshot, degraded_observability: ['TEST_ภาษาไทย'] })}\n\n`);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(new ReadableStream({
      start(controller) { for (const byte of bytes) controller.enqueue(new Uint8Array([byte])); controller.close(); },
    }), { headers: { 'Content-Type': 'text/event-stream' } })));
    const received = vi.fn();
    await streamSnapshots('test-only-token', new AbortController().signal, received);
    expect(received.mock.calls[0][0].degraded_observability).toEqual(['TEST_ภาษาไทย']);
  });

  it('rejects authorization failures without exposing server bodies', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('secret details', { status: 401 })));
    await expect(getSnapshot('test-only-token', new AbortController().signal)).rejects.toThrow('Token rejected');
  });

  it.each([
    ['monitor errors', 'data: {"error":"MONITOR_PROJECTION_UNAVAILABLE"}\n\n'],
    ['malformed JSON', 'data: invalid\n\n'],
    ['oversized frames', `data: ${'x'.repeat(262_145)}`],
  ])('rejects %s', async (_, frame) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(streamResponse([frame])));
    await expect(streamSnapshots('test-only-token', new AbortController().signal, vi.fn())).rejects.toThrow();
  });

  it('rejects non-SSE responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json(snapshot)));
    await expect(streamSnapshots('test-only-token', new AbortController().signal, vi.fn())).rejects.toThrow('event stream');
  });

  it.each([
    { ...snapshot, api_version: 'other' },
    { ...snapshot, cockpit: null },
    { ...snapshot, cockpit: { lanes: [{ ...snapshot.cockpit.lanes[0], state: {} }] } },
    { ...snapshot, cockpit: { lanes: [{ ...snapshot.cockpit.lanes[0], identity: { lane: {} } }] } },
  ])('rejects unsupported or malformed snapshots', value => {
    expect(() => parseSnapshot(value)).toThrow();
  });
});
