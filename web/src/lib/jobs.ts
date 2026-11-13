// Full role lists (web/src/data/jobs.json, written by scripts/fetch_jobs.py). Loaded on demand,
// as its own chunk: by the front page once it is on screen, and by the map when a company is opened.
import type { Prepared } from './data';

export interface Job { title: string; team: string; location: string; url: string }
export interface CompanyJobs { ats: string; board: string; jobs: Job[] }
/** One company's roles as the front page lists them: `jobs` are the ones that match the filters. */
export interface RoleGroup { c: Prepared; total: number; jobs: Job[]; matched: number }

let cache: Promise<Record<string, CompanyJobs>> | null = null;
export function loadAllJobs(): Promise<Record<string, CompanyJobs>> {
  cache ??= import('../data/jobs.json').then((m) => (m.default as any).companies as Record<string, CompanyJobs>);
  return cache.catch((e) => { cache = null; throw e; });
}
export const loadJobs = (id: string): Promise<CompanyJobs | undefined> => loadAllJobs().then((all) => all[id]);

// Job boards write locations freely ("Bengaluru-VTP, India", "Remote - India", "Pune").
const INDIA = /\b(india|bengaluru|bangalore|pune|hyderabad|gurgaon|gurugram|mumbai|delhi|noida|chennai|kolkata|ahmedabad|jaipur|kochi)\b/i;
export const inIndia = (location: string) => INDIA.test(location);
export const isRemote = (location: string) => /\bremote\b/i.test(location);
