<script lang="ts">
  import { loadJobs, type CompanyJobs } from '../lib/jobs';
  import { ATS_NAME, ROLES_FETCHED_AT } from '../lib/data';
  import { tracker, shortDate } from '../lib/tracker.svelte';
  // `preload` is passed by the static company page; the map app loads the list on demand.
  let { id, preload }: { id: string; preload?: CompanyJobs } = $props();

  const FIRST = 6;
  let data = $state<CompanyJobs | undefined>(preload);
  let failed = $state(false);
  let all = $state(false);
  let q = $state('');

  function load() {
    failed = false;
    loadJobs(id).then((d) => { data = d; }).catch(() => { failed = true; });
  }
  $effect(() => {
    // Reset when another company is opened in the same panel.
    id; all = false; q = '';
    if (!preload) { data = undefined; load(); }
  });

  const jobs = $derived(data?.jobs ?? []);
  const terms = $derived(q.toLowerCase().split(/\s+/).filter(Boolean));
  const matched = $derived(terms.length
    ? jobs.filter((j) => { const h = `${j.title} ${j.team} ${j.location}`.toLowerCase(); return terms.every((t) => h.includes(t)); })
    : jobs);
  const shown = $derived(all || terms.length ? matched : matched.slice(0, FIRST));
  const where = $derived(data ? ATS_NAME[data.ats] ?? 'their job board' : '');
  const open = (title: string) => { tracker.pending = id; tracker.pendingRole = title; };
</script>

{#if failed}
  <p class="rnote">Couldn't load the roles. <button class="tlink" onclick={load}>Try again</button></p>
{:else if !data}
  <ul class="roles" aria-busy="true" aria-label="Loading roles">
    {#each { length: 3 } as _}<li class="rskel"><i></i><i></i></li>{/each}
  </ul>
{:else if !jobs.length}
  <p class="rnote">No open roles on their {where} board right now.</p>
{:else}
  {#if jobs.length > FIRST}
    <label class="rfilter">
      <span class="sr">Filter roles</span>
      <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
      <input type="search" placeholder="Filter by title, team or city" bind:value={q} autocomplete="off" />
    </label>
  {/if}
  {#if shown.length}
    <ul class="roles">
      {#each shown as j (j.url)}
        <li>
          <a href={j.url} target="_blank" rel="noopener noreferrer" onclick={() => open(j.title)}>
            <span class="rtitle">{j.title}</span>
            {#if j.team || j.location}<span class="rwhere">{[j.team, j.location].filter(Boolean).join(', ')}</span>{/if}
          </a>
        </li>
      {/each}
    </ul>
  {:else}
    <p class="rnote">No roles match “{q}”.</p>
  {/if}
  <div class="rfoot">
    {#if !all && !terms.length && jobs.length > FIRST}
      <button class="tlink" onclick={() => (all = true)}>Show all {jobs.length} roles</button>
    {:else if terms.length}
      <span>{matched.length} of {jobs.length} roles</span>
    {/if}
    <span class="rsrc">From {where}, checked {shortDate(ROLES_FETCHED_AT)}</span>
  </div>
{/if}
