# AI Monitor — Wayland Widget

A lightweight desktop widget that monitors a remote AI server and local machine metrics. Built with GTK3 + WebKit2, it runs as a true background widget on GNOME — no dock indicator, no taskbar entry, always behind other windows.

![Widget showing CPU, GPU, memory, disk and network stats for a remote AI server and local machine](screenshots/screenshot.png)

## Features

- Monitors remote AI server (CPU, GPU, VRAM, memory, disk, network)
- Monitors local machine (CPU, memory, disk, network)
- Live-updating progress bars with smooth animations
- Multiple built-in themes + custom theme editor
- Transparent/frosted glass background
- Tray icon for settings and quit
- Reads/writes the same config as the Electron version — both can coexist

## Requirements

```
python3
gir1.2-gtk-3.0
gir1.2-webkit2-4.1
gir1.2-appindicator3-0.1
```

Install on Ubuntu/Debian:

```bash
sudo apt install gir1.2-webkit2-4.1 gir1.2-appindicator3-0.1
```

## Usage

```bash
./launch.sh
```

Right-click the tray icon to open Settings or quit.

## Autostart

To start on login, copy the autostart entry:

```bash
cp ai-monitor-wayland.desktop ~/.config/autostart/
```

Or toggle it from the Settings window.

## Configuration

Config is stored at `~/.config/ai-monitor/config.json` and shared with the Electron version of the app. Key settings:

| Key | Default | Description |
|-----|---------|-------------|
| `serverUrl` | `http://localhost:7070` | Remote AI server metrics endpoint |
| `pollInterval` | `3000` | Poll interval in milliseconds |
| `width` | `240` | Widget width in pixels |
| `opacity` | `0.87` | Background opacity (0–1) |
| `theme` | `dark-blue` | Active theme key |

## Why not the Electron version?

The Electron version works well but GNOME's BAMF daemon tracks running Electron apps at the process level and always shows a dock indicator, regardless of `skipTaskbar` or window type hints. This version uses GTK3 with X11 `_NET_WM_WINDOW_TYPE_DOCK` hints running under XWayland, which GNOME treats as a panel surface — no dock indicator, no Alt+Tab entry.

## Remote server

The widget expects a `/metrics` endpoint on the remote server returning JSON. See the [ai-monitor](https://github.com/Mikestove/ai-monitor) repo for the server component.
