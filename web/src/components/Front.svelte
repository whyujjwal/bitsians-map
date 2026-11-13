<script lang="ts">
  // The front page: open roles and the company register. The map lives at /map (App.svelte).
  import { onMount, tick } from 'svelte';
  import BatchChart from './BatchChart.svelte';
  import RoleGroups from './RoleGroups.svelte';
  import CompanyLine from './CompanyLine.svelte';
  import CompanyDetail from './CompanyDetail.svelte';
  import FilterChip from './FilterChip.svelte';
  import LocationFilter from './LocationFilter.svelte';
  import CheckList from './CheckList.svelte';
  import Tile from './Tile.svelte';
  import {
    prepare, applyFilters, emptyFilters, readUrl, filterParams, sortItems, sortSectors, sortStages,
    stageLabel, decadeLabel, SORTS, fixUrl, ROLES_FETCHED_AT, ALUMNI_FORM_URL,
    type Company, type Filters, type Prepared, type Sort,
  } from '../lib/data';
  import { loadAllJobs, inIndia, isRemote, type CompanyJobs, type Job, type RoleGroup } from '../lib/jobs';
  import { tracker, shortDate } from '../lib/tracker.svelte';
  import raw from '../data/index-data.json';

  // `preview` holds the first few roles per company, so the list is in the page before the full
  // role lists (their own chunk) arrive.
  let { preview = {} }: { preview?: Record<string, Job[]> } = $props();

  const all = prepare(raw as unknown as Company[]);
  const byId = new Map(all.map((c) => [c.id, c]));
  const count = (get: (c: Prepared) => string[]) => {
    const m = new Map<string, number>();
    for (const c of all) for (const k of get(c)) if (k) m.set(k, (m.get(k) ?? 0) + 1);
    return m;
  };
  const byCount = (m: Map<string, number>) => [...m].sort((a, b) => (a[0] === 'Unknown' ? 1 : 0) - (b[0] === 'Unknown' ? 1 : 0) || b[1] - a[1] || a[0].localeCompare(b[0]));
  const sectors = sortSectors([...count((c) => [c.sector])]);
  const stages = sortStages([...count((c) => [c.stage || 'none'])]);
  const campusCounts = count((c) => c.campuses);
  const campuses: [string, number][] = ['Pilani', 'Goa', 'Hyderabad', 'Dubai']
    .filter((k) => campusCounts.has(k)).map((k) => [k, campusCounts.get(k)!]);
  const batches = [...count((c) => c.decades)].sort((a, b) => b[0].localeCompare(a[0]));
  const cities = byCount(count((c) => [c.city]));
  const continents = byCount(count((c) => [c.continent || 'Unknown']));
  const countries = byCount(count((c) => [c.country || 'Unknown']));
  const states = byCount(count((c) => [c.state]));
  const hiringTotal = all.filter((c) => c.hiring).length;
  // Companies whose roles are listed here (none once the role data is too old to show).
  const withRoles = all.filter((c) => c.roles);
  const rolesTotal = withRoles.reduce((n, c) => n + (c.roles ?? 0), 0);
  const careersOnly = all.filter((c) => c.hiring && !c.roles);
  const fmt = (n: number) => n.toLocaleString('en-US');
  const plural = (n: number, one: string, many: string) => `${fmt(n)} ${n === 1 ? one : many}`;

  type Tab = 'roles' | 'companies' | 'saved' | 'applied';
  const defaultTab: Tab = withRoles.length ? 'roles' : 'companies';
  const emptyRoleFilters = () => ({ india: false, remote: false, teams: [] as string[], at: [] as string[] });

  let f = $state<Filters>(emptyFilters());
  let sort = $state<Sort>('notable');
  let tab = $state<Tab>(defaultTab);
  let rf = $state(emptyRoleFilters());
  let selectedId = $state('');
  let openKey = $state('');
  let sheet = $state(false);
  let mounted = $state(false);
  let jobs = $state.raw<Record<string, CompanyJobs> | null>(null);
  let jobsFailed = $state(false);
  let searchEl: HTMLInputElement;
  let stageEl: HTMLElement;
  let backEl = $state<HTMLButtonElement>();

  const terms = $derived(f.q.toLowerCase().split(/\s+/).filter(Boolean));
  const companyFilters = $derived({ ...($state.snapshot(f) as Filters), unmapped: false, track: '' as const });

  // ---- Roles ----
  const index = $derived.by(() => {
    if (!jobs) return null;
    const out: Record<string, { job: Job; hay: string; india: boolean; remote: boolean }[]> = {};
    for (const c of withRoles) {
      out[c.id] = (jobs[c.id]?.jobs ?? []).map((job) => ({
        job, hay: `${job.title} ${job.team} ${job.location} ${c.name}`.toLowerCase(),
        india: inIndia(job.location), remote: isRemote(job.location),
      }));
    }
    return out;
  });
  const everyRole = $derived(index ? Object.values(index).flat() : []);
  const indiaTotal = $derived(everyRole.filter((r) => r.india).length);
  const remoteTotal = $derived(everyRole.filter((r) => r.remote).length);
  const teams = $derived.by(() => {
    const m = new Map<string, number>();
    for (const r of everyRole) if (r.job.team) m.set(r.job.team, (m.get(r.job.team) ?? 0) + 1);
    return [...m].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  });
  const atOptions: [string, number][] = withRoles.map((c): [string, number] => [c.id, c.roles ?? 0]).sort((a, b) => b[1] - a[1]);
  const roleFilterOn = $derived(rf.india || rf.remote || rf.teams.length > 0 || rf.at.length > 0);
  const filteringRoles = $derived(!!index && (roleFilterOn || terms.length > 0));
  const groups = $derived.by((): RoleGroup[] => {
    const out: RoleGroup[] = [];
    for (const c of withRoles) {
      if (!index) { out.push({ c, total: c.roles ?? 0, jobs: preview[c.id] ?? [], matched: c.roles ?? 0 }); continue; }
      if (rf.at.length && !rf.at.includes(c.id)) continue;
      const list = index[c.id].filter((r) =>
        (!rf.india || r.india) && (!rf.remote || r.remote) && (!rf.teams.length || rf.teams.includes(r.job.team))
        && terms.every((t) => r.hay.includes(t))).map((r) => r.job);
      if (list.length) out.push({ c, total: index[c.id].length, jobs: list, matched: list.length });
    }
    return out.sort((a, b) => b.matched - a.matched);
  });
  const roleCount = $derived(groups.reduce((n, g) => n + g.matched, 0));
  // Hiring companies whose roles can't be listed; shown under the roles unless a role filter is on.
  const more = $derived(roleFilterOn ? [] : careersOnly.filter((c) => terms.every((t) => c.hay.includes(t))));

  // ---- Companies ----
  const filtered = $derived(applyFilters(all, companyFilters));
  const sorted = $derived(sortItems(filtered, sort));
  const hiringCount = $derived(filtered.reduce((n, c) => n + (c.hiring ? 1 : 0), 0));
  const activeCount = $derived(f.sectors.length + f.stages.length + f.campuses.length + f.batches.length + f.cities.length + f.continents.length + f.countries.length + f.states.length);
  const companyFilterOn = $derived(activeCount > 0 || f.hiring);
  const tracked = $derived.by(() => {
    if (tab !== 'saved' && tab !== 'applied') return [];
    const view = tab;
    return all.filter((c) => tracker.matches(c.id, view) && terms.every((t) => c.hay.includes(t)))
      .sort((a, b) => (tracker.entries[b.id]?.updatedAt ?? '').localeCompare(tracker.entries[a.id]?.updatedAt ?? ''));
  });
  const selected = $derived(selectedId ? byId.get(selectedId) : undefined);
  const mapHref = $derived.by(() => {
    if (tab !== 'companies') return '/map';
    const s = filterParams(companyFilters, '', sort).toString();
    return '/map' + (s ? '?' + s : '');
  });

  function fetchJobs() {
    jobsFailed = false;
    loadAllJobs().then((j) => (jobs = j)).catch(() => (jobsFailed = true));
  }

  onMount(() => {
    tracker.init();
    const p = new URLSearchParams(location.search);
    const u = readUrl(location.search);
    f = { ...u.f, unmapped: false, track: '' };
    sort = u.sort;
    rf = {
      india: p.get('in') === 'india', remote: p.get('remote') === '1', teams: p.getAll('team'),
      at: (p.get('at') ?? '').split(',').filter((id) => byId.has(id)),
    };
    // An explicit tab wins; old links (/?track=saved, /?sector=Fintech) open the view they meant.
    const t = p.get('tab') ?? u.f.track;
    const hadCompanyFilter = u.f.hiring || [u.f.sectors, u.f.stages, u.f.campuses, u.f.batches, u.f.cities, u.f.continents, u.f.countries, u.f.states].some((a) => a.length);
    if (t === 'saved' || t === 'applied' || t === 'companies') tab = t;
    else if (t === 'roles' && withRoles.length) tab = 'roles';
    else if (hadCompanyFilter) tab = 'companies';
    if (u.selected && byId.has(u.selected)) selectedId = u.selected;
    mounted = true;
    if (withRoles.length) fetchJobs();
    // A link that asks for a view, filter or search (not just a company) lands on the list.
    if (location.search && !selectedId) tick().then(() => { if (stageEl.getBoundingClientRect().top > innerHeight * 0.55) stageEl.scrollIntoView({ block: 'start' }); });

    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (openKey) openKey = '';
        else if (sheet) sheet = false;
        else if (selectedId) back();
      } else if (e.key === '/' && !e.metaKey && !e.ctrlKey && !e.altKey) {
        if ((e.target as HTMLElement).closest('input, textarea, select, [contenteditable]')) return;
        e.preventDefault();
        searchEl?.focus();
      }
    };
    const onDown = (e: PointerEvent) => {
      if (openKey && !(e.target as Element).closest('[data-pop]')) openKey = '';
    };
    addEventListener('keydown', onKey);
    addEventListener('pointerdown', onDown);
    return () => {
      removeEventListener('keydown', onKey);
      removeEventListener('pointerdown', onDown);
    };
  });

  $effect(() => {
    const p = filterParams(companyFilters, selectedId, sort);
    if (tab !== defaultTab || companyFilterOn) p.set('tab', tab);
    if (rf.india) p.set('in', 'india');
    if (rf.remote) p.set('remote', '1');
    for (const t of rf.teams) p.append('team', t);
    if (rf.at.length) p.set('at', rf.at.join(','));
    const s = p.toString();
    if (mounted) history.replaceState(null, '', location.pathname + (s ? '?' + s : ''));
  });

  type ListKey = 'sectors' | 'stages' | 'campuses' | 'batches' | 'cities' | 'continents' | 'countries' | 'states';
  const toggle = (key: ListKey) => (v: string) => {
    f[key] = f[key].includes(v) ? f[key].filter((x) => x !== v) : [...f[key], v];
  };
  const toggleRole = (key: 'teams' | 'at') => (v: string) => {
    rf[key] = rf[key].includes(v) ? rf[key].filter((x) => x !== v) : [...rf[key], v];
  };
  const clearRoles = () => { rf = emptyRoleFilters(); f.q = ''; openKey = ''; };
  const clearCompanies = () => { f = emptyFilters(); openKey = ''; };
  const setOpen = (k: string) => (openKey = openKey === k ? '' : k);

  // Bring the list into view when it is off screen (or scrolled past its top).
  function toStage() {
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
    stageEl.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
  }
  const nudge = () => { if (stageEl.getBoundingClientRect().top > innerHeight * 0.55) toStage(); };
  async function show(t: Tab) {
    tab = t;
    openKey = '';
    await tick();
    const top = stageEl.getBoundingClientRect().top;
    if (top < 0 || top > innerHeight * 0.55) toStage();
  }
  const showHiring = () => { f.hiring = true; show('companies'); };
  const pickBatch = (d: string) => { toggle('batches')(d); show('companies'); };

  async function select(id: string) {
    selectedId = id;
    openKey = '';
    await tick();
    backEl?.focus({ preventScroll: true });
  }
  async function back() {
    const id = selectedId;
    selectedId = '';
    await tick();
    if (id) document.querySelector<HTMLElement>(`[data-rid="${CSS.escape(id)}"]`)?.focus({ preventScroll: true });
  }
  function openLink(e: MouseEvent, id: string) {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
    e.preventDefault();
    select(id);
  }

  $effect(() => { if (sheet) tick().then(() => document.querySelector<HTMLElement>('.fsheet button')?.focus()); });
