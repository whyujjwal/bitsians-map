#!/usr/bin/env node
// Guarded production release: `pnpm run deploy` (or `pnpm run deploy:dry-run`).
//
// Refuses to deploy unless the checkout is exactly what is on origin/main, the toolchain and
// SITE_URL are right, and the built site passes basic checks. Then it deploys with the commit
// recorded on the Cloudflare version and tags the release in git, so every live version maps to
// a commit you can roll back to. See RELEASING.md.
//
//   --dry-run   run every check and the build, then `wrangler deploy --dry-run`; git problems
//               are reported as warnings; nothing is uploaded or tagged
//   --no-tag    deploy without creating and pushing the git tag
import { spawnSync } from 'node:child_process';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

const args = new Set(process.argv.slice(2));
const DRY = args.has('--dry-run');
const TAG = !args.has('--no-tag') && !DRY;
const OUT = '.wrangler/deploy';
const PROD_URL = 'https://bitsians-map.whyujjwalraj.workers.dev';

const problems = [];
const warnings = [];
const step = (msg) => console.log(`\n▸ ${msg}`);
const fail = (msg) => problems.push(msg);
const gitFail = (msg) => (DRY ? warnings : problems).push(msg);
function run(cmd, argv, opts = {}) {
  const r = spawnSync(cmd, argv, { encoding: 'utf8', ...opts });
  if (r.error) throw r.error;
  return r;
}
const git = (...a) => run('git', a).stdout.trim();
function stopIfProblems() {
  for (const w of warnings.splice(0)) console.warn(`  ! warning: ${w}`);
  if (!problems.length) return;
  console.error('\nRelease stopped:');
  for (const p of problems) console.error(`  ✗ ${p}`);
  console.error('\nNothing was deployed. See RELEASING.md.');
  process.exit(1);
}

// 1. Toolchain -------------------------------------------------------------------------------
step('Toolchain');
const [maj, min] = process.versions.node.split('.').map(Number);
if (maj < 22 || (maj === 22 && min < 12)) fail(`Node ${process.versions.node} is too old; use Node 24 (see web/.nvmrc).`);
else console.log(`  Node ${process.versions.node}`);

// 2. Git state ----------------------------------------------------------------------------------
step('Git state');
const branch = git('rev-parse', '--abbrev-ref', 'HEAD');
if (branch !== 'main') gitFail(`on branch "${branch}"; releases go out from main only.`);
const dirty = run('git', ['status', '--porcelain', '--untracked-files=normal']).stdout.replace(/\s+$/, '');
if (dirty) gitFail(`uncommitted or untracked changes would be deployed:\n${dirty.split('\n').map((l) => `      ${l}`).join('\n')}`);
const fetch = run('git', ['fetch', '--quiet', 'origin', 'main']);
if (fetch.status !== 0) gitFail(`could not fetch origin/main: ${fetch.stderr.trim()}`);
const head = git('rev-parse', 'HEAD');
const remote = git('rev-parse', 'origin/main');
if (head !== remote) gitFail(`HEAD (${head.slice(0, 7)}) is not origin/main (${remote.slice(0, 7)}); pull or push first.`);
const short = head.slice(0, 7);
console.log(`  ${branch} @ ${short}${head === remote ? ' = origin/main' : ''}`);

// 3. SITE_URL -------------------------------------------------------------------------------
step('SITE_URL');
if (!process.env.SITE_URL && existsSync('.env')) process.loadEnvFile('.env');
const site = (process.env.SITE_URL || '').replace(/\/$/, '');
if (!site) fail('SITE_URL is not set (copy web/.env.example to web/.env).');
else if (!site.startsWith('https://') || /localhost|127\.0\.0\.1/.test(site)) fail(`SITE_URL "${site}" is not a public https URL.`);
else {
  console.log(`  ${site}`);
  if (site !== PROD_URL) warnings.push(`SITE_URL differs from the known production URL ${PROD_URL}.`);
}

