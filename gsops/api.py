#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# =============================================================================
#            GAUSIUM OPS
# =============================================================================
# PROJECT : Guillaume Bally
# FILE : api.py
# DESCRIPTION : Background HTTP workers (Qt threads) for the Gausium API and map-image downloads.
"""
========= ============== ======================================================
Version   Date           Comment
========= ============== ======================================================
0.1.0     2026/06/22     Creation
========= ============== ======================================================
"""

# [IMPORTS]--------------------------------------------------------------------
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from .config import SSL_CONTEXT

# [MODULE INFO]----------------------------------------------------------------
__author__ = 'Guillaume'
__date__ = '2026/06/22'
__version__ = '0.1.0'
__maintainer__ = 'Guillaume'
__email__ = 'guillaumepointbally@gmail.com'

# [Functions]------------------------------------------------------------------
class ApiWorker(QObject):
    """Performs one HTTP request and emits the result.

    `tag` identifies which request this is so MainWindow can route the response.
    `content_type` is None for endpoints that reject a Content-Type header.
    """
    finished = pyqtSignal(bool, int, dict, str)  # ok, status, data, tag

    def __init__(self, url, token, method="GET", body=None, tag="", content_type="application/json"):
        super().__init__()
        self.url = url
        self.token = token
        self.method = method
        self.body = body
        self.tag = tag
        self.content_type = content_type

    def run(self):
        try:
            data = json.dumps(self.body).encode() if self.body else None
            # The Gausium API is inconsistent about Content-Type: POSTs and the
            # /openapi/v2alpha1 GETs require 'application/json', but the
            # /v1alpha1/robots list rejects any Content-Type (HTTP 415). So callers
            # set content_type explicitly (None to omit it).
            headers = {}
            if self.content_type:
                headers["Content-Type"] = self.content_type
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            req = Request(
                self.url,
                data=data,
                method=self.method,
                headers=headers,
            )
            with urlopen(req, timeout=15, context=SSL_CONTEXT) as resp:
                raw = resp.read().decode()
                try:
                    result = json.loads(raw)
                except Exception:
                    result = {"raw": raw}
                self.finished.emit(True, resp.status, result, self.tag)
        except HTTPError as e:
            body = ""
            try:
                body = e.read().decode(errors="replace")
            except Exception:
                pass
            try:
                result = json.loads(body)
            except Exception:
                # Keep the raw body so non-JSON error responses stay diagnosable.
                result = {"error": str(e), "body": body.strip()}
            self.finished.emit(False, e.code, result, self.tag)
        except Exception as e:
            self.finished.emit(False, 0, {"error": str(e)}, self.tag)

class ApiThread(QThread):
    """Runs an ApiWorker on a background thread so the UI never blocks on I/O."""
    finished = pyqtSignal(bool, int, dict, str)

    def __init__(self, url, token, method="GET", body=None, tag="", content_type="application/json"):
        super().__init__()
        self._url = url
        self._token = token
        self._method = method
        self._body = body
        self._tag = tag
        self._content_type = content_type

    def run(self):
        worker = ApiWorker(self._url, self._token, self._method, self._body, self._tag, self._content_type)
        worker.finished.connect(self.finished)
        worker.run()

class DownloadThread(QThread):
    """Downloads raw bytes from a URL (e.g. the presigned S3 map image) off the
    UI thread. No auth header — the S3 link is already presigned."""
    finished = pyqtSignal(bool, bytes)

    def __init__(self, url):
        super().__init__()
        self._url = url

    def run(self):
        try:
            with urlopen(Request(self._url, method="GET"), timeout=20, context=SSL_CONTEXT) as resp:
                self.finished.emit(True, resp.read())
        except Exception:
            self.finished.emit(False, b"")
