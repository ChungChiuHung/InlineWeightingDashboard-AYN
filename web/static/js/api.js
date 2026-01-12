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
  
  if (!r.ok) {
    const err = await r.json();
    throw new Error(err.detail || 'Save failed');
  }
  return await r.json();
}

// 刪除魚種 (DELETE)
export async function deleteFishType(code) {
  const r = await fetch(`/api/fish-types/${code}`, {
    method: 'DELETE'
  });
  
  if (!r.ok) {
    throw new Error('Delete failed');
  }
  return await r.json();
}

// 設定當前生產魚種 (寫入 PLC)
export async function setCategory(code) {
  const r = await fetch('/api/control/category', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code })
  });
  
  if (!r.ok) throw new Error('Control command failed');
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

// --- 分規設定 / 配方管理相關 API ---

// 取得指定魚種的配方設定 (從資料庫)
export async function getRecipe(fishCode) {
  const r = await fetch(`/api/recipes/${fishCode}`);
  if (!r.ok) throw new Error('Failed to load recipe');
  return await r.json();
}

// 儲存配方設定到資料庫
export async function saveRecipe(fishCode, params) {
  const r = await fetch('/api/recipes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fish_code: fishCode, params })
  });
  if (!r.ok) throw new Error('Failed to save recipe');
  return await r.json();
}

// 將配方設定寫入 PLC 設備
export async function writeRecipeToPLC(fishCode, params) {
  const r = await fetch('/api/control/write-recipe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fish_code: fishCode, params })
  });
  if (!r.ok) throw new Error('Failed to write to PLC');
  return await r.json();
}

// 通用寫入 (保留給其他簡單寫入需求)
export async function writeTag(tag, value) {
  return fetch(`/write/${tag}`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ value })
  });
}