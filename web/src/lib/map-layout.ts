import { initials, stageWeight, type Prepared } from './data';

/** 0 = hiring, 1 = active, 2 = inactive (acquired / closed). */
export type Kind = 0 | 1 | 2;

export interface Tile {
  id: string;
  groupKey: string;
  lng: number; lat: number;      // display position (sunflower or real address)
  rlng: number; rlat: number;    // real position as given in the data
  /** Position in its city's spiral (0 = centre); drives the bloom stagger. */
  idx: number;
  feature: GeoJSON.Feature<GeoJSON.Point>;
}
export interface Layout {
  tiles: Map<string, Tile>;
  /** Sunflower centre per city group (stable: computed from all companies). */
  centers: Map<string, [number, number]>;
}
export interface Bubble {
  key: string; city: string; lng: number; lat: number; count: number; hiring: number; r: number;
}

const GOLDEN = (137.508 * Math.PI) / 180;
const SPIRAL_KM = 1.9;
const BIG = new Set(['Unicorn', 'Soonicorn', 'Minicorn', 'Public']);

export const isInactive = (c: Prepared) => c.status.startsWith('acquired') || c.status === 'closed';
const kindOf = (c: Prepared): Kind => (c.hiring ? 0 : isInactive(c) ? 2 : 1);
const groupKeyOf = (c: Prepared) => (c.city ? `${c.city}|${c.country}` : `#${c.id}`);

export function buildLayout(all: Prepared[]): Layout {
  const groups = new Map<string, Prepared[]>();
  for (const c of all) {
    if (!c.pos) continue;
    const k = groupKeyOf(c);
    const g = groups.get(k);
    if (g) g.push(c); else groups.set(k, [c]);
  }
  const tiles = new Map<string, Tile>();
  const centers = new Map<string, [number, number]>();
  for (const [key, members] of groups) {
    // Centre: mean of city-level points (address points would skew it), else of all points.
    const cityLevel = members.filter((c) => c.precision !== 'address');
    const basis = cityLevel.length ? cityLevel : members;
    let sx = 0, sy = 0;
    for (const c of basis) { sx += c.pos![0]; sy += c.pos![1]; }
    const clng = sx / basis.length, clat = sy / basis.length;
    centers.set(key, [clng, clat]);
    const cosLat = Math.max(0.2, Math.cos((clat * Math.PI) / 180));
    const order = cityLevel.slice().sort((a, b) => stageWeight(a.stage) - stageWeight(b.stage) || a.name.localeCompare(b.name));
    const spiral = new Map<string, [number, number]>();
    const idxOf = new Map<string, number>();
    order.forEach((c, i) => {
      idxOf.set(c.id, i);
      const a = i * GOLDEN, r = SPIRAL_KM * Math.sqrt(i + 0.5);
      spiral.set(c.id, [clng + (r * Math.cos(a)) / (111.32 * cosLat), clat + (r * Math.sin(a)) / 110.574]);
    });
    for (const c of members) {
      const [lng, lat] = c.precision === 'address' ? c.pos! : spiral.get(c.id) ?? c.pos!;
      const big = BIG.has(c.stage);
      const kind = kindOf(c);
      const logo = !!c.logo;
      const size = logo ? (big ? 34 : 28) : big ? 28 : 22;
      tiles.set(c.id, {
        id: c.id, groupKey: key, lng, lat, rlng: c.pos![0], rlat: c.pos![1], idx: idxOf.get(c.id) ?? 0,
        feature: {
          type: 'Feature',
          geometry: { type: 'Point', coordinates: [lng, lat] },
          properties: {
            id: c.id, ini: logo ? '' : initials(c.name), img: logo ? `logo~${c.id}` : '', k: kind, ts: big ? 15 : 12,
            isz: size / 32, rsz: (size + 8) / 36,
            sk: (kind === 0 ? 100 : 0) + 10 - stageWeight(c.stage),
          },
        },
      });
    }
  }
  return { tiles, centers };
}

export function collection(layout: Layout, items: Prepared[]): GeoJSON.FeatureCollection<GeoJSON.Point> {
  const features: GeoJSON.Feature<GeoJSON.Point>[] = [];
  for (const c of items) { const t = layout.tiles.get(c.id); if (t) features.push(t.feature); }
  return { type: 'FeatureCollection', features };
}

