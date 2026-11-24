import { fireEvent, render, screen } from '@testing-library/react';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from '../src/App';
import { API_VERSION } from '../src/api';
import { SECTIONS } from '../src/sections';
import { snapshot, streamResponse } from './fixtures';

const TOKEN = 'test-only-token';

function stubMonitorApi(laneState = 'RUNNING', stale = false, staleReason: string | null = null) {
  const payload = {
    ...snapshot,
    stale,
    stale_reason: staleReason,
    cockpit: { lanes: [{ ...snapshot.cockpit.lanes[0], state: laneState }] },
  };
  const fetch = vi.fn().mockImplementation((path: string) => {
    if (path.endsWith('/health')) return Promise.resolve(Response.json({
      api_version: API_VERSION, status: 'ok', degraded: false, profile: 'headless-read-only', version: '1', conditions: [],
    }));
    if (path.endsWith('/snapshot')) return Promise.resolve(Response.json(payload));
    if (path.endsWith('/connectors')) return Promise.resolve(Response.json({ scope: 'app-session', connectors: [] }));
    return Promise.resolve(streamResponse([`data: ${JSON.stringify(payload)}\n\n`]));
  });
  vi.stubGlobal('fetch', fetch);
  return fetch;
}

afterEach(() => vi.unstubAllGlobals());

describe('stale truth handling (WO-P1-774 slice E)', () => {
  it('a stale snapshot never claims currency even when a lane reports READY', async () => {
    sessionStorage.setItem('sunday-family.monitor-token', TOKEN);
    stubMonitorApi('READY', true, 'STREAM_STALE_TEST');
    const { container } = render(<App />);
    expect(await screen.findByText('Stale: STREAM_STALE_TEST')).toBeInTheDocument();
    expect(screen.queryByText('Current at source')).toBeNull();
    const laneBadge = container.querySelector('.sf-badge[data-state="STALE"]');
    expect(laneBadge).not.toBeNull();
    expect(laneBadge?.className).not.toContain('verified');
    expect(screen.getByText(/Last reported: READY \(unverified\)/)).toBeInTheDocument();
  });

  it('disconnect while a lane is RUNNING returns to the token gate with no lane state left rendered', async () => {
    sessionStorage.setItem('sunday-family.monitor-token', TOKEN);
    stubMonitorApi('RUNNING');
    render(<App />);
    expect(await screen.findByText('WO-P1-690')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Disconnect & clear token' }));
    expect(await screen.findByLabelText('Bearer token')).toBeInTheDocument();
    expect(screen.queryByText('RUNNING')).toBeNull();
    expect(screen.queryByText('WO-P1-690')).toBeNull();
    expect(sessionStorage.length).toBe(0);
  });
});

describe('keyboard operability and focus (WO-P1-774 slice E)', () => {
  it('renders every section control as a native button reachable by keyboard', () => {
    sessionStorage.setItem('sunday-family.monitor-token', TOKEN);
    stubMonitorApi();
    render(<App />);
    const nav = screen.getByRole('navigation', { name: 'ส่วนงานหลัก / Primary sections' });
    for (const item of Array.from(nav.querySelectorAll('.nav-item'))) {
      expect(item.tagName).toBe('BUTTON');
      expect(item.getAttribute('tabindex')).toBeNull();
    }
    expect(nav.querySelectorAll('.nav-item')).toHaveLength(SECTIONS.length);
  });

  it('keeps the skip link and its target intact', () => {
    sessionStorage.setItem('sunday-family.monitor-token', TOKEN);
    stubMonitorApi();
    render(<App />);
    const skip = screen.getByText('Skip to monitor').closest('a');
    expect(skip?.getAttribute('href')).toBe('#main');
    expect(document.getElementById('main')).not.toBeNull();
  });
});

describe('a11y and theme CSS invariants (WO-P1-774 slice E)', () => {
  const css = readFileSync(resolve('src/styles.css'), 'utf8');

  function tokenHex(name: string): string {
    const match = css.match(new RegExp(`--${name}:\\s*(#[0-9A-Fa-f]{6})`));
    if (!match) throw new Error(`token --${name} missing`);
    return match[1];
  }

  function luminance(hex: string): number {
    const [r, g, b] = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255)
      .map(c => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  }

  function contrast(foreground: string, background: string): number {
    const [l1, l2] = [luminance(foreground), luminance(background)].sort((a, b) => b - a);
    return (l1 + 0.05) / (l2 + 0.05);
  }

  it('keeps normal text at 4.5:1 or better on every base surface', () => {
    for (const bg of ['sf-bg-canvas', 'sf-bg-surface', 'sf-bg-elevated']) {
      expect(contrast(tokenHex('sf-text-primary'), tokenHex(bg))).toBeGreaterThanOrEqual(4.5);
    }
    expect(contrast(tokenHex('sf-text-secondary'), tokenHex('sf-bg-surface'))).toBeGreaterThanOrEqual(4.5);
    expect(contrast(tokenHex('sf-text-muted'), tokenHex('sf-bg-surface'))).toBeGreaterThanOrEqual(4.5);
  });

  it('keeps status pigment text at 4.5:1 or better — labels are never color-only', () => {
    for (const tone of ['verified', 'running', 'waiting', 'degraded', 'blocked', 'info']) {
      expect(contrast(tokenHex(`sf-status-${tone}-fg`), tokenHex(`sf-status-${tone}-bg`))).toBeGreaterThanOrEqual(4.5);
    }
  });

  it('keeps the focus ring at 3:1 or better against the canvas', () => {
    expect(contrast(tokenHex('sf-focus-ring'), tokenHex('sf-bg-canvas'))).toBeGreaterThanOrEqual(3);
  });

  it('declares visible focus, reduced-motion guard, Thai wrap, and nav touch targets', () => {
    expect(css).toMatch(/:focus-visible\s*{[^}]*--sf-focus-ring/);
    expect(css).toMatch(/@media\s*\(prefers-reduced-motion:\s*reduce\)/);
    expect(css).toMatch(/overflow-wrap:\s*anywhere/);
    expect(css).toMatch(/\.nav-item\s*{[^}]*min-height:\s*(44px|2\.75rem)/s);
  });
});
