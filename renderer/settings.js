// BUILT_IN_THEMES loaded from themes.js

const $ = id => document.getElementById(id);

let currentConfig = {};
let selectedThemeKey = 'dark-blue';

// ── Helpers ──────────────────────────────────────────────────────────────────

function isCustom(key) { return key.startsWith('custom:'); }

function getAllThemes() {
  return { ...BUILT_IN_THEMES, ...(currentConfig.customThemes || {}) };
}

function showStatus(msg, type) {
  const el = $('status');
  el.textContent = msg;
  el.className = `status ${type}`;
  if (type === 'ok') setTimeout(() => { el.textContent = ''; el.className = 'status'; }, 2500);
}

// ── Theme picker ──────────────────────────────────────────────────────────────

function renderThemePicker() {
  const container = $('theme-picker');
  container.innerHTML = '';

  for (const [key, theme] of Object.entries(getAllThemes())) {
    const card = document.createElement('div');
    card.className = 'theme-card' + (key === selectedThemeKey ? ' selected' : '');

    const swatches = [theme.cpu, theme.gpu, theme.mem]
      .map(c => `<span class="swatch-dot" style="background:${c}"></span>`)
      .join('');

    card.innerHTML = `
      <div class="card-swatches">${swatches}</div>
      <div class="card-label">${theme.label || key.replace('custom:', '')}</div>
    `;

    card.addEventListener('click', () => {
      selectedThemeKey = key;
      renderThemePicker();
      loadThemeIntoEditor(key);
    });

    container.appendChild(card);
  }

  // New theme button
  const newCard = document.createElement('div');
  newCard.className = 'theme-card new-theme-card';
  newCard.innerHTML = `<span class="new-plus">+</span><div class="card-label">New</div>`;
  newCard.addEventListener('click', () => {
    selectedThemeKey = '__new__';
    renderThemePicker();
    loadBlankEditor();
  });
  container.appendChild(newCard);
}

// ── Theme editor ──────────────────────────────────────────────────────────────

function loadThemeIntoEditor(key) {
  const theme = getAllThemes()[key];
  if (!theme) return;

  $('theme-name').value   = theme.label || key.replace('custom:', '');
  $('tc-bg').value        = theme.bgColor      || '#080a12';
  $('tc-text').value      = theme.textPrimary  || '#e2e8f0';
  $('tc-subtext').value   = theme.textSecondary|| '#94a3b8';
  $('tc-cpu').value       = theme.cpu          || '#38bdf8';
  $('tc-gpu').value       = theme.gpu          || '#fb923c';
  $('tc-mem').value       = theme.mem          || '#a78bfa';
  $('tc-up').value        = theme.netUp        || '#4ade80';
  $('tc-dn').value        = theme.netDown      || '#22d3ee';

  $('deleteThemeBtn').style.display = isCustom(key) ? '' : 'none';
  $('saveThemeBtn').textContent = isCustom(key) ? 'Update Theme' : 'Save as Custom Theme';
  $('editor-title').textContent = isCustom(key) ? 'Edit Custom Theme' : 'Customize / Save as New';
  $('theme-name').readOnly = false;
}

function loadBlankEditor() {
  const d = BUILT_IN_THEMES['dark-blue'];
  $('theme-name').value   = '';
  $('tc-bg').value        = d.bgColor;
  $('tc-text').value      = d.textPrimary;
  $('tc-subtext').value   = d.textSecondary;
  $('tc-cpu').value       = d.cpu;
  $('tc-gpu').value       = d.gpu;
  $('tc-mem').value       = d.mem;
  $('tc-up').value        = d.netUp;
  $('tc-dn').value        = d.netDown;
  $('deleteThemeBtn').style.display = 'none';
  $('saveThemeBtn').textContent = 'Save as Custom Theme';
  $('editor-title').textContent = 'New Custom Theme';
}

