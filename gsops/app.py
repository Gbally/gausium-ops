#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# =============================================================================
#            GAUSIUM OPS
# =============================================================================
# PROJECT : Guillaume Bally
# FILE : app.py
# DESCRIPTION : MainWindow: credential bar, tab stack, all API handlers, notifications, and the entry point.
"""
========= ============== ======================================================
Version   Date           Comment
========= ============== ======================================================
0.1.0     2026/06/22     Creation
========= ============== ======================================================
"""

# [IMPORTS]--------------------------------------------------------------------
import json
import sys
import time
from functools import partial
from urllib.parse import urlencode
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QBrush, QColor, QIcon, QPainter, QPalette, QPixmap
from PyQt6.QtWidgets import QApplication, QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QScrollArea, QStackedWidget, QStatusBar, QSystemTrayIcon, QVBoxLayout, QWidget
from .api import ApiThread, DownloadThread
from .config import BASE_URL, COLORS, GRANT_TYPE, OAUTH_URL, STYLESHEET, TASK_ERROR_CODES, load_credentials, save_credentials
from .panes.console import ConsolePane
from .panes.fleet import FleetPane
from .panes.livemap import LiveMapPane
from .panes.reports import ReportsPane
from .panes.status import StatusPane
from .panes.task import TaskPane
from .widgets import LogPanel, NavButton, accent_button

# [MODULE INFO]----------------------------------------------------------------
__author__ = 'Guillaume'
__date__ = '2026/06/22'
__version__ = '0.1.0'
__maintainer__ = 'Guillaume'
__email__ = 'guillaumepointbally@gmail.com'

