/**
 * Dashboard Logic v2.10 (Fix Status Styles)
 * Integrates WebSocket real-time updates and Chart.js
 * Uses Centralized API Module
 */

import { getFishTypes, getDailyStats, getSystemStatus } from './api.js';

// --- 1. State & Config ---
let fishMapping = {};
let lastMappingRefresh = 0;
let initialLoadComplete = false;

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

const maxDataPoints = 60; 
let weightData = Array(maxDataPoints).fill(null); 
let timeLabels = Array(maxDataPoints).fill('');

// --- 2. Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    console.log("Dashboard initializing...");
    initCharts();
    connectWebSocket();
    
    loadFishMapping()
        .then(() => loadCurrentStatus())
        .then(() => {
            checkDataLoop();
        });
        
    loadDailyStats(); 
});

async function loadCurrentStatus() {
    try {
        const data = await getSystemStatus();
        if (data && Object.keys(data).length > 0) {
            updateDashboard(data);
            if (data.fish_code) initialLoadComplete = true;
        }
    } catch (e) {
        console.warn("Initial API status load failed:", e);
    }
}

function checkDataLoop() {
    if (initialLoadComplete) return;

    const interval = setInterval(async () => {
        if (initialLoadComplete) {
            clearInterval(interval);
            return;
        }
        await loadCurrentStatus();
    }, 2000);
    
    setTimeout(() => clearInterval(interval), 30000);
}

async function loadFishMapping() {
    try {
        const data = await getFishTypes();
        fishMapping = {};
        data.forEach(item => {
            fishMapping[item.code] = item.name;
        });
        lastMappingRefresh = Date.now();

        const currentCodeEl = document.getElementById('val-fish-code');
        if (currentCodeEl) {
            const code = currentCodeEl.innerText;
            if (code && code !== '----') updateFishNameDisplay(code);
        }
    } catch (e) {
        console.error("Failed to load fish mapping:", e);
    }
}

function initCharts() {
    const weightCanvas = document.getElementById('weightChart');
    if (weightCanvas) {
        const ctxWeight = weightCanvas.getContext('2d');
        weightChart = new Chart(ctxWeight, {
            type: 'line',
            data: {
                labels: timeLabels,
                datasets: [{
                    label: '即時重量 (g)',
                    data: weightData,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true,
                    pointRadius: 0, 
                    pointHoverRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 0 },
                interaction: { mode: 'index', intersect: false },
                scales: {
                    y: { 
                        beginAtZero: true, 
                        suggestedMax: 3000, 
                        title: { display: true, text: 'g' }
                    },
                    x: { display: false }
                },
                plugins: { legend: { display: false }, tooltip: { enabled: true, animation: false }}
            }
        });
    }

    const prodCanvas = document.getElementById('productionChart');
    if (prodCanvas) {
        const ctxProd = prodCanvas.getContext('2d');
        productionChart = new Chart(ctxProd, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: ['#10b981', '#f59e0b', '#ef4444', '#3b82f6', '#8b5cf6', '#ec4899', '#6366f1'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'right', labels: { font: { size: 11 }, boxWidth: 12 }}
                }
            }
        });
    }
}

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    const ws = new WebSocket(wsUrl);
    const elIndicator = document.getElementById('ws-indicator');
    const elText = document.getElementById('ws-text');

    ws.onopen = () => {
        if(elIndicator) {
            elIndicator.classList.remove('bg-red-500');
            elIndicator.classList.add('bg-green-500');
        }
        if(elText) elText.innerText = '連線中';
    };

    ws.onclose = () => {
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
            if (data && (data.fish_code || data.weight !== undefined)) {
                initialLoadComplete = true; 
            }
            updateDashboard(data);
        } catch (e) { console.error("WS Message Error:", e); }
    };
}

// --- API Calls ---
async function loadDailyStats() {
    try {
        const result = await getDailyStats();
        if (productionChart && result.labels && result.data) {
            productionChart.data.labels = result.labels;
            productionChart.data.datasets[0].data = result.data;
            productionChart.update();
        }
    } catch (e) { console.error("Failed to fetch stats", e); }
}

// --- UI Updates ---
function updateDashboard(data) {
    if (data.status) {
        const statusCard = document.getElementById('card-status');
        const statusText = document.getElementById('val-status');
        
        if (statusCard && statusText) {
            // 先移除所有可能的狀態 class
            statusCard.classList.remove('status-run', 'status-idle', 'status-alarm', 'status-stop', 'bg-white', 'border-l-8');
            
            // 根據狀態加入對應 class
            switch (data.status) {
                case 'RUN':
                    statusCard.classList.add('status-run');
                    break;
                case 'IDLE':
                    statusCard.classList.add('status-idle');
                    break;
                case 'ALARM':
                    statusCard.classList.add('status-alarm');
                    break;
                case 'STOP':
                    statusCard.classList.add('status-stop');
                    break;
                default:
                    // 未知狀態或預設狀態，回復白色背景與左側邊框寬度
                    statusCard.classList.add('bg-white', 'border-l-8');
                    break;
            }
            
            statusText.innerText = statusMap[data.status] || data.status;
        }
    }

    if (data.weight !== undefined) {
        const weightVal = parseFloat(data.weight);
        const elWeight = document.getElementById('val-weight');
        if(elWeight) elWeight.innerText = weightVal.toFixed(0);
        
        weightData.shift();
        timeLabels.shift();
        weightData.push(weightVal);
        timeLabels.push(new Date().toLocaleTimeString());

        if (weightChart) weightChart.update('none'); 
    }

    if (data.fish_code) {
        const elFishCode = document.getElementById('val-fish-code');
        if (elFishCode) elFishCode.innerText = data.fish_code;
        updateFishNameDisplay(data.fish_code);
    }
}

function updateFishNameDisplay(code) {
    const elFishName = document.getElementById('val-fish-name');
    if (!elFishName) return;

    let displayName = fishMapping[code];

    if (!displayName) {
        displayName = code;
        const now = Date.now();
        if (now - lastMappingRefresh > 10000) {
            loadFishMapping();
        }
    }
    elFishName.innerText = displayName;
}