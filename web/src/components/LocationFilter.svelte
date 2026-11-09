<script lang="ts">
  import CheckList from './CheckList.svelte';
  export interface LocGroup { label: string; options: [string, number][]; selected: string[]; onpick: (v: string) => void }
  let { groups, open, ontoggleopen, onclose }: {
    groups: LocGroup[]; open: boolean; ontoggleopen: () => void; onclose: () => void;
  } = $props();
  let btn: HTMLButtonElement;
  const count = $derived(groups.reduce((n, g) => n + g.selected.length, 0));

  function key(e: KeyboardEvent) {
    if (e.key === 'Escape' && open) { e.stopPropagation(); onclose(); btn.focus(); }
    else if (e.key === 'ArrowDown' && !open) { e.preventDefault(); ontoggleopen(); }
  }
  $effect(() => {
    if (open) queueMicrotask(() => document.querySelector<HTMLInputElement>('#pop-location input')?.focus());
  });
</script>

<div class="chipwrap" data-pop onkeydown={key} role="presentation">
  <button bind:this={btn} class="chip" class:on={count > 0} aria-expanded={open} aria-controls="pop-location" aria-haspopup="true" onclick={ontoggleopen}>
    Location{#if count}<span class="cnt">{count}</span>{/if}
    <svg class="car" viewBox="0 0 10 6" aria-hidden="true"><path d="M1 1l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
  </button>
  {#if open}
    <div class="pop locpop" id="pop-location">
      {#each groups as g (g.label)}
        {#if g.options.length}
          <h3 class="pophd">{g.label}</h3>
          <CheckList options={g.options} selected={g.selected} ontoggle={g.onpick} label={g.label} />
        {/if}
      {/each}
    </div>
  {/if}
</div>