// Open roles are baked into the build, and the site stops showing them 14 days after the fetch.
step('Open roles');
const jobsFile = 'src/data/jobs-summary.json';
if (existsSync(jobsFile)) {
  const fetchedAt = JSON.parse(readFileSync(jobsFile, 'utf8')).fetchedAt;
  const days = Math.floor((Date.now() - Date.parse(fetchedAt)) / 864e5);
  if (days < 7) console.log(`  fetched ${fetchedAt} (${days} days ago)`);
  else warnings.push(`open roles were fetched ${Number.isNaN(days) ? 'at an unknown time' : `${days} days ago`} and disappear from the site 14 days after the fetch. Refresh first: python3 -I scripts/fetch_jobs.py from the repo root, then commit.`);
}
stopIfProblems();

// 4. Build -----------------------------------------------------------------------------------
step(`Build into ${OUT}`);
const build = run('pnpm', ['exec', 'astro', 'build', '--outDir', OUT], { stdio: 'inherit', env: { ...process.env, SITE_URL: site } });
if (build.status !== 0) { fail('astro build failed.'); stopIfProblems(); }

// 5. Check the build ---------------------------------------------------------------------------
step('Check the built site');
const need = ['index.html', '404.html', 'sitemap-index.xml', 'maplibre/maplibre-gl-worker.mjs', '_headers'];
for (const f of need) if (!existsSync(join(OUT, f))) fail(`missing ${f} in the build.`);
const companies = JSON.parse(readFileSync('src/data/companies.json', 'utf8'));
const pages = existsSync(join(OUT, 'c')) ? readdirSync(join(OUT, 'c')).filter((d) => existsSync(join(OUT, 'c', d, 'index.html'))).length : 0;
if (pages !== companies.length) fail(`built ${pages} company pages but the data has ${companies.length} companies.`);
if (existsSync(join(OUT, 'index.html'))) {
  const html = readFileSync(join(OUT, 'index.html'), 'utf8');
  const canon = html.match(/<link rel="canonical" href="([^"]+)"/)?.[1] ?? '';
  if (!canon.startsWith(site)) fail(`home page canonical is "${canon}", expected it to start with ${site}.`);
}
if (existsSync(join(OUT, 'sitemap-0.xml'))) {
  const sm = readFileSync(join(OUT, 'sitemap-0.xml'), 'utf8');
  const other = [...sm.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]).filter((u) => !u.startsWith(site));
  if (other.length) fail(`sitemap has ${other.length} URLs outside ${site}, e.g. ${other[0]}.`);
}
stopIfProblems();
console.log(`  ${pages} company pages, canonical and sitemap on ${site}`);

// 6. Deploy ------------------------------------------------------------------------------------
const stamp = new Date().toISOString().slice(0, 16).replace(/[-:T]/g, '');
const tag = `release-${stamp}-${short}`;
step(DRY ? 'Wrangler dry run (nothing is uploaded)' : `Deploy ${short} to Cloudflare`);
const deploy = run('pnpm', ['exec', 'wrangler', 'deploy', ...(DRY ? ['--dry-run'] : []),
  '--tag', short, '--message', `${tag} ${git('log', '-1', '--format=%s')}`.slice(0, 100)], { stdio: 'inherit' });
if (deploy.status !== 0) {
  fail('wrangler deploy failed. The previously deployed version should still be live; check with `pnpm exec wrangler deployments status`.');
  stopIfProblems();
}

// 7. Tag ---------------------------------------------------------------------------------------
if (TAG) {
  step(`Tag ${tag}`);
  const t = run('git', ['tag', '-a', tag, '-m', `Released ${short} to ${site}`]);
  const p = t.status === 0 ? run('git', ['push', 'origin', tag]) : t;
  if (p.status !== 0) console.warn(`  ! could not create or push the tag (${p.stderr.trim()}). The deploy itself succeeded; tag ${short} by hand.`);
  else console.log(`  pushed ${tag}`);
}

console.log(DRY
  ? '\nDry run passed. Nothing was uploaded or tagged.'
  : `\nReleased ${short}. Now run the checks under "Verify" in RELEASING.md; if anything is wrong, follow "Roll back".`);
