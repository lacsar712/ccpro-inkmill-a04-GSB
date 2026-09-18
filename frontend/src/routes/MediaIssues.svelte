<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '../lib/api';
  import type { MediaIssue, MediaStock, Mill, Workshop } from '../lib/types';

  let stocks: MediaStock[] = [];
  let issues: MediaIssue[] = [];
  let workshops: Workshop[] = [];
  let mills: Mill[] = [];
  let error = '';
  let saving = false;

  function nowLocal(): string {
    const d = new Date();
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    return d.toISOString().slice(0, 16);
  }

  let form = {
    workshopId: '',
    mediaType: '',
    millId: '',
    qtyKg: '5',
    issuedAt: nowLocal(),
    operatorName: '',
  };

  async function load() {
    error = '';
    try {
      [stocks, issues, workshops, mills] = await Promise.all([
        api<MediaStock[]>('/media/stocks'),
        api<MediaIssue[]>('/media/issues'),
        api<Workshop[]>('/workshops'),
        api<Mill[]>('/mills'),
      ]);
      syncFormChoices();
    } catch (e) {
      error = e instanceof Error ? e.message : '加载失败';
    }
  }

  onMount(load);

  // 当前车间可选介质（来自该车间库存行）与磨机
  $: workshopStocks = stocks.filter((s) => String(s.workshopId) === form.workshopId);
  $: workshopMills = mills.filter((m) => String(m.workshopId) === form.workshopId);

  // 车间切换后，纠正已选介质 / 磨机，避免跨车间选项残留
  function stocksOf(workshopId: string) {
    return stocks.filter((s) => String(s.workshopId) === workshopId);
  }

  function syncFormChoices() {
    if (!form.workshopId && workshops[0]) form.workshopId = String(workshops[0].id);
    const list = stocksOf(form.workshopId);
    if (!list.some((s) => s.mediaType === form.mediaType)) {
      form.mediaType = list[0]?.mediaType ?? '';
    }
    if (form.millId && !workshopMills.some((m) => String(m.id) === form.millId)) {
      form.millId = '';
    }
  }

  function onWorkshopChange() {
    form.mediaType = stocksOf(form.workshopId)[0]?.mediaType ?? '';
    form.millId = '';
  }

  function workshopName(id: number): string {
    return workshops.find((w) => w.id === id)?.name ?? `#${id}`;
  }

  function millLabel(id: number | null): string {
    if (id == null) return '—';
    const m = mills.find((x) => x.id === id);
    return m ? `${m.millCode}` : `#${id}`;
  }

  $: selectedStock = workshopStocks.find((s) => s.mediaType === form.mediaType) ?? null;

  function reset() {
    form = {
      workshopId: workshops[0] ? String(workshops[0].id) : '',
      mediaType: '',
      millId: '',
      qtyKg: '5',
      issuedAt: nowLocal(),
      operatorName: form.operatorName,
    };
    syncFormChoices();
  }

  async function submit() {
    error = '';
    const qty = Number(form.qtyKg);
    if (!form.workshopId) {
      error = '请选择领用车间';
      return;
    }
    if (!form.mediaType) {
      error = '请选择研磨珠类型';
      return;
    }
    if (!(qty > 0)) {
      error = '领用数量(kg)必须大于 0';
      return;
    }
    if (!form.operatorName.trim()) {
      error = '请填写操作员（领用人）';
      return;
    }

    const payload = {
      workshopId: Number(form.workshopId),
      mediaType: form.mediaType,
      millId: form.millId ? Number(form.millId) : null,
      qtyKg: qty,
      issuedAt: form.issuedAt,
      operatorName: form.operatorName.trim(),
    };

    saving = true;
    try {
      await api('/media/issues', { method: 'POST', body: JSON.stringify(payload) });
      // 重新拉取，库存表数值立即反映扣减后的结余
      await load();
      form.qtyKg = '5';
      form.millId = '';
      form.issuedAt = nowLocal();
    } catch (e) {
      error = e instanceof Error ? e.message : '发料失败';
    } finally {
      saving = false;
    }
  }
</script>

<header class="page-head">
  <h1>耗材领用</h1>
  <p>研磨珠按车间建库存行（同车间同介质唯一），发料即扣减结余，库存不足拒绝发料</p>
</header>

