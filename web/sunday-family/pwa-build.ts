import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import type { Plugin } from 'vite';

export function pwaAssets(): Plugin {
  return {
    name: 'sunday-pwa-assets',
    apply: 'build',
    enforce: 'post',
    generateBundle(_options, bundle) {
      const assets = ['/index.html', '/manifest.webmanifest', '/icons/icon-192.svg', '/icons/icon-512.svg'];
      const hash = createHash('sha256');
      for (const [name, entry] of Object.entries(bundle).sort()) {
        hash.update(name).update(entry.type === 'chunk' ? entry.code : entry.source);
        if (/\.(js|css)$/.test(name)) assets.push(`/${name}`);
      }
      for (const name of ['sw.js', 'manifest.webmanifest', 'icons/icon-192.svg', 'icons/icon-512.svg']) {
        hash.update(readFileSync(new URL(`./public/${name}`, import.meta.url)));
      }
      this.emitFile({
        type: 'asset', fileName: 'precache.js',
        source: `self.SUNDAY_PRECACHE = ${JSON.stringify({ version: hash.digest('hex').slice(0, 16), assets })};\n`,
      });
    },
  };
}
