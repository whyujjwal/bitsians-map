import { continentOf, stateOf } from './regions';

export interface Founder { name: string; role: string; campus: string; gradYear: string }
export interface Company {
  id: string; name: string; website: string; careers: string; status: string;
  city: string; country: string; lat: number | null; lng: number | null;
  precision: string | null; founded: string; sector: string; stage: string;
  oneLine: string; campuses: string[]; founders: Founder[];
  logo: string; logoDark: boolean; sources?: string[];
}
export type TileKind = 'hiring' | 'active' | 'inactive';
export interface Prepared extends Company {
  hay: string;            // lowercase search string
  hiring: boolean;
  kind: TileKind;
  large: boolean;         // large map tile (Unicorn, Soonicorn, Minicorn, Public)
  pos: [number, number] | null; // real [lng, lat], or null when unknown
  foundedNum: number;     // 0 when unknown
  nameKey: string;
  continent: string;      // '' when the country is unknown
  state: string;          // state or province, '' when not in the lookup
}

// ---- Stages ----
const STAGE_W: Record<string, number> = {
  Unicorn: 0, Soonicorn: 1, Minicorn: 2, Public: 3, 'Series C+': 4, 'Series A/B': 5, Seed: 6,
};
export const stageWeight = (s: string) => STAGE_W[s] ?? 7;

export const LARGE_STAGES = new Set(['Unicorn', 'Soonicorn', 'Minicorn', 'Public']);
export const isLargeStage = (s: string) => LARGE_STAGES.has(s);
/** Stages whose label is highlighted in the list. */
export const isUnicornish = (s: string) => s === 'Unicorn' || s === 'Soonicorn' || s === 'Minicorn';

const STAGE_ORDER = ['Unicorn', 'Soonicorn', 'Minicorn', 'Public', 'Series C+', 'Series A/B', 'Seed', 'Acquired', 'none', 'Closed'];
export const stageLabel = (s: string) => (s === 'none' ? 'Not stated' : s);
/** Stage option order, "Closed" last. */
export function sortStages(entries: [string, number][]): [string, number][] {
  const rank = (s: string) => { const i = STAGE_ORDER.indexOf(s); return i < 0 ? STAGE_ORDER.length - 2 : i; };
  return [...entries].sort((a, b) => rank(a[0]) - rank(b[0]));
}
/** Sector option order: by count desc, "Other" last. */
export function sortSectors(entries: [string, number][]): [string, number][] {
  return [...entries].sort((a, b) => (a[0] === 'Other' ? 1 : 0) - (b[0] === 'Other' ? 1 : 0) || b[1] - a[1] || a[0].localeCompare(b[0]));
}

export const isInactive = (status: string) => status.startsWith('acquired') || status === 'closed';
export const tileKind = (c: Pick<Company, 'careers' | 'status'>): TileKind =>
  c.careers ? 'hiring' : isInactive(c.status) ? 'inactive' : 'active';

// ---- Sorting ----
export type Sort = 'notable' | 'newest' | 'az';
export const SORTS: [Sort, string][] = [['notable', 'Notable'], ['newest', 'Newest'], ['az', 'A–Z']];
/** `list` must be in Notable order (the order produced by prepare/applyFilters). */
export function sortItems(list: Prepared[], sort: Sort): Prepared[] {
  if (sort === 'notable') return list;
  const r = list.slice();
  if (sort === 'newest') {
    // Array.prototype.sort is stable, so ties keep Notable order.
    r.sort((a, b) => (a.foundedNum === 0 ? 1 : 0) - (b.foundedNum === 0 ? 1 : 0) || b.foundedNum - a.foundedNum);
  } else {
    r.sort((a, b) => (a.nameKey < b.nameKey ? -1 : a.nameKey > b.nameKey ? 1 : 0));
  }
  return r;
}

/** Sorted by stage weight then name; filtering preserves this order. */
export function prepare(list: Company[]): Prepared[] {
  return list
    .map((c): Prepared => ({
      ...c,
      hiring: !!c.careers,
      kind: tileKind(c),
      large: isLargeStage(c.stage),
      pos: c.lat == null || c.lng == null ? null : [c.lng, c.lat],
      foundedNum: parseInt(c.founded, 10) || 0,
      nameKey: c.name.toLowerCase(),
      continent: continentOf(c.country),
      state: stateOf(c.country, c.city),
      hay: [c.name, c.founders.map((f) => f.name).join(' '), c.sector, c.city, stateOf(c.country, c.city), c.country, c.campuses.join(' '), c.oneLine].join(' ').toLowerCase(),
    }))
    .sort((a, b) => stageWeight(a.stage) - stageWeight(b.stage) || a.name.localeCompare(b.name));
}

export interface Filters {
  q: string; sectors: string[]; stages: string[]; campuses: string[]; cities: string[]; hiring: boolean;
  continents: string[]; countries: string[]; states: string[];
  unmapped: boolean;
  /** Application tracker view; applied in App (the tracker lives in localStorage). */
  track: '' | 'saved' | 'applied';
}
export const emptyFilters = (): Filters => ({
  q: '', sectors: [], stages: [], campuses: [], cities: [], hiring: false, unmapped: false, track: '',
  continents: [], countries: [], states: [],
});

