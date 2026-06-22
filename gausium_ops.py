#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# =============================================================================
#            GAUSIUM OPS
# =============================================================================
# PROJECT : Guillaume Bally
# FILE : gausium_ops.py
# DESCRIPTION : Gausium Ops — launcher.
#   The application now lives in the `gsops/` package; this thin entry point keeps
#   `bash launch.sh` (which runs `gausium_ops.py`) working. See gsops/app.py for the
#   main window and gsops/panes/ for the individual tabs.
"""
========= ============== ======================================================
Version   Date           Comment
========= ============== ======================================================
0.1.0     2026/06/22     Creation
========= ============== ======================================================
"""

# [IMPORTS]--------------------------------------------------------------------
from gsops.app import main

# [MODULE INFO]----------------------------------------------------------------
__author__ = 'Guillaume'
__date__ = '2026/06/22'
__version__ = '0.1.0'
__maintainer__ = 'Guillaume'
__email__ = 'guillaumepointbally@gmail.com'

# [Functions]------------------------------------------------------------------
if __name__ == "__main__":
    main()