{#if error}
  <div class="err">{error}</div>
{/if}

<section class="panel">
  <h2>库存结余（kg）</h2>
  <table class="data-table">
    <thead>
      <tr>
        <th>车间</th>
        <th>研磨珠类型</th>
        <th>结余 (kg)</th>
      </tr>
    </thead>
    <tbody>
      {#each stocks as s}
        <tr class:low={s.onHandKg <= 10}>
          <td>{workshopName(s.workshopId)}</td>
          <td>{s.mediaType}</td>
          <td class="num">{s.onHandKg} {#if s.onHandKg <= 10}<span class="warn">余量偏低</span>{/if}</td>
        </tr>
      {:else}
        <tr><td colspan="3" class="muted">暂无库存</td></tr>
      {/each}
    </tbody>
  </table>
</section>

<section class="panel">
  <h2>发料登记</h2>
  <div class="fields">
    <div class="field">
      <label>领用车间
        <select bind:value={form.workshopId} on:change={onWorkshopChange}>
          {#each workshops as w}
            <option value={String(w.id)}>{w.name}</option>
          {/each}
        </select>
      </label>
    </div>
    <div class="field">
      <label>研磨珠类型
        <select bind:value={form.mediaType}>
          {#each workshopStocks as s}
            <option value={s.mediaType}>{s.mediaType}（结余 {s.onHandKg} kg）</option>
          {/each}
        </select>
      </label>
    </div>
    <div class="field">
      <label>领用磨机（可选，须同车间）
        <select bind:value={form.millId}>
          <option value="">不指定磨机</option>
          {#each workshopMills as m}
            <option value={String(m.id)}>{m.millCode} · {m.pigmentBase}</option>
          {/each}
        </select>
      </label>
    </div>
    <div class="field">
      <label>领用数量 (kg)
        <input type="number" min="0.01" step="0.01" bind:value={form.qtyKg} />
      </label>
    </div>
    <div class="field">
      <label>发料时间
        <input type="datetime-local" bind:value={form.issuedAt} />
      </label>
    </div>
    <div class="field">
      <label>操作员（领用人）
        <input placeholder="如：张研磨" bind:value={form.operatorName} />
      </label>
    </div>
  </div>
  {#if selectedStock}
    <div class="hint">
      当前「{selectedStock.mediaType}」结余 <strong>{selectedStock.onHandKg} kg</strong>，
      本次拟领 {form.qtyKg || 0} kg → 发料后结余
      <strong class:neg={Number(form.qtyKg) > selectedStock.onHandKg}>
        {(selectedStock.onHandKg - (Number(form.qtyKg) || 0)).toFixed(2)} kg
      </strong>
    </div>
  {/if}
  <div class="actions">
    <button class="btn-primary" disabled={saving} on:click={submit}>
      {saving ? '发料中…' : '确认发料'}
    </button>
    <button class="btn-ghost" on:click={reset}>重置</button>
  </div>
</section>

<section class="panel">
  <h2>发料记录</h2>
  <table class="data-table">
    <thead>
      <tr>
        <th>ID</th>
        <th>发料时间</th>
        <th>车间</th>
        <th>磨机</th>
        <th>研磨珠类型</th>
        <th>数量 (kg)</th>
        <th>领用人</th>
      </tr>
    </thead>
    <tbody>
      {#each issues as r}
        <tr>
          <td>{r.id}</td>
          <td>{r.issuedAt}</td>
          <td>{workshopName(r.workshopId)}</td>
          <td>{millLabel(r.millId)}</td>
          <td>{r.mediaType}</td>
          <td class="num">{r.qtyKg}</td>
          <td>{r.operatorName}</td>
        </tr>
      {:else}
        <tr><td colspan="7" class="muted">暂无发料记录</td></tr>
      {/each}
    </tbody>
  </table>
</section>

<style>
  .num {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  tr.low td {
    color: var(--vermillion-400);
  }

  .warn {
    margin-left: 0.5rem;
    font-size: 0.75rem;
    border: 1px solid var(--vermillion-700);
    padding: 0.05rem 0.35rem;
  }

  .hint {
    margin-top: 0.8rem;
    font-size: 0.85rem;
    color: var(--steel);
  }

  .hint strong {
    color: var(--paper);
  }

  .hint strong.neg {
    color: var(--vermillion-400);
  }

  button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
</style>
