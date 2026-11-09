import { defineConfig } from 'astro/config';
import svelte from '@astrojs/svelte';
import sitemap from '@astrojs/sitemap';
import { cpSync, existsSync, mkdirSync } from 'node:fs';

// maplibre-gl v6 loads its worker (and shared chunk) as separate files by URL.
// Serve them from /maplibre/ (generated into public/, git-ignored).
mkdirSync('public/maplibre', { recursive: true });
for (const f of ['maplibre-gl-worker.mjs']) {
  cpSync(`node_modules/maplibre-gl/dist/${f}`, `public/maplibre/${f}`);
}

// Public URL used for canonical links, og:url and the sitemap.
// Set SITE_URL in the environment or in web/.env (astro.config doesn't read .env
// on its own, and pnpm doesn't expose vite's loadEnv here, so use Node's loader).
if (!process.env.SITE_URL && existsSync('.env')) process.loadEnvFile('.env');
// A build without SITE_URL used to fall back to a placeholder domain and quietly ship wrong
// canonical links, og:url and sitemap entries, so builds now stop instead. `astro dev` keeps
// working without it. For a local test build: SITE_URL=http://localhost:4321 pnpm build
const building = process.argv.slice(2).includes('build');
const site = process.env.SITE_URL || (building ? '' : 'http://localhost:4321');
if (building) {
  let ok = false;
  try { ok = /^https?:$/.test(new URL(site).protocol); } catch { /* not a URL */ }
  if (!ok) {
    throw new Error(
      `SITE_URL is ${site ? `not a valid http(s) URL: "${site}"` : 'not set'}. ` +
      'Copy web/.env.example to web/.env (production: https://bitsians-map.whyujjwalraj.workers.dev), ' +
      'or set it in the environment. See RELEASING.md.',
    );
  }
}

export default defineConfig({
  output: 'static',
  site,
  // URLs have no trailing slash (/c/zeta). Pages still build as c/zeta/index.html
  // ("directory" format keeps Astro.url, and so the canonical tags, slash-free);
  // Cloudflare serves them at /c/zeta via html_handling "drop-trailing-slash".
  trailingSlash: 'never',
  integrations: [svelte(), sitemap({ filter: (u) => !/\/404\/?$/.test(u) })],
  build: { inlineStylesheets: 'always', format: 'directory' },
  // The map is a dynamic import, so the dev server only discovers maplibre-gl when a page
  // first asks for it and then re-bundles mid-session (504 "Outdated Optimize Dep").
  // Pre-bundle it at startup instead.
  vite: { optimizeDeps: { include: ['maplibre-gl'] } },
});
