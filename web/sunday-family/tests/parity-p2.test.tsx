import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ConnectorRow } from '../src/ConnectorRow';
import { ConnectorsPanel } from '../src/ConnectorsPanel';
import { MetricsPanel } from '../src/MetricsPanel';
import { getMetrics } from '../src/api';

const connector = { connector_id: 'conn-test', name: 'My connector', state: 'STOPPED' };
const metrics = { cpu_percent: 25, memory_used_bytes: 1024 ** 3, memory_total_bytes: 4 * 1024 ** 3, uptime_seconds: 5 };

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

function row(state = 'STOPPED') {
  const changed = vi.fn();
  const result = render(<table><tbody><ConnectorRow connector={{ ...connector, state }} token="test-token" onChanged={changed} /></tbody></table>);
  return { ...result, changed };
}

describe('P2 connector controls', () => {
  it('renders name and explicit state, renames using authenticated PATCH', async () => {
    const fetch = vi.fn().mockResolvedValue(Response.json({ status: 'renamed' }));
    vi.stubGlobal('fetch', fetch);
    const { changed } = row();
    expect(screen.getByText('My connector')).toBeInTheDocument();
    expect(screen.getByText('STOPPED')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Rename' }));
    fireEvent.change(screen.getByLabelText('Connector name'), { target: { value: 'New name' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save name' }));
    await waitFor(() => expect(changed).toHaveBeenCalledTimes(1));
    const [path, options] = fetch.mock.calls[0];
    expect(path).toBe('/api/v1/connectors/conn-test');
    expect(options.method).toBe('PATCH');
    expect(options.headers.Authorization).toBe('Bearer test-token');
    expect(options.headers['X-Confirm'].length).toBeGreaterThanOrEqual(8);
    expect(JSON.parse(options.body)).toEqual({ name: 'New name' });
    expect(options.cache).toBe('no-store');
  });

  it('cancels rename and refuses blank name without network traffic', () => {
    const fetch = vi.fn(); vi.stubGlobal('fetch', fetch);
    row();
    fireEvent.click(screen.getByRole('button', { name: 'Rename' }));
    fireEvent.change(screen.getByLabelText('Connector name'), { target: { value: ' ' } });
    expect(screen.getByRole('button', { name: 'Save name' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByLabelText('Connector name')).not.toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
  });

  it('requires delete confirmation and cancels without a request', async () => {
    const fetch = vi.fn().mockResolvedValue(Response.json({ status: 'deleted' }));
    vi.stubGlobal('fetch', fetch);
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
    const { changed } = row();
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('My connector'));
    expect(fetch).not.toHaveBeenCalled();
    confirm.mockReturnValue(true);
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
    await waitFor(() => expect(changed).toHaveBeenCalledTimes(1));
    expect(fetch.mock.calls[0][1].method).toBe('DELETE');
  });

  it.each(['RUNNING', 'UNKNOWN', 'STARTING'])('disables delete for %s', state => {
    row(state);
    expect(screen.getByRole('button', { name: 'Delete' })).toBeDisabled();
  });

  it('shows mutation failure without false success or leaking server body', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('private-secret', { status: 503 })));
    const { changed } = row();
    fireEvent.click(screen.getByRole('button', { name: 'Rename' }));
    fireEvent.click(screen.getByRole('button', { name: 'Save name' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Refresh connectors to reconcile');
    expect(screen.queryByText(/private-secret/)).not.toBeInTheDocument();
    expect(changed).not.toHaveBeenCalled();
  });

  it('aborts a pending mutation when the row unmounts', () => {
    const fetch = vi.fn().mockReturnValue(new Promise(() => {})); vi.stubGlobal('fetch', fetch);
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const { unmount } = row();
    fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
    expect(screen.getByRole('button', { name: 'Delete' })).toBeDisabled();
    unmount();
    expect(fetch.mock.calls[0][1].signal.aborted).toBe(true);
  });

  it('lists only real session rows and refreshes to empty', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(Response.json({ scope: 'app-session', connectors: [connector] }))
      .mockResolvedValueOnce(Response.json({ scope: 'app-session', connectors: [] }));
    vi.stubGlobal('fetch', fetch);
    render(<ConnectorsPanel token="test-token" />);
    expect(await screen.findByText('My connector')).toBeInTheDocument();
    expect(screen.getByText(/Not persisted Tk connectors/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Refresh connectors' }));
    expect(await screen.findByText('No connectors created in this API session.')).toBeInTheDocument();
  });
});

describe('P2 system metrics', () => {
  it('renders CPU/RAM readings and supports refresh', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(Response.json(metrics)).mockResolvedValueOnce(Response.json({ ...metrics, cpu_percent: 50 }));
    vi.stubGlobal('fetch', fetch);
    render(<MetricsPanel token="test-token" />);
    expect(await screen.findByText('25.0%')).toBeInTheDocument();
    expect(screen.getByText('1.0 / 4.0 GiB')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Refresh metrics' }));
    expect(await screen.findByText('50.0%')).toBeInTheDocument();
    expect(fetch.mock.calls[0][0]).toBe('/api/v1/metrics');
  });

  it('shows unavailable for null readings instead of zero', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json({ ...metrics, cpu_percent: null, memory_used_bytes: null, memory_total_bytes: null })));
    render(<MetricsPanel token="test-token" />);
    await waitFor(() => expect(screen.queryByText('Reading system metrics...')).not.toBeInTheDocument());
    expect(screen.getAllByText('Unavailable')).toHaveLength(2);
    expect(screen.queryByText('0.0%')).not.toBeInTheDocument();
  });

  it('clears previous readings when refresh fails and aborts on unmount', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(Response.json(metrics)).mockResolvedValueOnce(new Response(null, { status: 401 }));
    vi.stubGlobal('fetch', fetch);
    const { unmount } = render(<MetricsPanel token="test-token" />);
    await screen.findByText('25.0%');
    fireEvent.click(screen.getByRole('button', { name: 'Refresh metrics' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Token rejected');
    expect(screen.queryByText('25.0%')).not.toBeInTheDocument();
    unmount();
    expect(fetch.mock.calls[1][1].signal.aborted).toBe(true);
  });

  it.each([-1, 101, '25'])('rejects invalid CPU reading %s', async cpu_percent => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json({ ...metrics, cpu_percent })));
    await expect(getMetrics('test-token', new AbortController().signal)).rejects.toThrow('Invalid system metrics');
  });
});
