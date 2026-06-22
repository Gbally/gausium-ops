#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# =============================================================================
#            GAUSIUM OPS
# =============================================================================
# PROJECT : Guillaume Bally
# FILE : config.py
# DESCRIPTION : Constants, colour palette, stylesheet, credential storage, SSL context, and lookup tables.
"""
========= ============== ======================================================
Version   Date           Comment
========= ============== ======================================================
0.1.0     2026/06/22     Creation
========= ============== ======================================================
"""

# [IMPORTS]--------------------------------------------------------------------
import json
import ssl
import sys
from pathlib import Path

# [MODULE INFO]----------------------------------------------------------------
__author__ = 'Guillaume'
__date__ = '2026/06/22'
__version__ = '0.1.0'
__maintainer__ = 'Guillaume'
__email__ = 'guillaumepointbally@gmail.com'

# [GLOBALS]--------------------------------------------------------------------

# A single, platform-native monospace font. Listing fonts that don't exist on
# the running OS makes Qt warn ("missing font family …"), so we pick one.
if sys.platform == "darwin":
    MONO_FONT = "Menlo"
elif sys.platform.startswith("win"):
    MONO_FONT = "Consolas"
else:
    MONO_FONT = "'DejaVu Sans Mono'"

OAUTH_URL = "https://openapi.gs-robot.com/gas/api/v1alpha1/oauth/token"

GRANT_TYPE = "urn:gaussian:params:oauth:grant-type:open-access-token"

CONFIG_PATH = Path.home() / ".gausium_ops" / "credentials.json"

TASK_ERROR_CODES = {
    "2010100006": "Invalid tag",
    "2010100007": "Task area unreachable",
    "2010100008": "Task area operation type mismatch",
    "2010100009": "Operation data failure (task parameters rejected)",
    "2010100010": "No color camera installed",
    "2010100011": "No inspection equipment neural stick installed",
    "2010100012": "There are temporary tasks",
    "2010100013": "The robot cannot switch sites in the current state",
}

MODE_TRANSLATIONS = {
    "清扫": "Sweep",
    "吸尘": "Vacuum",
    "清洗": "Scrub / wash",
    "尘推": "Dust push",
    "__middle_cleaning": "Generic",
    # Mode identifiers reported by some robot models (note the "__" prefix).
    "__滚刷尘推": "Roller-brush dust mop (dry)",
    "__扫地": "Sweep",
    "__洗地": "Floor wash / scrub (wet)",
}

BASE_URL = "https://openapi.gs-robot.com"

COLORS = {
    "bg":       "#16151a",
    "bg2":      "#1e1d24",
    "bg3":      "#26252e",
    "bg4":      "#302f3a",
    "bg5":      "#3c3b48",
    "ink":      "#e8e6f0",
    "ink2":     "#9896a8",
    "ink3":     "#5a5870",
    "accent":   "#7c6af7",
    "accent2":  "#5b4fd4",
    "teal":     "#4ecba9",
    "teal2":    "#2d9e7e",
    "warn":     "#f0a030",
    "danger":   "#e8524a",
    "info":     "#4a9edd",
    "success":  "#4ecba9",
    "border":   "#2e2d38",
    "border2":  "#3d3c4c",
}

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {COLORS['bg']};
    color: {COLORS['ink']};
    font-family: "Helvetica Neue", Helvetica, Arial;
    font-size: 13px;
}}
QLabel {{ color: {COLORS['ink']}; background: transparent; }}
QLineEdit, QComboBox, QTextEdit, QDateTimeEdit {{
    background-color: {COLORS['bg4']};
    color: {COLORS['ink']};
    border: 1px solid {COLORS['border2']};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
    selection-background-color: {COLORS['accent2']};
}}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QDateTimeEdit:focus {{
    border: 1px solid {COLORS['accent']};
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox::down-arrow {{ width: 10px; }}
QComboBox QAbstractItemView {{
    background-color: {COLORS['bg4']};
    color: {COLORS['ink']};
    selection-background-color: {COLORS['accent2']};
    border: 1px solid {COLORS['border2']};
    border-radius: 4px;
    padding: 4px;
}}
QPushButton {{
    background-color: {COLORS['bg4']};
    color: {COLORS['ink']};
    border: 1px solid {COLORS['border2']};
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 13px;
    font-weight: 500;
}}
QPushButton:hover {{ background-color: {COLORS['bg5']}; border-color: {COLORS['accent']}; }}
QPushButton:pressed {{ background-color: {COLORS['bg3']}; }}
QPushButton:disabled {{ opacity: 0.4; }}
QScrollBar:vertical {{
    background: {COLORS['bg2']};
    width: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {COLORS['bg5']};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {COLORS['bg2']};
    height: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background: {COLORS['bg5']};
    border-radius: 3px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QProgressBar {{
    background-color: {COLORS['bg4']};
    border: none;
    border-radius: 3px;
    height: 6px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {COLORS['teal']};
    border-radius: 3px;
}}
QTabWidget::pane {{ border: none; background: transparent; }}
QTabBar::tab {{
    background: {COLORS['bg3']};
    color: {COLORS['ink2']};
    padding: 8px 18px;
    border: none;
    font-size: 12px;
}}
QTabBar::tab:selected {{
    background: {COLORS['bg4']};
    color: {COLORS['ink']};
    font-weight: 500;
    border-bottom: 2px solid {COLORS['accent']};
}}
QTabBar::tab:hover:!selected {{ background: {COLORS['bg4']}; color: {COLORS['ink']}; }}
QStatusBar {{
    background-color: {COLORS['bg2']};
    color: {COLORS['ink2']};
    border-top: 1px solid {COLORS['border']};
    font-size: 11px;
}}
QGroupBox {{
    color: {COLORS['ink2']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
    color: {COLORS['ink3']};
}}
QSplitter::handle {{ background: {COLORS['border']}; width: 1px; }}
"""


# [Functions]------------------------------------------------------------------

def _build_ssl_context():
    """Verified SSL context that tolerates non-critical Basic Constraints.

    Python 3.13 turns on VERIFY_X509_STRICT by default, which rejects CA certs
    (often from corporate TLS proxies) whose Basic Constraints extension isn't
    marked critical. We keep certificate + hostname verification on but clear
    that one over-strict flag, and prefer certifi's CA bundle when installed.
    """
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ctx = ssl.create_default_context()
    ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return ctx

SSL_CONTEXT = _build_ssl_context()

def mode_label(name):
    """Build a 'original — English' label for a cleaning-mode value."""
    t = MODE_TRANSLATIONS.get(name)
    return f"{name} — {t}" if t else name

def load_credentials():
    try:
        if CONFIG_PATH.exists():
            return json.loads(CONFIG_PATH.read_text())
    except Exception:
        pass
    return {}

def save_credentials(data):
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(data, indent=2))
    except Exception:
        pass
