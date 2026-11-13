<script lang="ts">
  // Open roles on the front page, grouped under the company (and the founder) they belong to.
  import Tile from './Tile.svelte';
  import { batchTag } from '../lib/data';
  import { tracker, isApplied, STATUS_LABEL } from '../lib/tracker.svelte';
  import type { RoleGroup } from '../lib/jobs';
  let { groups, filtering, onopen }: { groups: RoleGroup[]; filtering: boolean; onopen: (id: string) => void } = $props();

  let expanded = $state<Record<string, boolean>>({});
  // The posting that was just opened: its row asks whether they applied.
  let pendingUrl = $state('');
  const limit = $derived(filtering ? 6 : 4);

  function opened(id: string, title: string, url: string) {
    if (isApplied(tracker.entries[id]?.status)) return;
    tracker.pending = id; tracker.pendingRole = title; pendingUrl = url;
  }
  const applied = (id: string) => { tracker.markApplied(id); pendingUrl = ''; };
  const notYet = () => { tracker.pending = ''; tracker.pendingRole = ''; pendingUrl = ''; };
</script>

<div class="rgroups">
  {#each groups as g (g.c.id)}
    {@const c = g.c}
    {@const t = tracker.entries[c.id]}
    {@const lead = c.founders.find((f) => batchTag(f).text) ?? c.founders[0]}
    {@const b = lead ? batchTag(lead) : null}
    {@const open = !!expanded[c.id]}
    {@const partial = filtering && g.matched !== g.total}
    <section class="rgroup" aria-label="Open roles at {c.name}">
      <div class="rg-head">
        <button class="rg-co" data-rid={c.id} onclick={() => onopen(c.id)}>
          <Tile name={c.name} kind={c.kind} logo={c.logo} logoDark={c.logoDark} />
          <span class="rg-id">
            <span class="rg-name">{c.name}</span>
            {#if lead}
              <span class="rg-by">
                {lead.name}{#if c.founders.length > 1}&nbsp;+{c.founders.length - 1}{/if}
                {#if b?.text}<span class="batch" title={b.title}>{b.text}</span>{/if}
              </span>
            {/if}
          </span>
        </button>
        {#if t}
          <span class="rtrack">
            {#if isApplied(t.status)}<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 6 9 17l-5-5" /></svg>
            {:else}<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 21l-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" /></svg>{/if}
            {STATUS_LABEL[t.status]}
          </span>
        {/if}
        <span class="rg-n">{partial ? `${g.matched} of ${g.total}` : g.total} {g.total === 1 ? 'role' : 'roles'}</span>
      </div>
      <ul class="rrows">
        {#each open ? g.jobs : g.jobs.slice(0, limit) as j, i (i + j.url)}
          <li>
            <a class="rrow" href={j.url} target="_blank" rel="noopener noreferrer" onclick={() => opened(c.id, j.title, j.url)}>
              <span class="rr-title">{j.title}</span>
              <span class="rr-team">{j.team}</span>
              <span class="rr-loc">{j.location}</span>
            </a>
            {#if pendingUrl === j.url && tracker.pending === c.id && !isApplied(t?.status)}
              <p class="tprompt">
                Applied to this role?
                <button class="tlink" onclick={() => applied(c.id)}>Mark applied</button>
                <button class="tlink quiet" onclick={notYet}>Not yet</button>
              </p>
            {/if}
          </li>
        {/each}
      </ul>
      {#if g.jobs.length > limit}
        <button class="tlink quiet rg-more" aria-expanded={open} onclick={() => (expanded[c.id] = !open)}>
          {open ? 'Show fewer' : `Show all ${g.matched} ${partial ? 'matching roles' : 'roles'}`}
        </button>
      {/if}
    </section>
  {/each}
</div>
