<script lang="ts">
  import Tile from './Tile.svelte';
  import { isUnicornish, campusYear, type Prepared } from '../lib/data';
  let { c, selected, onselect, onhover }: {
    c: Prepared; selected: boolean; onselect: (id: string) => void; onhover: (id: string) => void;
  } = $props();
  const names = $derived(c.founders.slice(0, 2).map((f) => f.name).join(', ') + (c.founders.length > 2 ? ` +${c.founders.length - 2}` : ''));
  const cy = $derived.by(() => { for (const f of c.founders) { const s = campusYear(f); if (s) return s; } return ''; });
</script>

<li class="rowli">
  <button
    class="row" data-rid={c.id} class:selected aria-current={selected ? 'true' : undefined}
    onclick={() => onselect(c.id)} onpointerenter={() => onhover(c.id)} onpointerleave={() => onhover('')}
    onfocus={() => onhover(c.id)} onblur={() => onhover('')}
  >
    <Tile name={c.name} kind={c.kind} {selected} logo={c.logo} logoDark={c.logoDark} />
    <span class="rbody">
      <span class="rtop">
        <span class="rname">{c.name}</span>
        {#if c.hiring}<span class="hirepill">Hiring</span>{/if}
        {#if c.stage}<span class="rstage" class:peacock={isUnicornish(c.stage)}>{c.stage}</span>{/if}
      </span>
      {#if c.oneLine}<span class="rone">{c.oneLine}</span>{/if}
      <span class="rmeta">
        {#if names}<span class="rfounders">{names}</span>{/if}
        {#if cy}<span class="rcy">{cy}</span>{/if}
        {#if c.city}<span class="rcity">{c.city}</span>{/if}
      </span>
    </span>
  </button>
</li>
