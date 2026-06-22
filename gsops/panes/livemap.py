#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# =============================================================================
#            GAUSIUM OPS
# =============================================================================
# PROJECT : Guillaume Bally
# FILE : livemap.py
# DESCRIPTION : Live map tab: robot position + travelled path on the real map.
"""
========= ============== ======================================================
Version   Date           Comment
========= ============== ======================================================
0.1.0     2026/06/22     Creation
========= ============== ======================================================
"""

# [IMPORTS]--------------------------------------------------------------------
import math
from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen
from PyQt6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
from ..config import COLORS
from ..widgets import accent_button

# [MODULE INFO]----------------------------------------------------------------
__author__ = 'Guillaume'
__date__ = '2026/06/22'
__version__ = '0.1.0'
__maintainer__ = 'Guillaume'
__email__ = 'guillaumepointbally@gmail.com'

# [Functions]------------------------------------------------------------------
class MapCanvas(QWidget):
    """Draws the map image with the robot's live position + nav points overlaid.

    Grid coordinates from the status payload (`mapPosition`, `navPointGridX/Y`)
    index the occupancy grid the map PNG is rendered from (1 cell ≈ 1 pixel),
    origin bottom-left — so pixel_y = imageHeight − grid_y (toggle with flip_y)."""
    def __init__(self):
        super().__init__()
        self._pixmap = None
        self._pos = None        # (gx, gy, angle)
        self._navpoints = []    # [(name, gx, gy), …]
        self._trail = []        # [(gx, gy), …] travelled path
        self.flip_y = True
        self.show_trail = True
        self.setMinimumHeight(380)
        self.setStyleSheet(f"background: {COLORS['bg2']}; border-radius: 8px;")

    def set_map(self, pixmap):
        self._pixmap = pixmap
        self.update()

    def set_position(self, gx, gy, angle):
        self._pos = (gx, gy, angle)
        # Append to the trail when the robot actually moved (skip idle repeats).
        if gx is not None and gy is not None and (not self._trail or self._trail[-1] != (gx, gy)):
            self._trail.append((gx, gy))
            if len(self._trail) > 10000:        # cap unbounded growth
                self._trail = self._trail[-10000:]
        self.update()

    def clear_trail(self):
        self._trail = []
        self.update()

    def set_navpoints(self, points):
        self._navpoints = points
        self.update()

    def _to_screen(self, gx, gy, geom):
        ox, oy, sx, sy, ph = geom
        py = (ph - gy) if self.flip_y else gy
        return QPointF(ox + gx * sx, oy + py * sy)

    def paintEvent(self, _evt):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self._pixmap:
            p.setPen(QColor(COLORS["ink3"]))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "Press Start to load the map and track the robot…")
            p.end()
            return

        pm = self._pixmap
        scaled = pm.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
        ox = (self.width() - scaled.width()) / 2
        oy = (self.height() - scaled.height()) / 2
        p.drawPixmap(int(ox), int(oy), scaled)
        geom = (ox, oy, scaled.width() / pm.width(), scaled.height() / pm.height(), pm.height())

        # Travelled path (drawn under the markers so the robot stays on top).
        if self.show_trail and len(self._trail) >= 2:
            tcol = QColor(COLORS["accent"]); tcol.setAlpha(200)
            p.setPen(QPen(tcol, 2))
            pts = [self._to_screen(gx, gy, geom) for gx, gy in self._trail]
            for a, b in zip(pts, pts[1:]):
                p.drawLine(a, b)

        # Reference nav points (dock highlighted).
        for name, gx, gy in self._navpoints:
            pt = self._to_screen(gx, gy, geom)
            col = QColor(COLORS["teal"]) if "charg" in name.lower() else QColor(COLORS["ink3"])
            p.setPen(QPen(col, 1)); p.setBrush(QBrush(col))
            p.drawEllipse(pt, 3, 3)
            p.setPen(QColor(COLORS["ink2"]))
            p.drawText(QPointF(pt.x() + 5, pt.y() - 4), name)

        # Robot position + heading.
        if self._pos and self._pos[0] is not None:
            gx, gy, angle = self._pos
            pt = self._to_screen(gx, gy, geom)
            rad = math.radians(angle or 0)
            dx = math.cos(rad) * 22
            dy = (-math.sin(rad) if self.flip_y else math.sin(rad)) * 22
            p.setPen(QPen(QColor(COLORS["danger"]), 3))
            p.drawLine(pt, QPointF(pt.x() + dx, pt.y() + dy))
            p.setPen(QPen(QColor("white"), 2)); p.setBrush(QBrush(QColor(COLORS["danger"])))
            p.drawEllipse(pt, 7, 7)
        p.end()

