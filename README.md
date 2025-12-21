<p align="center">
  <h1 align="center">TvOverlay UI</h1>
  <p align="center">
    A Home Assistant integration for <a href="https://github.com/gugutab/TvOverlay">TvOverlay</a>
    <br />
    Send notifications and control overlays on your Android TV
  </p>
</p>

<p align="center">
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge" alt="HACS"></a>
  <a href="https://github.com/manjotsc/ha-tvoverlay/releases"><img src="https://img.shields.io/github/v/release/manjotsc/ha-tvoverlay?style=for-the-badge" alt="Release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/manjotsc/ha-tvoverlay?style=for-the-badge" alt="License"></a>
</p>

---

## Overview

**TvOverlay UI** brings the power of [TvOverlay](https://github.com/gugutab/TvOverlay) to Home Assistant with a clean, UI-friendly experience. No YAML required.

> **Credit**: This integration is built for the TvOverlay Android TV app by [@gugutab](https://github.com/gugutab)

---

## Installation

### HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=manjotsc&repository=ha-tvoverlay&category=integration)

Click the button above, or manually:

1. Open **HACS** → Click ⋮ → **Custom repositories**
2. Add: `https://github.com/manjotsc/ha-tvoverlay`
3. Category: **Integration**
4. Search **TvOverlay UI** → Install → Restart HA

### Manual

Copy `custom_components/tvoverlay_ui` to your HA config directory and restart.

---

## Setup

1. **Settings** → **Devices & Services** → **Add Integration**
2. Search **TvOverlay UI**
3. Enter device IP, port (default: 5001), and name

---

## Features

### Services

| Service | Description |
|:--------|:------------|
| `tvoverlay_ui.notify` | Send a notification |
| `tvoverlay_ui.notify_fixed` | Create a persistent widget (ID required) |
| `tvoverlay_ui.clear_fixed` | Remove a widget by ID |

### Controls

| Type | Entities |
|:-----|:---------|
| **Switches** | Display Clock, Display Notifications, Display Fixed Notifications, Pixel Shift, Debug Mode |
| **Sliders** | Clock Visibility, Overlay Visibility, Fixed Notifications Visibility, Notification Duration |
| **Selects** | Hot Corner, Default Shape |
| **Sensors** | Active Fixed Notifications |
| **Binary Sensors** | Connectivity (online/offline status) |

---

## Limitations

| Area | Limitation |
|:-----|:-----------|
| **Media** | Local paths not supported — use full URLs only |
| **Video** | Only RTSP, HLS (.m3u8), DASH (.mpd) — no MP4 |
| **Tracking** | Only tracks fixed notifications created via Home Assistant |

> **Note**: Entity states are polled from the device every 30 seconds.

---

## Contributing

Pull requests welcome.

---

## License

[MIT License](LICENSE)

---
