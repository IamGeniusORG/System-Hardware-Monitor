# ⬢ Quantum Monitor

## 🎥 Live Demonstrations
- **Windows (Dell G15):** [Download Video (Direct Link)](https://github.com/IamGeniusORG/System-Hardware-Monitor/raw/main/Tests/Dell%20g15%20testing.mp4)
- **macOS (Apple M4 Air):** [Download Video (Direct Link)](https://github.com/IamGeniusORG/System-Hardware-Monitor/raw/main/Tests/Apple%20M4%20Air%20testing.mp4)

> *Note: For Linux systems, the dashboard interface and functionality are pretty much the same as the Windows one!*

A lightweight, futuristic, cross-platform hardware resource monitor. This dashboard dynamically tracks your system's CPU, RAM, Storage I/O, Network Latency, Top Processes, and GPU utilization in real-time without dragging down system performance.

## 🚀 Features
- **Universal Cross-Platform Engine:** Runs seamlessly on Windows, macOS (including Apple Silicon), and Linux.
- **Deep Hardware Profiling:** Natively scans and detects hardware-level specs including RAM generation/speed (e.g., DDR5 @ 4800MHz), exact SSD NVMe PCIe generation, and true CPU Base Frequencies.
- **Dynamic Auto-Scaling I/O:** Real-time Disk Read/Write and Network Up/Down speeds intelligently auto-scale between B/s, KB/s, and MB/s just like native OS task managers.
- **Task Manager AI:** Groups background processes intelligently by exact memory usage (MB), perfectly mimicking native task managers.
- **Universal GPU Detection:** Gracefully falls back to OS-native APIs (`lspci`, `system_profiler`) if an NVIDIA driver isn't found.
- **Smart Analytics:** Tracks exact internet latency (TCP ping), active system uptime, and battery states.
- **One-Click Export:** Download your entire real-time monitoring session to a CSV file instantly for game benchmarking or troubleshooting.
- **Dynamic Theming:** Switch instantly between sleek "Frosted Light Mode" and "Cyberpunk Dark Mode".

---

## 🛠️ Installation & Setup

This monitor requires **Python 3.8+** to be installed on your system.

### 1. Clone the Repository
```bash
git clone https://github.com/IamGeniusORG/System-Hardware-Monitor.git
cd System-Hardware-Monitor
```

### 2. Install Dependencies
It's highly recommended to use a virtual environment, but you can also install the dependencies globally.

**For Windows:**
```bash
pip install -r requirements.txt
```

**For macOS / Linux:**
```bash
pip3 install -r requirements.txt
```

*(Note for Linux users: Depending on your distribution, you may need to ensure `pciutils` is installed if you want integrated GPU detection, which is usually pre-installed on modern distros).*

### 3. Launch the Monitor
Once dependencies are installed, start the backend server:

**For Windows:**
```bash
python app.py
```

**For macOS / Linux:**
```bash
python3 app.py
```

### 4. Open the Dashboard
Once you have done all the steps above and the server is running, then go to this link in your web browser:
**👉 [http://127.0.0.1:5000](http://127.0.0.1:5000)**

<!-- Test Commit -->