"""
mjpeg_server.py — Lightweight MJPEG streaming server.

Streams camera frames as MJPEG over HTTP.  Bypasses OpenCV highgui
(Qt5/X11/VNC) rendering issues — viewable in any browser.

Usage:
  from mjpeg_server import MjpegServer
  server = MjpegServer(camera, port=8080)
  server.start()   # non-blocking background thread
  ...
  server.stop()
"""

import logging
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class _StreamHandler(BaseHTTPRequestHandler):
    """Serve MJPEG stream and a simple status page."""

    camera_ref: "MjpegServer | None" = None  # set by MjpegServer

    def log_message(self, fmt, *args):
        logger.debug("HTTP: %s", fmt % args)

    def do_GET(self):
        if self.path == "/stream":
            self._serve_stream()
        elif self.path == "/snapshot":
            self._serve_snapshot()
        else:
            self._serve_index()

    def _serve_stream(self):
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Pragma", "no-cache")
        self.end_headers()

        server = self.camera_ref
        try:
            while server and server._running:
                frame = server.get_frame()
                if frame is None:
                    time.sleep(0.1)
                    continue

                _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                self.wfile.write(b"--frame\r\n")
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(jpeg)))
                self.end_headers()
                self.wfile.write(jpeg)
                self.wfile.write(b"\r\n")
                time.sleep(server._interval)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _serve_snapshot(self):
        server = self.camera_ref
        frame = server.get_frame() if server else None
        if frame is None:
            self.send_error(503, "No camera frame available")
            return

        _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(jpeg)))
        self.end_headers()
        self.wfile.write(jpeg)

    def _serve_index(self):
        html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Manual Drive — Camera</title>
<style>
  body { margin:0; background:#111; display:flex; flex-direction:column; align-items:center; }
  h1 { color:#ddd; font-family:sans-serif; margin:10px 0; }
  img { max-width:100%; border:2px solid #333; }
  .controls { margin:10px; }
  a { color:#4af; text-decoration:none; margin:0 10px; }
</style>
</head>
<body>
<h1>Manual Drive — Camera Stream</h1>
<img id="stream" src="/stream" alt="MJPEG stream">
<div class="controls">
  <a href="/stream">Stream</a>
  <a href="/snapshot">Snapshot</a>
</div>
</body>
</html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())


class MjpegServer:
    """Non-blocking MJPEG HTTP server."""

    def __init__(self, camera, port: int = 8080, fps: float = 15.0):
        self._camera = camera
        self._port = port
        self._interval = 1.0 / max(1.0, fps)
        self._running = False
        self._httpd: HTTPServer | None = None
        self._thread: threading.Thread | None = None

        # Latest frame cache (thread-safe via lock)
        self._frame: np.ndarray | None = None
        self._lock = threading.Lock()

    def update_frame(self, frame: np.ndarray):
        """Push latest frame (called from main loop)."""
        with self._lock:
            self._frame = frame.copy() if frame is not None else None

    def get_frame(self) -> np.ndarray | None:
        """Get latest frame (called from HTTP handler)."""
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    def start(self):
        """Start server in background thread."""
        if self._running:
            return
        self._running = True
        _StreamHandler.camera_ref = self
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        logger.info("MJPEG server started on http://0.0.0.0:%d/", self._port)

    def _serve(self):
        try:
            self._httpd = HTTPServer(("0.0.0.0", self._port), _StreamHandler)
            self._httpd.serve_forever()
        except OSError as e:
            logger.error("MJPEG server failed to bind port %d: %s", self._port, e)
        except Exception:
            logger.exception("MJPEG server error")
        finally:
            self._running = False

    def stop(self):
        """Shut down server."""
        self._running = False
        if self._httpd:
            try:
                self._httpd.shutdown()
            except Exception:
                pass
            self._httpd = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("MJPEG server stopped")
