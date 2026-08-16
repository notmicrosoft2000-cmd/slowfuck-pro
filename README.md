# SlowFuck Pro

A terminal network operations tool. It maps the local network — devices, vendors, pings, ports, OSes — and carries a lag engine for when a device needs a little humility.

**Features**
- ARP device scan with vendor labels (router, phones, TVs, IoT…)
- Live per-device ping tracking, colour-coded by latency
- Port probe across 18 common ports + OS detection via nmap
- Device info dossier: IP, MAC, vendor, label, ports, OS
- LAG ENGINE: ARP spoof + netem traffic shaping, applying configurable delay and jitter
- Operations log of everything it does
- Full curses TUI — keyboard driven

**Controls**

```
↑ ↓          navigate devices
ENTER        apply lag to the selected device
SPACE        stop lag
s            scan selected device
r            refresh network scan
h            help
q            quit
1-5          delay presets (500ms → 5000ms "brutal")
6-0          jitter presets (100ms → 1000ms "chaotic")
```

**Run it**

```bash
sudo apt install arp-scan arpspoof nmap netcat-openbsd
sudo python3 slowfuckpro.py
```

Needs root. It refuses to lag the gateway or itself.

**A note:** use this on your own network. Traffic shaping on machines you don't control may be against your provider's rules — the tool cleans up after itself, but it is your network and your call.

A Neptune Productions project.
