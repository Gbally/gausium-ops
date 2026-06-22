# Gausium Ops — PyQt6 Desktop App

A dark, native-feeling desktop app to control and monitor Gausium cleaning robots. Built with Python + PyQt6, no Electron, no browser.

> ⚠️ **Purpose & scope.** This is an **exploration and learning tool** — built to
> experiment with controlling the robots and to understand the Gausium OpenAPI
> (endpoints, payloads, and responses). It is **not production-ready** and should
> **not be used in production**. It's an unofficial, community client and is not
> affiliated with or endorsed by Gausium. Use it against real robots at your own
> risk, and review what each command does before sending it.

## Features

| Pane | What it does |
|---|---|
| **Fleet** | Lists all robots under your account — online status, model, software version. Click Select to target one. |
| **Live status** | Battery, operating mode, current map, consumables health, and a colour-coded **health banner**. Stop / Pause / Resume + **Return to charging**. Auto-refreshes on a configurable interval. |
| **Launch task** | Loads the robot's maps & areas, picks map + area + cleaning mode, sends a task with live payload preview. |
| **Live map** | Plots the robot's live position on the real floor-plan map, with its travelled-path trail. Start/stop monitoring. |
| **Reports** | Date-range task history — KPI cards, area-cleaned and battery-used bar charts, and a full task list. |
| **API console** | Send any API request with the live token and inspect the raw response — handy for debugging. |
| **Activity log** | Timestamped record of every API call and response. |

Plus cross-platform **desktop notifications** on robot state changes (e.g. task finished).

---

## Requirements

- **macOS or Linux** for the `launch.sh` helper (bash). On **Windows**, create a
  venv and run `python gausium_ops.py` (see below).
- **Python 3.10+** — install from [python.org](https://www.python.org) or via Homebrew (`brew install python`)

No other installation needed — `launch.sh` handles the virtual environment and dependencies.

---

## First run

```bash
# In Terminal, cd to this folder, then:
bash launch.sh
```

On first run it creates a local `.venv` and downloads PyQt6 (~60 MB). This only happens once.

Every subsequent launch:
```bash
bash launch.sh
```

---

## Connecting

The app performs the OAuth handshake for you — there's no manual token step.

1. Get your credentials from the [Gausium Developer Portal](https://developer.gs-robot.com)
   (`ClientID`, `ClientSecret`, `AccessKeyID`, `AccessKeySecret`).
2. In the top bar, fill the three fields:
   - **Client ID** → `ClientID`
   - **Client secret** → `ClientSecret`
   - **Open access key** → **`AccessKeySecret`**  *(not the AccessKeyID)*
3. Click **⚡ Connect**. The app fetches and auto-renews the token; your
   credentials are saved locally to `~/.gausium_ops/credentials.json` (never committed).

See **[DOCUMENTATION.md](DOCUMENTATION.md)** for the full user guide and
**[API_REQUESTS.md](API_REQUESTS.md)** for the raw request/response reference.

---

## Files

```
gausium-ops-pyqt/
├── gausium_ops.py        — Launcher (keeps `bash launch.sh` working)
├── gsops/                — Application package
│   ├── config.py         — Constants, palette, stylesheet, credentials, SSL, tables
│   ├── api.py            — Background HTTP workers (Qt threads)
│   ├── widgets.py        — Reusable widgets (cards, buttons, charts, nav, log)
│   ├── app.py            — MainWindow + entry point
│   └── panes/            — One module per tab
│       ├── fleet.py · status.py · task.py · livemap.py · reports.py · console.py
├── requirements.txt      — PyQt6, PyQt6-Charts
├── launch.sh             — Run this to start
├── DOCUMENTATION.md      — User guide & API reference
├── API_REQUESTS.md       — Request/response reference (shareable)
└── README.md
```

No CORS issues — all API calls go through Python's `urllib` directly.
