import { getFishTypes, getSystemStatus, getRecipe, saveRecipe, writeRecipeToPLC } from './api.js';

let fishList = [];

document.addEventListener('DOMContentLoaded', () => {
    initPage();
});

async function initPage() {
    // 1. 載入魚種列表
    try {
        fishList = await getFishTypes();
        renderFishSelect(fishList);
    } catch (e) {
        console.error("Init failed", e);
        document.getElementById('status-msg').innerText = "載入魚種失敗";
    }

    // 2. 渲染空的表格結構
    renderTable();
}

function renderFishSelect(list) {
    const select = document.getElementById('fish-select');
    select.innerHTML = '<option value="" disabled selected>-- 請選擇魚種以設定分規 --</option>';
    
    list.forEach(fish => {
        const opt = document.createElement('option');
        opt.value = fish.code;
        opt.innerText = `${fish.code} - ${fish.name}`;
        select.appendChild(opt);
    });

    // 事件監聽：當選擇改變時，自動從資料庫載入該魚種的配方
    select.addEventListener('change', async (e) => {
        const code = e.target.value;
        if(code) {
            await loadFromDB(code);
        }
    });
}

function renderTable(data = {}) {
    const tbody = document.getElementById('bucket-table-body');
    let html = '';

    for (let i = 1; i <= 7; i++) {
        const minVal = data[`cfg_b${i}_min`] !== undefined ? data[`cfg_b${i}_min`] : '';
        const maxVal = data[`cfg_b${i}_max`] !== undefined ? data[`cfg_b${i}_max`] : '';
        const targetVal = data[`cfg_b${i}_target`] !== undefined ? data[`cfg_b${i}_target`] : '';

        // Bucket 1 Min 可編輯，其他 Bucket Min 為唯讀
        const isMinEditable = (i === 1);
        const bgMin = isMinEditable ? 'bg-white' : 'bg-gray-100 text-gray-500';

        html += `
        <tr class="hover:bg-gray-50 transition">
            <td class="px-6 py-4 font-bold text-gray-700">分規 ${i}</td>
            
            <td class="px-6 py-2">
                <input type="number" data-key="cfg_b${i}_min" value="${minVal}" 
                    class="w-full border border-gray-300 rounded px-3 py-2 focus:ring-2 focus:ring-blue-500 outline-none ${bgMin}"
                    ${!isMinEditable ? 'disabled' : ''} placeholder="${isMinEditable ? '輸入數值' : '--'}">
            </td>
            
            <td class="px-6 py-2">
                <input type="number" data-key="cfg_b${i}_max" value="${maxVal}" 
                    class="w-full border border-gray-300 rounded px-3 py-2 focus:ring-2 focus:ring-blue-500 outline-none" placeholder="輸入數值">
            </td>
            
            <td class="px-6 py-2">
                <input type="number" data-key="cfg_b${i}_target" value="${targetVal}" 
                    class="w-full border border-gray-300 rounded px-3 py-2 focus:ring-2 focus:ring-blue-500 outline-none text-blue-700 font-semibold" placeholder="輸入數值">
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

function gatherTableData() {
    const inputs = document.querySelectorAll('#bucket-table-body input');
    const params = {};
    let hasData = false;

    inputs.forEach(input => {
        const key = input.dataset.key;
        if (input.value !== '') {
            params[key] = parseInt(input.value);
            hasData = true;
        }
    });
    return hasData ? params : null;
}

// 1. 從資料庫載入配方
async function loadFromDB(code) {
    const statusMsg = document.getElementById('status-msg');
    statusMsg.innerText = `正在讀取 ${code} 的資料庫設定...`;
    statusMsg.className = "text-blue-600 font-medium";

    try {
        const recipe = await getRecipe(code);
        
        if (Object.keys(recipe).length === 0) {
             statusMsg.innerText = `此魚種尚無儲存的設定 (顯示空白)`;
             statusMsg.className = "text-gray-500";
             renderTable({}); // 清空表格
        } else {
             renderTable(recipe);
             statusMsg.innerText = `已載入 ${code} 資料庫設定`;
             statusMsg.className = "text-green-600 font-medium";
        }
    } catch (e) {
        console.error(e);
        statusMsg.innerText = "讀取資料庫失敗";
        statusMsg.className = "text-red-500";
    }
}

// 2. 從 PLC 讀取當前數值 (Snapshot)
window.loadFromPLC = async function() {
    const statusMsg = document.getElementById('status-msg');
    const select = document.getElementById('fish-select');

    statusMsg.innerText = "正在讀取設備現值...";
    statusMsg.className = "text-blue-600 font-medium";
    
    try {
        const status = await getSystemStatus();
        
        // [修正] 自動同步選單，若不存在則動態新增選項
        if (status.fish_code && status.fish_code !== '----') {
            let option = select.querySelector(`option[value="${status.fish_code}"]`);
            
            if (!option) {
                // 如果本地清單沒有這個代碼，新增一個臨時選項
                console.warn(`PLC fish code [${status.fish_code}] not found in local list. Adding temporary option.`);
                option = document.createElement('option');
                option.value = status.fish_code;
                // 顯示為 (未設定名稱) 以提示使用者
                option.innerText = `${status.fish_code} (未設定名稱)`;
                option.classList.add('text-red-500'); // 紅色字體提示
                select.appendChild(option);
            }
            
            select.value = status.fish_code;
        }

        renderTable(status);
        
        const fishDisplay = status.fish_code ? `[${status.fish_code}]` : '';
        statusMsg.innerText = `已顯示設備當前數值 ${fishDisplay}`;
        statusMsg.className = "text-orange-600 font-medium";
        
    } catch(e) {
        console.error(e);
        alert("讀取設備失敗");
        statusMsg.innerText = "讀取失敗";
        statusMsg.className = "text-red-500";
    }
};

// 3. 儲存配方到資料庫
window.saveToDB = async function() {
    const code = getSelectedFish();
    if (!code) return;

    const params = gatherTableData();
    if (!params) {
        alert("表格為空，無法儲存");
        return;
    }

    const sel = document.getElementById('fish-select');
    const fishName = sel.options[sel.selectedIndex].text;

    if(!confirm(`確定要儲存 [${fishName}] 的分規數據到資料庫嗎？`)) return;

    try {
        await saveRecipe(code, params);
        alert("儲存成功！");
        
        const statusMsg = document.getElementById('status-msg');
        statusMsg.innerText = "設定已儲存至資料庫";
        statusMsg.className = "text-green-600 font-medium";
    } catch(e) {
        alert("儲存失敗: " + e.message);
    }
};

// 4. 寫入配方到 PLC
window.writeToPLC = async function() {
    const code = getSelectedFish();
    if (!code) return;

    const params = gatherTableData();
    if (!params) {
        alert("表格為空，無法寫入");
        return;
    }

    const sel = document.getElementById('fish-select');
    const fishName = sel.options[sel.selectedIndex].text;

    if(!confirm(`⚠️ 警告：這將會覆蓋 PLC 設備上 [${fishName}] 的設定值！\n確定要寫入嗎？`)) return;

    const statusMsg = document.getElementById('status-msg');
    statusMsg.innerText = "正在寫入設備...";
    statusMsg.className = "text-blue-600";

    try {
        await writeRecipeToPLC(code, params);
        
        alert("寫入設備成功！");
        statusMsg.innerText = "寫入完成";
        statusMsg.className = "text-green-600 font-bold";
        
    } catch(e) {
        console.error(e);
        alert("寫入設備失敗: " + e.message);
        statusMsg.innerText = "寫入失敗";
        statusMsg.className = "text-red-600";
    }
};