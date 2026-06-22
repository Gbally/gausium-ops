#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# =============================================================================
#            GAUSIUM OPS
# =============================================================================
# PROJECT : Guillaume Bally
# FILE : reports.py
# DESCRIPTION : Reports tab: task-report KPIs, charts, and history list.
"""
========= ============== ======================================================
Version   Date           Comment
========= ============== ======================================================
0.1.0     2026/06/22     Creation
========= ============== ======================================================
"""

# [IMPORTS]--------------------------------------------------------------------
from functools import partial
from PyQt6.QtCore import QDateTime, QUrl, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QCursor, QDesktopServices, QFont
from PyQt6.QtWidgets import QDateTimeEdit, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget
from PyQt6.QtCharts import QBarCategoryAxis, QBarSeries, QBarSet, QValueAxis
from ..config import COLORS
from ..widgets import accent_button, build_chart, card, metric_card, section_label

# [MODULE INFO]----------------------------------------------------------------
__author__ = 'Guillaume'
__date__ = '2026/06/22'
__version__ = '0.1.0'
__maintainer__ = 'Guillaume'
__email__ = 'guillaumepointbally@gmail.com'

# [Functions]------------------------------------------------------------------
class ReportsPane(QWidget):
    """Reports tab: a date range loads task reports into KPI cards, two bar
    charts (area cleaned / battery used), and a per-task list."""
    load_requested = pyqtSignal(str, str)  # from_iso, to_iso

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Header + date filters
        hdr = QHBoxLayout()
        title = QLabel("Reports")
        title.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {COLORS['ink']};")
        hdr.addWidget(title)
        hdr.addStretch()

        now = QDateTime.currentDateTime()
        week_ago = now.addDays(-7)
        self.dt_from = QDateTimeEdit(week_ago)
        self.dt_from.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.dt_from.setCalendarPopup(True)
        self.dt_to = QDateTimeEdit(now)
        self.dt_to.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.dt_to.setCalendarPopup(True)
        self.load_btn = accent_button("↻  Load reports")
        self.load_btn.clicked.connect(self._emit_load)

        for w in [QLabel("From:"), self.dt_from, QLabel("To:"), self.dt_to, self.load_btn]:
            hdr.addWidget(w)
        layout.addLayout(hdr)

        # KPI metrics
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(10)
        self._k_tasks, self._v_tasks = metric_card("Tasks")
        self._k_comp, self._v_comp = metric_card("Avg completion", color=COLORS["teal"])
        self._k_area, self._v_area = metric_card("Total area (m²)", color=COLORS["info"])
        self._k_eff, self._v_eff = metric_card("Avg efficiency")
        for i, c in enumerate([self._k_tasks, self._k_comp, self._k_area, self._k_eff]):
            kpi_grid.addWidget(c, 0, i)
        layout.addLayout(kpi_grid)

        # Charts
        chart_row = QHBoxLayout()
        chart_row.setSpacing(10)

        area_card = card()
        area_l = QVBoxLayout(area_card)
        area_l.setContentsMargins(12, 10, 12, 10)
        area_l.addWidget(section_label("Area cleaned per task (m²)"))
        self._area_color = COLORS["teal"]
        self._area_view, self._area_chart, self._area_set = build_chart("Area", self._area_color)
        area_l.addWidget(self._area_view)
        chart_row.addWidget(area_card)

        bat_card = card()
        bat_l = QVBoxLayout(bat_card)
        bat_l.setContentsMargins(12, 10, 12, 10)
        bat_l.addWidget(section_label("Battery used per task (%)"))
        self._bat_color = COLORS["warn"]
        self._bat_view, self._bat_chart, self._bat_set = build_chart("Battery", self._bat_color)
        bat_l.addWidget(self._bat_view)
        chart_row.addWidget(bat_card)

        layout.addLayout(chart_row)

        # Task list
        list_card = card()
        list_l = QVBoxLayout(list_card)
        list_l.setContentsMargins(14, 12, 14, 12)
        list_l.addWidget(section_label("Task history"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setSpacing(0)
        self._list_layout.addStretch()
        scroll.setWidget(self._list_widget)
        scroll.setMinimumHeight(180)
        list_l.addWidget(scroll)
        layout.addWidget(list_card)

    def _emit_load(self):
        f = self.dt_from.dateTime().toUTC().toString("yyyy-MM-ddTHH:mm:ssZ")
        t = self.dt_to.dateTime().toUTC().toString("yyyy-MM-ddTHH:mm:ssZ")
        self.load_requested.emit(f, t)

    def _update_chart(self, view, chart, color, labels, values):
        # removeAllSeries() deletes the previous QBarSet, so the bar colour is
        # tracked separately rather than read back off a (now-deleted) set.
        chart.removeAllSeries()
        col = QColor(color)
        new_set = QBarSet("")
        new_set.setColor(col)
        new_set.setBorderColor(col)
        for v in values:
            new_set.append(v)
        series = QBarSeries()
        series.append(new_set)
        series.setBarWidth(0.6)
        chart.addSeries(series)

        axes = chart.axes()
        for ax in axes:
            chart.removeAxis(ax)

        ax = QBarCategoryAxis()
        ax.append(labels)
        ax.setLabelsColor(QColor(COLORS["ink2"]))
        ax.setGridLineColor(QColor(COLORS["border"]))
        ax.setLinePenColor(QColor(COLORS["border"]))
        f = QFont(); f.setPointSize(9); ax.setLabelsFont(f)

        ay = QValueAxis()
        ay.setLabelsColor(QColor(COLORS["ink2"]))
        ay.setGridLineColor(QColor(COLORS["border"]))
        ay.setLinePenColor(QColor(COLORS["border"]))
        ay.setLabelsFont(f)
        ay.setRange(0, max(values) * 1.25 if values and max(values) > 0 else 10)

        chart.addAxis(ax, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(ay, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(ax)
        series.attachAxis(ay)

    def populate(self, reports):
        # KPIs
        n = len(reports)
        avg_comp = round(sum(r.get("completionPercentage", 0) for r in reports) / n * 100) if n else 0
        total_area = sum(r.get("actualCleaningAreaSquareMeter", 0) for r in reports)
        avg_eff = round(sum(r.get("efficiencySquareMeterPerHour", 0) for r in reports) / n) if n else 0
        self._v_tasks.setText(str(n))
        self._v_comp.setText(f"{avg_comp}%")
        self._v_area.setText(f"{total_area:.1f}")
        self._v_eff.setText(f"{avg_eff} m²/h")

        # Charts
        labels = [r.get("displayName") or f"Task {i+1}" for i, r in enumerate(reports)]
        short_labels = [lb[:10] for lb in labels]
        area_vals = [round(r.get("actualCleaningAreaSquareMeter", 0), 1) for r in reports]
        bat_vals = [max(0, round((r.get("startBatteryPercentage", 0) or 0) - (r.get("endBatteryPercentage", 0) or 0))) for r in reports]
        self._update_chart(self._area_view, self._area_chart, self._area_color, short_labels, area_vals)
        self._update_chart(self._bat_view, self._bat_chart, self._bat_color, short_labels, bat_vals)

        # Task list
        while self._list_layout.count() > 0:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for r in reports:
            row = self._make_task_row(r)
            self._list_layout.addWidget(row)
        self._list_layout.addStretch()

    def _make_task_row(self, r):
        frame = QFrame()
        frame.setStyleSheet(f"QFrame {{ border-bottom: 1px solid {COLORS['border']}; background: transparent; }}")
        hl = QHBoxLayout(frame)
        hl.setContentsMargins(4, 8, 4, 8)
        hl.setSpacing(12)

        # Name + meta
        info = QVBoxLayout()
        info.setSpacing(2)
        name = QLabel(r.get("displayName") or "—")
        name.setStyleSheet(f"font-weight: 600; color: {COLORS['ink']}; font-size: 13px;")
        mode = r.get("cleaningMode") or ""
        areas = r.get("areaNameList") or ""
        meta = QLabel(f"{mode}{'  ·  ' + areas if areas else ''}")
        meta.setStyleSheet(f"color: {COLORS['ink2']}; font-size: 11px;")
        info.addWidget(name)
        info.addWidget(meta)
        hl.addLayout(info, 3)

        # Completion
        comp = round((r.get("completionPercentage") or 0) * 100)
        area_val = r.get("actualCleaningAreaSquareMeter") or 0
        comp_col = QVBoxLayout()
        comp_col.setSpacing(2)
        comp_lbl = QLabel(f"{comp}%")
        comp_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        comp_lbl.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {COLORS['teal'] if comp > 80 else COLORS['warn']};")
        area_lbl = QLabel(f"{area_val:.1f} m²")
        area_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        area_lbl.setStyleSheet(f"font-size: 11px; color: {COLORS['ink2']};")
        comp_col.addWidget(comp_lbl)
        comp_col.addWidget(area_lbl)
        hl.addLayout(comp_col, 1)

        # Duration
        dur_secs = r.get("durationSeconds") or 0
        dur_str = f"{round(dur_secs/60)} min" if dur_secs else "—"
        eff = round(r.get("efficiencySquareMeterPerHour") or 0)
        dur_col = QVBoxLayout()
        dur_col.setSpacing(2)
        dur_lbl = QLabel(dur_str)
        dur_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dur_lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {COLORS['ink']};")
        eff_lbl = QLabel(f"{eff} m²/h")
        eff_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        eff_lbl.setStyleSheet(f"font-size: 11px; color: {COLORS['ink2']};")
        dur_col.addWidget(dur_lbl)
        dur_col.addWidget(eff_lbl)
        hl.addLayout(dur_col, 1)

        # Status badge + map link
        right_col = QVBoxLayout()
        right_col.setSpacing(4)
        right_col.setAlignment(Qt.AlignmentFlag.AlignRight)
        st = r.get("taskEndStatus")
        st_label = "Completed" if st == 1 else "Interrupted" if st == 2 else "Unknown"
        st_color = COLORS["teal"] if st == 1 else COLORS["warn"] if st == 2 else COLORS["ink3"]
        st_bg = "rgba(78,203,169,0.14)" if st == 1 else "rgba(240,160,48,0.14)" if st == 2 else "rgba(90,88,112,0.2)"
        badge = QLabel(st_label)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(f"background: {st_bg}; color: {st_color}; border-radius: 9px; padding: 3px 10px; font-size: 11px; font-weight: 600;")
        right_col.addWidget(badge)
        png_uri = r.get("taskReportPngUri")
        if png_uri:
            map_btn = QPushButton("↗ Map PNG")
            map_btn.setStyleSheet(f"color: {COLORS['info']}; background: transparent; border: none; font-size: 11px; padding: 0;")
            map_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            map_btn.clicked.connect(partial(QDesktopServices.openUrl, QUrl(png_uri)))
            right_col.addWidget(map_btn)
        hl.addLayout(right_col, 1)

        return frame
