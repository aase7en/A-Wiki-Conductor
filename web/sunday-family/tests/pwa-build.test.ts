// @vitest-environment node
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { build } from 'vite';
import type { RollupOutput } from 'rollup';

describe('production PWA build', () => {
  it('emits a versioned exact JS/CSS precache list and linked installable shell', async () => {
    const result = await build({ logLevel: 'silent', build: { write: false } }) as RollupOutput;
    const precache = result.output.find(entry => entry.fileName === 'precache.js');
    if (!precache || precache.type !== 'asset') throw new Error('Missing precache asset');
    const config = JSON.parse(String(precache.source).replace(/^self\.SUNDAY_PRECACHE = /, '').trim().replace(/;$/, ''));
    expect(config.version).toMatch(/^[0-9a-f]{16}$/);
    const built = result.output.filter(entry => /\.(js|css)$/.test(entry.fileName) && entry.fileName !== 'precache.js');
    expect(built.some(entry => entry.fileName.endsWith('.js'))).toBe(true);
    expect(built.some(entry => entry.fileName.endsWith('.css'))).toBe(true);
    for (const entry of built) expect(config.assets).toContain(`/${entry.fileName}`);
    expect(config.assets.length).toBeLessThanOrEqual(64);
    for (const path of config.assets.filter((path: string) => !path.startsWith('/assets/') && path !== '/index.html')) {
      expect(readFileSync(resolve(`public${path}`)).length).toBeGreaterThan(0);
    }
    const html = result.output.find(entry => entry.fileName === 'index.html');
    expect(html?.type === 'asset' && String(html.source)).toContain('rel="manifest"');
    expect(readFileSync(resolve('public/sw.js'), 'utf8')).toContain("importScripts('./precache.js')");
  }, 20000);
});
