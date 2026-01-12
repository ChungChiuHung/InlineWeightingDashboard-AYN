/**
 * Dashboard Logic v2.5
 * Integrates WebSocket real-time updates and Chart.js
 * Uses Centralized API Module
 */

import { getFishTypes, getDailyStats } from './api.js';

// --- 1. State & Config ---
let fishMapping = {};

const statusMap = {
    'RUN': '運轉中',
    'IDLE': '待機中',
    'ALARM': '異常',
    'STOP': '停止',
    'UNKNOWN': '未知'
};

// Chart Instances
let weightChart = null;
let productionChart = null;

// Buffers for Real-time Chart
// 設定顯示最近 60 筆數據
const maxDataPoints = 60; 
let weightData = Array(maxDataPoints).fill(null); 
let timeLabels = Array(maxDataPoints).fill('');

// --- 2. Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    console.log("Dashboard initializing...");
    loadFishMapping();
    initCharts();
    connectWebSocket();
    loadDailyStats(); 
});

async function loadFishMapping() {
    try {
        const data = await getFishTypes();
        fishMapping = {};
        data.forEach(item => {
            fishMapping[item.code] = item.name;
        });
        
        // Refresh display if data exists
        const currentCodeEl = document.getElementById('val-fish-code');
        if (currentCodeEl) {
            const code = currentCodeEl.innerText;
            if (code && code !== '----') {
                const nameEl = document.getElementById('val-fish-name');
                if (nameEl) nameEl.innerText = fishMapping[code] || code;
            }
        }
    } catch (e) {
        console.error("Failed to load fish mapping:", e);
    }
}

function initCharts() {
    // A. Real-time Weight Chart
    const weightCanvas = document.getElementById('weightChart');
    if (weightCanvas) {
        const ctxWeight = weightCanvas.getContext('2d');
        weightChart = new Chart(ctxWeight, {
            type: 'line',
            data: {
                labels: timeLabels,
                datasets: [{
                    label: '即時重量 (kg)',
                    data: weightData,
                    borderColor: '#3b82f6', // Tailwind blue-500
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    tension: 0.4, // 平滑曲線
                    fill: true,
                    pointRadius: 0, 
                    pointHoverRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 0 // 關閉動畫以獲得最佳即時效能
                },
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    y: { 
                        beginAtZero: true,
                        suggestedMax: 3.0, 
                        title: { display: true, text: 'kg' }
                    },
                    x: { 
                        display: false 
                    }
                },
                plugins: { 
                    legend: { display: false },
                    tooltip: { enabled: true, animation: false }
                }
            }
        });
    } else {
        console.error("Canvas element #weightChart not found!");
    }

    // B. Production Pie Chart
    const prodCanvas = document.getElementById('productionChart');
    if (prodCanvas) {
        const ctxProd = prodCanvas.getContext('2d');
        productionChart = new Chart(ctxProd, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [
                        '#10b981', '#f59e0b', '#ef4444', '#3b82f6', 
                        '#8b5cf6', '#ec4899', '#6366f1'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { 
                        position: 'right', 
                        labels: { font: { size: 11 }, boxWidth: 12 } 
                    }
                }
            }
        });
    }
}

// --- 3. WebSocket Connection ---
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    console.log(`Connecting to WebSocket: ${wsUrl}`);
    
    const ws = new WebSocket(wsUrl);

    const elIndicator = document.getElementById('ws-indicator');
    const elText = document.getElementById('ws-text');

    ws.onopen = () => {
        console.log("WebSocket Connected");
        if(elIndicator) {
            elIndicator.classList.remove('bg-red-500');
            elIndicator.classList.add('bg-green-500');
        }
        if(elText) elText.innerText = '連線中';
    };

    ws.onclose = () => {
        console.log("WebSocket Disconnected");
        if(elIndicator) {
            elIndicator.classList.remove('bg-green-500');
            elIndicator.classList.add('bg-red-500');
        }
        if(elText) elText.innerText = '離線';
        setTimeout(connectWebSocket, 3000);
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            updateDashboard(data);
        } catch (e) { console.error("WS Message Error:", e); }
    };
}

// --- 4. API Calls ---
async function loadDailyStats() {
    try {
        const result = await getDailyStats();
        if (productionChart && result.labels && result.data) {
            productionChart.data.labels = result.labels;
            productionChart.data.datasets[0].data = result.data;
            productionChart.update();
        }
    } catch (e) {
        console.error("Failed to fetch stats", e);
    }
}

// --- 5. UI Updates ---
function updateDashboard(data) {
    // 1. 更新狀態卡片
    if (data.status) {
        const statusCard = document.getElementById('card-status');
        const statusText = document.getElementById('val-status');
        
        if (statusCard && statusText) {
            statusCard.classList.remove('status-run', 'status-idle', 'status-alarm', 'bg-white', 'border-l-8');
            
            if (data.status === 'RUN') statusCard.classList.add('status-run');
            else if (data.status === 'IDLE') statusCard.classList.add('status-idle');
            else if (data.status === 'ALARM') statusCard.classList.add('status-alarm');
            else statusCard.classList.add('bg-white', 'border-l-8');
            
            statusText.innerText = statusMap[data.status] || data.status;
        }
    }

    // 2. 更新重量與即時圖表
    if (data.weight !== undefined) {
        const weightVal = parseFloat(data.weight);
        const elWeight = document.getElementById('val-weight');
        if(elWeight) elWeight.innerText = weightVal.toFixed(2);
        
        // 更新圖表數據陣列 (Rolling Update)
        weightData.shift();
        timeLabels.shift();

        weightData.push(weightVal);
        timeLabels.push(new Date().toLocaleTimeString());

        // 確保圖表實例存在再更新
        if (weightChart) {
            weightChart.update('none'); 
        }
    }

    // 3. 更新魚種資訊
    if (data.fish_code) {
        const elFishCode = document.getElementById('val-fish-code');
        const elFishName = document.getElementById('val-fish-name');
        
        if (elFishCode) elFishCode.innerText = data.fish_code;
        if (elFishName) elFishName.innerText = fishMapping[data.fish_code] || data.fish_code;
    }
}