</script>

{#snippet bookmark()}<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 21l-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" /></svg>{/snippet}
{#snippet check()}<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 6 9 17l-5-5" /></svg>{/snippet}

<div class="site" class:has-detail={!!selected}>
  <header class="sbar">
    <a class="brand" href="/" aria-label="BITSians Startup Map, home">
      <span class="logo" aria-hidden="true">B</span>
      <span class="wordmark">BITSians Startup Map</span>
    </a>
    <div class="search">
      <svg class="sic" viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
      <label class="sr" for="q">Search roles, companies, founders and cities</label>
      <input id="q" bind:this={searchEl} type="search" placeholder="Search roles, companies, founders" autocomplete="off" bind:value={f.q} oninput={nudge} />
      <kbd class="slash" aria-hidden="true">/</kbd>
    </div>
    <div class="sbar-nav">
      <a class="tpill" href={mapHref} aria-label="Map">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 6 6-2 6 2 6-2v14l-6 2-6-2-6 2z" /><path d="M9 4v14M15 6v14" /></svg>
        <span class="tl">Map</span>
      </a>
      <a class="tprimary" href={fixUrl()} target="_blank" rel="noopener noreferrer">Add a company</a>
    </div>
  </header>

  <div class="fwrap">
    <section class="hero">
      <div class="hero-text">
        <h1>Your seniors are hiring.</h1>
        <p class="lede">
          BITSians from Pilani, Goa, Hyderabad and Dubai have started
          <button onclick={() => show('companies')}>{fmt(all.length)} companies</button>.
          <button onclick={showHiring}>{hiringTotal} are hiring</button>{#if rolesTotal}<span class="needs-fresh">, with
            <button onclick={() => show('roles')}>{fmt(rolesTotal)} open roles</button> listed here</span>{/if}.
        </p>
      </div>
      <BatchChart {all} selected={f.batches} onpick={pickBatch} onopen={select} />
    </section>

    <main class="fstage" bind:this={stageEl}>
      <nav class="ftabs" aria-label="Views">
        {#if rolesTotal}
          <button class="ftab needs-fresh" aria-current={tab === 'roles' ? 'true' : undefined} onclick={() => show('roles')}>
            Roles <span class="n">{fmt(roleCount)}</span>
          </button>
        {/if}
        <button class="ftab" aria-current={tab === 'companies' ? 'true' : undefined} onclick={() => show('companies')}>
          Companies <span class="n">{fmt(filtered.length)}</span>
        </button>
        <button class="ftab push" aria-label="Saved: {tracker.savedCount}" aria-current={tab === 'saved' ? 'true' : undefined} onclick={() => show('saved')}>
          {@render bookmark()}<span class="tname">Saved</span> <span class="n">{tracker.savedCount}</span>
        </button>
        <button class="ftab" aria-label="Applied: {tracker.appliedCount}" aria-current={tab === 'applied' ? 'true' : undefined} onclick={() => show('applied')}>
          {@render check()}<span class="tname">Applied</span> <span class="n">{tracker.appliedCount}</span>
        </button>
      </nav>

      {#if tab === 'roles'}
        <div class="needs-fresh">
          <div class="chipbar">
            <button class="chip" class:on={rf.india} aria-pressed={rf.india} onclick={() => (rf.india = !rf.india)}>
              In India{#if index}<span class="cnt">{indiaTotal}</span>{/if}
            </button>
            <button class="chip" class:on={rf.remote} aria-pressed={rf.remote} onclick={() => (rf.remote = !rf.remote)}>
              Remote{#if index}<span class="cnt">{remoteTotal}</span>{/if}
            </button>
            <span class="desk chips">
              <FilterChip label="Team" options={teams} selected={rf.teams} open={openKey === 'team'} ontoggleopen={() => setOpen('team')} onclose={() => (openKey = '')} onpick={toggleRole('teams')} />
              <FilterChip label="Company" options={atOptions} selected={rf.at} open={openKey === 'company'} ontoggleopen={() => setOpen('company')} onclose={() => (openKey = '')} onpick={toggleRole('at')} name={(id) => byId.get(id)?.name ?? id} />
            </span>
            <button class="chip mob" class:on={rf.teams.length + rf.at.length > 0} aria-haspopup="dialog" aria-expanded={sheet} onclick={() => (sheet = true)}>
              Filters{#if rf.teams.length + rf.at.length}<span class="cnt">{rf.teams.length + rf.at.length}</span>{/if}
            </button>
            {#if filteringRoles}<button class="textbtn clear" onclick={clearRoles}>Clear</button>{/if}
          </div>
          <div class="fmeta">
            <span class="fsum" aria-live="polite">{plural(roleCount, 'role', 'roles')} at {plural(groups.length, 'company', 'companies')}</span>
            <span class="rsrc">From each company's job board, checked {shortDate(ROLES_FETCHED_AT)}</span>
          </div>
          {#if jobsFailed}
            <p class="rnote fnote">Couldn't load the full role lists. <button class="tlink" onclick={fetchJobs}>Try again</button></p>
          {/if}
          {#if groups.length}
            <RoleGroups {groups} filtering={filteringRoles} onopen={select} />
          {:else}
            <div class="empty">
              <p>No open roles match{#if f.q}&nbsp;&ldquo;{f.q}&rdquo;{/if}{#if roleFilterOn}{f.q ? ' with' : ''} these filters{/if}</p>
              <div class="empty-acts">
                <button class="btn" onclick={clearRoles}>Clear {f.q && !roleFilterOn ? 'search' : 'filters'}</button>
                {#if f.q && filtered.length}<button class="btn ghost" onclick={() => show('companies')}>Show {plural(filtered.length, 'matching company', 'matching companies')}</button>{/if}
              </div>
            </div>
          {/if}
          {#if more.length}
            <section class="more" aria-labelledby="more-h">
              <h2 id="more-h">{plural(more.length, 'more company is', 'more companies are')} hiring</h2>
              <p>Their job boards can't be read from here, so each one opens with a link to its careers page.</p>
              <ul class="morelist">
                {#each more as c (c.id)}
                  <li>
                    <a class="mchip" href={'/c/' + c.id} data-rid={c.id} onclick={(e) => openLink(e, c.id)}>
                      <Tile name={c.name} kind={c.kind} size="xs" logo={c.logo} logoDark={c.logoDark} />{c.name}
                    </a>
                  </li>
                {/each}
              </ul>
            </section>
          {/if}
        </div>
      {:else if tab === 'companies'}
        <div class="chipbar">
          <button class="chip hire" class:on={f.hiring} aria-pressed={f.hiring} onclick={() => (f.hiring = !f.hiring)}>
            <i class="dot" aria-hidden="true"></i>Hiring <span class="cnt">{hiringTotal}</span>
          </button>
          <span class="desk chips">
            <FilterChip label="Sector" options={sectors} selected={f.sectors} open={openKey === 'sector'} ontoggleopen={() => setOpen('sector')} onclose={() => (openKey = '')} onpick={toggle('sectors')} />
            <FilterChip label="Stage" options={stages} selected={f.stages} open={openKey === 'stage'} ontoggleopen={() => setOpen('stage')} onclose={() => (openKey = '')} onpick={toggle('stages')} name={stageLabel} />
            <FilterChip label="Campus" options={campuses} selected={f.campuses} open={openKey === 'campus'} ontoggleopen={() => setOpen('campus')} onclose={() => (openKey = '')} onpick={toggle('campuses')} />
            <FilterChip label="Batch" options={batches} selected={f.batches} open={openKey === 'batch'} ontoggleopen={() => setOpen('batch')} onclose={() => (openKey = '')} onpick={toggle('batches')} name={decadeLabel} />
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
          {#if companyFilterOn || f.q}<button class="textbtn clear" onclick={clearCompanies}>Clear</button>{/if}
        </div>
        <div class="fmeta">
          <span class="fsum" aria-live="polite">{plural(filtered.length, 'company', 'companies')}{#if hiringCount}, {fmt(hiringCount)} hiring{/if}</span>
          <span class="fmeta-r">
            <a href={mapHref}>See them on the map</a>
            <label class="sort">Sort
              <select bind:value={sort}>
                {#each SORTS as [v, l]}<option value={v}>{l}</option>{/each}
              </select>
            </label>
          </span>
        </div>
        {#if sorted.length}
          <ul class="clines">
            {#each sorted as c (c.id)}<CompanyLine {c} selected={c.id === selectedId} onselect={select} />{/each}
          </ul>
        {:else}
          <div class="empty">
            <p>No companies match{#if f.q}&nbsp;&ldquo;{f.q}&rdquo;{/if}{#if companyFilterOn}{f.q ? ' with' : ''} these filters{/if}</p>
            <div class="empty-acts">
              <button class="btn" onclick={clearCompanies}>Clear {f.q && !companyFilterOn ? 'search' : 'filters'}</button>
              {#if f.q && index && roleCount}<button class="btn ghost" onclick={() => show('roles')}>Show {plural(roleCount, 'matching role', 'matching roles')}</button>{/if}
            </div>
          </div>
        {/if}
      {:else}
        <div class="fmeta">
          <span class="fsum" aria-live="polite">{tab === 'saved' ? 'Saved companies' : 'Your applications'}, most recent first</span>
          <span class="rsrc">Kept in this browser only</span>
        </div>
        {#if tracked.length}
          <ul class="clines">
            {#each tracked as c (c.id)}<CompanyLine {c} selected={c.id === selectedId} onselect={select} note={tab === 'applied'} />{/each}
          </ul>
        {:else if f.q}
          <div class="empty">
            <p>Nothing {tab === 'saved' ? 'saved' : 'applied to'} matches &ldquo;{f.q}&rdquo;</p>
            <button class="btn" onclick={() => (f.q = '')}>Clear search</button>
          </div>
        {:else}
          <div class="empty">
            <p>{tab === 'saved'
              ? 'Nothing saved yet. Open a company and press Save to keep it here.'
              : 'No applications yet. Open a role, apply, then come back and mark it applied.'}</p>
            <button class="btn" onclick={() => show(tab === 'saved' ? 'companies' : defaultTab)}>{tab === 'saved' || !withRoles.length ? 'Browse companies' : 'Browse roles'}</button>
          </div>
        {/if}
      {/if}
    </main>

    <footer class="ffoot">
      <div>
        <h2>Looking for a role</h2>
        <p>Search roles by title, team or city, or browse companies by sector, campus and batch. Save the ones you like and mark the ones you apply to. Your list stays in this browser, with no account.</p>
      </div>
      <div>
        <h2>You founded one of these</h2>
        <p>Your company has its own page with your open roles. Share it when you're hiring, and tell us if anything is wrong or missing.</p>
        <p class="flinks">
          <button onclick={() => { searchEl.focus(); scrollTo({ top: 0 }); }}>Find your company</button>
          <a href={fixUrl()} target="_blank" rel="noopener noreferrer">Add a company</a>
        </p>
      </div>
      <div>
        <h2>Free for every BITSian, always</h2>
        <p>Companies and roles are public. Founders are listed from public sources, and every company page links to them. Independent community project, not affiliated with BITS Pilani.</p>
        <p class="flinks">
          {#if ALUMNI_FORM_URL}<a href={ALUMNI_FORM_URL} target="_blank" rel="noopener noreferrer">Would you refer a junior? Tell us</a>{/if}
          <a href="https://github.com/whyujjwal/bitsians-map" target="_blank" rel="noopener noreferrer">Source on GitHub</a>
        </p>
      </div>
    </footer>
  </div>

  {#if selected}
    <button class="fscrim" tabindex="-1" aria-label="Close {selected.name}" onclick={back}></button>
    <section class="fdetail" aria-label={selected.name}>
      {#key selected.id}
        <CompanyDetail c={selected} onback={back} bind:backref={backEl} backLabel="Back to the list" onmap />
      {/key}
    </section>
  {/if}

  {#if sheet}
    <button class="scrim" tabindex="-1" aria-label="Close filters" onclick={() => (sheet = false)}></button>
    <div class="fsheet" role="dialog" aria-modal="true" aria-label="Filters">
      <div class="fshead">
        <h2>Filters</h2>
        <button class="textbtn" onclick={tab === 'roles' ? clearRoles : clearCompanies}>Clear</button>
        <button class="x" aria-label="Close filters" onclick={() => (sheet = false)}>
          <svg viewBox="0 0 16 16" aria-hidden="true"><path d="m4 4 8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
        </button>
      </div>
      <div class="fsbody">
        {#if tab === 'roles'}
          <h3>Company</h3><CheckList label="Company" options={atOptions} selected={rf.at} ontoggle={toggleRole('at')} name={(id) => byId.get(id)?.name ?? id} />
          <h3>Team</h3><CheckList label="Team" options={teams} selected={rf.teams} ontoggle={toggleRole('teams')} />
        {:else}
          <h3>Sector</h3><CheckList label="Sector" options={sectors} selected={f.sectors} ontoggle={toggle('sectors')} />
          <h3>Stage</h3><CheckList label="Stage" options={stages} selected={f.stages} ontoggle={toggle('stages')} name={stageLabel} />
          <h3>Campus</h3><CheckList label="Campus" options={campuses} selected={f.campuses} ontoggle={toggle('campuses')} />
          <h3>Batch</h3><CheckList label="Batch" options={batches} selected={f.batches} ontoggle={toggle('batches')} name={decadeLabel} />
          <h3>Continent</h3><CheckList label="Continent" options={continents} selected={f.continents} ontoggle={toggle('continents')} />
          <h3>Country</h3><CheckList label="Country" options={countries} selected={f.countries} ontoggle={toggle('countries')} />
          <h3>State</h3><CheckList label="State" options={states} selected={f.states} ontoggle={toggle('states')} />
          <h3>City</h3><CheckList label="City" options={cities} selected={f.cities} ontoggle={toggle('cities')} />
        {/if}
      </div>
      <div class="fsfoot">
        <button class="show" onclick={() => (sheet = false)}>
          Show {tab === 'roles' ? plural(roleCount, 'role', 'roles') : plural(filtered.length, 'company', 'companies')}
        </button>
      </div>
    </div>
  {/if}
</div>
