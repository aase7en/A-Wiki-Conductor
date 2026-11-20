// @vitest-environment node
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { describe, expect, it, vi } from 'vitest';

const source = readFileSync(new URL('../public/sw.js', import.meta.url), 'utf8');
const assets = ['/index.html', '/assets/app.js', '/assets/app.css', '/icons/icon-192.svg'];

function worker(list = assets) {
  const handlers: Record<string, (event: unknown) => void> = {};
  const match = vi.fn().mockResolvedValue(new Response('cached shell'));
  const addAll = vi.fn().mockResolvedValue(undefined);
  const cache = { match, addAll };
  const caches = {
    open: vi.fn().mockResolvedValue(cache),
    keys: vi.fn().mockResolvedValue(['sunday-family-shell-old', 'sunday-family-shell-test', 'foreign-cache']),
    delete: vi.fn().mockResolvedValue(true),
  };
  const fetch = vi.fn().mockResolvedValue(new Response('network'));
  const claim = vi.fn().mockResolvedValue(undefined);
  runInNewContext(source, {
    self: { SUNDAY_PRECACHE: { version: 'test', assets: list }, location: { origin: 'https://sunday.test' },
      clients: { claim }, addEventListener: (type: string, fn: (event: unknown) => void) => { handlers[type] = fn; } },
    importScripts: vi.fn(), caches, fetch, Request, Response, URL,
  });
  function lifecycle(type: string) {
    let pending: Promise<unknown> | undefined;
    handlers[type]({ waitUntil: (promise: Promise<unknown>) => { pending = promise; } });
    return pending!;
  }
  function request(path: string, options: { mode?: string; method?: string; authorization?: string } = {}) {
    let response: Promise<Response> | undefined;
    const headers = new Headers();
    if (options.authorization) headers.set('authorization', options.authorization);
    handlers.fetch({ request: { url: new URL(path, 'https://sunday.test').href, method: options.method || 'GET',
      mode: options.mode || 'cors', headers }, respondWith: (value: Promise<Response>) => { response = value; } });
    return response;
  }
  return { caches, match, addAll, fetch, claim, lifecycle, request };
}

describe('service worker', () => {
  it('precaches built JS/CSS and shell without credentials', async () => {
    const w = worker();
    await w.lifecycle('install');
    const requests = w.addAll.mock.calls[0][0] as Request[];
    expect(requests.map(request => new URL(request.url).pathname)).toEqual(assets);
    expect(requests.every(request => request.credentials === 'omit' && request.cache === 'reload')).toBe(true);
    expect(w.caches.open).toHaveBeenCalledWith('sunday-family-shell-test');
  });
  it('fails install before writing if bounded precache exceeds 64 entries', async () => {
    const w = worker(Array.from({ length: 65 }, (_, index) => `/assets/${index}.js`));
    await expect(w.lifecycle('install')).rejects.toThrow('precache limit');
    expect(w.caches.open).not.toHaveBeenCalled();
  });
  it('removes only outdated Sunday shell caches on activation', async () => {
    const w = worker(); await w.lifecycle('activate');
    expect(w.caches.delete).toHaveBeenCalledExactlyOnceWith('sunday-family-shell-old');
    expect(w.claim).toHaveBeenCalledOnce();
  });
  it.each(['/api', '/api/v1/snapshot', '/api/v1/stream?cursor=1'])('never caches API %s, even when offline', async path => {
    const w = worker();
    await w.request(path, { authorization: 'test-token' });
    expect(w.fetch.mock.calls[0][1]).toEqual({ cache: 'no-store' });
    w.fetch.mockRejectedValue(new Error('offline'));
    await expect(w.request(path)).rejects.toThrow('offline');
    expect(w.caches.open).not.toHaveBeenCalled();
  });
  it('serves listed static assets cache-first without network', async () => {
    const w = worker();
    expect(await (await w.request('/assets/app.js'))!.text()).toBe('cached shell');
    expect(w.fetch).not.toHaveBeenCalled();
  });
  it('uses network for a missing static asset without writing runtime cache', async () => {
    const w = worker(); w.match.mockResolvedValue(undefined);
    expect(await (await w.request('/assets/app.js'))!.text()).toBe('network');
    expect(w.addAll).not.toHaveBeenCalled();
  });
  it('uses network-first navigation, falling back only to cached index offline', async () => {
    const w = worker();
    expect(await (await w.request('/lanes', { mode: 'navigate' }))!.text()).toBe('network');
    expect(w.caches.open).not.toHaveBeenCalled();
    w.fetch.mockRejectedValue(new Error('offline'));
    expect(await (await w.request('/lanes', { mode: 'navigate' }))!.text()).toBe('cached shell');
    expect(w.match).toHaveBeenCalledWith('/index.html');
  });
  it('fails closed if offline shell is missing', async () => {
    const w = worker(); w.fetch.mockRejectedValue(new Error('offline')); w.match.mockResolvedValue(undefined);
    expect((await w.request('/', { mode: 'navigate' }))!.type).toBe('error');
  });
  it('ignores foreign, unlisted, query-bearing, non-GET and authorized static requests', () => {
    const w = worker();
    expect(w.request('https://elsewhere.test/assets/app.js')).toBeUndefined();
    expect(w.request('/private.json')).toBeUndefined();
    expect(w.request('/assets/app.js?token=private')).toBeUndefined();
    expect(w.request('/assets/app.js', { method: 'POST' })).toBeUndefined();
    expect(w.request('/assets/app.js', { authorization: 'test' })).toBeUndefined();
    expect(w.caches.open).not.toHaveBeenCalled();
  });
});