function readEditor() {
  return {
    label:         $('theme-name').value.trim() || 'Custom Theme',
    bgColor:       $('tc-bg').value,
    textPrimary:   $('tc-text').value,
    textSecondary: $('tc-subtext').value,
    cpu:           $('tc-cpu').value,
    gpu:           $('tc-gpu').value,
    mem:           $('tc-mem').value,
    netUp:         $('tc-up').value,
    netDown:       $('tc-dn').value,
  };
}

async function saveTheme() {
  const values = readEditor();

  let key;
  if (isCustom(selectedThemeKey)) {
    key = selectedThemeKey;
  } else {
    const slug = values.label.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    key = `custom:${slug}-${Date.now()}`;
  }

  const customThemes = { ...(currentConfig.customThemes || {}), [key]: values };
  const updated = await window.electronAPI.saveConfig({ customThemes });
  currentConfig = updated;

  selectedThemeKey = key;
  renderThemePicker();
  loadThemeIntoEditor(key);
  showStatus('Theme saved.', 'ok');
}

async function deleteTheme() {
  if (!isCustom(selectedThemeKey)) return;
  const customThemes = { ...(currentConfig.customThemes || {}) };
  delete customThemes[selectedThemeKey];
  const updated = await window.electronAPI.saveConfig({ customThemes });
  currentConfig = updated;
  selectedThemeKey = 'dark-blue';
  renderThemePicker();
  loadThemeIntoEditor('dark-blue');
  showStatus('Theme deleted.', 'ok');
}

// ── Init ─────────────────────────────────────────────────────────────────────

function bindSlider(id, displayId) {
  $(id).addEventListener('input', () => { $(displayId).textContent = $(id).value; });
}

async function init() {
  currentConfig = await window.electronAPI.getConfig();
  selectedThemeKey = currentConfig.theme || 'dark-blue';

  // Connection
  $('serverUrl').value    = currentConfig.serverUrl || '';
  $('pollInterval').value = Math.round((currentConfig.pollInterval || 3000) / 1000);
  $('pollDisplay').textContent = $('pollInterval').value;
  bindSlider('pollInterval', 'pollDisplay');

  // Autostart
  $('autostart').checked = await window.electronAPI.getAutostart();
  $('autostart').addEventListener('change', async (e) => {
    await window.electronAPI.setAutostart(e.target.checked);
    showStatus(e.target.checked ? 'Will start on login.' : 'Removed from startup.', 'ok');
  });

  // Appearance
  $('opacity').value  = Math.round((currentConfig.opacity ?? 0.87) * 100);
  $('opacityDisplay').textContent = $('opacity').value;
  $('width').value    = currentConfig.width || 240;
  $('widthDisplay').textContent = $('width').value;
  bindSlider('opacity', 'opacityDisplay');
  bindSlider('width',   'widthDisplay');

  // Theme
  renderThemePicker();
  const themeToLoad = BUILT_IN_THEMES[selectedThemeKey]
    ? selectedThemeKey
    : (currentConfig.customThemes?.[selectedThemeKey] ? selectedThemeKey : 'dark-blue');
  loadThemeIntoEditor(themeToLoad);

  $('saveThemeBtn').addEventListener('click', saveTheme);
  $('deleteThemeBtn').addEventListener('click', deleteTheme);

  // Actions
  $('quitBtn').addEventListener('click', () => window.electronAPI.quitApp());

  $('saveBtn').addEventListener('click', async () => {
    const url = $('serverUrl').value.trim();
    if (!url) { showStatus('Server URL is required.', 'err'); return; }

    const data = {
      serverUrl:    url,
      pollInterval: parseInt($('pollInterval').value) * 1000,
      opacity:      parseInt($('opacity').value) / 100,
      theme:        selectedThemeKey === '__new__' ? 'dark-blue' : selectedThemeKey,
      width:        parseInt($('width').value),
    };

    await window.electronAPI.saveConfig(data);
    showStatus('Saved and applied.', 'ok');
  });
}

init();
