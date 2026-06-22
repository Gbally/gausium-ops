#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# =============================================================================
#            GAUSIUM OPS
# =============================================================================
# PROJECT : Guillaume Bally
# FILE : console.py
# DESCRIPTION : API console tab: send raw requests and inspect responses.
"""
========= ============== ======================================================
Version   Date           Comment
========= ============== ======================================================
0.1.0     2026/06/22     Creation
========= ============== ======================================================
"""

# [IMPORTS]--------------------------------------------------------------------
import json
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QApplication, QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget
from ..config import COLORS, MONO_FONT
from ..widgets import accent_button, card, section_label

# [MODULE INFO]----------------------------------------------------------------
__author__ = 'Guillaume'
__date__ = '2026/06/22'
__version__ = '0.1.0'
__maintainer__ = 'Guillaume'
__email__ = 'guillaumepointbally@gmail.com'

# [Functions]------------------------------------------------------------------
class ConsolePane(QWidget):
    """Interactive API console — pick or type a request, send it with the live
    token, and inspect the raw status + JSON response. Built to debug the
    map / area-id flow: presets include the subareas call (where area ids live).
    """
    # method, path, body_text, send_content_type
    send_request = pyqtSignal(str, str, str, bool)

    # (label, method, path, body) — {sn} is substituted with the current robot SN.
    PRESETS = [
        ("List robots", "GET", "/v1alpha1/robots?page=1&pageSize=50", ""),
        ("Get status (V2)", "GET", "/openapi/v2alpha1/s/robots/{sn}/status", ""),
        ("Get site info (site-bound robots only)", "GET",
         "/openapi/v2alpha1/robots/{sn}/getSiteInfo", ""),
        ("Get subareas → area ids", "POST", "/openapi/v1/map/subareas/get",
         '{\n  "mapId": "PASTE_MAP_ID_HERE",\n  "robotSn": "{sn}"\n}'),
        ("List robot maps → map ids (no site)", "POST", "/openapi/v1/map/robotMap/list",
         '{\n  "robotSn": "{sn}"\n}'),
        ("Get robot map (image URL)", "GET",
         "/openapi/v2alpha1/robots/{sn}/map?mapId=PASTE_MAP_ID&mapVersion=PASTE_MAP_VERSION&mapName=PASTE_MAP_NAME", ""),
        ("List task reports", "GET",
         "/openapi/v2alpha1/robots/{sn}/taskReports?page=1&pageSize=20", ""),
        ("Send command (pause)", "POST", "/v1alpha1/robots/{sn}/commands",
         '{\n  "serialNumber": "{sn}",\n  "remoteTaskCommandType": "PAUSE_TASK"\n}'),
        ("Navigate to charging (moves robot!)", "POST", "/v1alpha1/robots/{sn}/commands",
         '{\n  "serialNumber": "{sn}",\n  "remoteNavigationCommandType": "CROSS_NAVIGATE",\n'
         '  "commandParameter": {\n    "startNavigationParameter": '
         '{ "map": "MAP_NAME", "position": "charging" }\n  }\n}'),
        ("Send temp task", "POST", "/openapi/v2alpha1/robotCommand/tempTask:send",
         '{\n  "productId": "{sn}",\n  "tempTaskCommand": {\n    "taskName": "test",\n'
         '    "startParam": { "mapId": "", "areaId": "" }\n  }\n}'),
        ("Start task (START_TASK, by name)", "POST", "/v1alpha1/robots/{sn}/commands",
         '{\n  "serialNumber": "{sn}",\n  "remoteTaskCommandType": "START_TASK",\n'
         '  "commandParameter": {\n    "startTaskParameter": {\n'
         '      "cleaningMode": "__middle_cleaning",\n'
         '      "task": { "loop": false, "loopCount": 1, "map": "MAP_NAME", "name": "PASTE_TASK_NAME" }\n'
         '    }\n  }\n}'),
    ]

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel("API Console")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {COLORS['ink']};")
        layout.addWidget(title)

        hint = QLabel(
            "Send raw requests with the active token and inspect the response. "
            "mapId comes from “Get site info / maps”; area ids come from "
            "“Get subareas” → subareas.partitions[].id. {sn} is replaced with the selected robot."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {COLORS['ink2']}; font-size: 12px;")
        layout.addWidget(hint)

        # Request builder card
        req_card = card()
        req_l = QVBoxLayout(req_card)
        req_l.setContentsMargins(14, 12, 14, 14)
        req_l.setSpacing(8)

        req_l.addWidget(section_label("Request"))

        # Preset + method + path row
        row = QHBoxLayout()
        row.setSpacing(8)
        self.preset = QComboBox()
        self.preset.addItem("— Preset —", None)
        for i, (label, *_rest) in enumerate(self.PRESETS):
            self.preset.addItem(label, i)
        self.preset.currentIndexChanged.connect(self._apply_preset)
        self.preset.setMinimumWidth(180)

        self.method = QComboBox()
        self.method.addItems(["GET", "POST", "PUT", "DELETE"])
        self.method.setFixedWidth(90)

        self.path = QLineEdit()
        self.path.setPlaceholderText("/v1alpha1/robots?page=1&pageSize=50")

        row.addWidget(self.preset)
        row.addWidget(self.method)
        row.addWidget(self.path, 1)
        req_l.addLayout(row)

        # Body
        req_l.addWidget(section_label("Body (JSON — for POST/PUT, or GET-with-body like subareas)"))
        self.body = QTextEdit()
        self.body.setPlaceholderText("{ }")
        self.body.setFixedHeight(120)
        self.body.setStyleSheet(f"font-family: {MONO_FONT}; font-size: 12px;")
        req_l.addWidget(self.body)

        # Options + send
        opt_row = QHBoxLayout()
        self.send_ct = QCheckBox("Send Content-Type: application/json")
        self.send_ct.setChecked(True)
        self.send_ct.setStyleSheet(f"color: {COLORS['ink2']}; font-size: 12px;")
        ct_hint = QLabel("(uncheck for /v1alpha1/robots — it rejects Content-Type)")
        ct_hint.setStyleSheet(f"color: {COLORS['ink3']}; font-size: 11px;")
        self.send_btn = accent_button("➤  Send")
        self.send_btn.clicked.connect(self._emit_send)
        opt_row.addWidget(self.send_ct)
        opt_row.addWidget(ct_hint)
        opt_row.addStretch()
        opt_row.addWidget(self.send_btn)
        req_l.addLayout(opt_row)

        layout.addWidget(req_card)

        # Response card
        resp_card = card()
        resp_l = QVBoxLayout(resp_card)
        resp_l.setContentsMargins(14, 12, 14, 14)
        resp_l.setSpacing(8)
        resp_hdr = QHBoxLayout()
        resp_hdr.addWidget(section_label("Response"))
        resp_hdr.addStretch()
        self.status_lbl = QLabel("—")
        self.status_lbl.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {COLORS['ink2']};")
        copy_btn = QPushButton("Copy")
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(self.resp.toPlainText()))
        resp_hdr.addWidget(self.status_lbl)
        resp_hdr.addWidget(copy_btn)
        resp_l.addLayout(resp_hdr)

        self.resp = QTextEdit()
        self.resp.setReadOnly(True)
        self.resp.setStyleSheet(
            f"font-family: {MONO_FONT}; font-size: 12px; "
            f"background: {COLORS['bg2']}; color: {COLORS['ink2']};")
        self.resp.setMinimumHeight(220)
        resp_l.addWidget(self.resp)

        layout.addWidget(resp_card)

    def _apply_preset(self, _idx):
        i = self.preset.currentData()
        if i is None:
            return
        _label, method, path, body = self.PRESETS[i]
        self.method.setCurrentText(method)
        self.path.setText(path)
        self.body.setPlainText(body)
        # /v1alpha1/robots list rejects Content-Type; everything else needs it.
        self.send_ct.setChecked(not path.startswith("/v1alpha1/robots?"))

    def _emit_send(self):
        self.send_request.emit(
            self.method.currentText(),
            self.path.text().strip(),
            self.body.toPlainText().strip(),
            self.send_ct.isChecked(),
        )

    def set_sending(self):
        self.status_lbl.setText("sending…")
        self.status_lbl.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {COLORS['warn']};")

    def show_response(self, ok, status, data):
        color = COLORS["teal"] if ok else COLORS["danger"]
        self.status_lbl.setText(f"HTTP {status}" if status else ("OK" if ok else "ERROR"))
        self.status_lbl.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {color};")
        try:
            self.resp.setPlainText(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception:
            self.resp.setPlainText(str(data))
