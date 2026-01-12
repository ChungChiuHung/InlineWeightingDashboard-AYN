// 取得所有魚種
export async function getFishTypes() {
  const r = await fetch('/api/fish-types');
  if (!r.ok) throw new Error('Failed to fetch fish types');
  return await r.json();
}

// 新增或更新魚種 (POST)
export async function saveFishType(code, name) {
  const r = await fetch('/api/fish-types', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, name })
  });
  if (!r.ok) throw new Error('Save failed');
  return await r.json();
}

// 刪除魚種 (DELETE)
export async function deleteFishType(code) {
  const r = await fetch(`/api/fish-types/${code}`, { method: 'DELETE' });
  if (!r.ok) throw new Error('Delete failed');
  return await r.json();
}

// 設定當前生產魚種 (寫入 PLC)
export async function setCategory(code) {
  const r = await fetch('/api/control/category', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code })
  });
  if (!r.ok) throw new Error('Control failed');
  return await r.json();
}

// 取得系統狀態 (PLC 即時數值)
export async function getSystemStatus() {
  const r = await fetch('/api/status');
  if (!r.ok) throw new Error('Status fetch failed');
  return await r.json();
}

// 取得歷史統計 (Dashboard 用)
export async function getDailyStats() {
  const r = await fetch('/api/history/stats');
  if (!r.ok) throw new Error('Failed to fetch stats');
  return await r.json();
}

// 取得歷史資料 (History 頁面用)
export async function getHistoryData(query = {}) {
  const params = new URLSearchParams(query);
  const r = await fetch(`/api/history?${params.toString()}`);
  if (!r.ok) throw new Error('Failed to fetch history');
  return await r.json();
}

// [新增] 生成測試資料 (Debug)
export async function seedTestData() {
  const r = await fetch('/api/debug/seed', { method: 'POST' });
  if (!r.ok) throw new Error('Seeding failed');
  return await r.json();
}

// --- 分規設定 / 配方管理相關 API ---

export async function getRecipe(fishCode) {
  const r = await fetch(`/api/recipes/${fishCode}`);
  if (!r.ok) throw new Error('Failed to load recipe');
  return await r.json();
}

export async function saveRecipe(fishCode, params) {
  const r = await fetch('/api/recipes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fish_code: fishCode, params })
  });
  if (!r.ok) throw new Error('Failed to save recipe');
  return await r.json();
}

export async function writeRecipeToPLC(fishCode, params) {
  const r = await fetch('/api/control/write-recipe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fish_code: fishCode, params })
  });
  if (!r.ok) throw new Error('Failed to write to PLC');
  return await r.json();
}

export async function writeTag(tag, value) {
  return fetch(`/write/${tag}`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ value })
  });
}