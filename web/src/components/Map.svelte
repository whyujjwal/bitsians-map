<script lang="ts">
  import * as maplibregl from 'maplibre-gl';
  import 'maplibre-gl/dist/maplibre-gl.css';
  import { onMount, untrack } from 'svelte';
  import { initials, type Prepared } from '../lib/data';
  import {
    bubbles, buildLayout, cityCollection, collection, CAMPUSES,
    type Bubble, type CampusName,
  } from '../lib/map-layout';

  type Inset = { top: number; right: number; bottom: number; left: number };
  let { items, all, selectedId = '', hoveredId = '', onselect, oncampus, oninteract, inset = { top: 0, right: 0, bottom: 0, left: 0 }, fitKey = '' }: {
    items: Prepared[]; all: Prepared[]; selectedId?: string; hoveredId?: string;
    /** Changes when the place filters change: the camera then fits the results. */
    fitKey?: string;
    /** Space covered by floating panels; the camera centres and fits inside the rest. */
    inset?: Inset;
    onselect: (id: string) => void;
    oncampus?: (name: CampusName) => void;
    oninteract?: () => void;
  } = $props();

  maplibregl.setWorkerUrl('/maplibre/maplibre-gl-worker.mjs');

  const DEEP = 9;      // logo / monogram tiles from this zoom, city lights below
  const INDIA: maplibregl.LngLatBoundsLike = [[68, 6.5], [97.5, 35.5]];
  const PEACOCK = '#0A6C74', HIRE = '#23863F';

  // Base maps are Esri's keyless raster tile services (street map and imagery, one host); label
  // glyphs for our own layers are served from /map/fonts, so nothing else has to load.
  const ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services';
  const STREET = [`${ESRI}/World_Street_Map/MapServer/tile/{z}/{y}/{x}`];
  const STYLE: maplibregl.StyleSpecification = {
    version: 8,
    glyphs: '/map/fonts/{fontstack}/{range}.pbf',
    sources: {
      base: {
        type: 'raster', tiles: STREET, tileSize: 256, maxzoom: 19,
        attribution: 'Tiles &copy; Esri &mdash; Esri, HERE, Garmin, USGS, &copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors, and the GIS User Community',
      },
      sat: { type: 'raster', tiles: [`${ESRI}/World_Imagery/MapServer/tile/{z}/{y}/{x}`], tileSize: 256, maxzoom: 19, attribution: 'Imagery &copy; Esri, Maxar, Earthstar Geographics' },
      satlabels: { type: 'raster', tiles: [`${ESRI}/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}`], tileSize: 256, maxzoom: 19 },
    },
    layers: [
      { id: 'bg', type: 'background', paint: { 'background-color': '#F2EFE9' } },
      { id: 'base', type: 'raster', source: 'base' },
      { id: 'sat', type: 'raster', source: 'sat', layout: { visibility: 'none' } },
      { id: 'satlabels', type: 'raster', source: 'satlabels', layout: { visibility: 'none' } },
    ],
  };
  type Basemap = 'map' | 'satellite';
  const BM_KEY = 'bitsians-map:basemap';
  const readBasemap = (): Basemap => { try { return localStorage.getItem(BM_KEY) === 'satellite' ? 'satellite' : 'map'; } catch { return 'map'; } };
  let basemap = $state<Basemap>('map');
  let tilesFailing = $state(false);

  // `all` never changes: read it once, explicitly.
  const layout = untrack(() => buildLayout(all));
  const byId = untrack(() => new Map(all.map((c) => [c.id, c])));

  let host: HTMLDivElement;
  let map: maplibregl.Map | undefined;
  let ready = $state(false);
  let deep = $state(false);
  let lit = $state(false);
  let region = $state<'India' | 'World' | ''>('');

  interface Mk { marker: maplibregl.Marker; el: HTMLElement; lab: HTMLElement; r: number; w: number; h: number; lng: number; lat: number }
  let markers: Mk[] = [];
  type CampusMk = { marker: maplibregl.Marker; el: HTMLElement; lab: HTMLElement; pos: [number, number] };
  let campusMarkers: CampusMk[] = [];
  let relayoutTimer = 0;
  let curBubbles: Bubble[] = [];
  let lastFlown = '';
  let firstData = true;
  let lastFitKey = untrack(() => fitKey);
  let appliedSel = '';
  let appliedHov = '';
  let interacted = false;

  const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
  const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
  const easeOut = (x: number) => 1 - (1 - x) ** 3;

  function tileBounds(list: Prepared[]): maplibregl.LngLatBounds | null {
    let b: maplibregl.LngLatBounds | null = null;
    for (const c of list) {
      const t = layout.tiles.get(c.id);
      if (t) b = b ? b.extend([t.lng, t.lat]) : new maplibregl.LngLatBounds([t.lng, t.lat], [t.lng, t.lat]);
    }
    return b;
  }

  // ---- SDF icons -----------------------------------------------------------
  function sdRect(x: number, y: number, hw: number, hh: number, r: number) {
    const qx = Math.abs(x) - (hw - r), qy = Math.abs(y) - (hh - r);
    return Math.hypot(Math.max(qx, 0), Math.max(qy, 0)) + Math.min(Math.max(qx, qy), 0) - r;
  }
  /** SDF image (alpha channel carries the distance field; edge at 0.75). */
  function sdfImage(content: number, radius: number, stroke: number) {
    const PAD = 8, size = content + PAD * 2, c = size / 2;
    const data = new Uint8Array(size * size * 4);
    const half = stroke ? content / 2 - stroke / 2 : content / 2;
    for (let y = 0; y < size; y++) {
      for (let x = 0; x < size; x++) {
        let d = sdRect(x + 0.5 - c, y + 0.5 - c, half, half, stroke ? radius - stroke / 2 : radius);
        if (stroke) d = Math.abs(d) - stroke / 2;
        const a = Math.max(0, Math.min(1, 0.75 - d / 8));
        const i = (y * size + x) * 4;
        data[i] = data[i + 1] = data[i + 2] = 255;
        data[i + 3] = Math.round(a * 255);
      }
    }
    return { width: size, height: size, data };
  }

  // ---- logo chips ----------------------------------------------------------
  const CHIP = 96; // px, drawn at pixelRatio 3 => 32 css px
  function chip(c: Prepared, img?: HTMLImageElement): ImageData {
    const cv = document.createElement('canvas');
    cv.width = cv.height = CHIP;
    const g = cv.getContext('2d')!;
    const dark = !!c.logoDark;
    g.beginPath(); g.roundRect(2, 2, CHIP - 4, CHIP - 4, 26);
    g.fillStyle = dark ? '#16201B' : '#FFFFFF'; g.fill();
    const inset = c.hiring ? 16 : 12;
    g.beginPath(); g.roundRect(c.hiring ? 5 : 3, c.hiring ? 5 : 3, CHIP - (c.hiring ? 10 : 6), CHIP - (c.hiring ? 10 : 6), c.hiring ? 23 : 25);
    g.lineWidth = c.hiring ? 8 : 3; g.strokeStyle = c.hiring ? HIRE : '#D5DBD5'; g.stroke();
    if (img && img.naturalWidth > 0) {
      const box = CHIP - inset * 2, k = Math.min(box / img.naturalWidth, box / img.naturalHeight);
      const w = img.naturalWidth * k, h = img.naturalHeight * k;
      g.drawImage(img, (CHIP - w) / 2, (CHIP - h) / 2, w, h);
    } else {
      g.fillStyle = dark ? '#FFFFFF' : '#16201B';
      g.font = '800 34px "Archivo Variable", "Archivo", system-ui, sans-serif';
      g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillText(initials(c.name), CHIP / 2, CHIP / 2 + 2);
    }
    return g.getImageData(0, 0, CHIP, CHIP);
  }
  /** Logos load on demand: placeholder chip first, real logo swapped in when it arrives. */
  function onMissingImage(e: { id: string }) {
    const m = map;
    if (!m || !e.id.startsWith('logo~') || m.hasImage(e.id)) return;
    const c = byId.get(e.id.slice(5));
    if (!c || !c.logo) return;
    m.addImage(e.id, chip(c), { pixelRatio: 3 });
    // Symbols laid out while their image was missing stay invisible until the tile is laid out
    // again, so re-lay out once (debounced) after a batch of placeholders lands. updateImage()
    // below then swaps the real logo in without another layout.
    clearTimeout(relayoutTimer);
    relayoutTimer = window.setTimeout(() => {
      (map?.getSource('co') as maplibregl.GeoJSONSource | undefined)?.setData(collection(layout, items));
    }, 40);
    const img = new Image();
    img.decoding = 'async';
    img.onload = () => { if (map && map.hasImage(e.id)) map.updateImage(e.id, chip(c, img)); };
    img.src = c.logo; // on error the monogram placeholder simply stays
  }

  const O = ['coalesce', ['feature-state', 'o'], 1] as any;

  /** (Re)create images, sources and layers once the style has loaded. */
  function ensure(m: maplibregl.Map) {
    const css = (name: string, fallback: string) =>
      getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
    const ink = css('--ink', '#16201B');
    const ink3 = css('--ink-3', '#66726C');
    const hire = css('--hire', HIRE);
    const peacock = css('--peacock', PEACOCK);

    const opts = { sdf: true, pixelRatio: 2 };
    m.addImage('tile', sdfImage(64, 19, 0), opts);
    m.addImage('tile-o', sdfImage(64, 19, 4), opts);
    m.addImage('ring', sdfImage(72, 24, 4), opts);

    const bl = bubbles(layout, items);
    curBubbles = bl;
    m.addSource('cities', { type: 'geojson', promoteId: 'key', data: cityCollection(bl) });
    m.addSource('co', { type: 'geojson', promoteId: 'id', data: collection(layout, items) });

    // City markers below z9: a solid dot (green when someone there is hiring) on a soft halo.
    m.addLayer({
      id: 'glow', type: 'circle', source: 'cities', maxzoom: DEEP,
      paint: {
        'circle-radius': ['*', 2, ['get', 'r']], 'circle-blur': 0.6,
        'circle-color': ['case', ['==', ['get', 'h'], 1], hire, PEACOCK],
        'circle-opacity': ['interpolate', ['linear'], ['zoom'], 8.4, ['*', O, 0.16], 9, 0],
      },
    });
    m.addLayer({
      id: 'core', type: 'circle', source: 'cities', maxzoom: DEEP,
      paint: {
        'circle-radius': ['get', 'r'],
        'circle-color': ['case', ['==', ['get', 'h'], 1], hire, ink],
        'circle-stroke-color': '#FFFFFF', 'circle-stroke-width': 2,
        'circle-opacity': ['interpolate', ['linear'], ['zoom'], 8.4, O, 9, 0],
        'circle-stroke-opacity': ['interpolate', ['linear'], ['zoom'], 8.4, O, 9, 0],
      },
    });
    // Monogram tiles (SDF) for companies without a logo ...
    m.addLayer({
      id: 'tiles', type: 'symbol', source: 'co', minzoom: DEEP, filter: ['==', ['get', 'img'], ''],
      layout: {
        'icon-image': ['case', ['==', ['get', 'k'], 2], 'tile-o', 'tile'],
        'icon-size': ['get', 'isz'],
        'icon-allow-overlap': true, 'icon-ignore-placement': true,
        'text-field': ['get', 'ini'], 'text-font': ['Noto Sans Bold'], 'text-size': ['get', 'ts'],
        'text-allow-overlap': true, 'text-ignore-placement': true,
        'symbol-sort-key': ['get', 'sk'],
      },
      paint: {
        'icon-color': ['match', ['get', 'k'], 0, hire, 1, ink, ink3],
        'text-color': ['match', ['get', 'k'], 0, '#FFFFFF', 1, '#FFFFFF', ink3],
        'icon-opacity': O, 'text-opacity': O,
      },
    });
    // ... and logo chips (images added on demand) for the rest.
    m.addLayer({
      id: 'chips', type: 'symbol', source: 'co', minzoom: DEEP, filter: ['!=', ['get', 'img'], ''],
      layout: {
        'icon-image': ['get', 'img'], 'icon-size': ['get', 'isz'],
        'icon-allow-overlap': true, 'icon-ignore-placement': true,
        'symbol-sort-key': ['get', 'sk'],
      },
      paint: { 'icon-opacity': ['*', O, ['case', ['==', ['get', 'k'], 2], 0.45, 1]] },
    });
    // Company names under the markers once there is room; overlapping names drop out.
    m.addLayer({
      id: 'names', type: 'symbol', source: 'co', minzoom: 10,
      layout: {
        'text-field': ['get', 'nm'], 'text-font': ['Noto Sans Bold'], 'text-size': 11,
        'text-anchor': 'top', 'text-offset': [0, 1.55], 'text-max-width': 9, 'text-padding': 2,
        'symbol-sort-key': ['-', 0, ['get', 'sk']],
      },
      paint: { 'text-color': ink, 'text-halo-color': '#FFFFFF', 'text-halo-width': 2, 'text-opacity': O },
    });
    m.addLayer({
      id: 'ring', type: 'symbol', source: 'co', minzoom: DEEP,
      layout: { 'icon-image': 'ring', 'icon-size': ['get', 'rsz'], 'icon-allow-overlap': true, 'icon-ignore-placement': true },
      paint: {
        'icon-color': peacock,
        'icon-opacity': ['case', ['boolean', ['feature-state', 'sel'], false], 1, ['boolean', ['feature-state', 'hov'], false], 0.7, 0],
      },
    });
    appliedSel = ''; appliedHov = '';
    applyStates();
    renderLabels(bl);
  }

  function setState(source: string, id: string, st: Record<string, any>) {
    if (!id || !map?.getSource(source)) return;
    try { map.setFeatureState({ source, id }, st); } catch { /* source not ready */ }
  }
  function applyStates() {
    if (appliedSel !== selectedId) { setState('co', appliedSel, { sel: false }); setState('co', selectedId, { sel: true }); appliedSel = selectedId; }
    if (appliedHov !== hoveredId) { setState('co', appliedHov, { hov: false }); setState('co', hoveredId, { hov: true }); appliedHov = hoveredId; }
  }

  // ---- city labels (DOM; the lights themselves are GL circles) ---------------
  function makeCity(b: Bubble, rank: number, n: number): HTMLElement {
    const el = document.createElement('button');
    el.type = 'button';
    el.className = 'city';
    el.style.setProperty('--d', `${Math.round(b.r * 2)}px`);
    el.style.setProperty('--r', `${Math.round(b.r)}px`);
    el.style.setProperty('--dly', `${Math.round(150 + (850 * rank) / Math.max(1, n - 1))}ms`);
    el.setAttribute('aria-label', `${b.city}, ${b.count} ${b.count === 1 ? 'company' : 'companies'}${b.hiring ? `, ${b.hiring} hiring` : ''}. Zoom in.`);
    const lab = document.createElement('span'); lab.className = 'lab';
    const top = document.createElement('span'); top.className = 'cl-hd';
    const nm = document.createElement('span'); nm.className = 'nm'; nm.textContent = b.city;
    const ct = document.createElement('span'); ct.className = 'ct'; ct.textContent = String(b.count);
    top.append(nm, ct); lab.append(top);
    if (b.hiring) { const h = document.createElement('span'); h.className = 'hr'; h.textContent = `${b.hiring} hiring`; lab.append(h); }
    el.append(lab);
    // 11.4: the whole sunflower fits on screen and 32px tiles don't overlap (1.9 km spacing).
    el.addEventListener('click', (e) => { e.stopPropagation(); goTo([b.lng, b.lat], 11.4); });
    return el;
  }
  function renderLabels(bl: Bubble[]) {
    if (!map) return;
    for (const k of markers) k.marker.remove();
    markers = bl.map((b, i) => {
      const el = makeCity(b, i, bl.length);
      const marker = new maplibregl.Marker({ element: el, anchor: 'center' }).setLngLat([b.lng, b.lat]).addTo(map!);
      return { marker, el, lab: el.querySelector('.lab') as HTMLElement, r: b.r, w: 0, h: 0, lng: b.lng, lat: b.lat };
    });
    declutter();
  }

  /** Hide labels that would collide (largest city wins); the lights themselves stay. */
  function declutter() {
    if (!map || deep || !markers.length) return;
    const lowZ = map.getZoom() < 3;
    // On the globe, points more than ~75 degrees from the view centre sit on or past the horizon:
    // hide those markers instead of letting their labels pile up along the edge.
    const ctr = map.getCenter();
    const R = Math.PI / 180;
    const far = (lng: number, lat: number) =>
      Math.sin(lat * R) * Math.sin(ctr.lat * R) + Math.cos(lat * R) * Math.cos(ctr.lat * R) * Math.cos((lng - ctr.lng) * R) < Math.cos(75 * R);
    const W = host.clientWidth, H = host.clientHeight;
    const pts = markers.map((k) => map!.project([k.lng, k.lat]));
    const hidden = markers.map((k) => far(k.lng, k.lat));
    markers.forEach((k, i) => k.el.classList.toggle('far', hidden[i]));
    for (const cm of campusMarkers) cm.el.classList.toggle('far', far(cm.pos[0], cm.pos[1]));
    const taken: number[][] = markers.map((k, i) => hidden[i] ? [0, 0, 0, 0] : [pts[i].x - k.r, pts[i].y - k.r, pts[i].x + k.r, pts[i].y + k.r]);
    const hit = (a: number[], skip: number) => {
      for (let j = 0; j < taken.length; j++) {
        if (j === skip) continue;
        const b = taken[j];
        if (a[0] < b[2] && a[2] > b[0] && a[1] < b[3] && a[3] > b[1]) return true;
      }
      return false;
    };
    // Priority: cities with 10+ companies, then the four campus labels (always shown: the first
    // free side of the pin, else below), then the other cities by size.
    const placeCampus = (cm: CampusMk) => {
      const p = map!.project(cm.pos);
      const w = cm.lab.offsetWidth, h = cm.lab.offsetHeight;
      const opts: [string, number[]][] = [
        ['below', [p.x - w / 2, p.y + 18, p.x + w / 2, p.y + 20 + h]],
        ['left', [p.x - 22 - w, p.y - h / 2 - 1, p.x - 18, p.y + h / 2 + 1]],
        ['above', [p.x - w / 2, p.y - 20 - h, p.x + w / 2, p.y - 18]],
        ['right', [p.x + 18, p.y - h / 2 - 1, p.x + 22 + w, p.y + h / 2 + 1]],
      ];
      // Campuses always keep a label: the first free side inside the map, else the first inside it.
      const inside = opts.filter(([, b]) => b[0] >= 4 && b[2] <= W - 4 && b[1] >= 4 && b[3] <= H - 4);
      const pick = inside.find(([, b]) => !hit(b, -1)) ?? inside[0] ?? opts[0];
      cm.el.dataset.side = pick[0];
      taken.push(pick[1]);
    };
    // Campus pins and their rings block city labels around them.
    for (const cm of campusMarkers) {
      const p = map!.project(cm.pos);
      taken.push([p.x - 16, p.y - 16, p.x + 16, p.y + 16]);
    }
    const BIG_R = 3 + 2.2 * Math.sqrt(10);
    let campusesPlaced = false;
    markers.forEach((k, i) => {
      if (!campusesPlaced && k.r < BIG_R - 0.01) { campusesPlaced = true; for (const cm of campusMarkers) placeCampus(cm); }
      if (hidden[i]) return;
      if (!k.w) { k.w = k.lab.offsetWidth; k.h = k.lab.offsetHeight; }
      const y = pts[i].y;
      const x = pts[i].x;
      const boxes: [string, number[]][] = [
        ['r', [x + k.r + 6, y - k.h / 2 - 2, x + k.r + 10 + k.w, y + k.h / 2 + 2]],
        ['l', [x - k.r - 10 - k.w, y - k.h / 2 - 2, x - k.r - 6, y + k.h / 2 + 2]],
        ['b', [x - k.w / 2 - 2, y + k.r + 4, x + k.w / 2 + 2, y + k.r + 8 + k.h]],
        ['a', [x - k.w / 2 - 2, y - k.r - 8 - k.h, x + k.w / 2 + 2, y - k.r - 4]],
      ];
      const ok = (b: number[]) => b[0] >= 0 && b[2] <= W && !hit(b, i);
      const pick = lowZ && i >= 5 ? undefined : boxes.find(([, b]) => ok(b));
      const side = pick?.[0] ?? '';
      k.el.classList.toggle('nolab', side === '');
      k.el.classList.toggle('left', side === 'l');
      k.el.classList.toggle('below', side === 'b');
      k.el.classList.toggle('above', side === 'a');
      if (pick) taken.push(pick[1]);
    });
    if (!campusesPlaced) for (const cm of campusMarkers) placeCampus(cm);
  }

  // ---- campuses ------------------------------------------------------------
  function addCampuses(m: maplibregl.Map) {
    campusMarkers = CAMPUSES.map((c) => {
      const el = document.createElement('button');
      el.type = 'button'; el.className = 'campus';
      el.setAttribute('aria-label', `${c.name} campus: show its alumni companies`);
      el.style.zIndex = '3';
      const pin = document.createElement('span'); pin.className = 'pin';
      pin.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 9l10-5 10 5-10 5z"/><path d="M6 11v5c0 1.5 2.7 3 6 3s6-1.5 6-3v-5"/><path d="M22 9v6"/></svg>';
      const lab = document.createElement('span'); lab.className = 'cl';
      const nm = document.createElement('span'); nm.textContent = `${c.name} campus`;
      const ct = document.createElement('span'); ct.className = 'cc';
      lab.append(nm, ct);
      el.append(pin, lab);
      el.addEventListener('click', (e) => { e.stopPropagation(); oncampus?.(c.name); });
      const marker = new maplibregl.Marker({ element: el, anchor: 'center' }).setLngLat(c.pos).addTo(m);
      return { marker, el, lab, pos: c.pos };
    });
    updateCampusCounts();
  }
  function updateCampusCounts() {
    for (const cm of campusMarkers) {
      const name = cm.lab.firstChild?.textContent?.replace(' campus', '') ?? '';
      const n = items.reduce((k, c) => k + (c.campuses.includes(name) ? 1 : 0), 0);
      const ct = cm.lab.querySelector('.cc');
      if (ct) ct.textContent = n ? String(n) : '';
      cm.el.setAttribute('aria-label', `${name} campus, ${n} ${n === 1 ? 'company' : 'companies'} by its alumni: show them`);
    }
  }

  // ---- base map ------------------------------------------------------------
  function applyBasemap() {
    if (!map?.getLayer('base')) return;
    const sat = basemap === 'satellite';
    map.setLayoutProperty('base', 'visibility', sat ? 'none' : 'visible');
    map.setLayoutProperty('sat', 'visibility', sat ? 'visible' : 'none');
    map.setLayoutProperty('satlabels', 'visibility', sat ? 'visible' : 'none');
  }
  function setBasemap(b: Basemap) {
    basemap = b;
    try { localStorage.setItem(BM_KEY, b); } catch { /* private mode */ }
    applyBasemap();
  }
  function retryTiles() {
    tilesFailing = false;
    (map?.getSource('base') as maplibregl.RasterTileSource | undefined)?.setTiles(STREET);
    (map?.getSource('sat') as maplibregl.RasterTileSource | undefined)?.setTiles([`${ESRI}/World_Imagery/MapServer/tile/{z}/{y}/{x}`]);
  }

  // ---- camera --------------------------------------------------------------
  function goTo(center: [number, number], zoom: number, bottom = 0) {
    if (!map) return;
    const padding = { ...inset, bottom: inset.bottom + bottom };
    if (reduced()) map.jumpTo({ center, zoom, padding });
    else map.flyTo({ center, zoom, padding, duration: 900, essential: false });
  }
  function fit(b: maplibregl.LngLatBoundsLike, opts: maplibregl.FitBoundsOptions = {}) {
    if (!map) return;
    // The map's own padding already covers the floating panels (see setPadding below), and
    // fitBounds adds its padding on top of it, so only the breathing room goes here.
    map.setPadding(inset);
    map.fitBounds(b, { padding: 48, duration: reduced() ? 0 : 600, ...opts });
  }
  function showWorld() {
    if (!map) return;
    const w = host.clientWidth - inset.left - inset.right;
    const zoom = Math.max(0.8, Math.log2(w / 512) + 0.2);
    const o = { center: [40, 22] as [number, number], zoom, padding: inset };
    if (reduced()) map.jumpTo(o); else map.easeTo({ ...o, duration: 900 });
  }
  function updateRegion() {
    if (!map) return;
    // Judge by how much of the globe is in view, not zoom: fitting India on a phone needs z < 3.
    const z = map.getZoom(), c = map.getCenter(), b = map.getBounds();
    const span = Math.min(360, b.getEast() - b.getWest());
    const inIndia = c.lng > 62 && c.lng < 102 && c.lat > 2 && c.lat < 40;
    region = span > 130 ? 'World' : inIndia && z < 8 ? 'India' : '';
  }

  // ---- animation helpers -----------------------------------------------------
  let introActive = false, introRaf = 0;
  let finalCam: { center: [number, number]; zoom: number } | null = null;

  function setCities(o: (rank: number, n: number) => number) {
    const n = curBubbles.length;
    curBubbles.forEach((b, i) => setState('cities', b.key, { o: o(i, n) }));
  }

  function runIntro(m: maplibregl.Map) {
    introActive = true;
    const t0 = performance.now();
    setCities(() => 0);
    const lastO = new Float32Array(curBubbles.length).fill(-1);
    requestAnimationFrame(() => requestAnimationFrame(() => (lit = true)));
    if (finalCam) m.easeTo({ center: finalCam.center, zoom: finalCam.zoom, pitch: 0, duration: 2300, easing: easeOut, essential: true });
    const tick = () => {
      if (!introActive) return;
      const t = performance.now() - t0, n = curBubbles.length;
      curBubbles.forEach((b, i) => {
        const start = 150 + (850 * i) / Math.max(1, n - 1);
        const o = Math.round(easeOut(clamp01((t - start) / 450)) * 50) / 50;
        if (o !== lastO[i]) { lastO[i] = o; setState('cities', b.key, { o }); }
      });
      if (t >= 2000) { finishIntro(false); return; }
      introRaf = requestAnimationFrame(tick);
    };
    introRaf = requestAnimationFrame(tick);
  }

  /** Jump the choreography to its final frame. */
  function finishIntro(jumpCamera: boolean) {
    lit = true;
    if (!introActive) return;
    introActive = false;
    cancelAnimationFrame(introRaf);
    setCities(() => 1);
    if (jumpCamera && map && finalCam) { map.stop(); map.jumpTo({ center: finalCam.center, zoom: finalCam.zoom, pitch: 0 }); }
  }

  // Bloom: when the view crosses into z >= 9, tiles in view fade in along the spiral.
  let prevZ = 0, bloomList: { id: string; idx: number }[] = [], bloomRaf = 0, blooming = false;
  function prepBloom() {
    if (!map) return;
    cancelAnimationFrame(bloomRaf); blooming = false;
    const view = map.getBounds();
    bloomList = [];
    for (const c of items) {
      const t = layout.tiles.get(c.id);
      if (t && view.contains([t.lng, t.lat])) { bloomList.push({ id: t.id, idx: t.idx }); setState('co', t.id, { o: 0 }); }
    }
  }
  function releaseBloom() {
    for (const b of bloomList) setState('co', b.id, { o: 1 });
    bloomList = [];
  }
  function runBloom() {
    if (!bloomList.length) return;
    if (reduced()) { releaseBloom(); return; }
    const list = bloomList, t0 = performance.now();
    const last = new Float32Array(list.length).fill(-1);
    blooming = true;
    const tick = () => {
      const t = performance.now() - t0;
      let done = true;
      list.forEach((b, i) => {
        const o = Math.round(easeOut(clamp01((t - Math.min(b.idx * 12, 250)) / 190)) * 20) / 20;
        if (o < 1) done = false;
        if (o !== last[i]) { last[i] = o; setState('co', b.id, { o }); }
      });
      if (done || t > 600) { releaseBloom(); blooming = false; return; }
      bloomRaf = requestAnimationFrame(tick);
    };
    bloomRaf = requestAnimationFrame(tick);
  }
  function onZoom(m: maplibregl.Map) {
    const z = m.getZoom();
    if (z >= 8.8 && prevZ < 8.8) prepBloom();
    if (z >= DEEP && prevZ < DEEP) runBloom();
    if (z < 8.8 && prevZ >= 8.8 && !blooming && bloomList.length) releaseBloom();
    prevZ = z;
    const d = z >= DEEP;
    if (d !== deep) deep = d;
  }

  // ---- lifecycle -------------------------------------------------------------
  function create(): () => void {
    const mostIndia = (() => {
      let n = 0, t = 0;
      for (const c of items) { if (!layout.tiles.has(c.id)) continue; t++; if (c.country === 'India') n++; }
      return t === 0 || n * 2 >= t;
    })();
    const sel = selectedId ? layout.tiles.get(selectedId) : undefined;
    const start: maplibregl.MapOptions = sel
      ? { center: [sel.lng, sel.lat], zoom: 11.6 }
      : { bounds: mostIndia ? INDIA : (tileBounds(items) ?? INDIA), fitBoundsOptions: { padding: { top: inset.top + 48, left: inset.left + 48, right: inset.right + 48, bottom: inset.bottom + 48 }, maxZoom: mostIndia ? 6 : 9 } };
    if (sel) lastFlown = selectedId;
    basemap = readBasemap();
    const intro = !sel && !reduced();
    lit = !intro;

    const m = new maplibregl.Map({
      container: host, style: STYLE, attributionControl: { compact: true },
      minZoom: 0.8, maxPitch: 60, dragRotate: false, pitchWithRotate: false, ...start,
    });
    map = m;
    m.setPadding(sel && innerWidth < 960 ? { ...inset, bottom: Math.round(host.clientHeight * 0.45) } : inset);
    if (intro) {
      finalCam = { center: [m.getCenter().lng, m.getCenter().lat], zoom: m.getZoom() };
      m.jumpTo({ center: [finalCam.center[0] - 6, finalCam.center[1] - 3], zoom: Math.max(0.9, finalCam.zoom - 0.8) });
    } else {
      finalCam = { center: [m.getCenter().lng, m.getCenter().lat], zoom: m.getZoom() };
    }
    if (import.meta.env.DEV) {
      (window as any).__map = m;
      m.on('error', (e) => console.warn('[map]', e.error?.message ?? e));
    }
    m.touchZoomRotate.disableRotation();
    m.touchPitch.disable();
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right');
    addCampuses(m);

    m.on('styleimagemissing', onMissingImage);
    m.on('style.load', () => { ensure(m); applyBasemap(); ready = true; if (intro) runIntro(m); });
    // Tell people when base tiles fail (offline, blocked by an extension) instead of a blank map.
    let fails = 0;
    m.on('error', (e: any) => {
      const id = e?.sourceId ?? e?.source?.id;
      if (id === 'base' || id === 'sat') { fails++; if (fails >= 3) tilesFailing = true; }
    });
    m.on('sourcedata', (e: any) => {
      if ((e.sourceId === 'base' || e.sourceId === 'sat') && e.tile && e.tile.state === 'loaded') { fails = 0; tilesFailing = false; }
    });
    m.on('zoom', () => onZoom(m));
    m.on('moveend', () => { updateRegion(); declutter(); });
    m.on('click', ['tiles', 'chips'], (e) => {
      const id = e.features?.[0]?.properties?.id;
      if (id) onselect(id);
    });
    m.on('mouseenter', ['tiles', 'chips'], () => (m.getCanvas().style.cursor = 'pointer'));
    m.on('mouseleave', ['tiles', 'chips'], () => (m.getCanvas().style.cursor = ''));
    prevZ = m.getZoom();
    deep = prevZ >= DEEP;

    // First user interaction with the map: tell App once, and end the intro at its final frame.
    const touch = () => {
      if (!interacted) { interacted = true; oninteract?.(); }
      finishIntro(false);
    };
    const evs = ['pointerdown', 'wheel', 'keydown', 'touchstart'] as const;
    for (const ev of evs) host.addEventListener(ev, touch, { capture: true, passive: true });
    const anywhere = () => finishIntro(false);
    window.addEventListener('keydown', anywhere, { capture: true });

    return () => {
      for (const ev of evs) host.removeEventListener(ev, touch, { capture: true });
      window.removeEventListener('keydown', anywhere, { capture: true });
      cancelAnimationFrame(introRaf); cancelAnimationFrame(bloomRaf);
      for (const k of markers) k.marker.remove();
      for (const k of campusMarkers) k.marker.remove();
      m.remove(); map = undefined;
    };
  }

  // Create the map only once the container has a real size, otherwise the initial
  // fitBounds is computed against 0x0 and sticks at minZoom.
  onMount(() => {
    if (host.clientWidth > 0 && host.clientHeight > 0) return create();
    let off: (() => void) | undefined;
    const ro = new ResizeObserver(() => {
      if (host.clientWidth > 0 && host.clientHeight > 0) { ro.disconnect(); off = create(); }
    });
    ro.observe(host);
    return () => { ro.disconnect(); off?.(); };
  });

  // Data: filter by id set against precomputed features.
  $effect(() => {
    const list = items;
    if (!ready || !map) return;
    if (firstData) { firstData = false; updateRegion(); return; }
    if (introActive) finishIntro(true);
    const bl = bubbles(layout, list);
    curBubbles = bl;
    (map.getSource('co') as maplibregl.GeoJSONSource | undefined)?.setData(collection(layout, list));
    (map.getSource('cities') as maplibregl.GeoJSONSource | undefined)?.setData(cityCollection(bl));
    renderLabels(bl);
    updateCampusCounts();
    // Place filters changed: fit the results. Otherwise only move the camera when nothing from
    // the results is in view. Either way, decide once the camera has stopped.
    const m = map;
    const refit = fitKey !== lastFitKey;
    lastFitKey = fitKey;
    const check = () => {
      if (items !== list) return; // filters changed again meanwhile
      if (!refit) {
        const view = m.getBounds();
        for (const c of list) {
          const t = layout.tiles.get(c.id);
          if (t && view.contains([t.lng, t.lat])) return;
        }
      }
      const b = tileBounds(list); if (b) fit(b, { maxZoom: 10 });
    };
    if (m.isMoving()) m.once('moveend', check); else check();
  });

  // Keep the camera's padding in step with the floating panels.
  // setPadding is a jump, which would cancel a camera animation in flight, so wait for it to end.
  $effect(() => {
    const p = { ...inset };
    const m = map;
    if (!ready || !m) return;
    const same = (q: Inset) => q.top === p.top && q.right === p.right && q.bottom === p.bottom && q.left === p.left;
    if (same(m.getPadding() as Inset)) return;
    if (m.isMoving()) m.once('moveend', () => { if (same({ ...inset })) m.setPadding(p); });
    else m.setPadding(p);
  });

  // Selection: ring + fly to tile.
  $effect(() => {
    const id = selectedId;
    hoveredId;
    if (!ready || !map) return;
    applyStates();
    if (id && id !== lastFlown) {
      const t = layout.tiles.get(id);
      if (t) {
        finishIntro(false);
        lastFlown = id;
        goTo([t.lng, t.lat], 11.6, innerWidth < 960 ? Math.round(host.clientHeight * 0.45) : 0);
      }
    } else if (!id) lastFlown = '';
  });
