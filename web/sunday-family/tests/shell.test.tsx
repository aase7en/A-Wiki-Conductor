import { fireEvent, render, screen } from '@testing-library/react';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from '../src/App';
import { API_VERSION } from '../src/api';
import { StateBadge } from '../src/StateBadge';
import { EmptyState, ReasonLine, TruncatedNote } from '../src/StatusPanels';
import { SECTIONS } from '../src/sections';
import { snapshot, streamResponse } from './fixtures';

const TOKEN = 'test-only-token';

function stubMonitorApi() {
  const fetch = vi.fn().mockImplementation((path: string) => {
    if (path.endsWith('/health')) return Promise.resolve(Response.json({
      api_version: API_VERSION, status: 'ok', degraded: false, profile: 'headless-read-only', version: '1', conditions: [],
    }));
    if (path.endsWith('/snapshot')) return Promise.resolve(Response.json(snapshot));
    if (path.endsWith('/connectors')) return Promise.resolve(Response.json({ scope: 'app-session', connectors: [] }));
    return Promise.resolve(streamResponse([`data: ${JSON.stringify(snapshot)}\n\n`]));
  });
  vi.stubGlobal('fetch', fetch);
  return fetch;
}

function navButton(thai: string) {
  return screen.getByRole('button', { name: new RegExp(thai) });
}

afterEach(() => vi.unstubAllGlobals());

describe('seven-section shell (WO-P1-774 slice A)', () => {
  it('renders the seven accepted Thai-first sections in canonical order', () => {
    sessionStorage.setItem('sunday-family.monitor-token', TOKEN);
    stubMonitorApi();
    render(<App />);
    const nav = screen.getByRole('navigation', { name: 'ส่วนงานหลัก / Primary sections' });
    for (const section of SECTIONS) expect(navButton(section.thai)).toBeInTheDocument();
    expect(SECTIONS.map(section => section.id)).toEqual(['overview', 'fleet', 'work', 'tools', 'settings', 'jev', 'activity']);
  });

  it('marks Overview as the current section and moves aria-current on navigation', () => {
    sessionStorage.setItem('sunday-family.monitor-token', TOKEN);
    stubMonitorApi();
    render(<App />);
    const overview = navButton('ภาพรวม');
    expect(overview.getAttribute('aria-current')).toBe('page');
    const fleet = navButton('ทีมเครื่อง');
    expect(fleet.getAttribute('aria-current')).toBeNull();
    fireEvent.click(fleet);
    expect(fleet.getAttribute('aria-current')).toBe('page');
    expect(overview.getAttribute('aria-current')).toBeNull();
    fireEvent.click(overview);
    expect(overview.getAttribute('aria-current')).toBe('page');
  });

  it('keeps existing monitor projections under Overview and honest placeholders elsewhere', async () => {
    sessionStorage.setItem('sunday-family.monitor-token', TOKEN);
    stubMonitorApi();
    render(<App />);
    expect(await screen.findByText('Execution lanes')).toBeInTheDocument();
    for (const section of SECTIONS.filter(item => ['settings', 'jev', 'activity'].includes(item.id))) {
      fireEvent.click(navButton(section.thai));
      expect(screen.getByRole('heading', { level: 1, name: new RegExp(section.thai) })).toBeInTheDocument();
      expect(screen.getByRole('heading', { level: 2, name: new RegExp(section.thai) })).toBeInTheDocument();
      expect(screen.getAllByText('ยังไม่มีหลักฐานยืนยัน').length).toBeGreaterThan(0);
      expect(screen.getByText(section.reasonCode)).toBeInTheDocument();
      expect(screen.queryByText(/^0 (เครื่อง|งาน|รายการ)/)).toBeNull();
    }
  });

  it('issues only read requests while rendering and switching sections', () => {
    sessionStorage.setItem('sunday-family.monitor-token', TOKEN);
    const fetch = stubMonitorApi();
    render(<App />);
    for (const section of SECTIONS) fireEvent.click(navButton(section.thai));
    expect(fetch).toHaveBeenCalled();
    expect(fetch.mock.calls.filter(([, init]) => init?.method && init.method !== 'GET')).toEqual([]);
    expect(fetch.mock.calls.every(([path]) => typeof path === 'string' && path.startsWith('/api/v1/'))).toBe(true);
  });
});

