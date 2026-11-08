<script lang="ts">
  import CheckList from './CheckList.svelte';
  let { label, options, selected, open, ontoggleopen, onclose, onpick, name }: {
    label: string; options: [string, number][]; selected: string[]; open: boolean;
    ontoggleopen: () => void; onclose: () => void; onpick: (v: string) => void; name?: (v: string) => string;
  } = $props();
  let btn: HTMLButtonElement;
  const id = 'pop-' + label.toLowerCase();

  function key(e: KeyboardEvent) {
    if (e.key === 'Escape' && open) { e.stopPropagation(); onclose(); btn.focus(); }
    else if (e.key === 'ArrowDown' && !open) { e.preventDefault(); ontoggleopen(); }
  }
  $effect(() => {
    if (open) queueMicrotask(() => document.querySelector<HTMLInputElement>(`#${id} input`)?.focus());
  });
</script>

<div class="chipwrap" data-pop onkeydown={key} role="presentation">
  <button
    bind:this={btn} class="chip" class:on={selected.length > 0} aria-expanded={open} aria-controls={id} aria-haspopup="true"
    onclick={ontoggleopen}
  >
    {label}{#if selected.length}<span class="cnt">{selected.length}</span>{/if}
    <svg class="car" viewBox="0 0 10 6" aria-hidden="true"><path d="M1 1l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
  </button>
  {#if open}
    <div class="pop" id={id}>
      <CheckList {options} {selected} ontoggle={onpick} label={label} {name} />
    </div>
  {/if}
</div>
