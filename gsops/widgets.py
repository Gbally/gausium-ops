#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# =============================================================================
#            GAUSIUM OPS
# =============================================================================
# PROJECT : Guillaume Bally
# FILE : widgets.py
# DESCRIPTION : Reusable styled widgets: cards, buttons, metric cards, charts, nav button, log panel.
"""
========= ============== ======================================================
Version   Date           Comment
========= ============== ======================================================
0.1.0     2026/06/22     Creation
========= ============== ======================================================
"""

# [IMPORTS]--------------------------------------------------------------------
import html
from datetime import datetime
from PyQt6.QtCore import QMargins, Qt
from PyQt6.QtGui import QBrush, QColor, QCursor, QFont, QPainter
from PyQt6.QtWidgets import QFrame, QLabel, QPushButton, QTextEdit, QVBoxLayout
from PyQt6.QtCharts import QBarCategoryAxis, QBarSeries, QBarSet, QChart, QChartView, QValueAxis
from .config import COLORS, MONO_FONT

# [MODULE INFO]----------------------------------------------------------------
__author__ = 'Guillaume'
__date__ = '2026/06/22'
__version__ = '0.1.0'
__maintainer__ = 'Guillaume'
__email__ = 'guillaumepointbally@gmail.com'

# [Functions]------------------------------------------------------------------
def card(parent=None):
    w = QFrame(parent)
    w.setStyleSheet(f"""
        QFrame {{
            background-color: {COLORS['bg3']};
            border: 1px solid {COLORS['border']};
            border-radius: 10px;
        }}
    """)
    return w

def section_label(text):
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(f"color: {COLORS['ink3']}; font-size: 10px; font-weight: 600; letter-spacing: 1px;")
    return lbl

def accent_button(text, icon=""):
    btn = QPushButton(f"{icon}  {text}".strip() if icon else text)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {COLORS['accent2']};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 18px;
            font-weight: 600;
            font-size: 13px;
        }}
        QPushButton:hover {{ background-color: {COLORS['accent']}; }}
        QPushButton:pressed {{ background-color: #4a3db0; }}
        QPushButton:disabled {{ background-color: {COLORS['bg4']}; color: {COLORS['ink3']}; }}
    """)
    return btn

def danger_button(text):
    btn = QPushButton(text)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: rgba(232,82,74,0.15);
            color: {COLORS['danger']};
            border: 1px solid rgba(232,82,74,0.35);
            border-radius: 6px;
            padding: 7px 16px;
        }}
        QPushButton:hover {{ background-color: rgba(232,82,74,0.28); }}
    """)
    return btn

def metric_card(label, value="—", unit="", color=None):
    frame = card()
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(4)
    lbl = QLabel(label.upper())
    lbl.setStyleSheet(f"font-size: 10px; color: {COLORS['ink3']}; letter-spacing: 1px; font-weight: 600;")
    val_lbl = QLabel(value)
    val_lbl.setStyleSheet(f"font-size: 26px; font-weight: 600; color: {color or COLORS['ink']};")
    unit_lbl = QLabel(unit)
    unit_lbl.setStyleSheet(f"font-size: 11px; color: {COLORS['ink2']};")
    layout.addWidget(lbl)
    layout.addWidget(val_lbl)
    if unit:
        layout.addWidget(unit_lbl)
    return frame, val_lbl

def build_chart(title, bar_color, x_labels=None, values=None):
    series = QBarSeries()
    bar_set = QBarSet("")
    bar_set.setColor(QColor(bar_color))
    bar_set.setBorderColor(QColor(bar_color))
    if values:
        for v in values:
            bar_set.append(v)
    series.append(bar_set)
    series.setBarWidth(0.6)

    chart = QChart()
    chart.addSeries(series)
    chart.setTitle("")
    chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
    chart.legend().setVisible(False)
    chart.setBackgroundBrush(QBrush(QColor(COLORS["bg3"])))
    chart.setBackgroundRoundness(0)
    chart.setMargins(QMargins(0, 0, 0, 0))
    chart.layout().setContentsMargins(0, 0, 0, 0)

    ax = QBarCategoryAxis()
    ax.append(x_labels or [])
    ax.setLabelsColor(QColor(COLORS["ink2"]))
    ax.setGridLineColor(QColor(COLORS["border"]))
    ax.setLinePenColor(QColor(COLORS["border"]))
    fnt = QFont()
    fnt.setPointSize(9)
    ax.setLabelsFont(fnt)

    ay = QValueAxis()
    ay.setLabelsColor(QColor(COLORS["ink2"]))
    ay.setGridLineColor(QColor(COLORS["border"]))
    ay.setLinePenColor(QColor(COLORS["border"]))
    ay.setLabelsFont(fnt)
    if values:
        ay.setRange(0, max(values) * 1.2 if max(values) > 0 else 10)

    chart.addAxis(ax, Qt.AlignmentFlag.AlignBottom)
    chart.addAxis(ay, Qt.AlignmentFlag.AlignLeft)
    series.attachAxis(ax)
    series.attachAxis(ay)

    view = QChartView(chart)
    view.setRenderHint(QPainter.RenderHint.Antialiasing)
    view.setStyleSheet(f"background: {COLORS['bg3']}; border: none;")
    view.setMinimumHeight(200)
    return view, chart, bar_set

class NavButton(QPushButton):
    def __init__(self, icon_char, label, parent=None):
        super().__init__(parent)
        self._icon = icon_char
        self._label = label
        self.setText(f" {label}")
        self.setCheckable(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._update_style(False)

    def _update_style(self, active):
        if active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(124,106,247,0.16);
                    color: {COLORS['accent']};
                    border: none;
                    border-radius: 7px;
                    padding: 9px 12px;
                    font-size: 13px;
                    font-weight: 600;
                    text-align: left;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {COLORS['ink2']};
                    border: none;
                    border-radius: 7px;
                    padding: 9px 12px;
                    font-size: 13px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background: {COLORS['bg3']};
                    color: {COLORS['ink']};
                }}
            """)

    def setActive(self, active):
        self.setChecked(active)
        self._update_style(active)

class LogPanel(QTextEdit):
    """Read-only, timestamped, colour-coded activity log (the Activity log tab)."""
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setStyleSheet(f"""
            QTextEdit {{
                background: {COLORS['bg2']};
                color: {COLORS['ink2']};
                border: none;
                border-radius: 0;
                font-family: {MONO_FONT};
                font-size: 11px;
                padding: 8px;
            }}
        """)

    def append_log(self, msg, kind="info"):
        colors = {"ok": COLORS["teal"], "err": COLORS["danger"], "warn": COLORS["warn"], "info": COLORS["ink2"]}
        col = colors.get(kind, COLORS["ink2"])
        ts = datetime.now().strftime("%H:%M:%S")
        safe = html.escape(str(msg))
        self.append(f'<span style="color:{COLORS["ink3"]}">{ts}</span> <span style="color:{col}">{safe}</span>')
        sb = self.verticalScrollBar()
        sb.setValue(sb.maximum())
