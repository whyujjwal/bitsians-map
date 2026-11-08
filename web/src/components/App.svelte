<script lang="ts">
  import { onMount, tick, type Component } from 'svelte';
  import CompanyRow from './CompanyRow.svelte';
  import CompanyDetail from './CompanyDetail.svelte';
  import FilterChip from './FilterChip.svelte';
  import CheckList from './CheckList.svelte';
  import {
    prepare, applyFilters, emptyFilters, readUrl, writeUrl, sortItems, sortSectors, sortStages,
    stageLabel, SORTS,
    type Company, type Filters, type View, type Prepared, type Sort,
  } from '../lib/data';

  // Data ships inside this (hashed, long-cached) JS chunk instead of as island props:
  // Astro's prop serialization was ~2.4x the JSON size and slower to revive. Vite compiles
  // a JSON import this large to JSON.parse("..."), the fastest way to load it.
  import raw from '../data/index-data.json';

  const all = prepare(raw as unknown as Company[]);
  const byId = new Map(all.map((c) => [c.id, c]));
  const count = (get: (c: Prepared) => string[]) => {
    const m = new Map<string, number>();
    for (const c of all) for (const k of get(c)) if (k) m.set(k, (m.get(k) ?? 0) + 1);
    return m;
  };
  const sectors = sortSectors([...count((c) => [c.sector])]);
  const stages = sortStages([...count((c) => [c.stage || 'none'])]);
  const campusCounts = count((c) => c.campuses);
  const campuses: [string, number][] = ['Pilani', 'Goa', 'Hyderabad', 'Dubai']
    .filter((k) => campusCounts.has(k)).map((k) => [k, campusCounts.get(k)!]);
  const cities = [...count((c) => [c.city])].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  const hiringTotal = all.filter((c) => c.hiring).length;
  const fmt = (n: number) => n.toLocaleString('en-US');

  let f = $state<Filters>(emptyFilters());
  let sort = $state<Sort>('notable');
  let view = $state<View>('map');
  let selectedId = $state('');
  let hoveredId = $state('');
  let openKey = $state('');
  let sheet = $state(false);
  let about = $state(false);
  let mobile = $state(false);
  let mounted = $state(false);
  let MapView = $state.raw<Component<any> | null>(null);
  let mapLoading = false;
  let searchEl: HTMLInputElement;
  let backEl = $state<HTMLButtonElement>();
  let dragY = $state(0);
  let collapsed = $state(false);

  const filtered = $derived.by(() => {
    const snap = $state.snapshot(f) as Filters;
    const t = performance.now();
    const r = applyFilters(all, snap);
    if (import.meta.env.DEV) console.debug(`[filter] ${r.length} results in ${(performance.now() - t).toFixed(3)} ms`);
    return r;
  });
  const sorted = $derived(sortItems(filtered, sort));
  // Server-render and hydrate only the first rows (fast first paint and hydration),
  // then render the rest once the browser is idle.
  let rowLimit = $state(36);
  const rows = $derived(sorted.length > rowLimit ? sorted.slice(0, rowLimit) : sorted);
  const hiringCount = $derived(filtered.reduce((n, c) => n + (c.hiring ? 1 : 0), 0));
  const offMap = $derived(filtered.reduce((n, c) => n + (c.pos ? 0 : 1), 0));
  const selected = $derived(selectedId ? byId.get(selectedId) : undefined);
  const activeCount = $derived(f.sectors.length + f.stages.length + f.campuses.length + f.cities.length);
  const anyFilter = $derived(activeCount > 0 || f.hiring || f.q !== '');
  // The hero collapses on first filter, search, selection or map interaction, and stays collapsed.
  $effect(() => { if (anyFilter || selectedId) collapsed = true; });

  function loadMap() {
    if (MapView || mapLoading) return;
    mapLoading = true;
    import('./Map.svelte').then((m) => (MapView = m.default));
  }

  onMount(() => {
    const u = readUrl(location.search);
    f = u.f; sort = u.sort; view = u.view;
    if (u.selected && byId.has(u.selected)) { selectedId = u.selected; view = 'map'; }
    const mq = matchMedia('(max-width: 959px)');
    mobile = mq.matches;
    const onmq = () => (mobile = mq.matches);
    mq.addEventListener('change', onmq);
    mounted = true;
    loadMap();
    const idle = (window as any).requestIdleCallback ?? ((cb: () => void) => setTimeout(cb, 1));
    idle(() => (rowLimit = Infinity));

    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (openKey) openKey = '';
        else if (about) about = false;
        else if (sheet) sheet = false;
        else if (selectedId) back();
      } else if (e.key === '/' && !e.metaKey && !e.ctrlKey && !e.altKey) {
        const t = e.target as HTMLElement;
        if (t.closest('input, textarea, select, [contenteditable]')) return;
        e.preventDefault();
        searchEl?.focus();
      }
    };
    const onDown = (e: PointerEvent) => {
      const t = e.target as Element;
      if (openKey && !t.closest('[data-pop]')) openKey = '';
      if (about && !t.closest('[data-about]')) about = false;
    };
    addEventListener('keydown', onKey);
    addEventListener('pointerdown', onDown);
    return () => {
      removeEventListener('keydown', onKey);
      removeEventListener('pointerdown', onDown);
      mq.removeEventListener('change', onmq);
    };
  });

  $effect(() => {
    const url = writeUrl($state.snapshot(f) as Filters, view, selectedId, sort);
    if (mounted) history.replaceState(null, '', url);
  });

  const toggle = (key: 'sectors' | 'stages' | 'campuses' | 'cities') => (v: string) => {
    f[key] = f[key].includes(v) ? f[key].filter((x) => x !== v) : [...f[key], v];
  };
  const clearAll = () => { f = emptyFilters(); openKey = ''; };
  const setOpen = (k: string) => (openKey = openKey === k ? '' : k);

  async function select(id: string) {
    selectedId = id;
    if (mobile) view = 'map';
    openKey = '';
    await tick();
    if (!mobile) backEl?.focus({ preventScroll: true });
  }
  async function back() {
    const id = selectedId;
    selectedId = '';
    dragY = 0;
    await tick();
    if (!mobile && id) document.querySelector<HTMLElement>(`[data-rid="${CSS.escape(id)}"]`)?.focus({ preventScroll: true });
  }

  // Swipe-down to dismiss the mobile detail sheet from its handle.
  let dragStart = 0;
  const dragDown = (e: PointerEvent) => { dragStart = e.clientY; (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); };
  const dragMove = (e: PointerEvent) => { if (dragStart) dragY = Math.max(0, e.clientY - dragStart); };
  const dragUp = () => { const d = dragY; dragStart = 0; dragY = 0; if (d > 90) back(); };

  $effect(() => { if (sheet) tick().then(() => document.querySelector<HTMLElement>('.fsheet button')?.focus()); });
