/**
 * Dashboard Logic v2.0
 * Integrates WebSocket real-time updates and Chart.js
 */

// --- 1. State & Config ---
// In a real app, load this from /api/categories or enums.js
const fishMapping = {
    'F001': '白鯧 (White Pomfret)',
    'F002': '鮭魚 (Salmon)',
    'F003': '鮪魚 (Tuna)',
    'F004': '吳郭魚 (Tilapia)'
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
    initCharts();
    connectWebSocket();
    fetchDailyStats(); // Load initial pie chart data
});

function initCharts() {
    // A. Weight Trend Line Chart
    const ctxWeight = document.getElementById('weightChart').getContext('2d');
    weightChart = new Chart(ctxWeight, {
        type: 'line',
        data: {
            labels: timeLabels,
            datasets: [{
                label: 'Weight (kg)',
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
            animation: false, // Disable animation for performance on high-rate updates
            scales: {
                y: { beginAtZero: true, max: 5 },
                x: { display: false }
            },
            plugins: { legend: { display: false } }
        }
    });

    // B. Production Pie Chart (Initial Empty)
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
        elText.innerText = 'ONLINE';
        console.log("WebSocket Connected");
    };

    ws.onclose = () => {
        elIndicator.classList.remove('bg-green-500');
        elIndicator.classList.add('bg-red-500');
        elText.innerText = 'OFFLINE';
        setTimeout(connectWebSocket, 3000); // Reconnect logic
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            updateDashboard(data);
        } catch (e) {
            console.error("Parse Error", e);
        }
    };
}

// --- 4. API Calls ---
async function fetchDailyStats() {
    try {
        const response = await fetch('/api/history/stats');
        const result = await response.json();
        
        // Update Chart
        productionChart.data.labels = result.labels;
        productionChart.data.datasets[0].data = result.data;
        productionChart.update();
    } catch (e) {
        console.error("Failed to fetch stats", e);
    }
}

// --- 5. UI Updates ---
function updateDashboard(data) {
    // 5.1 Status Coloring
    if (data.status) {
        const statusCard = document.getElementById('card-status');
        const statusText = document.getElementById('val-status');
        
        statusCard.classList.remove('status-run', 'status-idle', 'status-alarm', 'bg-white', 'border-l-8');
        
        if (data.status === 'RUN') {
            statusCard.classList.add('status-run');
        } else if (data.status === 'IDLE') {
            statusCard.classList.add('status-idle');
        } else if (data.status === 'ALARM') {
            statusCard.classList.add('status-alarm');
        } else {
            statusCard.classList.add('bg-white', 'border-l-8');
        }
        statusText.innerText = data.status;
    }

    // 5.2 Numeric Values
    if (data.weight !== undefined) {
        document.getElementById('val-weight').innerText = parseFloat(data.weight).toFixed(2);
        
        // Update Chart Buffer
        weightData.push(data.weight);
        weightData.shift();
        weightChart.update();
    }

    if (data.fish_code) {
        document.getElementById('val-fish-code').innerText = data.fish_code;
        document.getElementById('val-fish-name').innerText = fishMapping[data.fish_code] || data.fish_code;
    }
}