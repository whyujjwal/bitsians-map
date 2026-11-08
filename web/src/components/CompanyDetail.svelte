<script lang="ts">
  import Tile from './Tile.svelte';
  import { isInactive, type Prepared } from '../lib/data';
  let { c, onback, backref = $bindable() }: { c: Prepared; onback: () => void; backref?: HTMLButtonElement } = $props();
  const place = $derived([c.city, c.country].filter(Boolean).join(', '));
  const status = $derived(isInactive(c.status) ? c.status[0].toUpperCase() + c.status.slice(1) : '');
  const host = (u: string) => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch { return u; } };
</script>

<div class="dhead">
  <button class="back" bind:this={backref} onclick={onback}>
    <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M10 3 5 8l5 5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
    All companies
  </button>
  <button class="x" aria-label="Close" onclick={onback}>
    <svg viewBox="0 0 16 16" aria-hidden="true"><path d="m4 4 8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
  </button>
</div>
<div class="dbody">
  <div class="dtitle">
    <Tile name={c.name} kind={c.kind} size="lg" logo={c.logo} logoDark={c.logoDark} />
    <h2>{c.name}</h2>
  </div>
  {#if c.oneLine}<p class="done">{c.oneLine}</p>{/if}
  <p class="facts">
    {#if c.stage}<span>{c.stage}</span>{/if}
    {#if c.sector}<span>{c.sector}</span>{/if}
    {#if place}<span>{place}</span>{/if}
    {#if c.founded}<span>Founded {c.founded}</span>{/if}
    {#if status}<span class="st">{status}</span>{/if}
  </p>
  {#if c.careers}
    <a class="cta" href={c.careers} target="_blank" rel="noopener noreferrer">View open roles</a>
  {/if}
  <p class="links">
    {#if c.website}<a href={c.website} target="_blank" rel="noopener noreferrer">Website <span class="sr">({host(c.website)})</span></a>{/if}
    <a href={'/c/' + c.id}>Full page</a>
  </p>
  {#if c.founders.length}
    <h3>Founders</h3>
    <ul class="founders">
      {#each c.founders as f}
        <li>
          <span class="fname">{f.name}</span>
          <span class="frole">{f.role}{#if f.campus || f.gradYear}<span class="fcy">{[f.campus, f.gradYear].filter(Boolean).join(', ')}</span>{/if}</span>
        </li>
      {/each}
    </ul>
  {/if}
</div>
