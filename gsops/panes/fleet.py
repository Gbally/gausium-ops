#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# =============================================================================
#            GAUSIUM OPS
# =============================================================================
# PROJECT : Guillaume Bally
# FILE : fleet.py
# DESCRIPTION : Fleet tab: robot cards for every robot on the account.
"""
========= ============== ======================================================
Version   Date           Comment
========= ============== ======================================================
0.1.0     2026/06/22     Creation
========= ============== ======================================================
"""

# [IMPORTS]--------------------------------------------------------------------
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget
from ..config import COLORS
from ..widgets import accent_button

# [MODULE INFO]----------------------------------------------------------------
__author__ = 'Guillaume'
__date__ = '2026/06/22'
__version__ = '0.1.0'
__maintainer__ = 'Guillaume'
__email__ = 'guillaumepointbally@gmail.com'

# [Functions]------------------------------------------------------------------
class RobotCard(QFrame):
    """One robot tile in the Fleet pane; emits `selected(sn)` when chosen."""
    selected = pyqtSignal(str)

    def __init__(self, robot_data, parent=None):
        super().__init__(parent)
        self.sn = robot_data.get("serialNumber", "")
        online = robot_data.get("online", False)
        name = robot_data.get("displayName") or self.sn
        model = robot_data.get("modelTypeCode") or robot_data.get("modelFamilyCode", "—")
        sw = (robot_data.get("softwareVersion") or "—")[:20]

        self.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['bg3']};
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
            }}
            QFrame:hover {{
                border-color: {COLORS['accent']};
                background: {COLORS['bg4']};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(12)

        # Status indicator dot
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {COLORS['teal'] if online else COLORS['ink3']}; font-size: 10px;")
        layout.addWidget(dot)

        # Info
        info = QVBoxLayout()
        info.setSpacing(2)
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {COLORS['ink']};")
        sn_lbl = QLabel(f"{self.sn}  ·  {model}")
        sn_lbl.setStyleSheet(f"font-size: 11px; color: {COLORS['ink2']};")
        sw_lbl = QLabel(f"SW: {sw}")
        sw_lbl.setStyleSheet(f"font-size: 10px; color: {COLORS['ink3']};")
        info.addWidget(name_lbl)
        info.addWidget(sn_lbl)
        info.addWidget(sw_lbl)
        layout.addLayout(info)
        layout.addStretch()

        # Badge
        badge = QLabel("Online" if online else "Offline")
        badge.setStyleSheet(f"""
            background: {'rgba(78,203,169,0.15)' if online else 'rgba(90,88,112,0.3)'};
            color: {COLORS['teal'] if online else COLORS['ink3']};
            border-radius: 10px;
            padding: 3px 10px;
            font-size: 11px;
            font-weight: 600;
        """)
        layout.addWidget(badge)

        # Select button
        btn = accent_button("Select")
        btn.setFixedWidth(90)
        btn.clicked.connect(lambda: self.selected.emit(self.sn))
        layout.addWidget(btn)

class FleetPane(QWidget):
    """Grid of RobotCards for every robot on the account (the Fleet tab)."""
    robot_selected = pyqtSignal(str)
    log_msg = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Header row
        hdr = QHBoxLayout()
        title = QLabel("Fleet")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {COLORS['ink']};")
        self.refresh_btn = accent_button("↻  Refresh fleet")
        hdr.addWidget(title)
        hdr.addStretch()
        hdr.addWidget(self.refresh_btn)
        layout.addLayout(hdr)

        # Scroll area for robot cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        self.cards_widget = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_widget)
        self.cards_layout.setSpacing(8)
        self.cards_layout.addStretch()
        scroll.setWidget(self.cards_widget)
        layout.addWidget(scroll)

        self._placeholder()

    def _placeholder(self):
        self._clear_cards()
        lbl = QLabel("Click Refresh to load your fleet.")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"color: {COLORS['ink3']}; font-size: 13px; padding: 40px;")
        self.cards_layout.insertWidget(0, lbl)

    def _clear_cards(self):
        while self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def populate(self, robots):
        self._clear_cards()
        if not robots:
            lbl = QLabel("No robots found. Check token and permissions.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color: {COLORS['ink3']}; padding: 40px;")
            self.cards_layout.addWidget(lbl)
        else:
            for r in robots:
                rc = RobotCard(r)
                rc.selected.connect(self.robot_selected)
                self.cards_layout.addWidget(rc)
        self.cards_layout.addStretch()

    def set_loading(self):
        self._clear_cards()
        lbl = QLabel("Loading fleet…")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"color: {COLORS['ink2']}; padding: 40px;")
        self.cards_layout.addWidget(lbl)
        self.cards_layout.addStretch()
