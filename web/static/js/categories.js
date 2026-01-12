document.addEventListener('DOMContentLoaded', () => {
    fetchList();
    initWebSocket();
    setupForm();
});

let currentActiveCode = null;
let fishMap = {}; 

// --- 1. Data Fetching ---

async function fetchList() {
    try {
        const res = await fetch('/api/fish-types');
        if (!res.ok) throw new Error("API Error");
        const data = await res.json();
        renderTable(data);
        
        fishMap = {};
        data.forEach(item => {
            fishMap[item.code] = item.name;
        });
        updateActiveDisplay(); 
    } catch (e) {
        console.error("Failed to fetch categories:", e);
        document.getElementById('table-body').innerHTML = 
            `<tr><td colspan="3" class="px-6 py-8 text-center text-red-500">Error loading data. Check console.</td></tr>`;
    }
}

function renderTable(list) {
    const tbody = document.getElementById('table-body');
    tbody.innerHTML = '';

    if (list.length === 0) {
        tbody.innerHTML = `<tr><td colspan="3" class="px-6 py-8 text-center text-gray-400">No records found.</td></tr>`;
        return;
    }

    list.forEach(item => {
        const isActive = item.code === currentActiveCode;
        const activeClass = isActive ? 'bg-blue-50 border-l-4 border-blue-500' : 'hover:bg-gray-50';
        const activeBadge = isActive ? `<span class="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">ACTIVE</span>` : '';

        const tr = document.createElement('tr');
        tr.className = `transition ${activeClass}`;
        tr.innerHTML = `
            <td class="px-6 py-4 font-mono font-bold text-gray-700">${item.code}</td>
            <td class="px-6 py-4 text-gray-800">${item.name} ${activeBadge}</td>
            <td class="px-6 py-4 text-right space-x-2">
                ${!isActive ? `
                <button onclick="setProduction('${item.code}')" class="text-xs bg-green-100 text-green-700 px-3 py-1 rounded border border-green-200 hover:bg-green-200 transition">
                    <i class="fa-solid fa-check mr-1"></i> Select
                </button>` : ''}
                <button onclick="editItem('${item.code}', '${item.name}')" class="text-gray-400 hover:text-blue-600 transition">
                    <i class="fa-solid fa-pen"></i>
                </button>
                <button onclick="deleteItem('${item.code}')" class="text-gray-400 hover:text-red-600 transition">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// --- 2. Form Handling (關鍵：發送 POST 請求) ---

function setupForm() {
    const form = document.getElementById('category-form');
    const btnClear = document.getElementById('btn-clear');

    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const code = document.getElementById('input-code').value.toUpperCase().trim();
        const name = document.getElementById('input-name').value.trim();

        if(!code || !name) return;

        try {
            // [關鍵] 這裡會發送 POST 請求到後端
            const res = await fetch('/api/fish-types', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({code, name})
            });
            
            if(res.ok) {
                form.reset();
                fetchList(); // 重新整理列表
            } else {
                const err = await res.json();
                alert('Save failed: ' + (err.detail || 'Unknown error'));
            }
        } catch(e) {
            console.error(e);
            alert('Network error during save');
        }
    });

    btnClear.addEventListener('click', () => {
        form.reset();
    });
}

// --- 3. Interactions & WebSocket ---

window.setProduction = async function(code) {
    if(!confirm(`Send code [${code}] to PLC for production?`)) return;
    try {
        const res = await fetch('/api/control/category', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({code: code})
        });
        const result = await res.json();
        if(!result.success) alert('Failed to write to PLC');
    } catch(e) { console.error(e); alert('API Error'); }
};

window.deleteItem = async function(code) {
    if(!confirm(`Delete mapping for [${code}]?`)) return;
    await fetch(`/api/fish-types/${code}`, { method: 'DELETE' });
    fetchList();
};

window.editItem = function(code, name) {
    document.getElementById('input-code').value = code;
    document.getElementById('input-name').value = name;
    document.getElementById('input-code').focus();
};

function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if(data.fish_code && data.fish_code !== currentActiveCode) {
                currentActiveCode = data.fish_code;
                updateActiveDisplay();
                fetchList();
            }
        } catch(e) {}
    };
    
    fetch('/api/status').then(r=>r.json()).then(data => {
        if(data.fish_code) {
            currentActiveCode = data.fish_code;
            updateActiveDisplay();
            fetchList();
        }
    });
}

function updateActiveDisplay() {
    const elCode = document.getElementById('active-code-display');
    const elName = document.getElementById('active-name-display');
    if (elCode && elName) {
        elCode.innerText = currentActiveCode || '----';
        elName.innerText = fishMap[currentActiveCode] || 'Unknown Code';
    }
}