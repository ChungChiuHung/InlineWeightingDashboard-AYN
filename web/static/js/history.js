import { getHistoryData, seedTestData, getFishTypes } from './api.js';

let trendChart = null;
let histogramChart = null;

document.addEventListener('DOMContentLoaded', () => {
    initDateInputs();
    initFishFilter(); 
    
    // 綁定查詢表單
    const form = document.getElementById('query-form');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await fetchData();
        });
    }

    // 預設自動查詢一次 (載入最近資料)
    fetchData();
});

// 載入魚種下拉選單
async function initFishFilter() {
    const select = document.getElementById('fishCode');
    if (!select) return;

    try {
        const list = await getFishTypes();
        
        // 建立預設選項
        select.innerHTML = '<option value="">全部魚種</option>';
        
        list.forEach(fish => {
            const opt = document.createElement('option');
            opt.value = fish.code;
            opt.innerText = `${fish.code} - ${fish.name}`;
            select.appendChild(opt);
        });
    } catch (e) {
        console.error("Failed to load fish types:", e);
        select.innerHTML = '<option value="">載入失敗</option>';
    }
}

// 初始化日期選擇器 (預設最近 24 小時)
function initDateInputs() {
    const now = new Date();
    const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    
    // 格式化為 datetime-local 所需的 YYYY-MM-DDTHH:mm
    const toLocalISO = (date) => {
        const offset = date.getTimezoneOffset() * 60000;
        return new Date(date.getTime() - offset).toISOString().slice(0, 16);
    };

    const endEl = document.getElementById('endTime');
    const startEl = document.getElementById('startTime');

    if (endEl) endEl.value = toLocalISO(now);
    if (startEl) startEl.value = toLocalISO(yesterday);
}

// 產生測試資料 (全域函式供 HTML onclick 使用)
window.generateTestData = async function() {
    if(!confirm("確定要生成 100 筆測試資料嗎？")) return;
    try {
        await seedTestData();
        alert("資料生成成功！");
        await fetchData(); // 重新整理圖表
    } catch(e) {
        alert("生成失敗: " + e.message);
    }
};

async function fetchData() {
    const startEl = document.getElementById('startTime');
    const endEl = document.getElementById('endTime');
    const codeEl = document.getElementById('fishCode');
    const tbody = document.getElementById('history-table-body');
    const countEl = document.getElementById('record-count');

    if (!startEl || !endEl || !codeEl || !tbody) return;

    const start = startEl.value;
    const end = endEl.value;
    const code = codeEl.value; 

    tbody.innerHTML = `<tr><td colspan="4" class="text-center py-8"><i class="fa-solid fa-spinner fa-spin text-gray-400 text-xl"></i></td></tr>`;

    try {
        // 建構查詢參數
        const query = { limit: 2000 }; // 限制 2000 筆以免瀏覽器卡頓
        if (start) query.start_time = start.replace('T', ' '); // 轉換格式以符合後端 SQL
        if (end) query.end_time = end.replace('T', ' ');
        if (code) query.fish_code = code;

        const data = await getHistoryData(query);
        
        if (countEl) countEl.innerText = `${data.length} 筆`;
        
        if (data.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" class="text-center py-8 text-gray-400">查無資料</td></tr>`;
            clearCharts();
            return;
        }

        renderTable(data, tbody);
        renderCharts(data);

    } catch (e) {
        console.error(e);
        tbody.innerHTML = `<tr><td colspan="4" class="text-center py-8 text-red-500">查詢失敗</td></tr>`;
    }
}

function renderTable(data, tbody) {
    let html = '';
    
    // 只顯示前 100 筆在表格中，以免 DOM 過重
    const displayData = data.slice(0, 100);
    
    displayData.forEach(row => {
        html += `
        <tr class="hover:bg-gray-50 border-b border-gray-100 last:border-0">
            <td class="px-6 py-3 font-mono text-gray-600">${row.timestamp}</td>
            <td class="px-6 py-3 font-mono font-bold text-gray-800">${row.fish_code || '--'}</td>
            <td class="px-6 py-3 text-right font-mono text-blue-600">${row.weight}</td>
            <td class="px-6 py-3">
                <span class="px-2 py-1 rounded text-xs ${row.status === 'RUN' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}">
                    ${row.status || 'UNKNOWN'}
                </span>
            </td>
        </tr>`;
    });

    if (data.length > 100) {
        html += `<tr><td colspan="4" class="text-center py-2 text-xs text-gray-400">... 僅顯示前 100 筆，共 ${data.length} 筆 ...</td></tr>`;
    }
    
    tbody.innerHTML = html;
}

function renderCharts(data) {
    // 資料預處理：反轉陣列讓時間由左至右 (假設 SQL 是 DESC)
    const sortedData = [...data].reverse();

    const labels = sortedData.map(d => d.timestamp.split(' ')[1]); // 只取時間部分 HH:mm:ss
    const weights = sortedData.map(d => d.weight);

    // 1. Line Chart (Trend)
    const trendCtx = document.getElementById('trendChart');
    if (trendCtx) {
        if (trendChart) trendChart.destroy();

        trendChart = new Chart(trendCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: '重量 (kg)',
                    data: weights,
                    borderColor: '#3b82f6', // Blue-500
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    pointRadius: 2,
                    tension: 0.2,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { mode: 'index', intersect: false }
                },
                scales: {
                    x: { ticks: { maxTicksLimit: 10 } },
                    y: { beginAtZero: false } // 自動縮放讓趨勢更明顯
                }
            }
        });
    }

    // 2. Histogram (Distribution)
    const histCtx = document.getElementById('histogramChart');
    if (histCtx) {
        const validWeights = weights.filter(w => w > 0);
        
        if (validWeights.length > 0) {
            const minW = Math.min(...validWeights);
            const maxW = Math.max(...validWeights);
            const binCount = 15; // 分成 15 個區間
            const range = maxW - minW || 1; 
            const step = range / binCount;

            const bins = new Array(binCount).fill(0);
            const binLabels = [];

            // 產生標籤
            for(let i=0; i<binCount; i++) {
                const start = (minW + i * step).toFixed(2);
                const end = (minW + (i+1) * step).toFixed(2);
                binLabels.push(`${start}-${end}`);
            }

            // 填入數據
            validWeights.forEach(w => {
                let idx = Math.floor((w - minW) / step);
                if (idx >= binCount) idx = binCount - 1; 
                bins[idx]++;
            });

            if (histogramChart) histogramChart.destroy();

            histogramChart = new Chart(histCtx.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: binLabels,
                    datasets: [{
                        label: '數量 (Count)',
                        data: bins,
                        backgroundColor: '#6366f1', // Indigo-500
                        borderRadius: 4,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        }
    }
}

function clearCharts() {
    if (trendChart) {
        trendChart.destroy();
        trendChart = null;
    }
    if (histogramChart) {
        histogramChart.destroy();
        histogramChart = null;
    }
}