describe('StateBadge truthful status components', () => {
  it.each(['READY', 'AVAILABLE', 'RUNNING', 'WAITING', 'STALE', 'DEGRADED', 'BLOCKED', 'DISCONNECTED', 'UNKNOWN'])(
    'renders %s with code plus Thai meaning, never color-only', state => {
      const { container } = render(<StateBadge state={state} />);
      expect(screen.getByText(state)).toBeInTheDocument();
      const meaning = container.querySelector('.sf-badge-meaning')?.textContent ?? '';
      expect(meaning).toMatch(/[\u0E00-\u0E7F]/);
      expect(meaning.length).toBeGreaterThan(3);
    });

  it('never paints UNKNOWN, STALE, DEGRADED, BLOCKED, or DISCONNECTED as healthy', () => {
    for (const state of ['UNKNOWN', 'STALE', 'DEGRADED', 'BLOCKED', 'DISCONNECTED']) {
      const { container } = render(<StateBadge state={state} />);
      const className = container.querySelector('.sf-badge')?.className ?? '';
      expect(className).not.toMatch(/verified|running/);
    }
  });

  it('fails closed on an unrecognized state code instead of rendering healthy', () => {
    const { container } = render(<StateBadge state="SUPER_READY" />);
    const badge = container.querySelector('.sf-badge');
    expect(badge?.getAttribute('data-state')).toBe('UNKNOWN');
    expect(screen.getByText(/SUPER_READY/)).toBeInTheDocument();
    expect(screen.getByText(/รหัสสถานะไม่รู้จัก/)).toBeInTheDocument();
    expect(badge?.className).not.toMatch(/verified|running/);
  });

  it('fails closed on an empty state string', () => {
    const { container } = render(<StateBadge state="" />);
    expect(container.querySelector('.sf-badge')?.getAttribute('data-state')).toBe('UNKNOWN');
  });

  it('distinguishes READY from AVAILABLE labels even in the same pigment family', () => {
    const { container } = render(<><StateBadge state="READY" /><StateBadge state="AVAILABLE" /></>);
    const meanings = Array.from(container.querySelectorAll('.sf-badge-meaning'), node => node.textContent);
    expect(meanings[0]).not.toBe(meanings[1]);
  });
});

describe('shared truth panels', () => {
  it('EmptyState states missing evidence, never a zero count', () => {
    render(<EmptyState reason="ยังไม่มี device projection" source="fleet read model" />);
    expect(screen.getByText(/^ไม่มีหลักฐาน/)).toBeInTheDocument();
    expect(screen.getByText(/ยังไม่มี device projection/)).toBeInTheDocument();
    expect(screen.getByText(/fleet read model/)).toBeInTheDocument();
    expect(screen.queryByText(/0/)).toBeNull();
  });

  it('ReasonLine shows sanitized reason, source, and unknown observation time honestly', () => {
    render(<ReasonLine reason="FLEET_PROJECTION_NOT_PROVIDED" source="web_api" observedAt={null} />);
    expect(screen.getByText('FLEET_PROJECTION_NOT_PROVIDED')).toBeInTheDocument();
    expect(screen.getByText(/ไม่ทราบเวลา/)).toBeInTheDocument();
  });

  it('TruncatedNote reports retained rows, truncation, and unknown dropped as ไม่ทราบ', () => {
    const { rerender } = render(<TruncatedNote retained={128} dropped={12} truncated />);
    expect(screen.getByText(/128/)).toBeInTheDocument();
    expect(screen.getByText(/12/)).toBeInTheDocument();
    rerender(<TruncatedNote retained={5} dropped={null} truncated />);
    expect(screen.getByText(/ไม่ทราบ/)).toBeInTheDocument();
  });
});

describe('Color E-Ink theme tokens (WO-P1-774 / DESIGN_LOCKED_FOR_CARD_04)', () => {
  it('declares the accepted design-system token set in styles.css', () => {
    const css = readFileSync(resolve('src/styles.css'), 'utf8');
    for (const token of [
      '--sf-bg-canvas', '--sf-bg-surface', '--sf-bg-surface-alt', '--sf-bg-elevated', '--sf-bg-brand-ink',
      '--sf-text-primary', '--sf-text-secondary', '--sf-text-muted',
      '--sf-border-ink', '--sf-border-subtle', '--sf-focus-ring',
      '--sf-status-verified-bg', '--sf-status-running-bg', '--sf-status-waiting-bg',
      '--sf-status-degraded-bg', '--sf-status-blocked-bg', '--sf-status-info-bg',
    ]) expect(css).toContain(token);
    expect(css).toContain('#F4EFE6');
    expect(css).toContain('#234B66');
  });
});
