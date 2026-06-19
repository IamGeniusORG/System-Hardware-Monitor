from flask import Flask, render_template, jsonify
import psutil
import GPUtil
import time
import cpuinfo
import platform
import threading
import subprocess
import os
import socket

app = Flask(__name__)

# Cache static system specs
system_specs = None
fallback_gpu_name = None

# Global state for accurate real-time stats
current_stats = {
    'cpu_percent': 0.0,
    'ram_percent': 0.0,
    'ram_used_gb': 0.0,
    'gpus': [],
    'disk': {'read_bytes_sec': 0, 'write_bytes_sec': 0},
    'network': {'bytes_recv_sec': 0, 'bytes_sent_sec': 0, 'ping_ms': 0},
    'top_processes': [],
    'system': {'uptime_sec': 0, 'battery_percent': None, 'battery_plugged': None},
    'timestamp': time.time()
}

def get_os_info():
    sys_os = platform.system()
    machine = platform.machine()
    if machine.upper() == 'AMD64':
        machine = 'x64'
        
    if sys_os == 'Darwin':
        mac_ver = platform.mac_ver()[0]
        return f"macOS {mac_ver} ({machine})"
    elif sys_os == 'Linux':
        try:
            with open('/etc/os-release') as f:
                for line in f:
                    if line.startswith('PRETTY_NAME='):
                        return line.split('=')[1].strip().strip('"') + f" ({machine})"
        except Exception:
            pass
        return f"Linux {platform.release()} ({machine})"
    else:
        return f"Windows {platform.release()} ({machine})"