</script>

<div class="app" data-view={view}>
  <header class="top">
    <a class="brand" href="/" aria-label="BITSians Startup Map, home">
      <span class="logo" aria-hidden="true">B</span>
      <span class="wordmark">BITSians <span class="wm-long">Startup</span> Map</span>
    </a>
    <div class="search">
      <label class="sr" for="q">Search companies, founders, cities</label>
      <input id="q" bind:this={searchEl} type="search" placeholder="Search companies, founders, cities" autocomplete="off" bind:value={f.q} />
      <kbd class="slash" aria-hidden="true">/</kbd>
    </div>
    <div class="aboutwrap" data-about>
      <button class="textbtn" aria-expanded={about} aria-controls="about" onclick={() => (about = !about)}>About</button>
      {#if about}
        <div class="aboutpop" id="about">
          <p>A map and directory of companies founded by BITS Pilani alumni across Pilani, Goa, Hyderabad and Dubai.</p>
          <p>Independent community project, not affiliated with BITS Pilani.</p>
        </div>
      {/if}
    </div>
  </header>

  <div class="shell">
    <aside class="panel" aria-label="Companies">
      <div class="chipbar">
        <button class="chip hire" class:on={f.hiring} aria-pressed={f.hiring} onclick={() => (f.hiring = !f.hiring)}>
          Hiring <span class="cnt">{hiringTotal}</span>
        </button>
        <span class="desk chips">
          <FilterChip label="Sector" options={sectors} selected={f.sectors} open={openKey === 'sector'} ontoggleopen={() => setOpen('sector')} onclose={() => (openKey = '')} onpick={toggle('sectors')} />
          <FilterChip label="Stage" options={stages} selected={f.stages} open={openKey === 'stage'} ontoggleopen={() => setOpen('stage')} onclose={() => (openKey = '')} onpick={toggle('stages')} name={stageLabel} />
          <FilterChip label="Campus" options={campuses} selected={f.campuses} open={openKey === 'campus'} ontoggleopen={() => setOpen('campus')} onclose={() => (openKey = '')} onpick={toggle('campuses')} />
          <FilterChip label="City" options={cities} selected={f.cities} open={openKey === 'city'} ontoggleopen={() => setOpen('city')} onclose={() => (openKey = '')} onpick={toggle('cities')} />
        </span>
        <button class="chip mob" class:on={activeCount > 0} aria-haspopup="dialog" aria-expanded={sheet} onclick={() => (sheet = true)}>
          Filters{#if activeCount}<span class="cnt">{activeCount}</span>{/if}
        </button>
        {#if anyFilter}<button class="textbtn clear" onclick={clearAll}>Clear</button>{/if}
      </div>

      <div class="listpane">
        <div class="meta">
          <p class="count" aria-live="polite">
            <b>{fmt(filtered.length)}</b> {filtered.length === 1 ? 'company' : 'companies'}{#if hiringCount}<span class="hc">{fmt(hiringCount)} hiring</span>{/if}
          </p>
          <label class="sort">Sort
            <select bind:value={sort}>
              {#each SORTS as [v, l]}<option value={v}>{l}</option>{/each}
            </select>
          </label>
        </div>
        <div class="list">
          {#if sorted.length === 0}
            <div class="empty">
              <p>No companies match these filters.</p>
              <button class="btn" onclick={clearAll}>Clear filters</button>
            </div>
          {:else}
            <ul class="rows">
              {#each rows as c (c.id)}
                <CompanyRow {c} selected={c.id === selectedId} onselect={select} onhover={(id) => (hoveredId = id)} />
              {/each}
            </ul>
          {/if}
        </div>
      </div>

      {#if selected}
        <section class="detail" aria-label={selected.name} style:transform={dragY ? `translateY(${dragY}px)` : undefined} style:transition={dragY ? 'none' : undefined}>
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div class="grab" onpointerdown={dragDown} onpointermove={dragMove} onpointerup={dragUp} onpointercancel={dragUp}><i></i></div>
          {#key selected.id}
            <CompanyDetail c={selected} onback={back} bind:backref={backEl} />
          {/key}
        </section>
      {/if}
    </aside>

    <main class="mapwrap">
      {#if MapView}
        <MapView items={filtered} {all} {selectedId} {hoveredId} onselect={(id: string) => select(id)} oninteract={() => (collapsed = true)} oncampus={(n: string) => { collapsed = true; toggle('campuses')(n); }} />
      {:else}
        <div class="maploading" role="status">Loading map&hellip;</div>
      {/if}
      <div class="mapfoot">
        <section class="hero" class:gone={collapsed} aria-hidden={collapsed} inert={collapsed}>
          <h1>Built by BITSians.</h1>
          <p>
            <span class="n">{fmt(filtered.length)}</span> {filtered.length === 1 ? 'company' : 'companies'} started by alumni of Pilani, Goa, Hyderabad and Dubai.
            {#if hiringCount}<button class="hirebtn" onclick={() => (f.hiring = true)}>{fmt(hiringCount)} of them {hiringCount === 1 ? 'is' : 'are'} hiring</button>.{/if}
          </p>
        </section>
        {#if offMap > 0}
          <p class="offmap">{fmt(offMap)} of these aren't on the map yet</p>
        {/if}
      </div>
    </main>

    <button class="pill" class:hidden={!!selected && mobile} onclick={() => (view = view === 'map' ? 'list' : 'map')}>
      {#if view === 'map'}
        <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 4h12M2 8h12M2 12h12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
        List <span class="pn">{fmt(filtered.length)}</span>
      {:else}
        <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M1.5 3.5 6 2l4 1.5L14.5 2v10.5L10 14l-4-1.5L1.5 14z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>
        Map
      {/if}
    </button>
  </div>

  {#if sheet}
    <button class="scrim" tabindex="-1" aria-label="Close filters" onclick={() => (sheet = false)}></button>
    <div class="fsheet" role="dialog" aria-modal="true" aria-label="Filters">
      <div class="fshead">
        <h2>Filters</h2>
        <button class="textbtn" onclick={clearAll} disabled={!anyFilter}>Clear</button>
        <button class="x" aria-label="Close filters" onclick={() => (sheet = false)}>
          <svg viewBox="0 0 16 16" aria-hidden="true"><path d="m4 4 8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
        </button>
      </div>
      <div class="fsbody">
        <h3>Sector</h3><CheckList label="Sector" options={sectors} selected={f.sectors} ontoggle={toggle('sectors')} />
        <h3>Stage</h3><CheckList label="Stage" options={stages} selected={f.stages} ontoggle={toggle('stages')} name={stageLabel} />
        <h3>Campus</h3><CheckList label="Campus" options={campuses} selected={f.campuses} ontoggle={toggle('campuses')} />
        <h3>City</h3><CheckList label="City" options={cities} selected={f.cities} ontoggle={toggle('cities')} />
      </div>
      <div class="fsfoot">
        <button class="show" onclick={() => (sheet = false)}>Show {fmt(filtered.length)} {filtered.length === 1 ? 'company' : 'companies'}</button>
      </div>
    </div>
  {/if}
</div>
