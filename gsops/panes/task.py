#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# =============================================================================
#            GAUSIUM OPS
# =============================================================================
# PROJECT : Guillaume Bally
# FILE : task.py
# DESCRIPTION : Launch task tab: map/area selection and temporary-task dispatch.
"""
========= ============== ======================================================
Version   Date           Comment
========= ============== ======================================================
0.1.0     2026/06/22     Creation
========= ============== ======================================================
"""

# [IMPORTS]--------------------------------------------------------------------
import json
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget
from ..config import COLORS, MONO_FONT, mode_label
from ..widgets import accent_button, card, section_label

# [MODULE INFO]----------------------------------------------------------------
__author__ = 'Guillaume'
__date__ = '2026/06/22'
__version__ = '0.1.0'
__maintainer__ = 'Guillaume'
__email__ = 'guillaumepointbally@gmail.com'

# [Functions]------------------------------------------------------------------
class TaskPane(QWidget):
    """Launch task tab. Flow: Load maps → pick a map (loads its areas) → pick an
    area + cleaning mode + name → Start task. Dropdowns store the real IDs as item
    data; `_build_payload()` assembles the tempTask body shown in the live preview."""
    launch_task = pyqtSignal(dict)          # assembled tempTask payload
    load_maps = pyqtSignal()                # request robotMap/list
    load_subareas = pyqtSignal(str)         # request subareas/get for a mapId

    def __init__(self):
        super().__init__()
        self._map_data = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel("Launch Task")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {COLORS['ink']};")
        layout.addWidget(title)

        # Info banner
        banner = QLabel("ℹ  Click Load maps to auto-fill IDs from your robot's site. Verify the payload preview before launching.")
        banner.setWordWrap(True)
        banner.setStyleSheet(f"""
            background: rgba(74,158,221,0.1);
            color: #85b7eb;
            border: 1px solid rgba(74,158,221,0.25);
            border-radius: 7px;
            padding: 9px 12px;
            font-size: 12px;
        """)
        layout.addWidget(banner)

        # Two-column form
        cols = QHBoxLayout()
        cols.setSpacing(10)

        # Left — task params
        left = card()
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(14, 12, 14, 12)
        left_l.addWidget(section_label("Task parameters"))
        left_l.addSpacing(6)

        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        def mk_lbl(t):
            l = QLabel(t)
            l.setStyleSheet(f"color: {COLORS['ink2']}; font-size: 11px;")
            return l

        self.t_name = QLineEdit()
        self.t_name.setPlaceholderText("e.g. Daily clean")
        self.t_mapname = QLineEdit()
        self.t_mapname.setPlaceholderText("Auto-filled from selected map")
        self.t_mapname.setReadOnly(True)
        self.t_mode = QComboBox()
        # Sensible defaults (shown with English hints); replaced with the robot's
        # actual modes once status loads. The item *data* is the value sent to the API.
        for m in ["清扫", "吸尘", "清洗", "尘推", "__middle_cleaning"]:
            self.t_mode.addItem(mode_label(m), m)
        self.t_loops = QLineEdit("1")
        self.t_loop = QCheckBox("Loop")
        self.t_loop.setStyleSheet(f"color: {COLORS['ink2']}; font-size: 12px;")
        for w in [self.t_name, self.t_loops]:
            w.textChanged.connect(self._update_preview)
        self.t_mode.currentIndexChanged.connect(self._update_preview)
        self.t_loop.toggled.connect(self._update_preview)

        # Loop count + the loop on/off toggle share one row.
        loop_row = QHBoxLayout()
        loop_row.setContentsMargins(0, 0, 0, 0)
        loop_row.addWidget(self.t_loops)
        loop_row.addWidget(self.t_loop)

        form.addRow(mk_lbl("Task name"), self.t_name)
        form.addRow(mk_lbl("Map name"), self.t_mapname)
        form.addRow(mk_lbl("Cleaning mode"), self.t_mode)
        form.addRow(mk_lbl("Loop count"), loop_row)
        left_l.addLayout(form)
        left_l.addStretch()
        cols.addWidget(left)

        # Right — map & area
        right = card()
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(14, 12, 14, 12)
        right_l.addWidget(section_label("Map & area"))
        right_l.addSpacing(6)

        form2 = QFormLayout()
        form2.setSpacing(8)
        form2.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.t_map_sel = QComboBox()
        self.t_map_sel.addItem("— load maps first —", None)
        self.t_map_sel.currentIndexChanged.connect(self._on_map_selected)
        self.t_area_sel = QComboBox()
        self.t_area_sel.addItem("— select a map —", None)
        self.t_area_sel.currentIndexChanged.connect(self._update_preview)
        self.t_mapid = QLineEdit()
        self.t_mapid.setReadOnly(True)
        self.t_mapid.setPlaceholderText("Auto-filled from selected map")

        form2.addRow(mk_lbl("Map"), self.t_map_sel)
        form2.addRow(mk_lbl("Area"), self.t_area_sel)
        form2.addRow(mk_lbl("Map ID"), self.t_mapid)
        right_l.addLayout(form2)
        right_l.addSpacing(8)

        self.load_maps_btn = QPushButton("↓  Load maps from robot")
        self.load_maps_btn.clicked.connect(self.load_maps)
        right_l.addWidget(self.load_maps_btn)
        right_l.addStretch()
        cols.addWidget(right)

        layout.addLayout(cols)

        # Payload preview
        prev_card = card()
        prev_l = QVBoxLayout(prev_card)
        prev_l.setContentsMargins(14, 12, 14, 12)
        prev_l.addWidget(section_label("Payload preview"))
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMaximumHeight(140)
        self.preview.setStyleSheet(f"""
            QTextEdit {{
                background: {COLORS['bg4']};
                color: {COLORS['teal']};
                border: none;
                border-radius: 6px;
                font-family: {MONO_FONT};
                font-size: 11px;
                padding: 8px;
            }}
        """)
        prev_l.addWidget(self.preview)
        layout.addWidget(prev_card)

        # Launch button + response
        btn_row = QHBoxLayout()
        self.launch_btn = accent_button("▶  Start task")
        self.launch_btn.setMinimumWidth(140)
        self.launch_btn.clicked.connect(self._do_launch)
        btn_row.addWidget(self.launch_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.resp_box = QTextEdit()
        self.resp_box.setReadOnly(True)
        self.resp_box.setMaximumHeight(110)
        self.resp_box.setStyleSheet(f"""
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
        self.resp_box.setPlaceholderText("Response will appear here…")
        layout.addWidget(self.resp_box)

        self._update_preview()

    def _build_payload(self):
        return {
            "productId": "",
            "tempTaskCommand": {
                "cleaningMode": self.t_mode.currentData() or self.t_mode.currentText(),
                "loop": "true" if self.t_loop.isChecked() else "false",
                "loopCount": self.t_loops.text().strip() or "1",
                "taskName": self.t_name.text().strip(),
                "mapName": self.t_mapname.text().strip(),
                "startParam": {
                    "mapId": self.t_mapid.text().strip(),
                    # API requires area_id as a string, not the numeric partition id.
                    "areaId": str(self.t_area_sel.currentData()) if self.t_area_sel.currentData() is not None else "",
                }
            }
        }

    def _update_preview(self):
        p = self._build_payload()
        self.preview.setPlainText(json.dumps(p, indent=2, ensure_ascii=False))

    def set_clean_modes(self, modes):
        """Populate the cleaning-mode dropdown from the robot's reported modes."""
        names = [m.get("name") for m in (modes or []) if m.get("name")]
        if not names:
            return
        current = self.t_mode.currentData()
        self.t_mode.blockSignals(True)
        self.t_mode.clear()
        for n in names:
            self.t_mode.addItem(mode_label(n), n)
        idx = self.t_mode.findData(current)
        if idx >= 0:
            self.t_mode.setCurrentIndex(idx)
        self.t_mode.blockSignals(False)
        self._update_preview()

    def populate_maps(self, maps):
        self._map_data = maps
        self.t_map_sel.blockSignals(True)
        self.t_map_sel.clear()
        if not maps:
            self.t_map_sel.addItem("— no maps found —", None)
            self.t_map_sel.blockSignals(False)
            return
        self.t_map_sel.addItem("— pick a map —", None)
        for m in maps:
            self.t_map_sel.addItem(m.get("mapName") or m.get("name") or "Unknown", m)
        self.t_map_sel.blockSignals(False)
        # Auto-select the only map for convenience.
        if len(maps) == 1:
            self.t_map_sel.setCurrentIndex(1)

    def _on_map_selected(self, _idx):
        m = self.t_map_sel.currentData()
        # Reset area choices until the new map's subareas arrive.
        self.t_area_sel.blockSignals(True)
        self.t_area_sel.clear()
        self.t_area_sel.addItem("— loading areas… —", None)
        self.t_area_sel.blockSignals(False)
        if not m:
            self.t_mapid.clear()
            self.t_mapname.clear()
            self._update_preview()
            return
        self.t_mapid.setText(m.get("mapId") or "")
        self.t_mapname.setText(m.get("mapName") or m.get("name") or "")
        self._update_preview()
        if m.get("mapId"):
            self.load_subareas.emit(m["mapId"])

    def populate_areas(self, partitions):
        self.t_area_sel.blockSignals(True)
        self.t_area_sel.clear()
        if not partitions:
            self.t_area_sel.addItem("— no areas —", None)
        else:
            for p in partitions:
                pid = p.get("id")
                name = p.get("name") or f"area {pid}"
                self.t_area_sel.addItem(f"{name}  (id {pid})", pid)
        self.t_area_sel.blockSignals(False)
        self._update_preview()

    def _do_launch(self):
        p = self._build_payload()
        self.launch_task.emit(p)

    def set_response(self, ok, data):
        txt = json.dumps(data, indent=2, ensure_ascii=False)
        col = COLORS["teal"] if ok else COLORS["danger"]
        self.resp_box.setStyleSheet(self.resp_box.styleSheet().replace(COLORS["ink2"], col))
        self.resp_box.setPlainText(txt)
