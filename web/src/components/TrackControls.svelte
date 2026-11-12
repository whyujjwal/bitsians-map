<script lang="ts">
  import { onMount } from 'svelte';
  import { tracker, isApplied, shortDate, STATUS_LABEL, APPLIED_STATUSES, type TrackStatus } from '../lib/tracker.svelte';
  // `cta` renames the careers link; `quiet` makes it secondary when roles are already listed above it.
  let { id, name, careers = '', cta = 'View open roles', quiet = false }: { id: string; name: string; careers?: string; cta?: string; quiet?: boolean } = $props();
  onMount(() => tracker.init());
  const e = $derived(tracker.entries[id]);
  const applied = $derived(isApplied(e?.status));
  let note = $state('');
  $effect(() => { note = e?.note ?? ''; });
  const saveNote = () => { if ((e?.note ?? '') !== note.trim()) tracker.setNote(id, note.trim()); };
</script>

{#if careers}
  <a class="cta" class:quiet href={careers} target="_blank" rel="noopener noreferrer" onclick={() => { if (!applied) { tracker.pending = id; tracker.pendingRole = ''; } }}>{cta}</a>
{/if}
<div class="track" aria-label="Application tracker for {name}" role="group">
  {#if tracker.pending === id && !applied}
    <p class="tprompt">
      Applied to {tracker.pendingRole ? `${tracker.pendingRole} at ${name}` : name}?
      <button class="tlink" onclick={() => tracker.markApplied(id)}>Mark applied</button>
      <button class="tlink quiet" onclick={() => { tracker.pending = ''; tracker.pendingRole = ''; }}>Not yet</button>
    </p>
  {/if}

  {#if applied && e}
    <div class="tcard">
      <div class="thead">
        <span class="tstate">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 6 9 17l-5-5" /></svg>
          Applied{#if e.appliedAt}&nbsp;on {shortDate(e.appliedAt)}{/if}
        </span>
        <label class="tstatus">
          <span class="sr">Status</span>
          <select value={e.status} onchange={(ev) => tracker.setStatus(id, (ev.currentTarget as HTMLSelectElement).value as TrackStatus)}>
            {#each APPLIED_STATUSES as s}<option value={s}>{STATUS_LABEL[s]}</option>{/each}
          </select>
        </label>
      </div>
      <label class="tnote">
        <span class="sr">Note</span>
        <input type="text" maxlength="280" placeholder="Note, e.g. referred by a batchmate" bind:value={note} onblur={saveNote}
          onkeydown={(ev) => { if (ev.key === 'Enter') (ev.currentTarget as HTMLInputElement).blur(); }} />
      </label>
      <button class="tlink quiet tremove" onclick={() => tracker.remove(id)}>Remove from tracker</button>
    </div>
  {:else}
    <div class="tbtns">
      <button class="tbtn" aria-pressed={e?.status === 'saved'} onclick={() => tracker.toggleSaved(id)}>
        <svg viewBox="0 0 24 24" aria-hidden="true" class:fill={e?.status === 'saved'}><path d="M19 21l-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" /></svg>
        {e?.status === 'saved' ? 'Saved' : 'Save'}
      </button>
      <button class="tbtn" onclick={() => tracker.markApplied(id)}>
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 6 9 17l-5-5" /></svg>
        Mark applied
      </button>
      {#if e?.status === 'saved' && e.savedAt}<span class="tmeta">Saved {shortDate(e.savedAt)}</span>{/if}
    </div>
  {/if}
</div>