# [Functions]------------------------------------------------------------------
class MainWindow(QMainWindow):
    """Owns the credential bar, the pane stack, and all API calls.

    Every request goes through `_api(path, tag, ...)`, which runs on a background
    thread and returns via `_on_api_result`, which dispatches by `tag` to the
    matching `_on_<thing>` handler. `_load_*` methods send; `_on_*` methods render.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gausium Ops")
        self.resize(1200, 820)
        self.setMinimumSize(900, 600)
        self._threads = []
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._auto_refresh)
        self._connected = False
        self._bearer_token = ""
        self._last_status = None
        # Live-map monitoring state.
        self._map_timer = QTimer()
        self._map_timer.timeout.connect(self._map_monitor_tick)
        self._map_loaded_id = None
        self._dl_thread = None
        # Notifications: background poll + last-seen taskState for change detection.
        self._prev_task_state = None
        self._notify_timer = QTimer()
        self._notify_timer.timeout.connect(self._notify_tick)
        self._tray = None

        self._build_ui()
        self._init_tray()
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Enter your Gausium API credentials and click Connect")
        self.log("Gausium Ops started — ready.")

    # ── UI build ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Sidebar ──
        sidebar = QWidget()
        sidebar.setFixedWidth(210)
        sidebar.setStyleSheet(f"background: {COLORS['bg2']}; border-right: 1px solid {COLORS['border']};")
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(10, 16, 10, 16)
        sb_layout.setSpacing(2)

        # Logo
        logo_row = QHBoxLayout()
        dot = QLabel("◆")
        dot.setStyleSheet(f"color: {COLORS['accent']}; font-size: 20px;")
        logo_text = QVBoxLayout()
        logo_text.setSpacing(0)
        t1 = QLabel("Gausium")
        t1.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {COLORS['ink']};")
        t2 = QLabel("Ops v1.0")
        t2.setStyleSheet(f"font-size: 10px; color: {COLORS['ink3']};")
        logo_text.addWidget(t1)
        logo_text.addWidget(t2)
        logo_row.addWidget(dot)
        logo_row.addLayout(logo_text)
        logo_row.addStretch()
        sb_layout.addLayout(logo_row)
        sb_layout.addSpacing(20)

        # Nav
        self._nav_btns = {}
        nav_items = [
            ("fleet", "⬚", "Fleet"),
            ("status", "◉", "Live status"),
            ("task", "▶", "Launch task"),
            ("livemap", "✛", "Live map"),
            ("reports", "▤", "Reports"),
            ("console", "⌘", "API console"),
            ("log", "≡", "Activity log"),
        ]
        for key, icon, label in nav_items:
            btn = NavButton(icon, label)
            btn.clicked.connect(partial(self._nav_to, key))
            self._nav_btns[key] = btn
            sb_layout.addWidget(btn)

        sb_layout.addStretch()

        # Connection indicator
        self._conn_frame = QFrame()
        self._conn_frame.setStyleSheet(f"background: {COLORS['bg3']}; border-radius: 7px; border: 1px solid {COLORS['border']};")
        conn_l = QHBoxLayout(self._conn_frame)
        conn_l.setContentsMargins(10, 8, 10, 8)
        self._conn_dot = QLabel("●")
        self._conn_dot.setStyleSheet(f"color: {COLORS['ink3']}; font-size: 8px;")
        self._conn_lbl = QLabel("Not connected")
        self._conn_lbl.setStyleSheet(f"color: {COLORS['ink2']}; font-size: 11px;")
        conn_l.addWidget(self._conn_dot)
        conn_l.addWidget(self._conn_lbl)
        conn_l.addStretch()
        sb_layout.addWidget(self._conn_frame)
        root.addWidget(sidebar)

        # ── Main area ──
        main_area = QWidget()
        main_layout = QVBoxLayout(main_area)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Config bar (top)
        cfg_bar = QWidget()
        cfg_bar.setStyleSheet(f"background: {COLORS['bg2']}; border-bottom: 1px solid {COLORS['border']};")
        cfg_l = QHBoxLayout(cfg_bar)
        cfg_l.setContentsMargins(20, 10, 20, 10)
        cfg_l.setSpacing(10)

        def cfg_group(label, widget):
            g = QVBoxLayout()
            g.setSpacing(3)
            lbl = QLabel(label.upper())
            lbl.setStyleSheet(f"font-size: 9px; color: {COLORS['ink3']}; letter-spacing: 1px; font-weight: 600;")
            g.addWidget(lbl)
            g.addWidget(widget)
            return g

        self.cfg_client_id = QLineEdit()
        self.cfg_client_id.setPlaceholderText("client_id")
        self.cfg_client_id.setEchoMode(QLineEdit.EchoMode.Password)
        self.cfg_client_id.setMinimumWidth(160)

        self.cfg_client_secret = QLineEdit()
        self.cfg_client_secret.setPlaceholderText("client_secret")
        self.cfg_client_secret.setEchoMode(QLineEdit.EchoMode.Password)
        self.cfg_client_secret.setMinimumWidth(160)

        self.cfg_access_key = QLineEdit()
        self.cfg_access_key.setPlaceholderText("open_access_key")
        self.cfg_access_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.cfg_access_key.setMinimumWidth(160)

        self.cfg_sn = QComboBox()
        self.cfg_sn.setEditable(True)
        self.cfg_sn.setPlaceholderText("Connect to load robots…")
        self.cfg_sn.setMinimumWidth(160)

        self.cfg_refresh = QComboBox()
        self.cfg_refresh.addItems(["Off", "15 s", "30 s", "60 s"])
        self.cfg_refresh.setCurrentIndex(2)
        self.cfg_refresh.setFixedWidth(80)
        self.cfg_refresh.currentIndexChanged.connect(self._refresh_interval_changed)

        self.cfg_notify = QCheckBox("🔔")
        self.cfg_notify.setToolTip("Desktop notifications on robot state changes (e.g. task finished)")
        self.cfg_notify.setChecked(True)
        self.cfg_notify.toggled.connect(self._notify_toggled)

        self.connect_btn = accent_button("⚡  Connect")
        self.connect_btn.clicked.connect(self._do_connect)

        # Token status indicator (read-only, shown after successful OAuth)
        self._token_status = QLabel("No token")
        self._token_status.setStyleSheet(f"font-size: 11px; color: {COLORS['ink3']}; padding: 0 4px;")

        cfg_l.addLayout(cfg_group("Client ID", self.cfg_client_id))
        cfg_l.addLayout(cfg_group("Client secret", self.cfg_client_secret))
        cfg_l.addLayout(cfg_group("Open access key", self.cfg_access_key))
        cfg_l.addLayout(cfg_group("Robot SN", self.cfg_sn))
        cfg_l.addLayout(cfg_group("Auto-refresh", self.cfg_refresh))
        cfg_l.addLayout(cfg_group("Notify", self.cfg_notify))
        cfg_l.addWidget(self.connect_btn)
        cfg_l.addWidget(self._token_status)
        main_layout.addWidget(cfg_bar)

        # Load saved credentials
        creds = load_credentials()
        if creds.get("client_id"):
            self.cfg_client_id.setText(creds["client_id"])
        if creds.get("client_secret"):
            self.cfg_client_secret.setText(creds["client_secret"])
        if creds.get("open_access_key"):
            self.cfg_access_key.setText(creds["open_access_key"])
        if creds.get("robot_sn"):
            self.cfg_sn.setCurrentText(creds["robot_sn"])
        self._bearer_token = creds.get("bearer_token", "")

        # Content stack
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: transparent;")

        def scroll_wrap(widget):
            sa = QScrollArea()
            sa.setWidgetResizable(True)
            sa.setFrameShape(QFrame.Shape.NoFrame)
            sa.setStyleSheet("background: transparent;")
            inner = QWidget()
            l = QVBoxLayout(inner)
            l.setContentsMargins(20, 20, 20, 20)
            l.addWidget(widget)
            l.addStretch()
            sa.setWidget(inner)
            return sa

        # Fleet
        self._fleet_pane = FleetPane()
        self._fleet_pane.refresh_btn.clicked.connect(self._load_fleet)
        self._fleet_pane.robot_selected.connect(self._on_robot_selected)
        self._stack.addWidget(scroll_wrap(self._fleet_pane))

        # Status
        self._status_pane = StatusPane()
        self._status_pane.refresh_requested.connect(self._load_status)
        self._status_pane.send_command.connect(self._send_cmd)
        self._status_pane.navigate_charge.connect(self._return_to_charge)
        self._stack.addWidget(scroll_wrap(self._status_pane))

        # Task
        self._task_pane = TaskPane()
        self._task_pane.launch_task.connect(self._launch_task)
        self._task_pane.load_maps.connect(self._load_maps)
        self._task_pane.load_subareas.connect(self._load_subareas)
        self._stack.addWidget(scroll_wrap(self._task_pane))

        # Live map (not scroll-wrapped — the canvas fills the area)
        self._live_map_pane = LiveMapPane()
        self._live_map_pane.monitor_toggled.connect(self._toggle_map_monitor)
        livemap_wrap = QWidget()
        livemap_l = QVBoxLayout(livemap_wrap)
        livemap_l.setContentsMargins(20, 20, 20, 20)
        livemap_l.addWidget(self._live_map_pane)
        self._stack.addWidget(livemap_wrap)

        # Reports
        self._reports_pane = ReportsPane()
        self._reports_pane.load_requested.connect(self._load_reports)
        self._stack.addWidget(scroll_wrap(self._reports_pane))

        # API Console
        self._console_pane = ConsolePane()
        self._console_pane.send_request.connect(self._on_console_send)
        self._stack.addWidget(scroll_wrap(self._console_pane))

        # Log
        self._log_panel = LogPanel()
        log_wrap = QWidget()
        log_wrap_l = QVBoxLayout(log_wrap)
        log_wrap_l.setContentsMargins(20, 20, 20, 20)
        lhdr = QHBoxLayout()
        lt = QLabel("Activity log")
        lt.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {COLORS['ink']};")
        cpy = QPushButton("Copy")
        cpy.clicked.connect(lambda: QApplication.clipboard().setText(self._log_panel.toPlainText()))
        clr = QPushButton("Clear")
        clr.clicked.connect(self._log_panel.clear)
        lhdr.addWidget(lt); lhdr.addStretch(); lhdr.addWidget(cpy); lhdr.addWidget(clr)
        log_wrap_l.addLayout(lhdr)
        log_wrap_l.addWidget(self._log_panel)
        self._stack.addWidget(log_wrap)

        main_layout.addWidget(self._stack)
        root.addWidget(main_area)

        # Default nav
        self._nav_to("fleet")

    # ── Nav ───────────────────────────────────────────────────────────────────
    def _nav_to(self, key):
        pages = ["fleet", "status", "task", "livemap", "reports", "console", "log"]
        idx = pages.index(key)
        self._stack.setCurrentIndex(idx)
        for k, btn in self._nav_btns.items():
            btn.setActive(k == key)

    # ── Connect ───────────────────────────────────────────────────────────────
    def _do_connect(self):
        client_id = self.cfg_client_id.text().strip()
        client_secret = self.cfg_client_secret.text().strip()
        access_key = self.cfg_access_key.text().strip()
        if not client_id or not client_secret or not access_key:
            self.log("All three credentials are required: client ID, client secret, open access key", "err")
            return
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Connecting…")
        self.log("Fetching OAuth token…")
        t = ApiThread(
            OAUTH_URL, token=None, method="POST",
            body={
                "grant_type": GRANT_TYPE,
                "client_id": client_id,
                "client_secret": client_secret,
                "open_access_key": access_key,
            },
            tag="oauth"
        )
        t.finished.connect(self._on_oauth)
        t.start()
        self._threads.append(t)

    @staticmethod
    def _token_lifetime_seconds(expires_raw):
        """Normalize Gausium's expires_in into seconds-from-now.

        Gausium may return a relative duration (seconds) or an absolute expiry
        timestamp in seconds or milliseconds — we detect which by magnitude.
        A real duration is at most a few million seconds; anything in the
        ~1e9 (epoch seconds) or ~1e12 (epoch ms) range is an absolute time.
        """
        try:
            val = int(expires_raw)
        except (TypeError, ValueError):
            return None
        now = time.time()
        if val > 1_000_000_000_000:      # epoch milliseconds
            return int(val / 1000 - now)
        if val > 1_000_000_000:          # epoch seconds
            return int(val - now)
        return val                       # plain duration in seconds

    @staticmethod
    def _fmt_duration(secs):
        secs = int(secs)
        if secs < 0:
            return "expired"
        if secs < 60:
            return f"{secs}s"
        if secs < 3600:
            return f"{secs // 60} min"
        if secs < 86400:
            return f"{secs // 3600} h {(secs % 3600) // 60} min"
        return f"{secs // 86400} d {(secs % 86400) // 3600} h"

    def _on_oauth(self, ok, status, data, tag):
        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("⚡  Connect")
        if ok and data.get("access_token"):
            self._bearer_token = data["access_token"]
            remaining = self._token_lifetime_seconds(data.get("expires_in"))
            disp = self._fmt_duration(remaining) if remaining is not None else "unknown"
            self._token_status.setText(f"✓ Token valid ({disp})")
            self._token_status.setStyleSheet(f"font-size: 11px; color: {COLORS['teal']}; padding: 0 4px;")
            self.log(f"OAuth token obtained (expires in {disp})", "ok")
            # Persist credentials (never store the token itself — fetch fresh each time)
            save_credentials({
                "client_id": self.cfg_client_id.text().strip(),
                "client_secret": self.cfg_client_secret.text().strip(),
                "open_access_key": self.cfg_access_key.text().strip(),
                "robot_sn": self.sn(),
            })
            self._load_fleet()
            self._load_sn_list()
            self._refresh_interval_changed()
            self._notify_toggled(self.cfg_notify.isChecked())   # start background notify poll
            # Auto-renew token slightly before expiry. Fall back to 55 min when the
            # lifetime is unknown. QTimer.singleShot takes a 32-bit int of milliseconds
            # (max ~24.8 days), so clamp long-lived tokens to that ceiling.
            renew_secs = max(60, remaining - 60) if remaining is not None else 3300
            renew_ms = min(renew_secs * 1000, 2_147_483_647)
            QTimer.singleShot(renew_ms, self._renew_token)
        else:
            self._bearer_token = ""
            self._token_status.setText("✗ Auth failed")
            self._token_status.setStyleSheet(f"font-size: 11px; color: {COLORS['danger']}; padding: 0 4px;")
            err = data.get("error_description") or data.get("message") or data.get("error") or str(data)
            self.log(f"OAuth failed ({status}): {err}", "err")

    def _renew_token(self):
        if self.cfg_client_id.text().strip():
            self.log("Auto-renewing OAuth token…")
            self._do_connect()

    def _set_connected(self, ok):
        self._connected = ok
        self._conn_dot.setStyleSheet(f"color: {COLORS['teal'] if ok else COLORS['ink3']}; font-size: 8px;")
        self._conn_lbl.setText("Connected" if ok else "Not connected")

    def _refresh_interval_changed(self):
        self._refresh_timer.stop()
        intervals = [0, 15000, 30000, 60000]
        idx = self.cfg_refresh.currentIndex()
        ms = intervals[idx] if idx < len(intervals) else 0
        if ms > 0:
            self._refresh_timer.start(ms)

    def _auto_refresh(self):
        page = self._stack.currentIndex()
        if page == 1:
            self._load_status()

    # ── Notifications ───────────────────────────────────────────────────────────
    def _init_tray(self):
        """Set up a system-tray icon used to post desktop notifications.
        QSystemTrayIcon.showMessage works on macOS, Windows and Linux."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        pm = QPixmap(64, 64)
        pm.fill(Qt.GlobalColor.transparent)
        pp = QPainter(pm)
        pp.setRenderHint(QPainter.RenderHint.Antialiasing)
        pp.setBrush(QBrush(QColor(COLORS["accent"])))
        pp.setPen(Qt.PenStyle.NoPen)
        pp.drawEllipse(8, 8, 48, 48)
        pp.end()
        self._tray = QSystemTrayIcon(QIcon(pm), self)
        self._tray.setToolTip("Gausium Ops")
        self._tray.show()

    def _notify(self, title, body):
        """Post a desktop notification (and mirror it to the activity log)."""
        self.log(f"🔔 {title}: {body}", "ok")
        if self._tray and self.cfg_notify.isChecked():
            self._tray.showMessage(title, body, QSystemTrayIcon.MessageIcon.Information, 6000)

    def _notify_toggled(self, on):
        if on and self.tok():
            self._notify_timer.start(30000)     # background poll every 30 s
        else:
            self._notify_timer.stop()

    def _notify_tick(self):
        if self.tok() and self.sn():
            self._api(f"/openapi/v2alpha1/s/robots/{self.sn()}/status", "notify")

    def _on_notify(self, ok, data):
        if ok:
            self._check_state_change(data)

    def _check_state_change(self, data):
        """Detect a taskState transition and fire a notification. Shared by the
        background poll and the status/map polls, keyed on one previous value so
        each real transition notifies once regardless of which poll saw it."""
        ts = data.get("taskState")
        if not ts:
            return
        prev = self._prev_task_state
        self._prev_task_state = ts
        if prev and ts != prev:
            if prev == "RUNNING" and ts == "IDLE":
                self._notify("Task finished", f"{self.sn()} is now idle.")
            elif ts == "RUNNING":
                self._notify("Task started", f"{self.sn()} started cleaning.")
            else:
                self._notify("Robot state changed", f"{self.sn()}: {prev} → {ts}")

    # ── API helpers ───────────────────────────────────────────────────────────
    def tok(self):
        return self._bearer_token

    def sn(self):
        data = self.cfg_sn.currentData()
        return data if data else self.cfg_sn.currentText().strip()

    def log(self, msg, kind="info"):
        self._log_panel.append_log(msg, kind)
        self._status_bar.showMessage(msg, 4000)

    def _api(self, path, tag, method="GET", body=None, content_type="application/json"):
        """Fire an async request. `path` may be absolute or relative to BASE_URL.
        The result comes back to `_on_api_result`, keyed by `tag`. Pass
        content_type=None for endpoints that reject a Content-Type header."""
        url = path if path.startswith("http") else BASE_URL + path
        t = ApiThread(url, self.tok(), method, body, tag, content_type)
        t.finished.connect(self._on_api_result)
        t.start()
        # Keep references so threads aren't GC'd mid-flight; prune finished ones.
        self._threads.append(t)
        self._threads = [x for x in self._threads if x.isRunning()]

    def _on_console_send(self, method, path, body_text, send_ct):
        if not self.tok():
            self._console_pane.show_response(False, 0, {"error": "Not connected — get a token first."})
            return
        if not path:
            self._console_pane.show_response(False, 0, {"error": "Path is required."})
            return
        path = path.replace("{sn}", self.sn())
        body = None
        if body_text:
            body = body_text.replace("{sn}", self.sn())
            try:
                body = json.loads(body)
            except json.JSONDecodeError as e:
                self._console_pane.show_response(False, 0, {"error": f"Invalid JSON body: {e}"})
                return
        self._console_pane.set_sending()
        self.log(f"Console: {method} {path}")
        content_type = "application/json" if send_ct else None
        self._api(path, "console", method, body, content_type)

    def _on_api_result(self, ok, status, data, tag):
        """Single entry point for every API response; routes by `tag`."""
        if tag == "oauth":
            self._on_oauth(ok, status, data, tag)
        elif tag == "fleet":
            self._on_fleet(ok, status, data)
        elif tag == "status":
            self._on_status(ok, data)
        elif tag == "maps":
            self._on_maps(ok, data)
        elif tag == "subareas":
            self._on_subareas(ok, data)
        elif tag == "task":
            self._on_task(ok, data)
        elif tag == "cmd":
            self._on_cmd(ok, data)
        elif tag == "reports":
            self._on_reports(ok, data)
        elif tag == "sn_list":
            self._on_sn_list(ok, data)
        elif tag == "console":
            self._console_pane.show_response(ok, status, data)
        elif tag == "monitor":
            self._on_monitor(ok, data)
        elif tag == "notify":
            self._on_notify(ok, data)
        elif tag == "monitor_mapurl":
            self._on_monitor_mapurl(ok, data)

    # ── Fleet ─────────────────────────────────────────────────────────────────
    def _load_fleet(self):
        if not self.tok(): return
        self._fleet_pane.set_loading()
        # This endpoint rejects any Content-Type header (HTTP 415), so omit it.
        self._api("/v1alpha1/robots?page=1&pageSize=50", "fleet", content_type=None)

    def _on_fleet(self, ok, status, data):
        # A 200 with an empty list is a successful call that simply matched no
        # robots — not a failure. Only treat non-2xx / malformed responses as errors.
        if ok and "robots" in data:
            robots = data.get("robots") or []
            self._set_connected(True)
            self._fleet_pane.populate(robots)
            if robots:
                self.log(f"Fleet loaded: {len(robots)} robot(s)", "ok")
            else:
                self.log("Connected — API returned 0 robots for this account.", "warn")
        else:
            self._fleet_pane.populate([])
            detail = json.dumps(data) if data else "empty response"
            self.log(f"Fleet load failed (HTTP {status}): {detail}", "err")

    def _load_sn_list(self):
        self._api("/v1alpha1/robots?page=1&pageSize=50", "sn_list", content_type=None)

    def _on_sn_list(self, ok, data):
        if not (ok and data.get("robots")):
            return
        current = self.sn()
        self.cfg_sn.blockSignals(True)
        self.cfg_sn.clear()
        for r in data["robots"]:
            sn = r.get("serialNumber", "")
            name = r.get("displayName") or sn
            label = f"{name}  ·  {sn}" if name != sn else sn
            self.cfg_sn.addItem(label, userData=sn)
        # Restore previous selection if still present
        idx = self.cfg_sn.findData(current)
        if idx >= 0:
            self.cfg_sn.setCurrentIndex(idx)
        elif current:
            self.cfg_sn.setCurrentText(current)
        self.cfg_sn.blockSignals(False)

    def _on_robot_selected(self, serial):
        idx = self.cfg_sn.findData(serial)
        if idx >= 0:
            self.cfg_sn.setCurrentIndex(idx)
        else:
            self.cfg_sn.setCurrentText(serial)
        self.log(f"Selected robot: {serial}", "ok")
        self._nav_to("status")
        self._load_status()

    # ── Status ────────────────────────────────────────────────────────────────
    def _load_status(self):
        if not self.tok() or not self.sn(): return
        self._api(f"/openapi/v2alpha1/s/robots/{self.sn()}/status", "status")

    def _on_status(self, ok, data):
        if ok:
            self._set_connected(True)
            self._last_status = data
            self._status_pane.update_status(data)
            # Feed the robot's real cleaning modes into the Launch task pane.
            self._task_pane.set_clean_modes(data.get("cleanModes") or data.get("workModes"))
            self._check_state_change(data)
            self.log("Status refreshed", "ok")
        else:
            self.log("Status error: " + str(data.get("error") or data.get("message") or ""), "err")

    # ── Live map ────────────────────────────────────────────────────────────────
    def _toggle_map_monitor(self, on):
        if on:
            if not self.tok() or not self.sn():
                self.log("Connect and select a robot first.", "err")
                self._live_map_pane.stop()
                return
            self._map_loaded_id = None
            self._live_map_pane.canvas.clear_trail()       # fresh path per session
            self._live_map_pane.set_info("Loading map and tracking position…")
            self._map_monitor_tick()                       # immediate first poll
            self._map_timer.start(self._live_map_pane.interval_ms())
        else:
            self._map_timer.stop()
            self._live_map_pane.set_info("Monitoring stopped.")

    def _map_monitor_tick(self):
        if not self.tok() or not self.sn():
            return
        self._api(f"/openapi/v2alpha1/s/robots/{self.sn()}/status", "monitor")

    def _on_monitor(self, ok, data):
        if not ok:
            self._live_map_pane.set_info("Status fetch failed — is the robot online?")
            return
        self._check_state_change(data)
        loc = data.get("localizationInfo") or {}
        mp = loc.get("mapPosition") or {}
        gx, gy, angle = mp.get("x"), mp.get("y"), mp.get("angle") or 0
        navpoints = [
            (p.get("naviPointName") or "", p.get("navPointGridX"), p.get("navPointGridY"))
            for p in ((data.get("navigationPoints") or {}).get("naviPoints") or [])
            if p.get("navPointGridX") is not None and p.get("navPointGridY") is not None
        ]
        if gx is not None and gy is not None:
            self._live_map_pane.update_robot(gx, gy, angle, navpoints)
            self._live_map_pane.set_info(
                f"Robot at grid ({gx}, {gy}), heading {round(angle)}°  ·  {data.get('taskState', '')}")
        # Fetch the map image once per map (presigned URL → download off-thread).
        # The endpoint requires a non-blank mapName, so pass it from the status.
        m = loc.get("map") or {}
        map_id, map_name = m.get("id"), m.get("name") or ""
        if map_id and map_id != self._map_loaded_id:
            self._map_loaded_id = map_id
            qs = urlencode({"mapId": map_id, "mapVersion": "", "mapName": map_name})
            self._api(f"/openapi/v2alpha1/robots/{self.sn()}/map?{qs}", "monitor_mapurl")

    def _on_monitor_mapurl(self, ok, data):
        uri = (data.get("downloadUri") or (data.get("data") or {}).get("downloadUri")) if ok else None
        if not uri:
            self._map_loaded_id = None       # allow a retry on the next tick
            self._live_map_pane.set_info("Could not get the map image URL.")
            self.log(f"Map image URL failed (ok={ok}): {json.dumps(data)[:300]}", "err")
            return
        self._dl_thread = DownloadThread(uri)
        self._dl_thread.finished.connect(self._on_map_downloaded)
        self._dl_thread.start()

    def _on_map_downloaded(self, ok, raw):
        if not ok or not raw:
            self._live_map_pane.set_info("Map image download failed.")
            return
        pm = QPixmap()
        if pm.loadFromData(raw):
            self._live_map_pane.set_map_image(pm)
        else:
            self._live_map_pane.set_info("Map image could not be decoded.")

    def _return_to_charge(self):
        """Send the robot to its charging point via a CROSS_NAVIGATE command.

        Map name and the charging point name are read from the latest status
        so we send real values, and the exact payload is confirmed before it
        moves a physical robot.
        """
        if not self.tok() or not self.sn():
            self.log("Token and robot SN required", "err")
            return
        if not self._last_status:
            self.log("Load status first so the map and charging point are known.", "warn")
            return
        loc = self._last_status.get("localizationInfo") or {}
        map_name = (loc.get("map") or {}).get("name")
        points = ((self._last_status.get("navigationPoints") or {}).get("naviPoints")) or []
        charge_pt = next(
            (p.get("naviPointName") for p in points
             if "charg" in (p.get("naviPointName") or "").lower()), None)
        if not map_name or not charge_pt:
            self.log("No charging navigation point found in this robot's map.", "err")
            return

        payload = {
            "serialNumber": self.sn(),
            "remoteNavigationCommandType": "CROSS_NAVIGATE",
            "commandParameter": {
                "startNavigationParameter": {"map": map_name, "position": charge_pt}
            },
        }
        # Physical movement — confirm with the exact payload before sending.
        resp = QMessageBox.question(
            self, "Return to charging",
            f"Send {self.sn()} to “{charge_pt}” on map “{map_name}”?\n\n"
            f"This will move the robot.\n\n{json.dumps(payload, indent=2)}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if resp != QMessageBox.StandardButton.Yes:
            self.log("Return to charging cancelled.", "info")
            return
        self.log(f"Navigating to charging point “{charge_pt}”…")
        self._api(f"/v1alpha1/robots/{self.sn()}/commands", "cmd", "POST", payload)

    def _send_cmd(self, cmd_type):
        labels = {"STOP_TASK": "Stop", "PAUSE_TASK": "Pause", "RESUME_TASK": "Resume"}
        self.log(f"Sending {labels.get(cmd_type, cmd_type)}…")
        self._api(
            f"/v1alpha1/robots/{self.sn()}/commands",
            "cmd", "POST",
            {"serialNumber": self.sn(), "remoteTaskCommandType": cmd_type}
        )

    def _on_cmd(self, ok, data):
        msg = "Command sent" if ok else "Command failed: " + str(data.get("message") or data.get("error") or "")
        self.log(msg, "ok" if ok else "err")
        if ok:
            QTimer.singleShot(1500, self._load_status)

    # ── Maps ──────────────────────────────────────────────────────────────────
    def _load_maps(self):
        if not self.tok() or not self.sn():
            self.log("Token and robot SN required", "err")
            return
        self.log("Loading robot maps…")
        self._api("/openapi/v1/map/robotMap/list", "maps", "POST", {"robotSn": self.sn()})

    def _on_maps(self, ok, data):
        # robotMap/list wraps the list under "data".
        maps = data.get("data") if isinstance(data.get("data"), list) else (
            data.get("maps") or data.get("mapList") or [])
        self._task_pane.populate_maps(maps or [])
        if ok and maps:
            self.log(f"Maps loaded: {len(maps)} map(s)", "ok")
        elif ok:
            self.log("No maps found for this robot.", "warn")
        else:
            self.log("Map load failed: " + json.dumps(data)[:200], "err")

    def _load_subareas(self, map_id):
        if not self.tok() or not self.sn() or not map_id:
            return
        self.log("Loading areas for map…")
        self._api("/openapi/v1/map/subareas/get", "subareas", "POST",
                  {"mapId": map_id, "robotSn": self.sn()})

    def _on_subareas(self, ok, data):
        partitions = (((data.get("data") or {}).get("subareas") or {}).get("partitions")) or []
        self._task_pane.populate_areas(partitions)
        if ok:
            self.log(f"Areas loaded: {len(partitions)} area(s)", "ok" if partitions else "warn")
        else:
            self.log("Area load failed: " + json.dumps(data)[:200], "err")

    # ── Task ──────────────────────────────────────────────────────────────────
    def _launch_task(self, payload):
        if not self.tok() or not self.sn():
            self.log("Token and robot SN required", "err")
            return
        payload["productId"] = self.sn()
        start = payload["tempTaskCommand"]["startParam"]
        if not start["mapId"]:
            self.log("Select a map first (Load maps from robot).", "err")
            return
        if not start["areaId"]:
            self.log("Select an area first.", "err")
            return
        if not payload["tempTaskCommand"]["taskName"]:
            self.log("Task name is required.", "err")
            return
        task_name = payload["tempTaskCommand"]["taskName"]
        self.log(f'Launching task "{task_name}"…')
        self._api("/openapi/v2alpha1/robotCommand/tempTask:send", "task", "POST", payload)

    def _on_task(self, ok, data):
        self._task_pane.set_response(ok, data)
        cmd_status = data.get("cmdStatus")
        result_code = data.get("cmdResultCode")
        # The reliable failure signal is a known task-startup error code (the
        # 201010000x family) or an HTTP error. cmdStatus 0 is a clean accept;
        # other statuses (e.g. 5) with an unrecognised code mean the robot took
        # the task and is executing — treat those as accepted, not rejected.
        if not ok:
            self.log("Task rejected: " + str(data.get("message") or result_code or data.get("error") or ""), "err")
        elif str(result_code) in TASK_ERROR_CODES:
            self.log(f"Task rejected (code {result_code}): {TASK_ERROR_CODES[str(result_code)]}", "err")
        elif cmd_status == 0:
            self.log("Task accepted (cmdStatus 0)", "ok")
            QTimer.singleShot(2000, self._load_status)
        else:
            self.log(f"Task accepted — robot executing (cmdStatus {cmd_status}, code {result_code})", "ok")
            QTimer.singleShot(2000, self._load_status)

    # ── Reports ───────────────────────────────────────────────────────────────
    def _load_reports(self, from_iso, to_iso):
        if not self.tok() or not self.sn(): return
        url = f"/openapi/v2alpha1/robots/{self.sn()}/taskReports?page=1&pageSize=50"
        if from_iso:
            url += f"&startTimeUtcFloor={from_iso}"
        if to_iso:
            url += f"&startTimeUtcUpper={to_iso}"
        self.log("Loading task reports…")
        self._api(url, "reports")

    def _on_reports(self, ok, data):
        reports = data.get("robotTaskReports") or []
        if ok and reports:
            self._reports_pane.populate(reports)
            self.log(f"Reports loaded: {len(reports)} task(s)", "ok")
        elif ok:
            self.log("No reports found — try a wider date range", "warn")
        else:
            self.log("Reports error: " + str(data.get("error") or data.get("message") or ""), "err")

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Gausium Ops")
    app.setApplicationVersion("1.0.0")
    app.setStyleSheet(STYLESHEET)

    # Dark palette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(COLORS["bg"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(COLORS["ink"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(COLORS["bg4"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(COLORS["ink"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(COLORS["bg4"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(COLORS["ink"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(COLORS["accent"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())
