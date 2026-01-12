/**
 * Dashboard Logic v2.2
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

// Buffers
const maxDataPoints = 30;
let weightData = Array(maxDataPoints).fill(0);
let timeLabels = Array(maxDataPoints).fill('');

// --- 2. Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    loadFishMapping();
    initCharts();
    connectWebSocket();
    loadDailyStats(); // Renamed to avoid conflict
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
    const ctxWeight = document.getElementById('weightChart').getContext('2d');
    weightChart = new Chart(ctxWeight, {
        type: 'line',
        data: {
            labels: timeLabels,
            datasets: [{
                label: '重量 (kg)',
                data: weightData,
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderWidth: 2,
                tension: 0.3,
                fill: true,
                pointRadius: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            scales: {
                y: { beginAtZero: true, max: 5 },
                x: { display: false }
            },
            plugins: { legend: { display: false } }
        }
    });

    const ctxProd = document.getElementById('productionChart').getContext('2d');
    productionChart = new Chart(ctxProd, {
        type: 'doughnut',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: ['#10b981', '#f59e0b', '#ef4444', '#3b82f6', '#8b5cf6'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right', labels: { font: { size: 10 } } }
            }
        }
    });
}

// --- 3. WebSocket Connection ---
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    const ws = new WebSocket(wsUrl);

    const elIndicator = document.getElementById('ws-indicator');
    const elText = document.getElementById('ws-text');

    ws.onopen = () => {
        elIndicator.classList.remove('bg-red-500');
        elIndicator.classList.add('bg-green-500');
        elText.innerText = '連線中';
    };

    ws.onclose = () => {
        elIndicator.classList.remove('bg-green-500');
        elIndicator.classList.add('bg-red-500');
        elText.innerText = '離線';
        setTimeout(connectWebSocket, 3000);
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            updateDashboard(data);
        } catch (e) { console.error(e); }
    };
}

// --- 4. API Calls ---
async function loadDailyStats() {
    try {
        const result = await getDailyStats();
        
        productionChart.data.labels = result.labels;
        productionChart.data.datasets[0].data = result.data;
        productionChart.update();
    } catch (e) {
        console.error("Failed to fetch stats", e);
    }
}

// --- 5. UI Updates ---
function updateDashboard(data) {
    if (data.status) {
        const statusCard = document.getElementById('card-status');
        const statusText = document.getElementById('val-status');
        
        statusCard.classList.remove('status-run', 'status-idle', 'status-alarm', 'bg-white', 'border-l-8');
        
        if (data.status === 'RUN') statusCard.classList.add('status-run');
        else if (data.status === 'IDLE') statusCard.classList.add('status-idle');
        else if (data.status === 'ALARM') statusCard.classList.add('status-alarm');
        else statusCard.classList.add('bg-white', 'border-l-8');
        
        statusText.innerText = statusMap[data.status] || data.status;
    }

    if (data.weight !== undefined) {
        document.getElementById('val-weight').innerText = parseFloat(data.weight).toFixed(2);
        
        weightData.push(data.weight);
        weightData.shift();
        weightChart.update();
    }

    if (data.fish_code) {
        document.getElementById('val-fish-code').innerText = data.fish_code;
        document.getElementById('val-fish-name').innerText = fishMapping[data.fish_code] || data.fish_code;
    }
}