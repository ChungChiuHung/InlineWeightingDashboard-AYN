import { getFishTypes, saveFishType, deleteFishType, setCategory } from './api.js';

// 等待 DOM 載入後執行初始化
document.addEventListener('DOMContentLoaded', () => {
    fetchList();
    // 移除 WebSocket 初始化，保持頁面靜態
    setupForm();
});

// --- 1. Data Fetching ---

async function fetchList() {
    try {
        const data = await getFishTypes();
        
        // 更新計數 (防呆檢查)
        const countEl = document.getElementById('list-count');
        if(countEl) countEl.innerText = `${data.length} 筆`;

        renderTable(data);
        
    } catch (e) {
        console.error("Failed to fetch categories:", e);
        const tbody = document.getElementById('table-body');
        if(tbody) {
            tbody.innerHTML = `<tr><td colspan="3" class="px-6 py-8 text-center text-red-500">載入資料失敗。請檢查連線。</td></tr>`;
        }
    }
}

function renderTable(list) {
    const tbody = document.getElementById('table-body');
    if (!tbody) return; // 防呆

    tbody.innerHTML = '';

    if (list.length === 0) {
        tbody.innerHTML = `<tr><td colspan="3" class="px-6 py-8 text-center text-gray-400">尚無資料，請新增。</td></tr>`;
        return;
    }

    list.forEach(item => {
        // 移除 isActive 判斷，所有項目樣式一致
        const tr = document.createElement('tr');
        tr.className = `transition border-b border-gray-100 last:border-0 hover:bg-gray-50`;
        
        tr.innerHTML = `
            <td class="px-6 py-3 font-mono font-bold text-gray-700">${item.code}</td>
            <td class="px-6 py-3 text-gray-800">${item.name}</td>
            <td class="px-6 py-3 text-right space-x-1">
                <button onclick="setProduction('${item.code}')" title="設為生產 (寫入 PLC)" class="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded hover:bg-green-100 hover:text-green-700 border border-gray-200 transition">
                    選用
                </button>
                <button onclick="editItem('${item.code}', '${item.name}')" title="編輯" class="p-1 text-gray-400 hover:text-blue-600 transition">
                    <i class="fa-solid fa-pen"></i>
                </button>
                <button onclick="deleteItem('${item.code}')" title="刪除" class="p-1 text-gray-400 hover:text-red-600 transition">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// --- 2. Form Handling ---

function setupForm() {
    const form = document.getElementById('category-form');
    const btnClear = document.getElementById('btn-clear');

    // 防禦性檢查：確保元素存在才綁定事件
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const codeInput = document.getElementById('input-code');
            const nameInput = document.getElementById('input-name');
            
            if(!codeInput || !nameInput) return;

            const code = codeInput.value.toUpperCase().trim();
            const name = nameInput.value.trim();

            if(!code || !name) return;

            if(code.length !== 4) {
                alert('PLC 代碼必須剛好是 4 碼 (例如 F001)');
                return;
            }

            try {
                await saveFishType(code, name);
                form.reset();
                fetchList();
            } catch(e) {
                console.error(e);
                alert('儲存失敗: ' + e.message);
            }
        });
    }

    if (btnClear) {
        btnClear.addEventListener('click', () => {
            if(form) form.reset();
            const codeInput = document.getElementById('input-code');
            if(codeInput) codeInput.focus();
        });
    }
}

// --- 3. Interactions ---

// 將函式明確掛載到 window，供 HTML onclick 屬性呼叫
window.setProduction = async function(code) {
    if(!confirm(`確定要將代碼 [${code}] 設定為目前生產魚種嗎？\n(這會將代碼寫入 PLC)`)) return;
    try {
        const result = await setCategory(code);
        if(result.success) {
            // 成功後僅提示，不刷新列表狀態
            // alert('設定成功'); 
        } else {
            alert('寫入 PLC 失敗，請檢查連線');
        }
    } catch(e) { console.error(e); alert('API 連線錯誤'); }
};

window.deleteItem = async function(code) {
    if(!confirm(`警告：確定刪除 [${code}] 嗎？\n這只會刪除資料庫設定，不會影響 PLC 運作。`)) return;
    try {
        await deleteFishType(code);
        fetchList();
    } catch(e) {
        alert('刪除失敗');
    }
};

window.editItem = function(code, name) {
    const codeInput = document.getElementById('input-code');
    const nameInput = document.getElementById('input-name');
    
    if(codeInput) codeInput.value = code;
    if(nameInput) {
        nameInput.value = name;
        nameInput.focus();
    }
    
    // Smooth scroll to top on mobile
    window.scrollTo({ top: 0, behavior: 'smooth' });
};

// --- 4. Batch Import Logic ---

window.toggleBatchModal = function() {
    const modal = document.getElementById('batch-modal');
    if(!modal) return;
    
    modal.classList.toggle('hidden');
    if (!modal.classList.contains('hidden')) {
        const input = document.getElementById('batch-input');
        const status = document.getElementById('batch-status');
        if(input) input.focus();
        if(status) status.innerText = '';
    }
};

window.processBatchImport = async function() {
    const inputEl = document.getElementById('batch-input');
    const statusEl = document.getElementById('batch-status');
    
    if (!inputEl || !statusEl) return;
    
    const input = inputEl.value;
    if (!input.trim()) return;

    const lines = input.split('\n');
    let successCount = 0;
    let failCount = 0;

    statusEl.innerText = '處理中...';

    for (const line of lines) {
        if (!line.trim()) continue;
        
        let parts = line.split(',');
        if (parts.length < 2) parts = line.split(/\s+/); 

        const code = parts[0]?.trim().toUpperCase();
        const name = parts[1]?.trim();

        if (code && name && code.length === 4) {
            try {
                await saveFishType(code, name);
                successCount++;
            } catch (e) {
                console.warn(`Failed line: ${line}`, e);
                failCount++;
            }
        } else {
            failCount++;
        }
        
        statusEl.innerText = `進度: 成功 ${successCount} / 失敗 ${failCount}`;
    }

    statusEl.innerText = `完成！成功匯入 ${successCount} 筆，失敗/格式錯誤 ${failCount} 筆。`;
    
    fetchList();
    
    if (failCount === 0) {
        setTimeout(() => {
            window.toggleBatchModal();
            inputEl.value = ''; 
        }, 1500);
    }
};