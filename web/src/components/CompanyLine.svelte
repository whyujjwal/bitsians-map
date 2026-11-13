<script lang="ts">
  // One company in the front page register. A real link to the company page; a plain click opens
  // the company beside the list instead.
  import Tile from './Tile.svelte';
  import { batchTag, type Prepared } from '../lib/data';
  import { tracker, isApplied, STATUS_LABEL } from '../lib/tracker.svelte';
  let { c, selected, onselect, note = false }: {
    c: Prepared; selected: boolean; onselect: (id: string) => void; note?: boolean;
  } = $props();
  const names = $derived(c.founders.slice(0, 2).map((f) => f.name).join(', ') + (c.founders.length > 2 ? ` +${c.founders.length - 2}` : ''));
  const t = $derived(tracker.entries[c.id]);
  const batch = $derived.by(() => { for (const f of c.founders) { const b = batchTag(f); if (b.text) return b; } return null; });
  function click(e: MouseEvent) {
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
    e.preventDefault();
    onselect(c.id);
  }
</script>

<li class="rowli">
  <a class="cline" href={'/c/' + c.id} data-rid={c.id} class:selected aria-current={selected ? 'true' : undefined} onclick={click}>
    <Tile name={c.name} kind={c.kind} {selected} logo={c.logo} logoDark={c.logoDark} />
    <span class="cl-main">
      <span class="cl-top">
        <span class="cl-name">{c.name}</span>
        {#if c.hiring}<span class="hirepill">{c.roles ? `${c.roles} ${c.roles === 1 ? 'role' : 'roles'}` : 'Hiring'}</span>{/if}
        {#if t}
          <span class="rtrack">
            {#if isApplied(t.status)}<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 6 9 17l-5-5" /></svg>
            {:else}<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 21l-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" /></svg>{/if}
            {STATUS_LABEL[t.status]}
          </span>
        {/if}
      </span>
      {#if note && t?.note}<span class="cl-one cl-note">{t.note}</span>
      {:else if c.oneLine}<span class="cl-one">{c.oneLine}</span>{/if}
    </span>
    <span class="cl-meta">
      <span class="cl-by">
        {#if names}<span class="cl-names">{names}</span>{/if}
        {#if batch}<span class="batch" title={batch.title}>{batch.text}</span>{/if}
      </span>
      <span class="cl-kind">
        {#if c.sector && c.sector !== 'Other'}<span>{c.sector}</span>{/if}
        {#if c.stage}<span class="cl-stage">{c.stage}</span>{/if}
      </span>
      <span class="cl-place">{c.city || c.country}</span>
    </span>
  </a>
</li>
