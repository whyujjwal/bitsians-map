<script lang="ts">
  import { initials, type TileKind } from '../lib/data';
  let { name, kind, size = 'sm', selected = false, logo = '', logoDark = false }: {
    name: string; kind: TileKind; size?: 'xs' | 'sm' | 'lg'; selected?: boolean; logo?: string; logoDark?: boolean;
  } = $props();
  let bad = $state(false);
  const px = $derived(size === 'lg' ? 48 : size === 'xs' ? 24 : 36);
  const inner = $derived(Math.round(px * 0.78));
</script>

{#if logo && !bad}
  <span class="tile logo {kind} t-{size}" class:dark={logoDark} class:selected aria-hidden="true">
    <img src={logo} alt="" width={inner} height={inner} loading="lazy" decoding="async" onerror={() => (bad = true)} />
  </span>
{:else}
  <span class="tile {kind} t-{size}" class:selected aria-hidden="true">{initials(name)}</span>
{/if}
