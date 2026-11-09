// Application tracker: which companies a visitor saved or applied to, kept in this browser only
// (localStorage, no account). Shared by the map app and the company pages; other tabs stay in
// sync through the `storage` event.

export type TrackStatus = 'saved' | 'applied' | 'interviewing' | 'offer' | 'rejected';
export interface TrackEntry {
  status: TrackStatus;
  savedAt?: string;    // ISO date
  appliedAt?: string;  // ISO date
  updatedAt: string;   // ISO timestamp, drives "most recent first"
  note?: string;
}
export type TrackView = '' | 'saved' | 'applied';

export const STATUS_LABEL: Record<TrackStatus, string> = {
  saved: 'Saved', applied: 'Applied', interviewing: 'Interviewing', offer: 'Offer', rejected: 'Not selected',
};
/** Statuses offered once a company is marked applied. */
export const APPLIED_STATUSES: TrackStatus[] = ['applied', 'interviewing', 'offer', 'rejected'];
export const isApplied = (s?: TrackStatus) => !!s && s !== 'saved';

const KEY = 'bitsians-map:tracker:v1';
const today = () => new Date().toISOString().slice(0, 10);

function load(): Record<string, TrackEntry> {
  try {
    const raw = localStorage.getItem(KEY);
    const o = raw ? JSON.parse(raw) : {};
    if (!o || typeof o !== 'object' || Array.isArray(o)) return {};
    const out: Record<string, TrackEntry> = {};
    for (const [id, e] of Object.entries(o as Record<string, any>)) {
      if (e && typeof e === 'object' && e.status in STATUS_LABEL) {
        out[id] = {
          status: e.status, updatedAt: String(e.updatedAt ?? ''),
          ...(e.savedAt && { savedAt: String(e.savedAt) }),
          ...(e.appliedAt && { appliedAt: String(e.appliedAt) }),
          ...(e.note && { note: String(e.note).slice(0, 280) }),
        };
      }
    }
    return out;
  } catch {
    return {};
  }
}

class Tracker {
  entries = $state<Record<string, TrackEntry>>({});
  /** Company whose careers page was just opened: the panel asks whether they applied. */
  pending = $state('');
  /** Role whose posting was just opened, used as the note when they mark the company applied. */
  pendingRole = $state('');
  #ready = false;

  savedCount = $derived(Object.values(this.entries).filter((e) => e.status === 'saved').length);
  appliedCount = $derived(Object.values(this.entries).filter((e) => isApplied(e.status)).length);

  /** Load from storage. Call from onMount (never during SSR); safe to call more than once. */
  init() {
    if (this.#ready || typeof window === 'undefined') return;
    this.#ready = true;
    this.entries = load();
    addEventListener('storage', (e) => { if (e.key === KEY) this.entries = load(); });
  }

  get(id: string): TrackEntry | undefined { return this.entries[id]; }

  matches(id: string, view: TrackView): boolean {
    const e = this.entries[id];
    if (!e) return false;
    return view === 'saved' ? e.status === 'saved' : isApplied(e.status);
  }

  #put(id: string, e: TrackEntry | undefined) {
    const next = { ...this.entries };
    if (e) next[id] = { ...e, updatedAt: new Date().toISOString() };
    else delete next[id];
    this.entries = next;
    try { localStorage.setItem(KEY, JSON.stringify(next)); } catch { /* private mode or full: keep in memory */ }
  }

  toggleSaved(id: string) {
    const e = this.entries[id];
    if (e?.status === 'saved') this.#put(id, undefined);
    else if (!e) this.#put(id, { status: 'saved', savedAt: today(), updatedAt: '' });
  }
  markApplied(id: string) {
    const e = this.entries[id];
    const role = this.pending === id ? this.pendingRole : '';
    this.#put(id, { ...e, status: 'applied', appliedAt: e?.appliedAt ?? today(), updatedAt: '',
      ...(role && !e?.note && { note: role.slice(0, 280) }) });
    if (this.pending === id) { this.pending = ''; this.pendingRole = ''; }
  }
  setStatus(id: string, status: TrackStatus) {
    const e = this.entries[id];
    if (e) this.#put(id, { ...e, status, ...(isApplied(status) && !e.appliedAt && { appliedAt: today() }) });
  }
  setNote(id: string, note: string) {
    const e = this.entries[id];
    if (e) this.#put(id, { ...e, note: note.slice(0, 280) || undefined });
  }
  remove(id: string) { this.#put(id, undefined); }
}

export const tracker = new Tracker();

/** "9 Nov 2026" from an ISO date. */
export const shortDate = (iso?: string) => {
  if (!iso) return '';
  const d = new Date(iso.length === 10 ? iso + 'T00:00:00' : iso);
  return isNaN(+d) ? '' : d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
};
