<script lang="ts">
  import Tile from './Tile.svelte';
  import { batchTag, type Prepared } from '../lib/data';
  import { tracker, isApplied, STATUS_LABEL } from '../lib/tracker.svelte';
  let { c, selected, onselect, onhover }: {
    c: Prepared; selected: boolean; onselect: (id: string) => void; onhover: (id: string) => void;
  } = $props();
  const names = $derived(c.founders.slice(0, 2).map((f) => f.name).join(', ') + (c.founders.length > 2 ? ` +${c.founders.length - 2}` : ''));
  const t = $derived(tracker.entries[c.id]);
  const batch = $derived.by(() => { for (const f of c.founders) { const b = batchTag(f); if (b.text) return b; } return null; });
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
        {#if t}
          <span class="rtrack" title={STATUS_LABEL[t.status]}>
            {#if isApplied(t.status)}<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 6 9 17l-5-5" /></svg>
            {:else}<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 21l-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" /></svg>{/if}
            {STATUS_LABEL[t.status]}
          </span>
        {/if}
        {#if c.stage}<span class="rstage">{c.stage}</span>{/if}
      </span>
      {#if c.oneLine}<span class="rone">{c.oneLine}</span>{/if}
      <span class="rmeta">
        {#if names}<span class="rfounders">{names}</span>{/if}
        {#if batch}<span class="batch" title={batch.title}>{batch.text}</span>{/if}
        {#if c.city}<span class="rcity">{c.city}</span>{/if}
      </span>
    </span>
  </button>
</li>
