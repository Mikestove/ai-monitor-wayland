#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1')
gi.require_version('AppIndicator3', '0.1')

from gi.repository import Gtk, WebKit2, GLib, Gdk, Gio, AppIndicator3
import os, json, time, socket, sys

WIDGET_DIR    = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH   = os.path.expanduser('~/.config/ai-monitor/config.json')
AUTOSTART_PATH = os.path.expanduser('~/.config/autostart/ai-monitor-wayland.desktop')

DEFAULTS = {
    'serverUrl':    'http://localhost:7070',
    'pollInterval': 3000,
    'width':        240,
    'opacity':      0.87,
    'theme':        'dark-blue',
}

def load_config():
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH) as f:
                return {**DEFAULTS, **json.load(f)}
    except Exception:
        pass
    return dict(DEFAULTS)

# ── Local metrics ──────────────────────────────────────────────────────────────

_prev_cpu = None
_prev_net = {'rx': 0, 'tx': 0, 'ts': 0.0}

def _cpu_stat():
    try:
        with open('/proc/stat') as f:
            parts = f.readline().split()[1:]
        vals  = list(map(int, parts))
        idle  = vals[3] + (vals[4] if len(vals) > 4 else 0)
        return {'idle': idle, 'total': sum(vals)}
    except Exception:
        return None

def _cpu_pct():
    global _prev_cpu
    curr = _cpu_stat()
    if not curr or not _prev_cpu:
        _prev_cpu = curr
        return 0
    di = curr['idle']  - _prev_cpu['idle']
    dt = curr['total'] - _prev_cpu['total']
    _prev_cpu = curr
    return round((1 - di / dt) * 100) if dt > 0 else 0

def _cpu_temp():
    try:
        for d in os.listdir('/sys/class/hwmon'):
            try:
                with open(f'/sys/class/hwmon/{d}/name') as f:
                    name = f.read().strip()
                if name in ('k10temp', 'zenpower', 'coretemp'):
                    with open(f'/sys/class/hwmon/{d}/temp1_input') as f:
                        return round(int(f.read().strip()) / 1000)
            except Exception:
                pass
    except Exception:
        pass
    return None

def _net_rates():
    global _prev_net
    now = time.monotonic()
    try:
        rx = tx = 0
        with open('/proc/net/dev') as f:
            for line in f.readlines()[2:]:
                p = line.strip().split()
                if not p or p[0] == 'lo:':
                    continue
                rx += int(p[1])
                tx += int(p[9])
        dt   = now - _prev_net['ts']
        up   = max(0, (tx - _prev_net['tx']) / dt) if dt > 0 else 0
        down = max(0, (rx - _prev_net['rx']) / dt) if dt > 0 else 0
        _prev_net = {'rx': rx, 'tx': tx, 'ts': now}
        return up, down
    except Exception:
        return 0, 0

def _fmt(bps):
    if bps < 1024:    return f'{round(bps)} B/s'
    if bps < 1024**2: return f'{bps/1024:.1f} KB/s'
    if bps < 1024**3: return f'{bps/1024**2:.1f} MB/s'
    return f'{bps/1024**3:.2f} GB/s'

def _disk_stats():
    try:
        st    = os.statvfs('/')
        total = st.f_blocks * st.f_frsize
        free  = st.f_bfree  * st.f_frsize
        used  = total - free
        return {'pct': round(used/total*100), 'used_gb': f'{used/1e9:.1f}', 'total_gb': f'{total/1e9:.1f}'}
    except Exception:
        return {'pct': 0, 'used_gb': '0', 'total_gb': '0'}

def local_metrics():
    try:
        with open('/proc/meminfo') as f:
            mem = {}
            for line in f:
                k, v = line.split(':')
                mem[k.strip()] = int(v.strip().split()[0]) * 1024
        total = mem.get('MemTotal', 1)
        used  = total - mem.get('MemAvailable', 0)
    except Exception:
        total, used = 1, 0

    up, down = _net_rates()
    disk     = _disk_stats()
    return {
        'hostname':      socket.gethostname(),
        'cpu':           _cpu_pct(),
        'cpu_temp':      _cpu_temp(),
        'mem_pct':       round(used / total * 100),
        'mem_used_gb':   f'{used/1e9:.1f}',
        'mem_total_gb':  f'{total/1e9:.1f}',
        'disk_pct':      disk['pct'],
        'disk_used_gb':  disk['used_gb'],
        'disk_total_gb': disk['total_gb'],
        'net_up':        _fmt(up),
        'net_down':      _fmt(down),
    }

