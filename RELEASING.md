# Releasing and rolling back

The site is static (Astro) and served by a Cloudflare Worker with static assets at
https://bitsians-map.whyujjwalraj.workers.dev. There is no server code and no database: a release
uploads a new set of files, and Cloudflare keeps every earlier upload as a version you can return to.

## Before you release

You need, once per machine:

- **Node 24** (`web/.nvmrc`; Astro needs 22.12 or newer and `pnpm install` refuses older ones) and
  **pnpm 10.14** (`corepack enable` picks the version from `web/package.json`).
- **`web/.env`** copied from `web/.env.example`. `SITE_URL` must be the production URL above; the
  build stops if it is missing or not a valid URL (it used to fall back to a placeholder domain and
  ship wrong canonical links, og:url and sitemap).
- **Cloudflare access** to the account that owns the `bitsians-map` Worker: `pnpm exec wrangler login`
  in `web/`. Today only whyujjwal's account has it, so only he can release or roll back.

## Release

1. Merge the change into `main` through a pull request.
2. On your machine: `git switch main && git pull`.
3. In `web/`: `pnpm install`, then `pnpm run deploy:dry-run`. It runs every check and the build,
   then `wrangler deploy --dry-run`; nothing is uploaded.
4. If that passes: `pnpm run deploy`.

`pnpm run deploy` (`web/scripts/release.mjs`) stops before building or uploading anything unless:

- you are on `main`, with no uncommitted or untracked files, and `HEAD` equals `origin/main`;
- Node is 22.12 or newer and `SITE_URL` is a public https URL (it warns if it is not the production URL);
- the build succeeds, contains the home page, map page, 404 page, sitemap and map worker, has one page per
  company in `web/src/data/companies.json`, and its canonical link and sitemap use `SITE_URL`.

Then it deploys with the commit recorded on the Cloudflare version (`--tag <short sha>`,
`--message release-<time>-<sha> <commit subject>`) and creates and pushes a git tag
`release-<YYYYMMDDHHMM>-<sha>`. Pass `--no-tag` (`pnpm run deploy -- --no-tag`) to skip the tag.

If `wrangler deploy` fails, the previous version stays live; check with
`pnpm exec wrangler deployments status`.

## Verify (right after every release)

Open each of these on the live site and hard refresh:

- [ ] Home page loads with the batch chart and the Roles view listing roles by company.
- [ ] On the home page, a search and a filter (In India, then Companies and Hiring) change the lists and the counts on the views.
- [ ] `/map` loads, shows tiles and city markers, and a filter (Hiring, Location) changes the list and the map.
- [ ] An old link, `/?c=swiggy`, opens Swiggy on the home page.
- [ ] A company page, e.g. `/c/swiggy`, shows founders and "View open roles".
- [ ] `/c/swiggy/` redirects to `/c/swiggy`; `/c/does-not-exist` shows the 404 page.
- [ ] View source on the home page: `<link rel="canonical">` starts with the production URL.
- [ ] `/sitemap-index.xml` loads and its URLs use the production URL.

If any check fails and the cause is not obvious within a few minutes, roll back first and debug after.

## Roll back

Rolling back makes an earlier upload live again without rebuilding. Run these in `web/`, logged in
to the Cloudflare account that owns the Worker.

1. **Find the last good version.**
   `pnpm exec wrangler deployments list`. Each entry shows a version id, when it was deployed and
   the message, which names the release tag and commit for releases made with `pnpm run deploy`.
2. **Roll back to it.**
   `pnpm exec wrangler rollback <version-id> --message "<what broke>"`.
   With no version id, wrangler offers the previous version.
3. **Verify** with the checklist above.
4. **Fix forward on `main`.** Revert or fix the bad commit, so the next release does not bring it back.

**If rollback is unavailable** (for example an old version is missing): check out the last good
release tag (`git tag --list 'release-*'`), make sure `web/.env` is set, and in `web/` run
`pnpm install && pnpm exec astro build --outDir .wrangler/deploy && pnpm exec wrangler deploy`.
This bypasses the main-branch check on purpose; afterwards, fix `main` as in step 4.

> **Not yet rehearsed.** These commands come from wrangler 4.158's help. Try steps 1 and 2 once on
> a harmless release (roll back, then forward again) and note here that it worked, including
> whether static assets rolled back with the version.

## Things that are not covered yet

- No CI: tests, type checks and the build are not run on pull requests.
- No preview deployments (`preview_urls: false`), so pull requests are reviewed locally.
- No error monitoring or uptime checks; problems after a release are only found by the checks above.
- The data pipeline (`scripts/`) is run by hand and its intermediate files are not in git.
