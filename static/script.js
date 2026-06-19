// Global Defaults
Chart.defaults.color = '#64748b';
Chart.defaults.font.family = "'Orbitron', sans-serif";

function getThemeColors() {
    const isLight = document.body.classList.contains('light-theme');
    return {
        bgStart: isLight ? 'rgba(255,255,255,0.8)' : 'rgba(10, 15, 25, 0.9)',
        cpuBg: isLight ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.05)'
    };
}

Chart.defaults.plugins.tooltip.backgroundColor = getThemeColors().bgStart;

// Helpers
function createGradient(ctx, colorStart, colorEnd) {
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, colorStart);
    gradient.addColorStop(1, colorEnd);
    return gradient;
}

const gaugeOptions = {
    responsive: true, maintainAspectRatio: false, cutout: '80%',
    plugins: { tooltip: { enabled: false }, legend: { display: false } },
    animation: { duration: 500, easing: 'easeOutQuart' }
};

const lineOptions = {
    responsive: true, maintainAspectRatio: false,
    scales: { y: { beginAtZero: true, display: false }, x: { display: false } },
    plugins: { legend: { display: false } },
    elements: { point: { radius: 0 } },
    animation: { duration: 0 }
};

// State
const maxPoints = 40;
const labels = Array(maxPoints).fill('');
const gpuCoreData = Array(maxPoints).fill(0);
const gpuMemData = Array(maxPoints).fill(0);

// Export Data Collection
let exportData = [["Timestamp", "CPU (%)", "RAM (%)", "GPU Core (%)", "GPU VRAM (%)", "GPU Temp (C)"]];
let isRecording = true;

// Charts
const cpuCtx = document.getElementById('cpuGauge').getContext('2d');
const cpuChart = new Chart(cpuCtx, {
    type: 'doughnut',
    data: {
        labels: ['Used', 'Free'],
        datasets: [{ data: [0, 100], backgroundColor: ['#0ea5e9', 'rgba(255,255,255,0.05)'], borderWidth: 0 }]
    },
    options: gaugeOptions
});

const ramCtx = document.getElementById('ramGauge').getContext('2d');
const ramChart = new Chart(ramCtx, {
    type: 'doughnut',
    data: {
        labels: ['Used', 'Free'],
        datasets: [{ data: [0, 100], backgroundColor: ['#a855f7', 'rgba(255,255,255,0.05)'], borderWidth: 0 }]
    },
    options: gaugeOptions
});

const gpuCtx = document.getElementById('mainGpuChart').getContext('2d');
const gpuChart = new Chart(gpuCtx, {
    type: 'line',
    data: {
        labels: labels,
        datasets: [
            { label: 'CUDA Core %', data: gpuCoreData, borderColor: '#10b981', backgroundColor: createGradient(gpuCtx, 'rgba(16, 185, 129, 0.2)', 'transparent'), fill: true, borderWidth: 2, tension: 0.4 },
            { label: 'VRAM %', data: gpuMemData, borderColor: '#a855f7', backgroundColor: 'transparent', borderWidth: 2, tension: 0.4, borderDash: [5, 5] }
        ]
    },
    options: {
        ...lineOptions,
        scales: { y: { display: true, grid: { color: 'rgba(148,163,184,0.1)' }, max: 100 }, x: { display: false } },
        plugins: { legend: { display: true, position: 'top', labels: { color: '#64748b', boxWidth: 12 } } }
    }
});

// UI Logic
function updateArray(arr, val) { arr.push(val); arr.shift(); }

function formatBytes(bytesPerSec) {
    if (bytesPerSec === 0) return '0 MB/s';
    return (bytesPerSec / (1024 * 1024)).toFixed(1) + ' MB/s';
}

function formatBits(bytesPerSec) {
    if (bytesPerSec === 0) return '0 Mbps';
    return ((bytesPerSec * 8) / (1024 * 1024)).toFixed(1) + ' Mbps';
}

function formatUptime(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return `${h}h ${m}m`;
}

// Alerts Logic
let alertPlaying = false;
function handleAlerts(temp, ram) {
    const gpuPanel = document.getElementById('gpu-panel');
    const ramPanel = document.getElementById('ram-panel');
    const audio = document.getElementById('alert-sound');
    
    let critical = false;

    if (temp >= 85) { gpuPanel.classList.add('alert-flash'); critical = true; }
    else { gpuPanel.classList.remove('alert-flash'); }

    if (ram >= 95) { ramPanel.classList.add('alert-flash'); critical = true; }
    else { ramPanel.classList.remove('alert-flash'); }

    if (critical && !alertPlaying) {
        audio.play().catch(e => console.log("Audio play blocked by browser."));
        alertPlaying = true;
    } else if (!critical) {
        alertPlaying = false;
    }
}

// Fetch Logic
async function fetchSpecs() {
    try {
        const res = await fetch('/api/specs');
        const specs = await res.json();
        
        document.getElementById('os-name').innerText = specs.os;
        document.getElementById('cpu-name').innerText = specs.cpu.name;
        document.getElementById('cpu-cores').innerText = specs.cpu.cores;
        document.getElementById('cpu-threads').innerText = specs.cpu.threads;
        document.getElementById('ram-total').innerText = specs.ram.total_gb + " GB TOTAL";
        
        let totalUsed = 0;
        let totalCap = 0;
        specs.disks.forEach(d => {
            totalUsed += (d.used_gb || 0);
            totalCap += (d.total_gb || 0);
        });
        document.getElementById('disk-list').innerText = `${totalUsed.toFixed(1)} GB / ${totalCap.toFixed(1)} GB USED`;
    } catch (e) {}
}