class LiveMapPane(QWidget):
    """Live map tab: tracks the robot's position on the real map while monitoring.
    Independent of the Launch task flow — works for any connected robot."""
    monitor_toggled = pyqtSignal(bool)   # True = start, False = stop

    INTERVALS = [("2 s", 2000), ("5 s", 5000), ("10 s", 10000)]

    def __init__(self):
        super().__init__()
        self._monitoring = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        hdr = QHBoxLayout()
        title = QLabel("Live Map")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {COLORS['ink']};")
        hdr.addWidget(title)
        hdr.addStretch()
        self.interval = QComboBox()
        self.interval.addItems([lbl for lbl, _ in self.INTERVALS])
        self.interval.setCurrentIndex(1)
        self.interval.setFixedWidth(70)
        self.flip_chk = QCheckBox("Flip Y")
        self.flip_chk.setChecked(True)
        self.flip_chk.setStyleSheet(f"color: {COLORS['ink2']}; font-size: 12px;")
        self.trail_chk = QCheckBox("Trail")
        self.trail_chk.setChecked(True)
        self.trail_chk.setStyleSheet(f"color: {COLORS['ink2']}; font-size: 12px;")
        self.clear_btn = QPushButton("Clear trail")
        self.toggle_btn = accent_button("▶  Start monitoring")
        self.toggle_btn.clicked.connect(self._toggle)
        hdr.addWidget(QLabel("Every"))
        hdr.addWidget(self.interval)
        hdr.addWidget(self.flip_chk)
        hdr.addWidget(self.trail_chk)
        hdr.addWidget(self.clear_btn)
        hdr.addWidget(self.toggle_btn)
        layout.addLayout(hdr)

        self._info = QLabel("Idle — press Start to load the map and track the robot.")
        self._info.setStyleSheet(f"color: {COLORS['ink2']}; font-size: 12px;")
        layout.addWidget(self._info)

        self.canvas = MapCanvas()
        self.flip_chk.toggled.connect(self._on_flip)
        self.trail_chk.toggled.connect(self._on_trail)
        self.clear_btn.clicked.connect(self.canvas.clear_trail)
        layout.addWidget(self.canvas, 1)

    def _on_flip(self, on):
        self.canvas.flip_y = on
        self.canvas.update()

    def _on_trail(self, on):
        self.canvas.show_trail = on
        self.canvas.update()

    def interval_ms(self):
        return self.INTERVALS[self.interval.currentIndex()][1]

    def _toggle(self):
        self._monitoring = not self._monitoring
        self.toggle_btn.setText("⏹  Stop monitoring" if self._monitoring else "▶  Start monitoring")
        self.monitor_toggled.emit(self._monitoring)

    def stop(self):
        if self._monitoring:
            self._monitoring = False
            self.toggle_btn.setText("▶  Start monitoring")

    def set_info(self, text):
        self._info.setText(text)

    def set_map_image(self, pixmap):
        self.canvas.set_map(pixmap)

    def update_robot(self, gx, gy, angle, navpoints):
        self.canvas.set_navpoints(navpoints)
        self.canvas.set_position(gx, gy, angle)
