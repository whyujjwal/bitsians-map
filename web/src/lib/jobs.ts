// Full role lists (web/src/data/jobs.json, written by scripts/fetch_jobs.py). Loaded on demand,
// as its own chunk, the first time a company with roles is opened in the map app.
export interface Job { title: string; team: string; location: string; url: string }
export interface CompanyJobs { ats: string; board: string; jobs: Job[] }

let cache: Promise<Record<string, CompanyJobs>> | null = null;
export function loadJobs(id: string): Promise<CompanyJobs | undefined> {
  cache ??= import('../data/jobs.json').then((m) => (m.default as any).companies as Record<string, CompanyJobs>);
  return cache.then((all) => all[id]).catch((e) => { cache = null; throw e; });
}