def get_fallback_gpu():
    global fallback_gpu_name
    if fallback_gpu_name: return fallback_gpu_name
    
    sys_os = platform.system()
    fallback_gpu_name = "Primary Display Adapter"
    
    try:
        if sys_os == 'Windows':
            out = subprocess.check_output(['wmic', 'path', 'win32_VideoController', 'get', 'name'], text=True, creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            lines = [l.strip() for l in out.split('\n') if l.strip() and l.strip().lower() != 'name']
            if lines: fallback_gpu_name = lines[0]
        elif sys_os == 'Darwin':
            out = subprocess.check_output(['system_profiler', 'SPDisplaysDataType'], text=True)
            for line in out.split('\n'):
                if 'Chipset Model:' in line:
                    fallback_gpu_name = line.split(':')[1].strip()
                    break
        elif sys_os == 'Linux':
            out = subprocess.check_output("lspci | grep -i 'vga\\|3d\\|display'", shell=True, text=True)
            if out:
                parts = out.strip().split(': ')
                if len(parts) > 1:
                    fallback_gpu_name = parts[-1].split(' (')[0].strip()
    except Exception:
        pass
        
    return fallback_gpu_name

def get_system_specs():
    global system_specs
    if system_specs is None:
        try:
            info = cpuinfo.get_cpu_info()
            cpu_name = info.get('brand_raw', platform.processor())
        except Exception:
            cpu_name = platform.processor()
            if not cpu_name: cpu_name = "Unknown CPU"
        
        cpu_cores = psutil.cpu_count(logical=False) or 0
        cpu_threads = psutil.cpu_count(logical=True) or 0
        ram_total = round(psutil.virtual_memory().total / (1024**3), 2)
        os_name = get_os_info()
        sys_os = platform.system()
        
        def get_base_dev(device):
            import re
            if device.startswith('/dev/disk'):
                return re.sub(r's\d+.*$', '', device)
            if device.startswith('/dev/sd') or device.startswith('/dev/vd'):
                return re.sub(r'\d+$', '', device)
            if device.startswith('/dev/nvme'):
                return re.sub(r'p\d+$', '', device)
            return device

        disks = []
        seen_base_devices = set()
        
        for part in psutil.disk_partitions(all=False):
            if 'cdrom' in part.opts or part.fstype == '':
                continue
            if part.device.startswith('/dev/loop') or part.fstype in ('tmpfs', 'devtmpfs', 'squashfs'):
                continue
            
            base_dev = get_base_dev(part.device)
            if base_dev in seen_base_devices:
                continue
                
            try:
                usage = psutil.disk_usage(part.mountpoint)
                total_gb = round(usage.total / (1024**3), 2)
                used_gb = round(usage.used / (1024**3), 2)
                if total_gb > 0:
                    seen_base_devices.add(base_dev)
                    disks.append({
                        'device': part.device,
                        'mountpoint': part.mountpoint,
                        'total_gb': total_gb,
                        'used_gb': used_gb
                    })
            except PermissionError:
                continue

        system_specs = {
            'cpu': {'name': cpu_name, 'cores': cpu_cores, 'threads': cpu_threads},
            'ram': {'total_gb': ram_total},
            'os': os_name,
            'disks': disks,
            'fallback_gpu': get_fallback_gpu()
        }
    return system_specs

def get_ping_ms():
    """Cross-platform TCP ping to measure internet latency."""
    try:
        start = time.perf_counter()
        socket.create_connection(('8.8.8.8', 53), timeout=1.0)
        end = time.perf_counter()
        return round((end - start) * 1000)
    except Exception:
        return 0

def get_top_processes():
    """Get top 5 processes by exact memory usage in MB, grouped by name to match Task Manager."""
    proc_groups = {}
    try:
        for p in psutil.process_iter(['name', 'memory_info']):
            try:
                info = p.info
                name = info['name']
                if not name:
                    continue
                
                mem = info['memory_info'].rss if info['memory_info'] else 0
                
                # Group processes with the same name (e.g. multiple chrome.exe)
                if name in proc_groups:
                    proc_groups[name] += mem
                else:
                    proc_groups[name] = mem
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
                
        # Sort by grouped memory descending
        sorted_procs = sorted(proc_groups.items(), key=lambda item: item[1], reverse=True)
        
        # Take top 5 and convert bytes to MB
        top_5 = []
        for name, mem_bytes in sorted_procs[:5]:
            mem_mb = mem_bytes / (1024 * 1024)
            top_5.append({
                'name': name,
                'memory_mb': round(mem_mb, 1)
            })
        return top_5
    except Exception:
        return []

def hardware_monitor_thread():
    """Background thread to poll hardware accurately."""
    global current_stats
    
    last_disk = None
    last_net = psutil.net_io_counters()
    last_time = time.time()
    
    # Initialize CPU for processes
    for p in psutil.process_iter(['cpu_percent']): pass
    
    # Prime the non-blocking CPU percent
    psutil.cpu_percent(interval=None)
    
    sys_os = platform.system()
    
    while True:
        # Sleep exactly 1 second to gather average usage smoothly
        time.sleep(1.0)
        
        # interval=None calculates CPU over the exact time elapsed since last call,
        # which is extremely accurate and avoids micro-spikes on Apple Silicon.
        cpu_percent = psutil.cpu_percent(interval=None)
        current_time = time.time()
        dt = current_time - last_time
        
        # RAM
        ram = psutil.virtual_memory()
        
        # Disk IO
        disk_counters = psutil.disk_io_counters(perdisk=True)
        if disk_counters:
            r_bytes = sum(d.read_bytes for d in disk_counters.values())
            w_bytes = sum(d.write_bytes for d in disk_counters.values())
            if last_disk is None:
                disk_r_sec = 0
                disk_w_sec = 0
            else:
                disk_r_sec = max(0, (r_bytes - last_disk['read_bytes']) / dt)
                disk_w_sec = max(0, (w_bytes - last_disk['write_bytes']) / dt)
            last_disk = {'read_bytes': r_bytes, 'write_bytes': w_bytes}
        else:
            disk_r_sec = 0
            disk_w_sec = 0
        
        # Net IO
        net = psutil.net_io_counters()
        net_r_sec = max(0, (net.bytes_recv - last_net.bytes_recv) / dt) if net and last_net else 0
        net_s_sec = max(0, (net.bytes_sent - last_net.bytes_sent) / dt) if net and last_net else 0
        last_net = net
        ping_ms = get_ping_ms()
        
        # GPU
        try:
            gpus = GPUtil.getGPUs()
        except Exception:
            gpus = []
            
        gpu_data = []
        if gpus:
            for gpu in gpus:
                gpu_data.append({
                    'id': gpu.id,
                    'name': gpu.name,
                    'load': round(gpu.load * 100, 1),
                    'mem_util': round(gpu.memoryUtil * 100, 1),
                    'mem_used': round(gpu.memoryUsed, 1),
                    'mem_total': round(gpu.memoryTotal, 1),
                    'temperature': gpu.temperature,
                    'is_nvidia': True,
                    'vendor': 'nvidia'
                })
        else:
            fallback = get_fallback_gpu()
            vendor = 'apple' if 'apple' in fallback.lower() else 'amd' if 'amd' in fallback.lower() or 'radeon' in fallback.lower() else 'intel' if 'intel' in fallback.lower() else 'unknown'
            
            g_load = 0
            g_mem_util = 0
            g_mem_used = 0
            g_mem_total = 0
            g_temp = 0
            
            if sys_os == 'Darwin' and vendor == 'apple':
                try:
                    import re
                    out = subprocess.check_output(["ioreg", "-l", "-d", "1", "-w", "0", "-r", "-c", "AppleAGX"], text=True)
                    match = re.search(r'"Device Utilization %"\s*=\s*(\d+)', out)
                    if match:
                        g_load = int(match.group(1))
                except Exception:
                    pass
                
                # Apple Silicon Unified Memory
                g_mem_total = round(ram.total / (1024**2))
                g_mem_used = round(ram.used / (1024**2))
                g_mem_util = round((g_mem_used / g_mem_total) * 100, 1) if g_mem_total else 0
            
            gpu_data.append({
                'id': 0,
                'name': fallback,
                'load': g_load, 'mem_util': g_mem_util, 'mem_used': g_mem_used, 'mem_total': g_mem_total, 'temperature': g_temp,
                'is_nvidia': False,
                'vendor': vendor
            })
            
        # Top Processes
        top_procs = get_top_processes()
        
        # System & Battery
        uptime = current_time - psutil.boot_time()
        batt = psutil.sensors_battery()
        batt_pct = batt.percent if batt else None
        batt_plug = batt.power_plugged if batt else None
                
        last_time = current_time

        # Update global stats
        current_stats = {
            'timestamp': current_time,
            'cpu_percent': cpu_percent,
            'ram_percent': ram.percent,
            'ram_used_gb': round(ram.used / (1024**3), 2),
            'gpus': gpu_data,
            'disk': {'read_bytes_sec': disk_r_sec, 'write_bytes_sec': disk_w_sec},
            'network': {'bytes_recv_sec': net_r_sec, 'bytes_sent_sec': net_s_sec, 'ping_ms': ping_ms},
            'top_processes': top_procs,
            'system': {'uptime_sec': uptime, 'battery_percent': batt_pct, 'battery_plugged': batt_plug}
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/specs')
def specs():
    return jsonify(get_system_specs())

@app.route('/api/stats')
def stats():
    return jsonify(current_stats)

if __name__ == '__main__':
    monitor = threading.Thread(target=hardware_monitor_thread, daemon=True)
    monitor.start()
    
    print("Dashboard starting with all Advanced Features! Open http://127.0.0.1:5000 in your browser.")
    app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=False)
