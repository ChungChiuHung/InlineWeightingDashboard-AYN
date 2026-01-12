import { getFishTypes, writeTag } from './api.js';

async function loadFishTypes() {
  const list = await getFishTypes();
  const sel = document.getElementById('fishType');

  list.forEach(f => {
    const opt = document.createElement('option');
    opt.value = f.code;                       // 寫入 PLC
    opt.textContent = `[${f.code}] ${f.name}`; // 顯示中文
    sel.appendChild(opt);
  });
}

document.getElementById('btnWrite').onclick = async () => {
  const code = document.getElementById('fishType').value;
  await writeTag('category_a_code', code);
  alert('已寫入 PLC');
};

loadFishTypes();
