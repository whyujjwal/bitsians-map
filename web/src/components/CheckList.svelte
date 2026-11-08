<script lang="ts">
  let { options, selected, ontoggle, label, name = (v: string) => v }: {
    options: [string, number][]; selected: string[]; ontoggle: (v: string) => void; label: string;
    name?: (v: string) => string;
  } = $props();

  function key(e: KeyboardEvent) {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp' && e.key !== 'Home' && e.key !== 'End') return;
    const boxes = [...(e.currentTarget as HTMLElement).querySelectorAll<HTMLInputElement>('input')];
    const i = boxes.indexOf(document.activeElement as HTMLInputElement);
    if (i < 0) return;
    e.preventDefault();
    const n = e.key === 'Home' ? 0 : e.key === 'End' ? boxes.length - 1 : Math.max(0, Math.min(boxes.length - 1, i + (e.key === 'ArrowDown' ? 1 : -1)));
    boxes[n].focus();
  }
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<ul class="checklist" role="group" aria-label={label} onkeydown={key}>
  {#each options as [v, n] (v)}
    <li>
      <label>
        <input type="checkbox" checked={selected.includes(v)} onchange={() => ontoggle(v)} />
        <span class="box" aria-hidden="true"></span>
        <span class="lbl">{name(v)}</span>
        <span class="n">{n}</span>
      </label>
    </li>
  {/each}
</ul>
