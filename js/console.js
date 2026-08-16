(function () {
  var devicesEl = document.getElementById("tuiDevices");
  var logEl = document.getElementById("tuiLog");
  var lagEl = document.getElementById("tuiLag");

  var DEVICES = [
    { ip: "192.168.1.1", label: "ROUTER", base: 2, var: 3 },
    { ip: "192.168.1.5", label: "YOUR PC", base: 12, var: 8 },
    { ip: "192.168.1.9", label: "TV", base: 84, var: 26 },
    { ip: "192.168.1.12", label: "PHONE", base: 26, var: 16 },
    { ip: "192.168.1.23", label: "XIAOMI IOT", base: 48, var: 40 },
    { ip: "192.168.1.33", label: "LAPTOP", base: 9, var: 6 }
  ];

  function pingClass(ms) {
    if (ms < 30) return "ok";
    if (ms < 80) return "warn";
    return "bad";
  }

  var rows = [];
  var pings = DEVICES.map(function (d) { return d.base; });

  if (devicesEl) {
    DEVICES.forEach(function (d, i) {
      var row = document.createElement("div");
      row.className = "tui-row";
      var ip = document.createElement("span");
      ip.className = "c-ip";
      ip.textContent = d.ip;
      var lab = document.createElement("span");
      lab.className = "c-label";
      lab.textContent = d.label;
      var ping = document.createElement("span");
      ping.className = "c-ping ok";
      ping.textContent = pings[i] + "ms";
      row.appendChild(ip); row.appendChild(lab); row.appendChild(ping);
      devicesEl.appendChild(row);
      rows.push({ row: row, ping: ping, cfg: d });
    });
  }

  setInterval(function () {
    for (var i = 0; i < rows.length; i++) {
      var v = pings[i] + (Math.random() * rows[i].cfg.var * 2 - rows[i].cfg.var);
      v = Math.max(1, Math.round(v));
      pings[i] = v;
      rows[i].ping.textContent = v + "ms";
      rows[i].ping.className = "c-ping " + pingClass(v);
    }
  }, 1600);

  var LOG_LINES = [
    "[+] SlowFuck Pro initialized",
    "[+] Gateway: 192.168.1.1   My IP: 192.168.1.5",
    "[*] Scanning 192.168.1.23...",
    "[+] Scan complete: 2 open ports | OS: Android 11",
    "[*] Starting lag on 192.168.1.23 \u2014 delay 2000ms + 500ms jitter",
    "[+] LAG ACTIVE",
    "[!] Cleanup complete \u2014 forwarding off, shaping removed",
    "[*] Refreshing ARP table...",
    "[+] 8 devices found, 2 of them suspiciously new",
    "[+] Port probe: 80 OPEN, 8080 OPEN on 192.168.1.9",
    "[*] Device 192.168.1.12 reconnecting... again",
    "[+] Netem applied to 192.168.1.23 \u2014 it feels slow, it IS slow"
  ];

  function logLine(text, cls) {
    if (!logEl) return;
    var line = document.createElement("div");
    line.className = "lg " + (cls || "");
    line.textContent = text;
    logEl.appendChild(line);
    while (logEl.childNodes.length > 7) logEl.removeChild(logEl.firstChild);
    logEl.scrollTop = logEl.scrollHeight;
  }

  var li = 0;
  function logLoop() {
    var l = LOG_LINES[li % LOG_LINES.length];
    var cls = "";
    if (l.indexOf("LAG ACTIVE") !== -1) cls = "lg-red";
    else if (l.indexOf("[+]") === 0) cls = "lg-green";
    else if (l.indexOf("[!]") === 0) cls = "lg-amber";
    logLine(l, cls);
    li++;
    setTimeout(logLoop, 2100 + Math.random() * 1800);
  }
  setTimeout(logLoop, 1400);

  if (lagEl) {
    var base = 2000;
    setInterval(function () {
      lagEl.textContent = base + "ms";
    }, 3000);
    setInterval(function () {
      base = [500, 1000, 2000, 3000, 5000][Math.floor(Math.random() * 5)];
      lagEl.textContent = base + "ms";
    }, 4600);
  }

  /* ---- lag gauge ---- */
  var fill = document.getElementById("gaugeFill");
  var dot = document.getElementById("gaugeDot");
  var delayEl = document.getElementById("gaugeDelay");
  var jitterEl = document.getElementById("gaugeJitter");
  var targetEl = document.getElementById("gaugeTarget");

  var PRESETS = [
    [500, 100], [1000, 300], [2000, 500], [3000, 800], [5000, 1000]
  ];
  var targets = ["XIAOMI IOT", "TV", "PHONE", "LAPTOP", "XIAOMI IOT"];

  function setGauge(delay, jitter) {
    if (!fill || !delayEl || !jitterEl) return;
    delayEl.textContent = String(delay);
    jitterEl.textContent = String(jitter);
    var pct = Math.min(100, (delay / 5000) * 100);
    fill.style.width = pct + "%";
    if (dot) dot.style.left = pct + "%";
    fill.className = "gauge-fill " + (delay >= 3000 ? "gauge-red" : delay >= 1000 ? "gauge-amber" : "gauge-green");
  }

  var gi = 0;
  function gaugeLoop() {
    var p = PRESETS[gi % PRESETS.length];
    if (targetEl) targetEl.textContent = targets[gi % targets.length];
    setGauge(p[0], p[1]);
    gi++;
    setTimeout(gaugeLoop, 3200);
  }
  if (fill) setTimeout(gaugeLoop, 900);

  /* ---- scroll reveal ---- */
  var revealIO = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) {
        e.target.classList.add("in");
        revealIO.unobserve(e.target);
      }
    });
  }, { threshold: 0.12 });
  document.querySelectorAll(".reveal").forEach(function (el, i) {
    el.style.setProperty("--d", String((i % 4) * 0.07) + "s");
    revealIO.observe(el);
  });
})();
