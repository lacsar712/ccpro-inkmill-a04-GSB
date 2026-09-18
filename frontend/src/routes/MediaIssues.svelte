<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '../lib/api';
  import type { MediaIssue, MediaStock, Mill, Workshop } from '../lib/types';

  let stocks: MediaStock[] = [];
  let issues: MediaIssue[] = [];
  let workshops: Workshop[] = [];
  let mills: Mill[] = [];
  let error = '';
  let ok = '';

  function nowLocal(): string {
    const d = new Date();
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    return d.toISOString().slice(0, 16);
  }

  let form = {
    workshopId: '',
    millId: '',
    mediaType: '',
    qtyKg: '',
    issuedAt: nowLocal(),
    operatorName: '',
  };

  async function load() {
    error = '';
    try {
      [stocks, issues, workshops, mills] = await Promise.all([
        api<MediaStock[]>('/media-stocks'),
        api<MediaIssue[]>('/media-issues'),
        api<Workshop[]>('/workshops'),
        api<Mill[]>('/mills'),
      ]);
      if (!form.workshopId && workshops[0]) form.workshopId = String(workshops[0].id);
    } catch (e) {
      error = e instanceof Error ? e.message : '加载失败';
    }
  }

  onMount(load);

  $: workshopMills = mills.filter((m) => String(m.workshopId) === form.workshopId);
  $: workshopStocks = stocks.filter((s) => String(s.workshopId) === form.workshopId);

  function onWorkshopChange() {
    form.millId = '';
    form.mediaType = '';
  }

  function workshopName(id: number): string {
    return workshops.find((w) => w.id === id)?.name || `#${id}`;
  }

  function millLabel(id: number | null): string {
    if (id == null) return '—';
    const m = mills.find((x) => x.id === id);
    return m ? `${m.millCode} (#${m.id})` : `#${id}`;
  }

  function onHandOf(mediaType: string): number {
    return workshopStocks.find((s) => s.mediaType === mediaType)?.onHandKg ?? 0;
  }

  async function save() {
    error = '';
    ok = '';
    const payload = {
      workshopId: Number(form.workshopId),
      millId: form.millId ? Number(form.millId) : null,
      mediaType: form.mediaType,
      qtyKg: Number(form.qtyKg),
      issuedAt: form.issuedAt,
      operatorName: form.operatorName,
    };
    try {
      await api('/media-issues', { method: 'POST', body: JSON.stringify(payload) });
      ok = `发料成功：${form.mediaType} ${form.qtyKg} kg`;
      form.qtyKg = '';
      form.operatorName = '';
      form.issuedAt = nowLocal();
      await load();
    } catch (e) {
      error = e instanceof Error ? e.message : '发料失败';
    }
  }
</script>

<header class="page-head">
  <h1>耗材领用</h1>
  <p>研磨珠按车间建库存行，发料即时扣减结存；库存不足返回 409，不允许负库存</p>
</header>

{#if error}
  <div class="err">{error}</div>
{/if}
{#if ok}
  <div class="ok">{ok}</div>
{/if}

<section class="panel">
  <h2>库存结存（kg）</h2>
  <table class="data-table">
    <thead>
      <tr>
        <th>ID</th>
        <th>车间</th>
        <th>研磨介质</th>
        <th>结存(kg)</th>
      </tr>
    </thead>
    <tbody>
      {#each stocks as row}
        <tr class:low={row.onHandKg <= 10}>
          <td>{row.id}</td>
          <td>{workshopName(row.workshopId)}</td>
          <td>{row.mediaType}</td>
          <td class="num">{row.onHandKg}</td>
        </tr>
      {:else}
        <tr><td colspan="4">暂无库存</td></tr>
      {/each}
    </tbody>
  </table>
</section>

<section class="panel">
  <h2>发料登记</h2>
  <div class="fields">
    <div class="field">
      <label>车间
        <select bind:value={form.workshopId} on:change={onWorkshopChange}>
          {#each workshops as w}
            <option value={String(w.id)}>{w.name}</option>
          {/each}
        </select>
      </label>
    </div>
    <div class="field">
      <label>研磨机（可空）
        <select bind:value={form.millId}>
          <option value="">不指定磨机</option>
          {#each workshopMills as m}
            <option value={String(m.id)}>{m.millCode}</option>
          {/each}
        </select>
      </label>
    </div>
    <div class="field">
      <label>研磨介质
        <select bind:value={form.mediaType}>
          <option value="" disabled>请选择</option>
          {#each workshopStocks as s}
            <option value={s.mediaType}>{s.mediaType}（结存 {s.onHandKg} kg）</option>
          {/each}
        </select>
      </label>
    </div>
    <div class="field">
      <label>发料重量(kg)
        <input type="number" min="0.01" step="0.01" bind:value={form.qtyKg} />
      </label>
    </div>
    <div class="field"><label>发料时间<input type="datetime-local" bind:value={form.issuedAt} /></label></div>
    <div class="field"><label>操作员<input bind:value={form.operatorName} /></label></div>
  </div>
  {#if form.mediaType}
    <p class="hint">当前结存：<strong>{onHandOf(form.mediaType)} kg</strong></p>
  {/if}
  <div class="actions">
    <button class="btn-primary" on:click={save}>确认发料</button>
  </div>
</section>

<section class="panel">
  <h2>发料记录</h2>
  <table class="data-table">
    <thead>
      <tr>
        <th>ID</th>
        <th>车间</th>
        <th>研磨机</th>
        <th>研磨介质</th>
        <th>数量(kg)</th>
        <th>发料时间</th>
        <th>操作员</th>
      </tr>
    </thead>
    <tbody>
      {#each issues as row}
        <tr>
          <td>{row.id}</td>
          <td>{workshopName(row.workshopId)}</td>
          <td>{millLabel(row.millId)}</td>
          <td>{row.mediaType}</td>
          <td class="num">{row.qtyKg}</td>
          <td>{row.issuedAt}</td>
          <td>{row.operatorName}</td>
        </tr>
      {:else}
        <tr><td colspan="7">暂无发料记录</td></tr>
      {/each}
    </tbody>
  </table>
</section>

<style>
  .num {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  tr.low td.num {
    color: var(--vermillion-400);
    font-weight: 600;
  }

  .ok {
    border: 1px solid rgba(46, 204, 113, 0.4);
    background: rgba(46, 204, 113, 0.08);
    color: #2ecc71;
    padding: 0.6rem 0.85rem;
    margin-bottom: 1rem;
    border-radius: 2px;
  }

  .hint {
    margin: 0.6rem 0 0;
    font-size: 0.85rem;
    color: var(--steel);
  }
</style>
