import { getFishTypes, getSystemStatus, getRecipe, saveRecipe, writeRecipeToPLC } from './api.js';

let fishList = [];

document.addEventListener('DOMContentLoaded', () => {
    initPage();
});

async function initPage() {
    // 1. Load Fish Types
    try {
        fishList = await getFishTypes();
        renderFishSelect(fishList);
    } catch (e) {
        console.error("Init failed", e);
        document.getElementById('status-msg').innerText = "載入魚種失敗";
    }

    // 2. Render Empty Table Structure
    renderTable();
}

function renderFishSelect(list) {
    const select = document.getElementById('fish-select');
    select.innerHTML = '<option value="" disabled selected>-- 請選擇魚種 --</option>';
    
    list.forEach(fish => {
        const opt = document.createElement('option');
        opt.value = fish.code;
        opt.innerText = `${fish.code} - ${fish.name}`;
        select.appendChild(opt);
    });

    // Event Listener: When selection changes, try to load recipe from DB
    select.addEventListener('change', async (e) => {
        const code = e.target.value;
        if(code) await loadFromDB(code);
    });
}

function renderTable(data = {}) {
    const tbody = document.getElementById('bucket-table-body');
    let html = '';

    for (let i = 1; i <= 7; i++) {
        // Values (default to empty string if undefined)
        const minVal = data[`cfg_b${i}_min`] !== undefined ? data[`cfg_b${i}_min`] : '';
        const maxVal = data[`cfg_b${i}_max`] !== undefined ? data[`cfg_b${i}_max`] : '';
        const targetVal = data[`cfg_b${i}_target`] !== undefined ? data[`cfg_b${i}_target`] : '';

        // Bucket 1 Min is editable, others are Read-Only (PLC logic)
        const isMinEditable = (i === 1);
        const bgMin = isMinEditable ? 'bg-white' : 'bg-gray-100 text-gray-500';

        html += `
        <tr class="hover:bg-gray-50 transition">
            <td class="px-6 py-4 font-bold text-gray-700">分規 ${i}</td>
            
            <td class="px-6 py-2">
                <input type="number" data-key="cfg_b${i}_min" value="${minVal}" 
                    class="w-full border border-gray-300 rounded px-3 py-2 focus:ring-2 focus:ring-blue-500 outline-none ${bgMin}"
                    ${!isMinEditable ? 'disabled' : ''} placeholder="--">
            </td>
            
            <td class="px-6 py-2">
                <input type="number" data-key="cfg_b${i}_max" value="${maxVal}" 
                    class="w-full border border-gray-300 rounded px-3 py-2 focus:ring-2 focus:ring-blue-500 outline-none" placeholder="0">
            </td>
            
            <td class="px-6 py-2">
                <input type="number" data-key="cfg_b${i}_target" value="${targetVal}" 
                    class="w-full border border-gray-300 rounded px-3 py-2 focus:ring-2 focus:ring-blue-500 outline-none text-blue-700 font-semibold" placeholder="0">
            </td>
        </tr>
        `;
    }
    tbody.innerHTML = html;
}

// --- Actions ---

function getSelectedFish() {
    const sel = document.getElementById('fish-select');
    if (!sel.value) {
        alert("請先選擇魚種");
        return null;
    }
    return sel.value;
}

// 1. Load from DB (Recipe)
async function loadFromDB(code) {
    document.getElementById('status-msg').innerText = `正在讀取 ${code} 的資料庫設定...`;
    try {
        const recipe = await getRecipe(code);
        // If recipe is empty, we might want to keep inputs empty or notify
        if (Object.keys(recipe).length === 0) {
             document.getElementById('status-msg').innerText = `此魚種尚無儲存的設定 (顯示空白)`;
             renderTable({}); // Clear table
        } else {
             renderTable(recipe);
             document.getElementById('status-msg').innerText = `已載入 ${code} 資料庫設定`;
        }
    } catch (e) {
        console.error(e);
        alert("讀取資料庫失敗");
    }
}

// 2. Load from PLC (Current Values)
window.loadFromPLC = async function() {
    document.getElementById('status-msg').innerText = "正在讀取設備現值...";
    try {
        const status = await getSystemStatus();
        renderTable(status);
        document.getElementById('status-msg').innerText = "已顯示設備當前數值 (尚未儲存)";
    } catch(e) {
        console.error(e);
        alert("讀取設備失敗");
    }
};

// Helper: Gather data from inputs
function gatherTableData() {
    const inputs = document.querySelectorAll('#bucket-table-body input');
    const params = {};
    inputs.forEach(input => {
        if (!input.disabled && input.value !== '') {
            params[input.dataset.key] = parseInt(input.value);
        }
    });
    return params;
}

// 3. Save to DB
window.saveToDB = async function() {
    const code = getSelectedFish();
    if (!code) return;

    const params = gatherTableData();
    if (Object.keys(params).length === 0) {
        alert("表格為空，無法儲存");
        return;
    }

    if(!confirm(`確定要儲存 [${code}] 的分規數據到資料庫嗎？`)) return;

    try {
        await saveRecipe(code, params);
        alert("儲存成功！");
        document.getElementById('status-msg').innerText = "設定已儲存至資料庫";
    } catch(e) {
        alert("儲存失敗: " + e.message);
    }
};

// 4. Write to PLC
window.writeToPLC = async function() {
    const code = getSelectedFish();
    if (!code) return; // 雖然寫入 PLC 不一定需要魚種代號，但通常是針對當前魚種的操作

    const params = gatherTableData();
    if (Object.keys(params).length === 0) return;

    if(!confirm(`⚠️ 警告：這將會覆蓋 PLC 設備上的設定值！\n確定要寫入嗎？`)) return;

    try {
        document.getElementById('status-msg').innerText = "寫入設備中...";
        await writeRecipeToPLC(code, params);
        alert("寫入設備成功！");
        document.getElementById('status-msg').innerText = "寫入完成";
        
        // Reload from PLC to verify
        setTimeout(loadFromPLC, 500); 
    } catch(e) {
        alert("寫入設備失敗: " + e.message);
    }
};