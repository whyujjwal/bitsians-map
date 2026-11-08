<script lang="ts">
  import * as maplibregl from 'maplibre-gl';
  import 'maplibre-gl/dist/maplibre-gl.css';
  import { onMount, untrack } from 'svelte';
  import { initials, type Prepared } from '../lib/data';
  import {
    arcCollection, bubbles, buildLayout, cityCollection, collection, CAMPUSES,
    type Bubble, type CampusName,
  } from '../lib/map-layout';

  let { items, all, selectedId = '', hoveredId = '', onselect, oncampus, oninteract }: {
    items: Prepared[]; all: Prepared[]; selectedId?: string; hoveredId?: string;
    onselect: (id: string) => void;
    oncampus?: (name: CampusName) => void;
    oninteract?: () => void;
  } = $props();

  maplibregl.setWorkerUrl('/maplibre/maplibre-gl-worker.mjs');

  const DEEP = 9;      // logo / monogram tiles from this zoom, city lights below
  const INDIA: maplibregl.LngLatBoundsLike = [[68, 6.5], [97.5, 35.5]];
  const PEACOCK = '#44B3B0', MARIGOLD = '#F1A10A';

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
    g.beginPath(); g.roundRect(0, 0, CHIP, CHIP, 28);
    g.fillStyle = dark ? '#13222C' : '#FFFFFF'; g.fill();
    const inset = c.hiring ? 14 : 8;
    if (c.hiring) {
      g.beginPath(); g.roundRect(4, 4, CHIP - 8, CHIP - 8, 24);
      g.lineWidth = 8; g.strokeStyle = MARIGOLD; g.stroke();
    }
    if (img && img.naturalWidth > 0) {
      const box = CHIP - inset * 2, k = Math.min(box / img.naturalWidth, box / img.naturalHeight);
      const w = img.naturalWidth * k, h = img.naturalHeight * k;
      g.drawImage(img, (CHIP - w) / 2, (CHIP - h) / 2, w, h);
    } else {
      g.fillStyle = dark ? '#FFFFFF' : '#13222C';
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

  // ---- arcs gradient (also drives the intro draw-out) -----------------------
  const lerpHex = (t: number) => {
    const a = [0x44, 0xb3, 0xb0], b = [0xf1, 0xa1, 0x0a];
    return a.map((v, i) => Math.round(v + (b[i] - v) * t));
  };
  function gradient(p: number): any {
    if (p >= 1) return ['interpolate', ['linear'], ['line-progress'], 0, PEACOCK, 1, MARIGOLD];
    const q = Math.max(0.001, Math.min(0.99, p)), [r, g, b] = lerpHex(q);
    return ['interpolate', ['linear'], ['line-progress'],
      0, PEACOCK, q, `rgb(${r},${g},${b})`, Math.min(q + 0.004, 0.999), `rgba(${r},${g},${b},0)`, 1, `rgba(${r},${g},${b},0)`];
  }

  const O = ['coalesce', ['feature-state', 'o'], 1] as any;

  /** (Re)create images, sources and layers once the style has loaded. */
  function ensure(m: maplibregl.Map, intro: boolean) {
    const css = (name: string, fallback: string) =>
      getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
    const ink = css('--ink', '#E7EEF0');
    const paper = css('--paper', '#0B141A');
    const ink3 = css('--ink-3', '#6E828B');
    const marigold = css('--marigold', '#F4B02E');
    const onMarigold = css('--on-marigold', '#13222C');
    const peacock = css('--peacock', PEACOCK);

    const opts = { sdf: true, pixelRatio: 2 };
    m.addImage('tile', sdfImage(64, 19, 0), opts);
    m.addImage('tile-o', sdfImage(64, 19, 4), opts);
    m.addImage('ring', sdfImage(72, 24, 4), opts);

    const bl = bubbles(layout, items);
    curBubbles = bl;
    m.addSource('arcs', { type: 'geojson', lineMetrics: true, data: arcCollection(layout, items, bl) });
    m.addSource('cities', { type: 'geojson', promoteId: 'key', data: cityCollection(bl) });
    m.addSource('co', { type: 'geojson', promoteId: 'id', data: collection(layout, items) });

    m.addLayer({
      id: 'arcs', type: 'line', source: 'arcs', maxzoom: 7,
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: {
        'line-width': ['get', 'w'],
        'line-opacity': ['interpolate', ['linear'], ['zoom'], 6, 0.5, 7, 0],
        'line-gradient': gradient(intro ? 0 : 1),
      },
    });
    const hireGlow = ['case', ['==', ['get', 'h'], 1], 0.22, 0.18];
    m.addLayer({
      id: 'glow', type: 'circle', source: 'cities', maxzoom: DEEP,
      paint: {
        'circle-radius': ['*', 2.6, ['get', 'r']], 'circle-blur': 1,
        'circle-color': ['case', ['==', ['get', 'h'], 1], MARIGOLD, PEACOCK],
        'circle-opacity': ['interpolate', ['linear'], ['zoom'], 8.4, ['*', O, hireGlow], 9, 0],
      },
    });
    m.addLayer({
      id: 'core', type: 'circle', source: 'cities', maxzoom: DEEP,
      paint: {
        'circle-radius': ['get', 'r'], 'circle-blur': 0.25,
        'circle-color': ['case', ['==', ['get', 'h'], 1], '#FFE3A3', '#BDF2EC'],
        'circle-opacity': ['interpolate', ['linear'], ['zoom'], 8.4, O, 9, 0],
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
        'icon-color': ['match', ['get', 'k'], 0, marigold, 1, ink, ink3],
        'text-color': ['match', ['get', 'k'], 0, onMarigold, 1, paper, ink3],
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
    const pts = markers.map((k) => map!.project([k.lng, k.lat]));
    const taken: number[][] = markers.map((k, i) => [pts[i].x - k.r, pts[i].y - k.r, pts[i].x + k.r, pts[i].y + k.r]);
    const hit = (a: number[], skip: number) => {
      for (let j = 0; j < taken.length; j++) {
        if (j === skip) continue;
        const b = taken[j];
        if (a[0] < b[2] && a[2] > b[0] && a[1] < b[3] && a[3] > b[1]) return true;
      }
      return false;
    };
    // Priority: cities with 3+ companies label first, then the four campus labels (below, left,
    // above or right of the ring, whichever is free; hidden if none is), then the small cities.
    const BIG_R = 3 + 2.2 * Math.sqrt(3);
    let campusesPlaced = false;
    const placeCampuses = () => {
      campusesPlaced = true;
      for (const cm of campusMarkers) {
        const p = map!.project(cm.pos);
        const w = cm.lab.offsetWidth, h = cm.lab.offsetHeight;
        const opts: [string, number[]][] = [
          ['below', [p.x - w / 2, p.y + 10, p.x + w / 2, p.y + 12 + h]],
          ['left', [p.x - 14 - w, p.y - h / 2 - 1, p.x - 10, p.y + h / 2 + 1]],
          ['above', [p.x - w / 2, p.y - 12 - h, p.x + w / 2, p.y - 10]],
          ['right', [p.x + 10, p.y - h / 2 - 1, p.x + 14 + w, p.y + h / 2 + 1]],
        ];
        const pick = opts.find(([, b]) => !hit(b, -1));
        cm.el.dataset.side = pick ? pick[0] : 'none';
        if (pick) taken.push(pick[1]);
      }
    };
    markers.forEach((k, i) => {
      if (!campusesPlaced && k.r < BIG_R - 0.01) placeCampuses();
      if (!k.w) { k.w = k.lab.offsetWidth; k.h = k.lab.offsetHeight; }
      const y = pts[i].y;
      const right = [pts[i].x + k.r + 6, y - k.h / 2 - 2, pts[i].x + k.r + 10 + k.w, y + k.h / 2 + 2];
      const left = [pts[i].x - k.r - 10 - k.w, y - k.h / 2 - 2, pts[i].x - k.r - 6, y + k.h / 2 + 2];
      const side = lowZ && i >= 5 ? '' : !hit(right, i) ? 'r' : !hit(left, i) ? 'l' : '';
      k.el.classList.toggle('nolab', side === '');
      k.el.classList.toggle('left', side === 'l');
      if (side) taken.push(side === 'l' ? left : right);
    });
    if (!campusesPlaced) placeCampuses();
  }

  // ---- campuses ------------------------------------------------------------
  function addCampuses(m: maplibregl.Map) {
    campusMarkers = CAMPUSES.map((c) => {
      const el = document.createElement('button');
      el.type = 'button'; el.className = 'campus';
      el.setAttribute('aria-label', `${c.name} campus: show its alumni companies`);
      const ring = document.createElement('span'); ring.className = 'ring';
      const lab = document.createElement('span'); lab.className = 'cl'; lab.textContent = `${c.name} campus`;
      el.append(ring, lab);
      el.addEventListener('click', (e) => { e.stopPropagation(); oncampus?.(c.name); });
      const marker = new maplibregl.Marker({ element: el, anchor: 'center' }).setLngLat(c.pos).addTo(m);
      return { marker, el, lab, pos: c.pos };
    });
  }

  // ---- camera --------------------------------------------------------------
  function goTo(center: [number, number], zoom: number, bottom = 0) {
    if (!map) return;
    const padding = { top: 0, left: 0, right: 0, bottom };
    if (reduced()) map.jumpTo({ center, zoom, padding });
    else map.flyTo({ center, zoom, padding, duration: 900, essential: false });
  }
  function fit(b: maplibregl.LngLatBoundsLike, opts: maplibregl.FitBoundsOptions = {}) {
    map?.fitBounds(b, { padding: 48, duration: reduced() ? 0 : 600, ...opts });
  }
  function showWorld() {
    if (!map) return;
    const d = Math.min(host.clientWidth, host.clientHeight) * 0.82;
    const zoom = Math.max(0.8, Math.log2((Math.PI * d) / 512));
    const o = { center: [45, 20] as [number, number], zoom, padding: { top: 0, left: 0, right: 0, bottom: 0 } };
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
    let lastP = -1;
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
      const p = Math.round(easeOut(clamp01((t - 500) / 1400)) * 100) / 100;
      if (p !== lastP && m.getLayer('arcs')) { lastP = p; m.setPaintProperty('arcs', 'line-gradient', gradient(p)); }
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
    if (map?.getLayer('arcs')) map.setPaintProperty('arcs', 'line-gradient', gradient(1));
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
      : { bounds: mostIndia ? INDIA : (tileBounds(items) ?? INDIA), fitBoundsOptions: { padding: { top: 24, left: 24, right: 24, bottom: sel ? 24 : 200 }, maxZoom: 6 } };
    if (sel) lastFlown = selectedId;
    const intro = !sel && !reduced();
    lit = !intro;

    const m = new maplibregl.Map({
      container: host, style: '/map/night.json', attributionControl: { compact: true },
      minZoom: 0.8, maxPitch: 60, dragRotate: false, pitchWithRotate: false, ...start,
    });
    map = m;
    if (sel && innerWidth < 960) m.setPadding({ top: 0, left: 0, right: 0, bottom: Math.round(host.clientHeight * 0.45) });
    if (intro) {
      finalCam = { center: [m.getCenter().lng, m.getCenter().lat], zoom: m.getZoom() };
      m.jumpTo({ center: [finalCam.center[0] - 16, finalCam.center[1] - 6], zoom: Math.max(0.9, finalCam.zoom - 1.4), pitch: 28 });
    } else {
      finalCam = { center: [m.getCenter().lng, m.getCenter().lat], zoom: m.getZoom() };
    }
    if (import.meta.env.DEV) {
      (window as any).__map = m;
      m.on('error', (e) => console.error('[map]', e.error?.message ?? e));
    }
    m.touchZoomRotate.disableRotation();
    m.touchPitch.disable();
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
    addCampuses(m);

    m.on('styleimagemissing', onMissingImage);
    m.on('style.load', () => { ensure(m, intro); ready = true; if (intro) runIntro(m); });
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
    (map.getSource('arcs') as maplibregl.GeoJSONSource | undefined)?.setData(arcCollection(layout, list, bl));
    renderLabels(bl);
    // Only move the camera when nothing from the results is in view.
    if (map.isMoving()) return;
    const view = map.getBounds();
    let any = false;
    for (const c of list) {
      const t = layout.tiles.get(c.id);
      if (t && view.contains([t.lng, t.lat])) { any = true; break; }
    }
    if (!any) { const b = tileBounds(list); if (b) fit(b, { maxZoom: 10 }); }
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

  <div class="seg" role="group" aria-label="Map region">
    <button type="button" aria-pressed={region === 'India'} onclick={() => fit(INDIA)}>India</button>
    <button type="button" aria-pressed={region === 'World'} onclick={showWorld}>World</button>
  </div>

  {#if deep}
    <p class="note">Companies are grouped around each city centre; exact offices aren't mapped yet.</p>
  {/if}
</div>

<style>
  .root { position: absolute; inset: 0; background: #060C11; }
  .canvas { position: absolute; inset: 0; }

  .seg {
    position: absolute; top: 12px; left: 12px; z-index: 2; display: flex; padding: 3px; gap: 2px;
    background: var(--surface); border-radius: 999px;
    box-shadow: 0 1px 2px rgb(0 0 0 / .08), 0 4px 16px rgb(0 0 0 / .08);
  }
  @media (max-width: 959px) { .seg { top: 64px; } }
  .seg button {
    font: inherit; font-size: 13px; font-weight: 600; line-height: 1; padding: 7px 14px; border: 0; border-radius: 999px;
    background: transparent; color: var(--ink-2); cursor: pointer;
  }
  .seg button[aria-pressed='true'] { background: var(--peacock); color: var(--on-peacock); }
  .seg button:focus-visible { outline: 2px solid var(--peacock); outline-offset: 2px; }

  .note {
    position: absolute; top: 16px; left: 50%; transform: translateX(-50%); z-index: 2; margin: 0;
    width: max-content; max-width: min(440px, calc(100% - 300px)); text-align: center;
    font-size: 12px; line-height: 1.35; font-weight: 500; color: var(--ink-2); pointer-events: none;
    text-shadow: 0 0 3px var(--paper), 0 0 8px var(--paper);
  }
  @media (max-width: 959px) { .note { top: 108px; max-width: calc(100% - 32px); } }

  /* City labels: DOM markers so they can use Archivo. Hidden once tiles take over. */
  .root.deep :global(.city), .root.deep :global(.campus .cl) { display: none; }
  :global(.city) {
    width: var(--d); height: var(--d); padding: 0; border: 0; border-radius: 50%; background: transparent; cursor: pointer;
    font-family: 'Archivo Variable', 'Archivo', system-ui, sans-serif;
  }
  :global(.city .lab) {
    position: absolute; left: calc(100% + 6px); top: 50%; transform: translateY(-50%);
    display: grid; gap: 2px; text-align: left; white-space: nowrap; pointer-events: none;
    color: var(--ink); text-shadow: 0 0 2px #0B141A, 0 0 2px #0B141A, 0 1px 3px #0B141A;
    opacity: 0;
  }
  .root.lit :global(.city .lab) { opacity: 1; transition: opacity .5s ease var(--dly, 0ms); }
  :global(.city .cl-hd) { display: flex; gap: 6px; align-items: baseline; }
  :global(.city .nm) { font-size: 15px; line-height: 1; font-weight: 760; font-variation-settings: 'wdth' 70, 'wght' 760; }
  :global(.city .ct) { font-size: 13px; line-height: 1; font-weight: 500; color: var(--ink-2); font-variant-numeric: tabular-nums; font-variation-settings: 'wdth' 85; }
  :global(.city .hr) { font-size: 13px; line-height: 1; font-weight: 700; color: var(--marigold); font-variation-settings: 'wdth' 85; }
  :global(.city.left .lab) { left: auto; right: calc(100% + 6px); text-align: right; justify-items: end; }
  :global(.city.left .cl-hd) { flex-direction: row-reverse; }
  .root.lit :global(.city.nolab .lab) { opacity: 0; }
  .root.lit :global(.city:hover .lab), .root.lit :global(.city:focus-visible .lab) { opacity: 1; transition-delay: 0ms; }
  :global(.city:focus-visible) { outline: 2px solid var(--peacock); outline-offset: 4px; }

  /* Campuses: thin white ring plus label. */
  :global(.campus) {
    width: 16px; height: 16px; padding: 0; border: 0; background: transparent; cursor: pointer;
    font-family: 'Archivo Variable', 'Archivo', system-ui, sans-serif;
  }
  :global(.campus .ring) { position: absolute; inset: 0; border: 1.5px solid #fff; border-radius: 50%; box-shadow: 0 0 6px rgb(255 255 255 / .35); }
  :global(.campus .cl) {
    position: absolute; top: calc(100% + 4px); left: 50%; transform: translateX(-50%); white-space: nowrap; pointer-events: none;
    font-size: 12px; line-height: 1; font-weight: 600; color: var(--ink-2);
    text-shadow: 0 0 2px #0B141A, 0 0 2px #0B141A, 0 1px 3px #0B141A;
  }
  :global(.campus[data-side='left'] .cl) { top: 50%; left: auto; right: calc(100% + 6px); transform: translateY(-50%); }
  :global(.campus[data-side='right'] .cl) { top: 50%; left: calc(100% + 6px); transform: translateY(-50%); }
  :global(.campus[data-side='above'] .cl) { top: auto; bottom: calc(100% + 4px); }
  :global(.campus[data-side='none'] .cl) { opacity: 0; }
  :global(.campus[data-side='none']:hover .cl), :global(.campus[data-side='none']:focus-visible .cl) { opacity: 1; }
  :global(.campus:hover .ring) { background: rgb(255 255 255 / .2); }
  :global(.campus:focus-visible) { outline: 2px solid var(--peacock); outline-offset: 3px; border-radius: 50%; }
</style>