async function fetchStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();

        // Uptime & Battery
        document.getElementById('uptime-val').innerText = "Uptime: " + formatUptime(data.system.uptime_sec);
        if (data.system.battery_percent !== null) {
            const battEl = document.getElementById('batt-val');
            battEl.style.display = 'inline-block';
            battEl.innerText = `Battery: ${Math.round(data.system.battery_percent)}% ${data.system.battery_plugged ? '⚡' : ''}`;
        }

        // CPU
        document.getElementById('cpu-val').innerText = Math.round(data.cpu_percent);
        cpuChart.data.datasets[0].data = [data.cpu_percent, 100 - data.cpu_percent];
        cpuChart.update();

        // RAM
        document.getElementById('ram-val').innerText = Math.round(data.ram_percent);
        document.getElementById('ram-used').innerText = data.ram_used_gb;
        ramChart.data.datasets[0].data = [data.ram_percent, 100 - data.ram_percent];
        ramChart.update();

        // GPU
        let gTemp = 0, gLoad = 0, gMemUtil = 0;
        if (data.gpus && data.gpus.length > 0) {
            const gpu = data.gpus[0];
            gTemp = gpu.temperature;
            gLoad = gpu.load;
            gMemUtil = gpu.mem_util;

            document.getElementById('gpu-name').innerText = gpu.name.toUpperCase();
            document.getElementById('gpu-load').innerText = gLoad;
            document.getElementById('gpu-mem-mb').innerText = gpu.mem_used;
            document.getElementById('gpu-mem').innerText = gMemUtil;
            document.getElementById('gpu-mem-total').innerText = gpu.mem_total;
            
            if (gpu.vendor === 'apple' && gTemp === 0) {
                document.getElementById('gpu-temp').innerText = 'N/A';
                document.getElementById('gpu-temp-unit').style.display = 'none';
            } else {
                document.getElementById('gpu-temp').innerText = gTemp;
                document.getElementById('gpu-temp-unit').style.display = 'inline';
            }

            if (gpu.vendor === 'nvidia') {
                document.getElementById('gpu-core-label').innerText = 'CUDA CORE';
                document.getElementById('gpu-mem-label').innerText = 'VRAM';
                gpuChart.data.datasets[0].label = 'CUDA Core %';
                gpuChart.data.datasets[1].label = 'VRAM %';
            } else if (gpu.vendor === 'apple') {
                document.getElementById('gpu-core-label').innerText = 'METAL CORE';
                document.getElementById('gpu-mem-label').innerText = 'UNIFIED MEM';
                gpuChart.data.datasets[0].label = 'Metal Core %';
                gpuChart.data.datasets[1].label = 'Unified Mem %';
            } else {
                document.getElementById('gpu-core-label').innerText = 'GPU CORE';
                document.getElementById('gpu-mem-label').innerText = 'VRAM';
                gpuChart.data.datasets[0].label = 'GPU Core %';
                gpuChart.data.datasets[1].label = 'VRAM %';
            }

            updateArray(gpuCoreData, gLoad);
            updateArray(gpuMemData, gMemUtil);
            gpuChart.update();
        }

        // Handle Alerts
        handleAlerts(gTemp, data.ram_percent);

        // I/O & Ping
        document.getElementById('disk-read').innerText = formatBytes(data.disk.read_bytes_sec);
        document.getElementById('disk-write').innerText = formatBytes(data.disk.write_bytes_sec);
        document.getElementById('net-recv').innerText = formatBits(data.network.bytes_recv_sec);
        document.getElementById('net-sent').innerText = formatBits(data.network.bytes_sent_sec);
        document.getElementById('net-ping').innerText = data.network.ping_ms + ' ms';

        // Top Processes
        const procList = document.getElementById('process-list');
        procList.innerHTML = '';
        data.top_processes.forEach(p => {
            procList.innerHTML += `
                <div class="proc-item">
                    <span class="proc-name">${p.name}</span>
                    <span class="proc-mem">${p.memory_mb} MB</span>
                </div>
            `;
        });

        // Record for Export
        if (isRecording) {
            const timeStr = new Date(data.timestamp * 1000).toLocaleTimeString();
            exportData.push([timeStr, data.cpu_percent, data.ram_percent, gLoad, gMemUtil, gTemp]);
            // Limit memory usage
            if (exportData.length > 3600) exportData.splice(1, 1);
        }

    } catch (e) {}
}

// Actions
document.getElementById('theme-toggle').addEventListener('click', () => {
    document.body.classList.toggle('light-theme');
    const isLight = document.body.classList.contains('light-theme');
    document.getElementById('theme-toggle').innerText = isLight ? '🌙 DARK' : '☀️ LIGHT';
    
    // Update chart backgrounds
    const colors = getThemeColors();
    cpuChart.data.datasets[0].backgroundColor[1] = colors.cpuBg;
    ramChart.data.datasets[0].backgroundColor[1] = colors.cpuBg;
    Chart.defaults.plugins.tooltip.backgroundColor = colors.bgStart;
    
    cpuChart.update(); ramChart.update(); gpuChart.update();
});

document.getElementById('export-csv').addEventListener('click', () => {
    let csvContent = "data:text/csv;charset=utf-8," 
        + exportData.map(e => e.join(",")).join("\n");
    
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "quantum_monitor_log.csv");
    document.body.appendChild(link);
    link.click();
    link.remove();
});

// Init
fetchSpecs();
setInterval(fetchStats, 1000);
fetchStats();
