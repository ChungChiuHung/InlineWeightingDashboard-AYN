import { getHistoryData, getFishTypes } from './api.js';

let trendChart = null;
let histogramChart = null;
let currentData = []; // 暫存目前的查詢結果，供匯出 CSV 使用
let fishMap = {}; // 用於儲存魚種代碼與名稱的對照表

document.addEventListener('DOMContentLoaded', () => {
    initDateInputs();
    initFishFilter(); 
    initUIControls();
    
    const form = document.getElementById('query-form');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await fetchData();
        });
    }
    
    // 初始檢查一次按鈕狀態 (預設禁用)
    updateActionButtonsState();
});

function initUIControls() {
    const btnToggle = document.getElementById('btn-toggle-list');
    const container = document.getElementById('table-container');
    const btnExport = document.getElementById('btn-export-csv');

    if (btnToggle && container) {
        btnToggle.addEventListener('click', () => {
            if (btnToggle.disabled) return;

            const isHidden = container.classList.contains('hidden');
            if (isHidden) {
                container.classList.remove('hidden');
                btnToggle.innerHTML = '<i class="fa-solid fa-chevron-up mr-1"></i> <span>隱藏列表</span>';
            } else {
                container.classList.add('hidden');
                btnToggle.innerHTML = '<i class="fa-solid fa-chevron-down mr-1"></i> <span>顯示列表</span>';
            }
        });
    }

    if (btnExport) {
        btnExport.addEventListener('click', exportToCSV);
    }
}

// 統一管理所有功能按鈕的狀態 (匯出 & 顯示列表)
function updateActionButtonsState() {
    const btnExport = document.getElementById('btn-export-csv');
    const btnToggle = document.getElementById('btn-toggle-list');
    
    const hasData = currentData && currentData.length > 0;

    const setBtnState = (btn, enabled) => {
        if (!btn) return;
        if (enabled) {
            btn.disabled = false;
            btn.removeAttribute('disabled');
            btn.classList.remove('opacity-50', 'cursor-not-allowed');
        } else {
            btn.disabled = true;
            btn.setAttribute('disabled', 'true');
            btn.classList.add('opacity-50', 'cursor-not-allowed');
        }
    };

    setBtnState(btnExport, hasData);
    setBtnState(btnToggle, hasData);
}