</script>

<div class="root" class:deep class:lit>
  <div class="canvas" bind:this={host} role="region" aria-label="Map of companies. The list has the same information in an accessible form."></div>

  <div class="mapctl">
    <div class="seg" role="group" aria-label="Map type">
      <button type="button" aria-pressed={basemap === 'map'} onclick={() => setBasemap('map')}>Map</button>
      <button type="button" aria-pressed={basemap === 'satellite'} onclick={() => setBasemap('satellite')}>Satellite</button>
    </div>
    <div class="seg" role="group" aria-label="Jump to">
      <button type="button" aria-pressed={region === 'India'} onclick={() => fit(INDIA)}>India</button>
      <button type="button" aria-pressed={region === 'World'} onclick={showWorld}>World</button>
    </div>
  </div>

  {#if tilesFailing}
    <div class="tilefail" role="alert">
      <p>Map tiles aren&rsquo;t loading. Check your connection, or allow server.arcgisonline.com in your ad blocker.</p>
      <button type="button" onclick={retryTiles}>Try again</button>
    </div>
  {/if}

  {#if deep}
    <p class="note">Companies are grouped around each city centre; exact offices aren't mapped yet.</p>
  {/if}
</div>

<style>
  .root { position: absolute; inset: 0; background: #DCE8EC; }
  .canvas { position: absolute; inset: 0; }

  .mapctl {
    position: absolute; z-index: 2; right: calc(var(--inset-r, 0px) + 12px); top: calc(var(--inset-t, 0px) + 12px);
    display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; max-width: calc(100% - var(--inset-l, 0px) - var(--inset-r, 0px) - 24px);
  }
  .seg { display: flex; padding: 4px; gap: 4px; background: var(--surface); border-radius: 999px; box-shadow: var(--float); }
  .tilefail {
    position: absolute; z-index: 3; left: calc(var(--inset-l, 0px) + 12px); right: calc(var(--inset-r, 0px) + 12px); top: calc(var(--inset-t, 0px) + 64px);
    margin: 0 auto; max-width: 440px; display: flex; align-items: center; gap: 12px; padding: 12px 12px 12px 16px;
    background: var(--surface); border: 1px solid var(--line); border-radius: 16px; box-shadow: var(--float); font-size: 13px; color: var(--ink);
  }
  .tilefail p { margin: 0; flex: 1; }
  .tilefail button { flex: none; height: 36px; padding: 0 14px; border: 0; border-radius: 999px; background: var(--ink); color: #fff; font: inherit; font-weight: 600; cursor: pointer; }
  .seg button {
    font: inherit; font-size: 13px; font-weight: 500; line-height: 1; padding: 8px 12px; border: 0; border-radius: 999px;
    background: transparent; color: var(--ink-2); cursor: pointer; transition: background-color .12s, color .12s;
  }
  .seg button:hover { color: var(--ink); }
  .seg button[aria-pressed='true'] { background: var(--ink); color: #fff; }
  .seg button:focus-visible { outline: 2px solid var(--peacock); outline-offset: 2px; }
  .root :global(.maplibregl-ctrl-bottom-right) { right: var(--inset-r, 0px); bottom: calc(var(--inset-b, 0px) + 56px); }
  .root :global(.maplibregl-ctrl-group) { border-radius: 12px; box-shadow: var(--float); overflow: hidden; }
  .root :global(.maplibregl-ctrl-group button) { width: 36px; height: 36px; }

  .note {
    position: absolute; z-index: 2; top: calc(var(--inset-t, 0px) + 64px);
    left: calc(var(--inset-l, 0px) + (100% - var(--inset-l, 0px) - var(--inset-r, 0px)) / 2); transform: translateX(-50%); margin: 0;
    width: max-content; max-width: min(420px, calc(100% - var(--inset-l, 0px) - var(--inset-r, 0px) - 32px)); text-align: center;
    padding: 8px 12px; border-radius: 999px; background: var(--surface); box-shadow: var(--float);
    font-size: 12px; line-height: 1.35; font-weight: 500; color: var(--ink-2); pointer-events: none;
  }

  @media (max-width: 959px) { .note { top: calc(var(--inset-t, 0px) + 108px); } }

  /* City labels: DOM markers so they can use Archivo. Hidden once tiles take over. */
  .root.deep :global(.city), .root.deep :global(.campus .cl) { display: none; }
  :global(.city.far), :global(.campus.far) { visibility: hidden; }
  :global(.city) {
    width: var(--d); height: var(--d); padding: 0; border: 0; border-radius: 50%; background: transparent; cursor: pointer;
    font-family: 'Archivo Variable', 'Archivo', system-ui, sans-serif;
  }
  :global(.city .lab) {
    position: absolute; left: calc(100% + 6px); top: 50%; transform: translateY(-50%);
    display: grid; gap: 2px; text-align: left; white-space: nowrap; pointer-events: none;
    padding: 4px 8px; border-radius: 8px; background: var(--surface); box-shadow: 0 1px 2px rgb(22 32 27 / .12), 0 2px 8px rgb(22 32 27 / .08);
    color: var(--ink); opacity: 0;
  }
  .root.lit :global(.city .lab) { opacity: 1; transition: opacity .5s ease var(--dly, 0ms); }
  :global(.city .cl-hd) { display: flex; gap: 6px; align-items: baseline; }
  :global(.city .nm) { font-size: 13px; line-height: 1.1; font-weight: 600; }
  :global(.city .ct) { font-size: 12px; line-height: 1.1; font-weight: 500; color: var(--ink-3); font-variant-numeric: tabular-nums; }
  :global(.city .hr) { font-size: 12px; line-height: 1.1; font-weight: 600; color: var(--hire-ink); font-variant-numeric: tabular-nums; }
  :global(.city.left .lab) { left: auto; right: calc(100% + 6px); text-align: right; justify-items: end; }
  :global(.city.left .cl-hd) { flex-direction: row-reverse; }
  :global(.city.below .lab) { left: 50%; top: calc(100% + 4px); transform: translateX(-50%); }
  :global(.city.above .lab) { left: 50%; top: auto; bottom: calc(100% + 4px); transform: translateX(-50%); }
  .root.lit :global(.city.nolab .lab) { opacity: 0; }
  .root.lit :global(.city:hover .lab), .root.lit :global(.city:focus-visible .lab) { opacity: 1; transition-delay: 0ms; z-index: 1; }
  :global(.city:focus-visible) { outline: 2px solid var(--peacock); outline-offset: 4px; }

  /* Campuses: the strongest marker on the map, a peacock pin with a cap and an always-on label. */
  :global(.campus) {
    width: 32px; height: 32px; padding: 0; border: 0; background: transparent; cursor: pointer;
    font-family: 'Archivo Variable', 'Archivo', system-ui, sans-serif;
  }
  :global(.campus .pin) {
    position: absolute; inset: 0; display: grid; place-items: center; border-radius: 50%;
    background: var(--peacock); border: 3px solid #fff; box-shadow: 0 0 0 4px color-mix(in oklab, var(--peacock) 25%, transparent), 0 2px 8px rgb(22 32 27 / .3);
    transition: transform .12s;
  }
  :global(.campus .pin svg) { width: 16px; height: 16px; fill: none; stroke: #fff; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
  :global(.campus .cl) {
    position: absolute; top: calc(100% + 6px); left: 50%; transform: translateX(-50%); white-space: nowrap; pointer-events: none;
    display: inline-flex; align-items: baseline; gap: 6px; padding: 4px 10px; border-radius: 999px; background: var(--peacock); color: #fff;
    font-size: 12px; line-height: 1.2; font-weight: 600; box-shadow: 0 1px 4px rgb(22 32 27 / .25);
  }
  :global(.campus .cc) { font-weight: 500; opacity: .85; font-variant-numeric: tabular-nums; }
  :global(.campus .cc:empty) { display: none; }
  :global(.campus[data-side='left'] .cl) { top: 50%; left: auto; right: calc(100% + 6px); transform: translateY(-50%); }
  :global(.campus[data-side='right'] .cl) { top: 50%; left: calc(100% + 6px); transform: translateY(-50%); }
  :global(.campus[data-side='above'] .cl) { top: auto; bottom: calc(100% + 6px); }
  :global(.campus:hover .pin) { transform: scale(1.08); }
  :global(.campus:focus-visible) { outline: 2px solid var(--peacock); outline-offset: 4px; border-radius: 50%; }
</style>