export function bubbles(layout: Layout, items: Prepared[]): Bubble[] {
  const acc = new Map<string, { city: string; sx: number; sy: number; n: number; h: number }>();
  for (const c of items) {
    const t = layout.tiles.get(c.id);
    if (!t) continue;
    let g = acc.get(t.groupKey);
    if (!g) acc.set(t.groupKey, (g = { city: c.city || c.name, sx: 0, sy: 0, n: 0, h: 0 }));
    g.sx += t.rlng; g.sy += t.rlat; g.n++;
    if (c.hiring) g.h++;
  }
  const out: Bubble[] = [];
  for (const [key, g] of acc) out.push({ key, city: g.city, lng: g.sx / g.n, lat: g.sy / g.n, count: g.n, hiring: g.h, r: 3 + 2.2 * Math.sqrt(g.n) });
  return out.sort((a, b) => b.count - a.count);
}

export function cityCollection(list: Bubble[]): GeoJSON.FeatureCollection<GeoJSON.Point> {
  return {
    type: 'FeatureCollection',
    features: list.map((b, rank) => ({
      type: 'Feature', geometry: { type: 'Point', coordinates: [b.lng, b.lat] },
      properties: { key: b.key, r: b.r, h: b.hiring ? 1 : 0, rank },
    })),
  };
}

// ---- campuses and arcs ----
export type CampusName = 'Pilani' | 'Goa' | 'Hyderabad' | 'Dubai';
export const CAMPUSES: { name: CampusName; pos: [number, number] }[] = [
  { name: 'Pilani', pos: [75.587, 28.3639] },
  { name: 'Goa', pos: [73.8782, 15.3911] },
  { name: 'Hyderabad', pos: [78.5718, 17.5449] },
  { name: 'Dubai', pos: [55.4196, 25.131] },
];
const CAMPUS_POS = new Map(CAMPUSES.map((c) => [c.name as string, c.pos]));

const rad = Math.PI / 180;
const arcCache = new Map<string, [number, number][]>();
/** Great circle, 48 points, longitudes unwrapped so the line never jumps across the antimeridian. */
function greatCircle(a: [number, number], b: [number, number]): [number, number][] {
  const k = `${a}|${b}`;
  const hit = arcCache.get(k);
  if (hit) return hit;
  const [l1, p1] = [a[0] * rad, a[1] * rad], [l2, p2] = [b[0] * rad, b[1] * rad];
  const d = 2 * Math.asin(Math.sqrt(Math.sin((p2 - p1) / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin((l2 - l1) / 2) ** 2));
  const out: [number, number][] = [];
  let prev = a[0];
  for (let i = 0; i <= 47; i++) {
    const f = i / 47;
    let lng: number, lat: number;
    if (d < 1e-6) { lng = a[0]; lat = a[1]; } else {
      const A = Math.sin((1 - f) * d) / Math.sin(d), B = Math.sin(f * d) / Math.sin(d);
      const x = A * Math.cos(p1) * Math.cos(l1) + B * Math.cos(p2) * Math.cos(l2);
      const y = A * Math.cos(p1) * Math.sin(l1) + B * Math.cos(p2) * Math.sin(l2);
      const z = A * Math.sin(p1) + B * Math.sin(p2);
      lat = Math.atan2(z, Math.hypot(x, y)) / rad; lng = Math.atan2(y, x) / rad;
    }
    while (lng - prev > 180) lng -= 360;
    while (lng - prev < -180) lng += 360;
    prev = lng;
    out.push([lng, lat]);
  }
  arcCache.set(k, out);
  return out;
}

/** One arc per campus-city pair, weight = number of companies. */
export function arcCollection(layout: Layout, items: Prepared[], cityBubbles: Bubble[]): GeoJSON.FeatureCollection<GeoJSON.LineString> {
  const at = new Map(cityBubbles.map((b) => [b.key, b]));
  const pairs = new Map<string, { campus: string; key: string; w: number }>();
  for (const c of items) {
    const t = layout.tiles.get(c.id);
    if (!t) continue;
    for (const campus of c.campuses) {
      if (!CAMPUS_POS.has(campus)) continue;
      const k = `${campus}>${t.groupKey}`;
      const p = pairs.get(k);
      if (p) p.w++; else pairs.set(k, { campus, key: t.groupKey, w: 1 });
    }
  }
  const features: GeoJSON.Feature<GeoJSON.LineString>[] = [];
  for (const p of pairs.values()) {
    const b = at.get(p.key), from = CAMPUS_POS.get(p.campus)!;
    if (!b) continue;
    if (Math.hypot(b.lng - from[0], b.lat - from[1]) < 0.4) continue; // the campus city itself
    features.push({
      type: 'Feature', geometry: { type: 'LineString', coordinates: greatCircle(from, [b.lng, b.lat]) },
      properties: { w: 0.8 + 0.6 * Math.log2(p.w) },
    });
  }
  return { type: 'FeatureCollection', features };
}