export function applyFilters(all: Prepared[], f: Filters): Prepared[] {
  const terms = f.q.toLowerCase().split(/\s+/).filter(Boolean);
  const { sectors, stages, campuses, cities, hiring, unmapped, continents, countries, states } = f;
  const out: Prepared[] = [];
  outer: for (let i = 0; i < all.length; i++) {
    const c = all[i];
    if (hiring && !c.hiring) continue;
    if (unmapped && c.pos) continue;
    if (sectors.length && !sectors.includes(c.sector)) continue;
    if (stages.length && !stages.includes(c.stage || 'none')) continue;
    if (cities.length && !cities.includes(c.city)) continue;
    if (continents.length && !continents.includes(c.continent || 'Unknown')) continue;
    if (countries.length && !countries.includes(c.country || 'Unknown')) continue;
    if (states.length && !states.includes(c.state)) continue;
    if (campuses.length) {
      let ok = false;
      for (const k of campuses) if (c.campuses.includes(k)) { ok = true; break; }
      if (!ok) continue;
    }
    for (let t = 0; t < terms.length; t++) if (!c.hay.includes(terms[t])) continue outer;
    out.push(c);
  }
  return out;
}

export const initials = (n: string) => {
  const w = n.replace(/[^\p{L}\p{N} ]/gu, '').split(/\s+/).filter(Boolean);
  return ((w[0]?.[0] ?? '?') + (w.length > 1 ? w[1][0] : '')).toUpperCase();
};

/** "Pilani 2008", "Pilani", "2008" or "". */
export const campusYear = (f: Founder) => [f.campus, f.gradYear].filter(Boolean).join(' ');

/** The batch tag shown wherever a founder appears: "Pilani '08", "Class of '10", "Goa" or "". */
export function batchTag(f: Pick<Founder, 'campus' | 'gradYear'>): { text: string; title: string } {
  const y = /^\d{4}$/.test(f.gradYear) ? f.gradYear : '';
  const yy = y ? '\u2019' + y.slice(2) : '';
  if (f.campus && y) return { text: `${f.campus} ${yy}`, title: `BITS ${f.campus}, batch of ${y}` };
  if (y) return { text: `Class of ${yy}`, title: `BITS batch of ${y}, campus not known` };
  if (f.campus) return { text: f.campus, title: `BITS ${f.campus} campus, batch not known` };
  return { text: '', title: '' };
}

/** Domain shown for a source link: "bits-pilani.ac.in". */
export const sourceHost = (u: string) => {
  try { return new URL(u).hostname.replace(/^www\./, ''); } catch { return u; }
};

const REPO = 'https://github.com/whyujjwal/bitsians-map';
/** A prefilled GitHub issue for correcting one company, or adding a new one. */
export function fixUrl(c?: Pick<Company, 'id' | 'name'>): string {
  const p = new URLSearchParams(c
    ? { title: `Fix: ${c.name}`, body: `Company: ${c.name} (${c.id})\n\nWhat is wrong:\n\nWhat it should say:\n\nSource (link):\n`, labels: 'correction' }
    : { title: 'Add a company', body: 'Company:\nWebsite:\nFounder(s) and BITS campus/batch:\n\nSource (link):\n', labels: 'new company' });
  return `${REPO}/issues/new?${p}`;
}

// ---- URL state ----
export type View = 'list' | 'map';
export interface UrlState { f: Filters; view: View; selected: string; sort: Sort }
export function readUrl(search: string): UrlState {
  const p = new URLSearchParams(search);
  const arr = (k: string) => (p.get(k) ?? '').split(',').filter(Boolean);
  const s = p.get('sort');
  return {
    f: {
      q: p.get('q') ?? '', sectors: arr('sector'), stages: arr('stage'), campuses: arr('campus'),
      cities: arr('city'), continents: arr('continent'), countries: arr('country'), states: arr('state'), hiring: p.get('hiring') === '1', unmapped: p.get('unmapped') === '1',
      track: p.get('track') === 'saved' || p.get('track') === 'applied' ? (p.get('track') as 'saved' | 'applied') : '',
    },
    selected: p.get('c') ?? p.get('focus') ?? '',
    view: p.get('view') === 'list' ? 'list' : 'map',
    sort: s === 'newest' || s === 'az' ? s : 'notable',
  };
}
export function writeUrl(f: Filters, view: View, selected: string, sort: Sort): string {
  const p = new URLSearchParams();
  if (selected) p.set('c', selected);
  if (f.q) p.set('q', f.q);
  if (f.sectors.length) p.set('sector', f.sectors.join(','));
  if (f.stages.length) p.set('stage', f.stages.join(','));
  if (f.campuses.length) p.set('campus', f.campuses.join(','));
  if (f.cities.length) p.set('city', f.cities.join(','));
  if (f.continents.length) p.set('continent', f.continents.join(','));
  if (f.countries.length) p.set('country', f.countries.join(','));
  if (f.states.length) p.set('state', f.states.join(','));
  if (f.hiring) p.set('hiring', '1');
  if (f.unmapped) p.set('unmapped', '1');
  if (f.track) p.set('track', f.track);
  if (sort !== 'notable') p.set('sort', sort);
  if (view === 'list') p.set('view', 'list');
  const s = p.toString();
  return location.pathname + (s ? '?' + s : '');
}

/** @deprecated kept so older map code keeps compiling; the redesign uses tile kinds. */
export const sectorColor = (_s: string) => '#0a6c74';
