<script lang="ts">
  import Tile from './Tile.svelte';
  import TrackControls from './TrackControls.svelte';
  import Roles from './Roles.svelte';
  import { isInactive, batchTag, sourceHost, fixUrl, roleBoard, referralFormUrl, ATS_NAME, type Prepared } from '../lib/data';
  // `backLabel` names where the back button returns to; `onmap` adds a "See it on the map" link (front page).
  let { c, onback, backref = $bindable(), backLabel = 'All companies', onmap = false }: {
    c: Prepared; onback: () => void; backref?: HTMLButtonElement; backLabel?: string; onmap?: boolean;
  } = $props();
  const referral = $derived(referralFormUrl(c.name));
  const place = $derived([c.city, c.country].filter(Boolean).join(', '));
  const status = $derived(isInactive(c.status) ? c.status[0].toUpperCase() + c.status.slice(1) : '');
  const facts = $derived(([
    ['stage', 'Stage', c.stage],
    ['sector', 'Sector', c.sector],
    ['place', 'Based in', place],
    ['founded', 'Founded', c.founded],
    ['status', 'Status', status],
  ] as const).filter(([, , v]) => v));
</script>

{#snippet icon(name: string)}
  <svg viewBox="0 0 24 24" aria-hidden="true">
    {#if name === 'stage'}<path d="M3 17l6-6 4 4 8-8" /><path d="M14 7h7v7" />
    {:else if name === 'sector'}<rect x="3" y="7" width="18" height="13" rx="2" /><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    {:else if name === 'place'}<path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z" /><circle cx="12" cy="10" r="2.5" />
    {:else if name === 'founded'}<rect x="3" y="5" width="18" height="16" rx="2" /><path d="M3 10h18M8 3v4M16 3v4" />
    {:else if name === 'status'}<circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" />
    {:else if name === 'about'}<path d="M4 6h16M4 12h16M4 18h10" />
    {:else if name === 'people'}<circle cx="9" cy="8" r="3.5" /><path d="M2.5 20a6.5 6.5 0 0 1 13 0" /><path d="M16 4.5a3.5 3.5 0 0 1 0 7M18 14a6.5 6.5 0 0 1 3.5 6" />
    {:else if name === 'roles'}<rect x="3" y="7" width="18" height="13" rx="2" /><path d="M3 13h18" />
    {:else if name === 'link'}<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1" /><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1" />
    {/if}
  </svg>
{/snippet}

{#if c.hiring}<p class="banner"><i class="dot" aria-hidden="true"></i>Hiring now{#if c.roles}, {c.roles} open {c.roles === 1 ? 'role' : 'roles'}{/if}</p>{/if}
<div class="dhead">
  <button class="back" bind:this={backref} onclick={onback}>
    <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M10 3 5 8l5 5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
    {backLabel}
  </button>
  <button class="x" aria-label="Close" onclick={onback}>
    <svg viewBox="0 0 16 16" aria-hidden="true"><path d="m4 4 8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
  </button>
</div>
<div class="dbody">
  <div class="dtitle">
    <Tile name={c.name} kind={c.kind} size="lg" logo={c.logo} logoDark={c.logoDark} />
    <div class="dname">
      <h2>{c.name}</h2>
      {#if c.website}<a class="dsite" href={c.website} target="_blank" rel="noopener noreferrer">{sourceHost(c.website)}</a>{/if}
    </div>
  </div>

  {#if c.oneLine}
    <div class="drow">
      {@render icon('about')}
      <p class="done">{c.oneLine}</p>
    </div>
  {/if}

  {#if facts.length}
    <dl class="dfacts">
      {#each facts as [k, label, v] (k)}
        <div class="drow">{@render icon(k)}<dt>{label}</dt><dd>{v}</dd></div>
      {/each}
    </dl>
  {/if}

  <section class="dsec" aria-labelledby="d-roles">
    <h3 id="d-roles" class="dlabel">{@render icon('roles')}{c.hiring || c.roles != null ? 'Open roles' : 'Track this company'}{c.roles ? ` (${c.roles})` : ''}</h3>
    <div class="dcard">
      {#if c.roles != null}<Roles id={c.id} />{/if}
      <TrackControls id={c.id} name={c.name} careers={c.jobsUrl}
        quiet={c.roles != null} cta={c.roles != null ? `See all on ${ATS_NAME[roleBoard(c.id)?.ats ?? ''] ?? 'their careers page'}` : 'View open roles'} />
    </div>
    {#if referral && c.hiring}
      <p class="refer">Want a BITSian here to refer you? Referrals aren't open yet. <a href={referral} target="_blank" rel="noopener noreferrer">Join the waitlist</a></p>
    {/if}
  </section>

  {#if c.founders.length}
    <section class="dsec" aria-labelledby="d-founders">
      <h3 id="d-founders" class="dlabel">{@render icon('people')}Founders ({c.founders.length})</h3>
      <ul class="founders">
        {#each c.founders as f}
          {@const b = batchTag(f)}
          <li>
            <span class="finit" aria-hidden="true">{f.name.split(/\s+/).map((w) => w[0]).slice(0, 2).join('')}</span>
            <span class="fwho"><span class="fname">{f.name}</span>{#if f.role}<span class="frole">{f.role}</span>{/if}</span>
            {#if b.text}<span class="batch" title={b.title}>{b.text}</span>{/if}
          </li>
        {/each}
      </ul>
    </section>
  {/if}

  {#if c.sources?.length}
    <section class="dsec" aria-labelledby="d-src">
      <h3 id="d-src" class="dlabel">{@render icon('link')}Sources</h3>
      <ul class="srcs">
        {#each c.sources as u}<li><a href={u} target="_blank" rel="noopener noreferrer">{sourceHost(u)}</a></li>{/each}
      </ul>
    </section>
  {/if}

  <p class="dfoot">
    <a href={'/c/' + c.id}>Open full page</a>
    {#if onmap && c.pos}<a href={'/map?c=' + encodeURIComponent(c.id)}>See it on the map</a>{/if}
    <a class="fix" href={fixUrl(c)} target="_blank" rel="noopener noreferrer">Suggest a fix</a>
  </p>
</div>