function exportToCSV() {
    if (!currentData || currentData.length === 0) {
        alert("無資料可匯出");
        return;
    }

    const headers = ["時間 (Time)", "代碼 (Code)", "名稱 (Name)", "重量 (g)"];
    
    const rows = currentData.map(item => {
        const timeStr = item.timestamp ? item.timestamp.replace('T', ' ') : '--';
        const weight = parseInt(item.weight) || 0;
        const name = fishMap[item.fish_code] || '';
        return `"${timeStr}","${item.fish_code}","${name}","${weight}"`;
    });

    const csvContent = "\uFEFF" + [headers.join(","), ...rows].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    
    const timestamp = new Date().toISOString().slice(0,10).replace(/-/g,"");
    link.setAttribute("href", url);
    link.setAttribute("download", `production_history_${timestamp}.csv`);
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

async function initFishFilter() {
    const select = document.getElementById('fishCode');
    if (!select) return;

    try {
        const list = await getFishTypes();
        select.innerHTML = '<option value="" disabled selected>-- 請選擇魚種 --</option>';
        
        fishMap = {};
        
        list.forEach(fish => {
            fishMap[fish.code] = fish.name;
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

function initDateInputs() {
    const now = new Date();
    const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    
    const toLocalISO = (date) => {
        const offset = date.getTimezoneOffset() * 60000;
        return new Date(date.getTime() - offset).toISOString().slice(0, 16);
    };

    const endEl = document.getElementById('endTime');
    const startEl = document.getElementById('startTime');

    if (endEl) endEl.value = toLocalISO(now);
    if (startEl) startEl.value = toLocalISO(yesterday);
}

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

    if (!code) {
        alert("請選擇一個魚種以進行查詢");
        return;
    }

    updateStatsDisplay(0, 0, 0);
    
    currentData = [];
    updateActionButtonsState();

    // [修改] colspan 5
    tbody.innerHTML = `<tr><td colspan="5" class="text-center py-8"><i class="fa-solid fa-spinner fa-spin text-gray-400 text-xl"></i></td></tr>`;

    try {
        const query = { limit: 2000 };
        if (start) query.start_time = start.replace('T', ' ');
        if (end) query.end_time = end.replace('T', ' ');
        if (code) query.fish_code = code;

        const data = await getHistoryData(query);
        
        currentData = data;
        
        if (countEl) countEl.innerText = `${data.length} 筆`;
        
        updateActionButtonsState();

        if (data.length === 0) {
            // [修改] colspan 5
            tbody.innerHTML = `<tr><td colspan="5" class="text-center py-8 text-gray-400">查無資料</td></tr>`;
            clearCharts();
            showChartMessage('查無資料');
            return;
        }

        calculateAndShowStats(data);
        
        // [新增] 計算各魚種平均重量
        const fishAverages = calculateFishAverages(data);
        
        renderTable(data, tbody, fishAverages);
        renderCharts(data);

    } catch (e) {
        console.error(e);
        // [修改] colspan 5
        tbody.innerHTML = `<tr><td colspan="5" class="text-center py-8 text-red-500">查詢失敗</td></tr>`;
        updateActionButtonsState();
    }
}

// [新增] 計算各魚種平均重量的函式
function calculateFishAverages(data) {
    const sums = {}; // { code: { total: 0, count: 0 } }
    data.forEach(row => {
        const code = row.fish_code;
        const weight = parseFloat(row.weight) || 0;
        if (!sums[code]) sums[code] = { total: 0, count: 0 };
        sums[code].total += weight;
        sums[code].count++;
    });

    const averages = {};
    for (const code in sums) {
        averages[code] = sums[code].count > 0 ? (sums[code].total / sums[code].count) : 0;
    }
    return averages;
}

// ... (圖表訊息與統計函式保持不變) ...

function showChartMessage(msg) {
    const trendContainer = document.getElementById('trendChart')?.parentElement;
    const histContainer = document.getElementById('histogramChart')?.parentElement;
    
    if (trendContainer) {
        if (!trendContainer.querySelector('.chart-msg')) {
            const div = document.createElement('div');
            div.className = 'chart-msg absolute inset-0 flex items-center justify-center text-gray-400 text-sm bg-white bg-opacity-90';
            div.innerText = msg;
            trendContainer.appendChild(div);
        }
    }
    
    if (histContainer) {
        if (!histContainer.querySelector('.chart-msg')) {
            const div = document.createElement('div');
            div.className = 'chart-msg absolute inset-0 flex items-center justify-center text-gray-400 text-sm bg-white bg-opacity-90';
            div.innerText = msg;
            histContainer.appendChild(div);
        }
    }
}

function clearChartMessages() {
    document.querySelectorAll('.chart-msg').forEach(el => el.remove());
}

function calculateAndShowStats(data) {
    let totalWeight = 0;
    let count = data.length;

    data.forEach(row => {
        const w = parseFloat(row.weight) || 0;
        totalWeight += w;
    });

    const avgWeight = count > 0 ? (totalWeight / count) : 0;
    updateStatsDisplay(count, totalWeight, avgWeight);
    return avgWeight;
}

function updateStatsDisplay(count, total, avg) {
    const elCount = document.getElementById('stat-count');
    const elTotal = document.getElementById('stat-total-weight');
    const elAvg = document.getElementById('stat-avg-weight');

    if (elCount) elCount.innerText = count.toLocaleString();
    if (elTotal) elTotal.innerText = Math.round(total).toLocaleString();
    if (elAvg) elAvg.innerText = Math.round(avg).toLocaleString();
}

function renderTable(data, tbody, averages) {
    let html = '';
    const displayData = data.slice(0, 100);
    
    displayData.forEach(row => {
        const timeStr = row.timestamp ? row.timestamp.replace('T', ' ') : '--';
        // [新增] 取得名稱與平均重量
        const name = fishMap[row.fish_code] || '--';
        const avg = averages[row.fish_code] ? averages[row.fish_code].toFixed(0) : '-';
        
        html += `
        <tr class="hover:bg-gray-50 border-b border-gray-100 last:border-0">
            <td class="px-6 py-3 font-mono text-gray-600">${timeStr}</td>
            <td class="px-6 py-3 font-mono font-bold text-gray-800">${row.fish_code || '--'}</td>
            <!-- [新增] 名稱欄位 -->
            <td class="px-6 py-3 text-gray-700">${name}</td>
            <td class="px-6 py-3 text-right font-mono text-blue-600">${parseInt(row.weight)}</td>
            <!-- [新增] 平均重量欄位 -->
            <td class="px-6 py-3 text-right font-mono text-gray-500">${avg}</td>
        </tr>`;
    });

    if (data.length > 100) {
        // [修改] colspan 5
        html += `<tr><td colspan="5" class="text-center py-2 text-xs text-gray-400">... 僅顯示前 100 筆，共 ${data.length} 筆 ...</td></tr>`;
    }
    
    tbody.innerHTML = html;
}

function renderCharts(data) {
    clearChartMessages();

    const sortedData = [...data].reverse();

    const labels = sortedData.map(d => {
        const ts = d.timestamp.replace('T', ' ');
        return ts.split(' ')[1] || ts;
    }); 
    const weights = sortedData.map(d => parseFloat(d.weight));

    const totalWeight = weights.reduce((a, b) => a + b, 0);
    const avgWeight = weights.length > 0 ? totalWeight / weights.length : 0;

    const trendCtx = document.getElementById('trendChart');
    if (trendCtx) {
        if (trendChart) trendChart.destroy();

        trendChart = new Chart(trendCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: '重量 (g)',
                    data: weights,
                    borderColor: '#3b82f6', 
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
                    y: { beginAtZero: false } 
                }
            }
        });
    }

    const histCtx = document.getElementById('histogramChart');
    if (histCtx) {
        const validWeights = weights.filter(w => w > 0);
        
        if (validWeights.length > 0) {
            const minW = Math.min(...validWeights);
            const maxW = Math.max(...validWeights);
            const binCount = 15;
            const range = maxW - minW || 1; 
            const step = range / binCount;

            const bins = new Array(binCount).fill(0);
            const binLabels = [];

            for(let i=0; i<binCount; i++) {
                const start = (minW + i * step).toFixed(0);
                const end = (minW + (i+1) * step).toFixed(0);
                binLabels.push(`${start}-${end}`);
            }

            validWeights.forEach(w => {
                let idx = Math.floor((w - minW) / step);
                if (idx >= binCount) idx = binCount - 1; 
                bins[idx]++;
            });

            if (histogramChart) histogramChart.destroy();

            const avgLinePlugin = {
                id: 'avgLine',
                afterDatasetsDraw(chart, args, options) {
                    const { ctx, chartArea: { top, bottom, left, right, width }, scales: { x, y } } = chart;
                    
                    if (maxW === minW) return;

                    const ratio = (avgWeight - minW) / (maxW - minW);
                    const validRatio = Math.max(0, Math.min(1, ratio));
                    
                    const xPos = left + width * validRatio;

                    ctx.save();
                    ctx.beginPath();
                    ctx.lineWidth = 2;
                    ctx.strokeStyle = 'red';
                    ctx.setLineDash([5, 5]);
                    ctx.moveTo(xPos, top);
                    ctx.lineTo(xPos, bottom);
                    ctx.stroke();
                    
                    ctx.fillStyle = 'red';
                    ctx.textAlign = 'center';
                    ctx.font = 'bold 12px sans-serif';
                    ctx.fillText(`Avg: ${avgWeight.toFixed(0)}g`, xPos, top - 5);
                    
                    ctx.restore();
                }
            };

            histogramChart = new Chart(histCtx.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: binLabels,
                    datasets: [{
                        label: '數量 (Count)',
                        data: bins,
                        backgroundColor: '#6366f1',
                        borderRadius: 4,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                title: (items) => `區間: ${items[0].label}`,
                            }
                        }
                    },
                    scales: {
                        y: { beginAtZero: true },
                        x: { ticks: { maxTicksLimit: 10 } }
                    },
                    layout: {
                        padding: { top: 20 }
                    }
                },
                plugins: [avgLinePlugin]
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