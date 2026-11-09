<script lang="ts">
  import { onMount, tick, type Component } from 'svelte';
  import CompanyRow from './CompanyRow.svelte';
  import CompanyDetail from './CompanyDetail.svelte';
  import FilterChip from './FilterChip.svelte';
  import LocationFilter from './LocationFilter.svelte';
  import CheckList from './CheckList.svelte';
  import {
    prepare, applyFilters, emptyFilters, readUrl, writeUrl, sortItems, sortSectors, sortStages,
    stageLabel, SORTS, fixUrl,
    type Company, type Filters, type View, type Prepared, type Sort,
  } from '../lib/data';

  // Data ships inside this (hashed, long-cached) JS chunk instead of as island props:
  // Astro's prop serialization was ~2.4x the JSON size and slower to revive. Vite compiles
  // a JSON import this large to JSON.parse("..."), the fastest way to load it.
  import raw from '../data/index-data.json';
  import { tracker } from '../lib/tracker.svelte';

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
  const byCount = (m: Map<string, number>) => [...m].sort((a, b) => (a[0] === 'Unknown' ? 1 : 0) - (b[0] === 'Unknown' ? 1 : 0) || b[1] - a[1] || a[0].localeCompare(b[0]));
  const cities = byCount(count((c) => [c.city]));
  const continents = byCount(count((c) => [c.continent || 'Unknown']));
  const countries = byCount(count((c) => [c.country || 'Unknown']));
  const states = byCount(count((c) => [c.state]));
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
  let listOpen = $state(true);
  // Space the floating panels cover, so the map centres and fits companies in what is left.
  const inset = $derived(mobile
    ? { top: 72, right: 0, bottom: 72, left: 0 }
    : { top: 84, right: selected ? 444 : 0, bottom: 0, left: listOpen ? 404 : 0 });

  const filtered = $derived.by(() => {
    const snap = $state.snapshot(f) as Filters;
    const t = performance.now();
    let r = applyFilters(all, snap);
    if (snap.track) r = r.filter((c) => tracker.matches(c.id, snap.track));
    if (import.meta.env.DEV) console.debug(`[filter] ${r.length} results in ${(performance.now() - t).toFixed(3)} ms`);
    return r;
  });
  // The tracker views list the most recently updated company first.
  const sorted = $derived(f.track
    ? [...filtered].sort((a, b) => (tracker.entries[b.id]?.updatedAt ?? '').localeCompare(tracker.entries[a.id]?.updatedAt ?? ''))
    : sortItems(filtered, sort));
  // Server-render and hydrate only the first rows (fast first paint and hydration),
  // then render the rest once the browser is idle.
  let rowLimit = $state(36);
  const rows = $derived(sorted.length > rowLimit ? sorted.slice(0, rowLimit) : sorted);
  const hiringCount = $derived(filtered.reduce((n, c) => n + (c.hiring ? 1 : 0), 0));
  const offMap = $derived(filtered.reduce((n, c) => n + (c.pos ? 0 : 1), 0));
  const selected = $derived(selectedId ? byId.get(selectedId) : undefined);
  const activeCount = $derived(f.sectors.length + f.stages.length + f.campuses.length + f.cities.length + f.continents.length + f.countries.length + f.states.length);
  // The map refits to the results whenever the place filters change.
  const fitKey = $derived([f.continents, f.countries, f.states, f.cities, f.campuses].map((a) => a.join(',')).join('|'));
  const anyFilter = $derived(activeCount > 0 || f.hiring || f.unmapped || !!f.track || f.q !== '');
  const searchOnly = $derived(f.q !== '' && activeCount === 0 && !f.hiring && !f.unmapped && !f.track);
  // The hero collapses on first filter, search, selection or map interaction, and stays collapsed.
  $effect(() => { if (anyFilter || selectedId) collapsed = true; });

  function loadMap() {
    if (MapView || mapLoading) return;
    mapLoading = true;
    import('./Map.svelte').then((m) => (MapView = m.default));
  }

  onMount(() => {
    tracker.init();
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

  const toggle = (key: 'sectors' | 'stages' | 'campuses' | 'cities' | 'continents' | 'countries' | 'states') => (v: string) => {
    f[key] = f[key].includes(v) ? f[key].filter((x) => x !== v) : [...f[key], v];
  };
  const clearAll = () => { f = emptyFilters(); openKey = ''; };
  const showUnmapped = () => { f.unmapped = true; view = 'list'; collapsed = true; };
  const showTrack = (t: 'saved' | 'applied') => { f.track = f.track === t ? '' : t; if (f.track) { view = 'list'; listOpen = true; selectedId = ''; } collapsed = true; };
  const discover = () => { if (f.track) { f.track = ''; listOpen = true; } else listOpen = !listOpen; };
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

{#snippet bookmark()}<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 21l-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" /></svg>{/snippet}
{#snippet check()}<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 6 9 17l-5-5" /></svg>{/snippet}
{#snippet xmark()}<svg class="car" viewBox="0 0 10 10" aria-hidden="true"><path d="m2 2 6 6M8 2 2 8" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>{/snippet}

<div class="app" data-view={view} class:listclosed={!listOpen}>
  <nav class="rail" aria-label="Main">
    <a class="rmark" href="/" aria-label="BITSians Startup Map, home">B</a>
    <button class="rbtn" aria-pressed={listOpen && !f.track} onclick={discover}>
      <span class="ric"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="m15.5 8.5-2 5-5 2 2-5z" /></svg></span>
      Discover
    </button>
    <button class="rbtn" aria-pressed={f.track === 'saved'} onclick={() => showTrack('saved')}>
      <span class="ric">{@render bookmark()}{#if tracker.savedCount}<i class="badge">{tracker.savedCount}</i>{/if}</span>
      Saved
    </button>
    <button class="rbtn" aria-pressed={f.track === 'applied'} onclick={() => showTrack('applied')}>
      <span class="ric">{@render check()}{#if tracker.appliedCount}<i class="badge">{tracker.appliedCount}</i>{/if}</span>
      Applied
    </button>
    <button class="rbtn rabout" data-about aria-expanded={about} aria-controls="about" onclick={() => (about = !about)}>
      <span class="ric"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" /></svg></span>
      About
    </button>
  </nav>

  <div class="stage" style:--inset-t="{inset.top}px" style:--inset-r="{inset.right}px" style:--inset-b="{inset.bottom}px" style:--inset-l="{inset.left}px">
    <main class="mapwrap">
      {#if MapView}
        <MapView items={filtered} {all} {selectedId} {hoveredId} {inset} {fitKey} onselect={(id: string) => select(id)} oninteract={() => (collapsed = true)} oncampus={(n: string) => { collapsed = true; toggle('campuses')(n); }} />
      {:else}
        <div class="maploading" role="status">Loading map&hellip;</div>
      {/if}
    </main>

    <header class="top">
      <a class="brand" href="/" aria-label="BITSians Startup Map, home">
        <span class="logo" aria-hidden="true">B</span>
        <span class="wordmark">BITSians <span class="wm-long">Startup</span> Map</span>
      </a>
      <div class="search">
        <svg class="sic" viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
        <label class="sr" for="q">Search companies, founders, cities</label>
        <input id="q" bind:this={searchEl} type="search" placeholder="Search companies, founders, cities" autocomplete="off" bind:value={f.q} />
        <kbd class="slash" aria-hidden="true">/</kbd>
      </div>
      <div class="tactions">
        <button class="tpill" aria-pressed={f.track === 'saved'} onclick={() => showTrack('saved')}>
          {@render bookmark()}<span class="tl">Saved</span> <span class="n">{tracker.savedCount}</span>
        </button>
        <button class="tpill" aria-pressed={f.track === 'applied'} onclick={() => showTrack('applied')}>
          {@render check()}<span class="tl">Applied</span> <span class="n">{tracker.appliedCount}</span>
        </button>
        <a class="tprimary" href={fixUrl()} target="_blank" rel="noopener noreferrer">Add a company</a>
        <button class="tinfo" data-about aria-label="About" aria-expanded={about} aria-controls="about" onclick={() => (about = !about)}>
          <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" /></svg>
        </button>
      </div>
    </header>

    {#if about}
      <div class="aboutpop" id="about" data-about>
        <p>A map and directory of companies founded by BITS Pilani alumni across Pilani, Goa, Hyderabad and Dubai.</p>
        <p>Every listing links to the public source it came from. Spot a mistake or a missing company?</p>
        <p class="aboutlinks"><a href={fixUrl()} target="_blank" rel="noopener noreferrer">Add a company</a><a href="https://github.com/whyujjwal/bitsians-map" target="_blank" rel="noopener noreferrer">Source on GitHub</a></p>
        <p>Your saved and applied companies stay in this browser only.</p>
        <p>Independent community project, not affiliated with BITS Pilani.</p>
      </div>
    {/if}

    <aside class="panel" aria-label="Companies" hidden={!mobile && !listOpen}>
      <div class="phead">
        <h1 class="ptitle">{f.track === 'saved' ? 'Saved companies' : f.track === 'applied' ? 'Your applications' : 'Built by BITSians'}</h1>
        <p class="count" aria-live="polite">
          <b>{fmt(filtered.length)}</b> {filtered.length === 1 ? 'company' : 'companies'}{#if hiringCount}<span class="hc">{fmt(hiringCount)} hiring</span>{/if}
        </p>
      </div>
      <div class="chipbar">
        <button class="chip hire" class:on={f.hiring} aria-pressed={f.hiring} onclick={() => (f.hiring = !f.hiring)}>
          <i class="dot" aria-hidden="true"></i>Hiring <span class="cnt">{hiringTotal}</span>
        </button>
        {#if f.track}
          <button class="chip on" aria-pressed="true" onclick={() => (f.track = '')}>{f.track === 'saved' ? 'Saved' : 'Applied'}{@render xmark()}</button>
        {/if}
        {#if f.unmapped}
          <button class="chip on" aria-pressed="true" onclick={() => (f.unmapped = false)}>Not on the map{@render xmark()}</button>
        {/if}
        <span class="desk chips">
          <FilterChip label="Sector" options={sectors} selected={f.sectors} open={openKey === 'sector'} ontoggleopen={() => setOpen('sector')} onclose={() => (openKey = '')} onpick={toggle('sectors')} />
          <FilterChip label="Stage" options={stages} selected={f.stages} open={openKey === 'stage'} ontoggleopen={() => setOpen('stage')} onclose={() => (openKey = '')} onpick={toggle('stages')} name={stageLabel} />
          <FilterChip label="Campus" options={campuses} selected={f.campuses} open={openKey === 'campus'} ontoggleopen={() => setOpen('campus')} onclose={() => (openKey = '')} onpick={toggle('campuses')} />
          <LocationFilter open={openKey === 'location'} ontoggleopen={() => setOpen('location')} onclose={() => (openKey = '')} groups={[
            { label: 'Continent', options: continents, selected: f.continents, onpick: toggle('continents') },
            { label: 'Country', options: countries, selected: f.countries, onpick: toggle('countries') },
            { label: 'State', options: states, selected: f.states, onpick: toggle('states') },
            { label: 'City', options: cities, selected: f.cities, onpick: toggle('cities') },
          ]} />
        </span>
        <button class="chip mob" class:on={activeCount > 0} aria-haspopup="dialog" aria-expanded={sheet} onclick={() => (sheet = true)}>
          Filters{#if activeCount}<span class="cnt">{activeCount}</span>{/if}
        </button>
        {#if anyFilter}<button class="textbtn clear" onclick={clearAll}>Clear</button>{/if}
      </div>
      <div class="meta">
        {#if f.track}
          <span class="sort">Most recent first</span>
        {:else}
          <label class="sort">Sort
            <select bind:value={sort}>
              {#each SORTS as [v, l]}<option value={v}>{l}</option>{/each}
            </select>
          </label>
        {/if}
      </div>
      <div class="list">
        {#if sorted.length === 0}
          <div class="empty">
            {#if f.track && !f.q && activeCount === 0 && !f.hiring && !f.unmapped}
              <p>{f.track === 'saved'
                ? 'Nothing saved yet. Open a company and press Save to keep it here'
                : 'No applications yet. Open a company and press Mark applied to track it here'}</p>
              <button class="btn" onclick={() => (f.track = '')}>Browse all companies</button>
            {:else if searchOnly}
              <p>No companies, founders or cities match &ldquo;{f.q}&rdquo;</p>
              <button class="btn" onclick={() => (f.q = '')}>Clear search</button>
            {:else}
              <p>No companies match these filters</p>
              <button class="btn" onclick={clearAll}>Clear filters</button>
            {/if}
          </div>
        {:else}
          <ul class="rows">
            {#each rows as c (c.id)}
              <CompanyRow {c} selected={c.id === selectedId} onselect={select} onhover={(id) => (hoveredId = id)} />
            {/each}
          </ul>
        {/if}
      </div>
    </aside>

    {#if selected}
      <section class="detail" aria-label={selected.name} style:transform={dragY ? `translateY(${dragY}px)` : undefined} style:transition={dragY ? 'none' : undefined}>
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="grab" onpointerdown={dragDown} onpointermove={dragMove} onpointerup={dragUp} onpointercancel={dragUp}><i></i></div>
        {#key selected.id}
          <CompanyDetail c={selected} onback={back} bind:backref={backEl} />
        {/key}
      </section>
    {/if}

    <div class="mapfoot" class:hidden={!!selected && mobile}>
      <button class="fpill mob" onclick={() => (view = view === 'map' ? 'list' : 'map')}>
        {#if view === 'map'}
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16" /></svg>List
        {:else}
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 6 6-2 6 2 6-2v14l-6 2-6-2-6 2z" /><path d="M9 4v14M15 6v14" /></svg>Map
        {/if}
      </button>
      <span class="fpill stat desk">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 21V7l8-4 8 4v14" /><path d="M9 21v-6h6v6" /></svg>
        {fmt(filtered.length)} {filtered.length === 1 ? 'company' : 'companies'}
      </span>
      <button class="fpill" aria-pressed={f.hiring} onclick={() => (f.hiring = !f.hiring)}>
        <i class="dot" aria-hidden="true"></i>{fmt(hiringCount)} hiring
      </button>
      <button class="fpill mob icon" aria-pressed={f.track === 'saved'} aria-label="Saved companies: {tracker.savedCount}" onclick={() => showTrack('saved')}>{@render bookmark()}{tracker.savedCount}</button>
      <button class="fpill mob icon" aria-pressed={f.track === 'applied'} aria-label="Applied: {tracker.appliedCount}" onclick={() => showTrack('applied')}>{@render check()}{tracker.appliedCount}</button>
      {#if offMap > 0 && !f.unmapped}
        <button class="fpill desk" onclick={showUnmapped}>{fmt(offMap)} not on the map</button>
      {/if}
    </div>
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
        <h3>Continent</h3><CheckList label="Continent" options={continents} selected={f.continents} ontoggle={toggle('continents')} />
        <h3>Country</h3><CheckList label="Country" options={countries} selected={f.countries} ontoggle={toggle('countries')} />
        <h3>State</h3><CheckList label="State" options={states} selected={f.states} ontoggle={toggle('states')} />
        <h3>City</h3><CheckList label="City" options={cities} selected={f.cities} ontoggle={toggle('cities')} />
        {#if offMap > 0}
          <h3>Location</h3>
          <button class="chip" class:on={f.unmapped} aria-pressed={f.unmapped} onclick={() => (f.unmapped = !f.unmapped)}>Only the {fmt(offMap)} not on the map</button>
        {/if}
      </div>
      <div class="fsfoot">
        <button class="show" onclick={() => (sheet = false)}>Show {fmt(filtered.length)} {filtered.length === 1 ? 'company' : 'companies'}</button>
      </div>
    </div>
  {/if}
</div>
