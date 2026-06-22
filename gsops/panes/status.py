#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# =============================================================================
#            GAUSIUM OPS
# =============================================================================
# PROJECT : Guillaume Bally
# FILE : status.py
# DESCRIPTION : Live status tab: metrics, health banner, consumables, and robot controls.
"""
========= ============== ======================================================
Version   Date           Comment
========= ============== ======================================================
0.1.0     2026/06/22     Creation
========= ============== ======================================================
"""

# [IMPORTS]--------------------------------------------------------------------
import json
from datetime import datetime
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFormLayout, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QTextEdit, QVBoxLayout, QWidget
from ..config import COLORS, MONO_FONT
from ..widgets import accent_button, card, danger_button, metric_card, section_label

# [MODULE INFO]----------------------------------------------------------------
__author__ = 'Guillaume'
__date__ = '2026/06/22'
__version__ = '0.1.0'
__maintainer__ = 'Guillaume'
__email__ = 'guillaumepointbally@gmail.com'

# [Functions]------------------------------------------------------------------
class StatusPane(QWidget):
    """Live status tab: battery/mode/map metrics, details, consumables, and the
    Stop/Pause/Resume + Return-to-charging controls. `update_status(data)`
    re-renders everything from a V2 status payload."""
    send_command = pyqtSignal(str)          # remoteTaskCommandType (STOP/PAUSE/RESUME)
    refresh_requested = pyqtSignal()
    navigate_charge = pyqtSignal()          # request CROSS_NAVIGATE to the dock

    def __init__(self):
        super().__init__()
        self._stall_count = 0  # consecutive polls of "running but not moving"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("Live Status")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {COLORS['ink']};")
        self.refresh_btn = accent_button("↻  Refresh")
        self.refresh_btn.clicked.connect(self.refresh_requested)
        hdr.addWidget(title)
        hdr.addStretch()
        hdr.addWidget(self.refresh_btn)
        layout.addLayout(hdr)

        # Health / alert banner — colour-coded summary refreshed on every poll.
        self._health = QLabel("—")
        self._health.setWordWrap(True)
        self._set_health("ok", "Awaiting status…")
        layout.addWidget(self._health)

        # Metric grid
        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(10)
        self._bat_card, self._bat_val = metric_card("Battery", color=COLORS["teal"])
        self._mode_card, self._mode_val = metric_card("Mode")
        self._map_card, self._map_val = metric_card("Current map")
        self._ts_card, self._ts_val = metric_card("Last refresh")
        self._mode_val.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {COLORS['ink']};")
        self._map_val.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {COLORS['ink']};")
        self._ts_val.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {COLORS['ink']};")
        metrics_grid.addWidget(self._bat_card, 0, 0)
        metrics_grid.addWidget(self._mode_card, 0, 1)
        metrics_grid.addWidget(self._map_card, 0, 2)
        metrics_grid.addWidget(self._ts_card, 0, 3)
        layout.addLayout(metrics_grid)

        # Details + Consumables
        mid = QHBoxLayout()
        mid.setSpacing(10)

        # Details card
        det_card = card()
        det_layout = QVBoxLayout(det_card)
        det_layout.setContentsMargins(14, 12, 14, 12)
        det_layout.addWidget(section_label("Robot details"))
        self._details_layout = QFormLayout()
        self._details_layout.setSpacing(6)
        self._details_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        det_layout.addLayout(self._details_layout)
        det_layout.addStretch()
        mid.addWidget(det_card)

        # Consumables card
        cons_card = card()
        cons_layout = QVBoxLayout(cons_card)
        cons_layout.setContentsMargins(14, 12, 14, 12)
        cons_layout.addWidget(section_label("Consumables"))
        self._cons_layout = QVBoxLayout()
        self._cons_layout.setSpacing(8)
        cons_layout.addLayout(self._cons_layout)
        cons_layout.addStretch()
        mid.addWidget(cons_card)

        layout.addLayout(mid)

        # Command buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._stop_btn = danger_button("⏹  Stop task")
        self._stop_btn.clicked.connect(lambda: self.send_command.emit("STOP_TASK"))
        self._pause_btn = QPushButton("⏸  Pause")
        self._pause_btn.clicked.connect(lambda: self.send_command.emit("PAUSE_TASK"))
        self._resume_btn = QPushButton("▶  Resume")
        self._resume_btn.clicked.connect(lambda: self.send_command.emit("RESUME_TASK"))
        btn_row.addWidget(self._stop_btn)
        btn_row.addWidget(self._pause_btn)
        btn_row.addWidget(self._resume_btn)
        btn_row.addStretch()
        self._charge_btn = accent_button("⌂  Return to charging")
        self._charge_btn.clicked.connect(self.navigate_charge)
        btn_row.addWidget(self._charge_btn)
        layout.addLayout(btn_row)

        # Raw JSON accordion
        self._raw = QTextEdit()
        self._raw.setReadOnly(True)
        self._raw.setMinimumHeight(300)
        self._raw.setStyleSheet(f"""
            QTextEdit {{
                background: {COLORS['bg4']};
                color: {COLORS['ink2']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                font-family: {MONO_FONT};
                font-size: 11px;
                padding: 8px;
            }}
        """)
        self._raw.setPlaceholderText("Raw API response will appear here…")
        layout.addWidget(self._raw)

    def _form_row(self, key, value, color=None):
        k = QLabel(key)
        k.setStyleSheet(f"color: {COLORS['ink2']}; font-size: 12px;")
        v = QLabel(str(value))
        v.setStyleSheet(f"color: {color or COLORS['ink']}; font-size: 12px; font-weight: 500;")
        v.setWordWrap(True)
        self._details_layout.addRow(k, v)

    _HEALTH_COLORS = {"ok": "teal", "warn": "warn", "danger": "danger"}

    def _set_health(self, level, text):
        c = COLORS[self._HEALTH_COLORS.get(level, "ink2")]
        icon = {"ok": "✓", "warn": "⚠", "danger": "✕"}.get(level, "•")
        self._health.setText(f"{icon}  {text}")
        self._health.setStyleSheet(
            f"background: {c}22; color: {c}; border: 1px solid {c}55; "
            f"border-radius: 7px; padding: 8px 12px; font-size: 13px; font-weight: 600;")

    def _assess_health(self, data):
        """Derive a health level + message from a status payload (poll-based;
        a richer signal would be the Incident Push webhook). Returns (level, msg)
        where level is 'ok' / 'warn' / 'danger'."""
        if not data.get("online"):
            self._stall_count = 0
            return "danger", "Robot offline"

        rank = {"ok": 0, "warn": 1, "danger": 2}
        level, alerts = "ok", []

        def bump(lv, msg):
            nonlocal level
            if rank[lv] > rank[level]:
                level = lv
            alerts.append(msg)

        if (data.get("emergencyStop") or {}).get("enabled"):
            bump("danger", "Emergency stop active")

        loc_state = (data.get("localizationInfo") or {}).get("localizationState")
        if loc_state and loc_state != "NORMAL":
            bump("danger", f"Localization {loc_state}")

        battery = data.get("battery") or {}
        bat, charging = battery.get("powerPercentage"), battery.get("charging")
        if bat is not None and not charging:
            if bat <= 15:
                bump("danger", f"Low battery {round(bat)}%")
            elif bat <= 30:
                bump("warn", f"Battery {round(bat)}%")

        # Heuristic "stuck": running but not moving across several consecutive polls.
        speed = data.get("speedKilometerPerHour") or 0
        if data.get("taskState") == "RUNNING" and speed == 0:
            self._stall_count += 1
        else:
            self._stall_count = 0
        if self._stall_count >= 3:
            bump("warn", "Possibly stalled (running but not moving)")

        if not alerts:
            return "ok", "Normal"
        return level, " · ".join(alerts)

    def update_status(self, data):
        # Colour-coded health banner derived from this poll's payload.
        self._set_health(*self._assess_health(data))

        # Battery (V2 nests it under "battery"; fall back to the older flat field).
        battery = data.get("battery") or {}
        bat = battery.get("powerPercentage")
        if bat is None:
            bat = data.get("currentBatteryPower")
        charging = bool(battery.get("charging"))
        bat_str = (f"{round(bat)}%" + (" ⚡" if charging else "")) if bat is not None else "—"
        bat_color = COLORS["teal"] if bat and bat > 40 else COLORS["warn"] if bat and bat > 15 else COLORS["danger"]
        self._bat_val.setText(bat_str)
        self._bat_val.setStyleSheet(f"font-size: 26px; font-weight: 600; color: {bat_color};")

        self._mode_val.setText(data.get("taskState") or data.get("robotMode") or data.get("taskStatus") or "—")

        loc = data.get("localizationInfo") or {}
        map_name = (loc.get("map") or {}).get("name") or data.get("currentMapName") or data.get("mapName") or "—"
        self._map_val.setText(map_name[:20])
        self._ts_val.setText(datetime.now().strftime("%H:%M:%S"))

        # Details
        while self._details_layout.rowCount():
            self._details_layout.removeRow(0)
        estop = (data.get("emergencyStop") or {}).get("enabled")
        if estop is None:
            estop = data.get("eStop")
        speed = data.get("speedKilometerPerHour")
        fields = [
            ("Online", "Yes" if data.get("online") else "No"),
            ("Task state", data.get("taskState") or "—"),
            ("Charging", "Yes" if charging else "No"),
            ("Speed", f"{speed} km/h" if speed is not None else "—"),
            ("Localization", loc.get("localizationState") or "—"),
            ("Nav status", data.get("navStatus") or "—"),
            ("E-Stop", "⚠ ACTIVE" if estop else "No"),
        ]
        for k, v in fields:
            ec = COLORS["danger"] if v == "⚠ ACTIVE" else None
            self._form_row(k, v, ec)

        # Consumables. Prefer an explicit residual-percentage map; otherwise derive
        # remaining life from the device's lifeSpan/usedLife pairs (V2 format).
        while self._cons_layout.count():
            item = self._cons_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        cons = {}
        explicit = data.get("consumablesResidualPercentage") or data.get("consumablesLife")
        if explicit:
            for k, v in explicit.items():
                try:
                    cons[k] = float(v)
                except (TypeError, ValueError):
                    pass
        else:
            device = data.get("device") or {}
            parts = [
                ("rollingBrush", "Rolling brush"),
                ("rightSideBrush", "Side brush"),
                ("softSqueegee", "Soft squeegee"),
                ("cleanWaterFilter", "Water filter"),
                ("hepaSensor", "HEPA sensor"),
            ]
            for key, label in parts:
                d = device.get(key) or {}
                ls, ul = d.get("lifeSpan"), d.get("usedLife")
                if ls and ls > 0 and ul is not None:
                    cons[label] = max(0.0, min(100.0, (1 - ul / ls) * 100))
        if cons:
            for k, v in cons.items():
                pct = max(0, min(100, round(float(v))))
                row = QHBoxLayout()
                lbl = QLabel(k)
                lbl.setFixedWidth(90)
                lbl.setStyleSheet(f"color: {COLORS['ink2']}; font-size: 12px;")
                bar = QProgressBar()
                bar.setValue(pct)
                bar.setTextVisible(False)
                bar.setFixedHeight(6)
                bar_color = COLORS["teal"] if pct > 55 else COLORS["warn"] if pct > 25 else COLORS["danger"]
                bar.setStyleSheet(f"QProgressBar {{ background: {COLORS['bg4']}; border: none; border-radius: 3px; }} QProgressBar::chunk {{ background: {bar_color}; border-radius: 3px; }}")
                pct_lbl = QLabel(f"{pct}%")
                pct_lbl.setFixedWidth(36)
                pct_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
                pct_lbl.setStyleSheet(f"color: {COLORS['ink']}; font-size: 12px; font-weight: 600;")
                row.addWidget(lbl)
                row.addWidget(bar)
                row.addWidget(pct_lbl)
                w = QWidget()
                w.setLayout(row)
                w.setStyleSheet("background: transparent;")
                self._cons_layout.addWidget(w)
        else:
            lbl = QLabel("No consumable data")
            lbl.setStyleSheet(f"color: {COLORS['ink3']}; font-size: 11px;")
            self._cons_layout.addWidget(lbl)

        self._raw.setPlainText(json.dumps(data, indent=2))