# ── Widget ─────────────────────────────────────────────────────────────────────

class AIMonitorWidget:
    def __init__(self):
        self.webview      = None
        self.win          = None
        self.config       = load_config()
        self.ready        = False
        self._settings_win = None
        self._settings_wv  = None

    def run(self):
        _cpu_stat()
        _net_rates()

        win = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.win = win

        # X11 window hints — must be set before show()
        win.set_type_hint(Gdk.WindowTypeHint.DOCK)
        win.set_keep_below(True)
        win.set_skip_taskbar_hint(True)
        win.set_skip_pager_hint(True)
        win.set_decorated(False)
        win.set_app_paintable(True)
        win.stick()  # Show on all workspaces

        # Transparency
        screen = win.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            win.set_visual(visual)

        # Position: left edge, full workarea height
        display  = Gdk.Display.get_default()
        monitor  = display.get_primary_monitor()
        geo      = monitor.get_workarea()
        width    = self.config['width']
        win.move(geo.x, geo.y)
        win.set_default_size(width, geo.height)

        # WebView
        webview = WebKit2.WebView()
        self.webview = webview

        bg = Gdk.RGBA()
        bg.red = bg.green = bg.blue = bg.alpha = 0.0
        webview.set_background_color(bg)

        webview.connect('load-changed', self._on_load_changed)

        html_path = os.path.join(WIDGET_DIR, 'renderer', 'index.html')
        webview.load_uri(f'file://{html_path}')

        win.add(webview)
        win.connect('delete-event', lambda *_: True)  # prevent close
        win.show_all()

        # Watch config file for live updates
        cfg_file = Gio.File.new_for_path(CONFIG_PATH)
        self._cfg_monitor = cfg_file.monitor_file(Gio.FileMonitorFlags.NONE, None)
        self._cfg_monitor.connect('changed', self._on_config_changed)

        self._setup_tray()
        GLib.timeout_add(3000, self._tick)
        Gtk.main()

    def _setup_tray(self):
        icon_path = os.path.join(WIDGET_DIR, 'icons', '32x32.png')
        self._indicator = AppIndicator3.Indicator.new(
            'ai-monitor-wayland',
            icon_path,
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS,
        )
        self._indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

        menu = Gtk.Menu()

        title = Gtk.MenuItem(label='AI Monitor')
        title.set_sensitive(False)
        menu.append(title)
        menu.append(Gtk.SeparatorMenuItem())

        settings_item = Gtk.MenuItem(label='Settings…')
        settings_item.connect('activate', lambda _: self._open_settings())
        menu.append(settings_item)

        menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label='Quit')
        quit_item.connect('activate', lambda _: Gtk.main_quit())
        menu.append(quit_item)

        menu.show_all()
        self._indicator.set_menu(menu)

    def _is_autostart(self):
        return os.path.exists(AUTOSTART_PATH)

    def _set_autostart(self, enable):
        if enable:
            os.makedirs(os.path.dirname(AUTOSTART_PATH), exist_ok=True)
            with open(AUTOSTART_PATH, 'w') as f:
                f.write('\n'.join([
                    '[Desktop Entry]',
                    'Name=AI Monitor (Wayland)',
                    f'Exec={WIDGET_DIR}/launch.sh',
                    'Type=Application',
                    'Hidden=false',
                    'NoDisplay=true',
                    'X-GNOME-Autostart-enabled=true',
                    '',
                ]))
        else:
            if os.path.exists(AUTOSTART_PATH):
                os.unlink(AUTOSTART_PATH)

    def _save_config(self, updates=None):
        try:
            os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
            current = load_config()
            if updates:
                # Deep-merge customThemes so individual saves don't wipe other themes
                if 'customThemes' in updates:
                    updates['customThemes'] = {
                        **(current.get('customThemes') or {}),
                        **updates['customThemes'],
                    }
                current.update(updates)
            else:
                current.update(self.config)
            self.config = current
            with open(CONFIG_PATH, 'w') as f:
                json.dump(current, f, indent=2)
            return current
        except Exception as e:
            print(f'Config save failed: {e}')
            return self.config

    def _open_settings(self):
        if hasattr(self, '_settings_win') and self._settings_win:
            self._settings_win.present()
            return

        # IPC bridge injected before settings.html runs
        bridge = """
const __cb = {};
let __id = 0;
window.electronAPI = {
  getConfig:    ()     => new Promise(r => { const id=++__id; __cb[id]=r; window.webkit.messageHandlers.ipc.postMessage({id, m:'getConfig'}); }),
  saveConfig:   (data) => new Promise(r => { const id=++__id; __cb[id]=r; window.webkit.messageHandlers.ipc.postMessage({id, m:'saveConfig', a:data}); }),
  getAutostart: ()     => new Promise(r => { const id=++__id; __cb[id]=r; window.webkit.messageHandlers.ipc.postMessage({id, m:'getAutostart'}); }),
  setAutostart: (v)    => new Promise(r => { const id=++__id; __cb[id]=r; window.webkit.messageHandlers.ipc.postMessage({id, m:'setAutostart', a:v}); }),
  quitApp:      ()     => window.webkit.messageHandlers.ipc.postMessage({id:0, m:'quitApp'}),
};
window.__resolve = (id, val) => { if(__cb[id]){ __cb[id](val); delete __cb[id]; } };
"""
        cm = WebKit2.UserContentManager()
        cm.add_script(WebKit2.UserScript(
            bridge,
            WebKit2.UserContentInjectedFrames.TOP_FRAME,
            WebKit2.UserScriptInjectionTime.START,
            None, None,
        ))
        cm.register_script_message_handler('ipc')
        cm.connect('script-message-received::ipc', self._on_settings_ipc)

        win = Gtk.Window(title='AI Monitor — Settings')
        self._settings_win = win
        win.set_default_size(420, 700)
        win.set_resizable(False)

        wv = WebKit2.WebView.new_with_user_content_manager(cm)
        self._settings_wv = wv
        html_path = os.path.join(WIDGET_DIR, 'renderer', 'settings.html')
        wv.load_uri(f'file://{html_path}')

        win.add(wv)
        win.connect('delete-event', self._on_settings_closed)
        win.show_all()

    def _on_settings_closed(self, win, _event):
        self._settings_win = None
        self._settings_wv  = None
        win.destroy()
        return False

    def _on_settings_ipc(self, _cm, js_result):
        try:
            msg  = json.loads(js_result.get_js_value().to_json(0))
            m, a = msg.get('m'), msg.get('a')
            i    = msg.get('id', 0)

            if m == 'getConfig':
                result = self.config
            elif m == 'saveConfig':
                result = self._save_config(a)
                # Push updated config to widget
                self._js(f'window.__widgetInit && window.__widgetInit({json.dumps(result)})')
            elif m == 'getAutostart':
                result = self._is_autostart()
            elif m == 'setAutostart':
                self._set_autostart(bool(a))
                result = None
            elif m == 'quitApp':
                Gtk.main_quit()
                return
            else:
                result = None

            if i and self._settings_wv:
                self._settings_wv.evaluate_javascript(
                    f'window.__resolve({i},{json.dumps(result)})',
                    -1, None, None, None, None, None,
                )
        except Exception as e:
            print(f'IPC error: {e}')

    def _js(self, script):
        if self.webview:
            self.webview.evaluate_javascript(script, -1, None, None, None, None, None)

    def _on_load_changed(self, _wv, event):
        if event != WebKit2.LoadEvent.FINISHED:
            return
        self.ready = True
        self._js(f'window.__widgetInit && window.__widgetInit({json.dumps(self.config)})')

    def _on_config_changed(self, _mon, _file, _other, event):
        if event not in (Gio.FileMonitorEvent.CHANGED, Gio.FileMonitorEvent.CREATED):
            return
        self.config = load_config()
        if self.ready:
            self._js(f'window.__widgetInit && window.__widgetInit({json.dumps(self.config)})')

    def _tick(self):
        if self.ready:
            self._js(f'window.__localMetrics && window.__localMetrics({json.dumps(local_metrics())})')
        return GLib.SOURCE_CONTINUE

if __name__ == '__main__':
    AIMonitorWidget().run()
