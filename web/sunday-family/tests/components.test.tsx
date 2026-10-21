import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from '../src/App';
import { HealthIndicator } from '../src/HealthIndicator';
import { LiveStream } from '../src/LiveStream';
import { SnapshotView } from '../src/SnapshotView';
import { TokenGate } from '../src/TokenGate';
import { API_VERSION } from '../src/api';
import { snapshot, streamResponse } from './fixtures';

afterEach(() => vi.unstubAllGlobals());

describe('monitor components', () => {
  it('keeps the token in sessionStorage and clears it on disconnect', () => {
    render(<TokenGate>{(token, disconnect) => <><p>Connected: {token.length}</p><button onClick={disconnect}>Disconnect</button></>}</TokenGate>);
    fireEvent.change(screen.getByLabelText('Bearer token'), { target: { value: 'test-only-token' } });
    fireEvent.click(screen.getByRole('button', { name: 'Connect monitor' }));
    expect(sessionStorage.getItem('sunday-family.monitor-token')).toBe('test-only-token');
    expect(localStorage.length).toBe(0);
    fireEvent.click(screen.getByRole('button', { name: 'Disconnect' }));
    expect(sessionStorage.length).toBe(0);
    expect(screen.getByLabelText('Bearer token')).toHaveValue('');
  });

  it('restores only the current tab session token', () => {
    sessionStorage.setItem('sunday-family.monitor-token', 'test-only-token');
    render(<TokenGate>{() => <p>Restored session</p>}</TokenGate>);
    expect(screen.getByText('Restored session')).toBeInTheDocument();
  });

  it('makes no network request before token entry', () => {
    const fetch = vi.fn(); vi.stubGlobal('fetch', fetch);
    render(<App />);
    expect(fetch).not.toHaveBeenCalled();
  });

  it('renders real lanes, gates, and honest unavailable states', () => {
    render(<SnapshotView snapshot={snapshot} />);
    expect(screen.getByText('WO-P1-690')).toBeInTheDocument();
    expect(screen.getByText('RUNNING')).toBeInTheDocument();
    expect(screen.getByText('ci: UNKNOWN')).toBeInTheDocument();
    expect(screen.getAllByText('Unavailable')).toHaveLength(2);
    expect(screen.getByText(/Stream snapshots are not an activity log/)).toBeInTheDocument();
    expect(screen.getByText('ACTIVITY_READER_UNAVAILABLE')).toBeInTheDocument();
  });

  it('shows stale, degraded, and empty states explicitly', () => {
    render(<SnapshotView snapshot={{ ...snapshot, cockpit: { lanes: [] }, stale: true, stale_reason: 'PROJECTION_STALE', monitor_stream_degraded: true }} />);
    expect(screen.getByText('Stale: PROJECTION_STALE')).toBeInTheDocument();
    expect(screen.getByText(/updates may have been dropped/)).toBeInTheDocument();
    expect(screen.getByText('No execution lanes in this snapshot.')).toBeInTheDocument();
  });

  it('shows API degradation instead of claiming healthy', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json({
      api_version: API_VERSION, status: 'ok', degraded: true, profile: 'headless-read-only', version: '1.0', conditions: ['OPTIONAL_MONITOR_UNAVAILABLE'],
    })));
    render(<HealthIndicator token="test-only-token" />);
    expect(await screen.findByText('API: degraded')).toBeInTheDocument();
    expect(screen.getByText('OPTIONAL_MONITOR_UNAVAILABLE')).toBeInTheDocument();
  });

  it('shows unauthorized health as unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 401 })));
    render(<HealthIndicator token="test-only-token" />);
    expect(await screen.findByText('API: unavailable')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('Token rejected');
  });

  it('handles stream EOF, manual reconnect, and cleanup abort', async () => {
    const fetch = vi.fn().mockImplementation(() => Promise.resolve(streamResponse([`data: ${JSON.stringify(snapshot)}\n\n`])));
    vi.stubGlobal('fetch', fetch);
    const onSnapshot = vi.fn();
    const { unmount } = render(<LiveStream token="test-only-token" onSnapshot={onSnapshot} />);
    await screen.findByText('Stream: disconnected');
    expect(onSnapshot).toHaveBeenCalledWith(snapshot);
    fireEvent.click(screen.getByRole('button', { name: 'Reconnect stream' }));
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
    await screen.findByText('Stream: disconnected');
    unmount();
    expect(fetch.mock.calls[1][1].signal.aborted).toBe(true);
  });

  it('loads the shell, applies streamed snapshots, and disconnects all requests', async () => {
    sessionStorage.setItem('sunday-family.monitor-token', 'test-only-token');
    const signals: AbortSignal[] = [];
    vi.stubGlobal('fetch', vi.fn().mockImplementation((path: string, init: RequestInit) => {
      signals.push(init.signal as AbortSignal);
      if (path.endsWith('/health')) return Promise.resolve(Response.json({ api_version: API_VERSION, status: 'ok', degraded: true, profile: 'headless-read-only', version: '1', conditions: [] }));
      if (path.endsWith('/snapshot')) return Promise.resolve(Response.json(snapshot));
      return Promise.resolve(streamResponse([`data: ${JSON.stringify({ ...snapshot, stale: true, stale_reason: 'STREAM_TEST' })}\n\n`]));
    }));
    render(<App />);
    expect(await screen.findByText('Stale: STREAM_TEST')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Disconnect & clear token' }));
    await act(async () => {});
    expect(screen.getByLabelText('Bearer token')).toBeInTheDocument();
    expect(signals.every(signal => signal.aborted)).toBe(true);
    expect(sessionStorage.length).toBe(0);
  });
});
