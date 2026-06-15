// BUILT_IN_THEMES is loaded from themes.js before this script

let config = { serverUrl: 'http://localhost:7070', pollInterval: 3000 };
let pollTimer = null;

const $ = id => document.getElementById(id);

function hexToRgba(hex, opacity) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${opacity})`;
}

function resolveTheme(cfg) {
  if (BUILT_IN_THEMES[cfg.theme]) return BUILT_IN_THEMES[cfg.theme];
  if (cfg.customThemes?.[cfg.theme]) return cfg.customThemes[cfg.theme];
  return BUILT_IN_THEMES['dark-blue'];
}

function applyTheme(cfg) {
  const t = resolveTheme(cfg);
  const opacity = cfg.opacity ?? 0.87;
  const root = document.documentElement;
  root.style.setProperty('--bg',     hexToRgba(t.bgColor, opacity));
  root.style.setProperty('--text-1', t.textPrimary);
  root.style.setProperty('--text-2', t.textSecondary);
  root.style.setProperty('--cpu',    t.cpu);
  root.style.setProperty('--gpu',    t.gpu);
  root.style.setProperty('--mem',    t.mem);
  root.style.setProperty('--disk',   t.disk || '#818cf8');
  root.style.setProperty('--up',     t.netUp);
  root.style.setProperty('--dn',     t.netDown);
}

function setText(id, val) {
  const el = $(id);
  if (el) el.textContent = val;
}

function setBar(id, pct) {
  const el = $(id);
  if (el) el.style.width = `${Math.max(0, Math.min(100, pct ?? 0))}%`;
}

function applyMetrics(m) {
  const dot = $('status-dot');
  if (dot) dot.className = 'status-dot' + (m.online ? ' online' : '');
  setText('hostname',  m.hostname    || 'unknown');
  setText('cpu-pct',   `${m.cpu}%`);
  setBar('cpu-bar',     m.cpu);
  setText('cpu-temp',   m.cpu_temp   ? `${m.cpu_temp}°C` : '—');
  setText('gpu-pct',      `${m.gpu_util}%`);
  setBar('gpu-bar',        m.gpu_util);
  setText('gpu-name',      m.gpu_name    || '—');
  setText('gpu-temp',      m.gpu_temp    ? `${m.gpu_temp}°C` : '—');
  setText('gpu-vram-pct', `${m.gpu_vram_pct}%`);
  setBar('vram-bar',       m.gpu_vram_pct);
  setText('gpu-vram',     `${m.gpu_vram_used_gb} / ${m.gpu_vram_total_gb} GB`);
  setText('gpu-power',     m.gpu_power_w ? `${m.gpu_power_w} W` : '—');
  setText('mem-pct',   `${m.mem_pct}%`);
  setBar('mem-bar',     m.mem_pct);
  setText('mem-usage', `${m.mem_used_gb} / ${m.mem_total_gb} GB`);
  setText('net-up',     m.net_up     || '—');
  setText('net-down',   m.net_down   || '—');
  setText('disk-pct',  `${m.disk_pct}%`);
  setBar('disk-bar',    m.disk_pct);
  setText('disk-usage', `${m.disk_used_gb} / ${m.disk_total_gb} GB`);
}

function showOffline() {
  const dot = $('status-dot');
  if (dot) dot.className = 'status-dot';
  setText('hostname', 'offline');
  ['cpu-bar', 'gpu-bar', 'mem-bar'].forEach(id => setBar(id, 0));
}

async function poll() {
  try {
    const res = await fetch(`${config.serverUrl}/metrics`, {
      signal: AbortSignal.timeout(2500),
    });
    if (res.ok) applyMetrics(await res.json());
    else showOffline();
  } catch {
    showOffline();
  }
}

function startPolling(interval) {
  if (pollTimer) clearInterval(pollTimer);
  poll();
  pollTimer = setInterval(poll, interval);
}

function applyLocalMetrics(m) {
  setText('local-hostname',   m.hostname || '');
  setText('local-cpu-pct',   `${m.cpu}%`);
  setBar('local-cpu-bar',     m.cpu);
  setText('local-cpu-temp',   m.cpu_temp ? `${m.cpu_temp}°C` : '—');
  setText('local-mem-pct',   `${m.mem_pct}%`);
  setBar('local-mem-bar',     m.mem_pct);
  setText('local-mem-usage', `${m.mem_used_gb} / ${m.mem_total_gb} GB`);
  setText('local-net-up',     m.net_up   || '—');
  setText('local-net-down',   m.net_down || '—');
  setText('local-disk-pct',  `${m.disk_pct}%`);
  setBar('local-disk-bar',    m.disk_pct);
  setText('local-disk-usage', `${m.disk_used_gb} / ${m.disk_total_gb} GB`);
}

function init() {
  if (window.electronAPI) {
    // Electron mode — unchanged
    window.electronAPI.getConfig().then(cfg => {
      config = cfg;
      applyTheme(config);
      startPolling(config.pollInterval);
    });
    window.electronAPI.onConfigUpdate(updated => {
      config = { ...config, ...updated };
      applyTheme(config);
      startPolling(config.pollInterval);
    });
    window.electronAPI.onLocalMetrics(applyLocalMetrics);
  } else {
    // Python/WebKit mode — Python calls these after page load
    window.__widgetInit = (cfg) => {
      config = { ...config, ...cfg };
      applyTheme(config);
      startPolling(config.pollInterval);
    };
    window.__localMetrics = applyLocalMetrics;
    // Start with defaults until Python injects config
    applyTheme(config);
    startPolling(config.pollInterval);
  }
}

init();
