<script lang="ts">
  // Founders by BITS batch: one square per founder, stacked on their batch year. Green squares are
  // founders whose company is hiring. The decade buttons under the plot filter the company list;
  // the squares themselves are a pointer convenience (the same people are in the list below).
  import { batchTag, decadeOf, decadeLabel, type Prepared } from '../lib/data';
  let { all, selected = [], onpick, onopen }: {
    all: Prepared[]; selected?: string[]; onpick: (decade: string) => void; onopen: (id: string) => void;
  } = $props();

  interface Dot { name: string; tag: string; id: string; company: string; hiring: boolean }
  const byYear = new Map<number, Dot[]>();
  for (const c of all) {
    for (const f of c.founders) {
      if (!decadeOf(f.gradYear)) continue;
      const y = +f.gradYear;
      if (!byYear.has(y)) byYear.set(y, []);
      byYear.get(y)!.push({ name: f.name, tag: batchTag(f).text, id: c.id, company: c.name, hiring: c.hiring });
    }
  }
  const years = [...byYear.keys()];
  const first = Math.floor(Math.min(...years) / 10) * 10;
  const last = Math.max(...years);
  // Hiring founders sit at the bottom of each stack, so the green reads as one band along the baseline.
  const cols: Dot[][] = Array.from({ length: last - first + 1 }, (_, i) =>
    (byYear.get(first + i) ?? []).sort((a, b) => +b.hiring - +a.hiring));
  const rows = Math.max(...cols.map((c) => c.length));
  const total = cols.reduce((n, c) => n + c.length, 0);
  const decades = Array.from({ length: Math.floor((last - first) / 10) + 1 }, (_, i) => {
    const from = first + i * 10;
    const span = Math.min(from + 9, last) - from + 1;
    const dots = cols.slice(from - first, from - first + span).flat();
    return { key: String(from), span, n: dots.length, hiring: dots.filter((d) => d.hiring).length };
  });

  // Raw, so the hovered square can be found by identity (a $state proxy would never equal it).
  let hover = $state.raw<Dot | null>(null);
  let touch = false;
  function at(e: PointerEvent | MouseEvent): Dot | null {
    const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const u = r.width / cols.length;
    const x = Math.floor((e.clientX - r.left) / u);
    // The pointer only has to be near a stack: try its own column, then the neighbours.
    for (const i of [x, x - 1, x + 1]) {
      const col = cols[i];
      if (!col?.length) continue;
      return col[Math.max(0, Math.min(col.length - 1, Math.floor((r.bottom - e.clientY) / u)))];
    }
    return null;
  }
  const move = (e: PointerEvent) => { touch = e.pointerType === 'touch'; hover = at(e); };
  const leave = () => { if (!touch) hover = null; };
  // A mouse click opens the company; a tap only picks the square, and the readout offers the company.
  const click = (e: MouseEvent) => { const d = at(e); hover = d; if (d && !touch) onopen(d.id); };
</script>

<section class="bchart" aria-labelledby="bc-h">
  <div class="bc-head">
    <h2 id="bc-h">Founders by BITS batch</h2>
    <ul class="bc-legend">
      <li><i class="sq hire" aria-hidden="true"></i>Hiring now</li>
      <li><i class="sq" aria-hidden="true"></i>Not hiring</li>
    </ul>
  </div>
  <p class="bc-read">
    {#if hover}
      <span class="bc-who"><b>{hover.name}</b> <span class="batch">{hover.tag}</span></span>
      <button class="bc-co" onclick={() => onopen(hover!.id)}>{hover.company}{#if hover.hiring}<span class="hirepill">Hiring</span>{/if}</button>
    {:else}
      Each square is a founder, placed at their batch. {total} founders have a known batch.
    {/if}
  </p>
  <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
  <div class="bc-plot" aria-hidden="true" style:--cols={cols.length} style:--rows={rows}
    onpointermove={move} onpointerdown={move} onpointerleave={leave} onclick={click}>
    {#each cols as col, i}
      <div class="bc-col" class:dim={selected.length > 0 && !selected.includes(decadeOf(String(first + i)))} style:--i={i}>
        {#each col as d}<i class="sq" class:hire={d.hiring} class:on={d === hover}></i>{/each}
      </div>
    {/each}
  </div>
  <div class="bc-axis">
    {#each decades as d (d.key)}
      <button style:flex-grow={d.span} aria-pressed={selected.includes(d.key)}
        aria-label="{decadeLabel(d.key)}: {d.n} {d.n === 1 ? 'founder' : 'founders'}, {d.hiring} at companies that are hiring. Show their companies"
        title="{d.n} {d.n === 1 ? 'founder' : 'founders'}, {d.hiring} hiring"
        onclick={() => onpick(d.key)}>&rsquo;{d.key.slice(2)}s</button>
    {/each}
  </div>
</section>
