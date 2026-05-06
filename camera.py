"""
camera.py — Camera manager (PiCamera2 CSI / USB).

Adapted from raspberry_pi5_freenove_car for manual drive use.
"""

import logging
import time

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class Camera:
    """Unified camera interface for CSI or USB."""

    def __init__(self, config):
        self.config = config
        self.cap = None
        self.picam2 = None
        self.use_picamera2 = config.CAMERA_USE_PICAMERA2
        self.width = config.CAMERA_WIDTH
        self.height = config.CAMERA_HEIGHT
        self.fps = config.CAMERA_FPS
        self.flip_h = config.CAMERA_FLIP_HORIZONTAL
        self.flip_v = config.CAMERA_FLIP_VERTICAL
        self.exposure_value = getattr(config, 'CAMERA_EXPOSURE_VALUE', 2.0)
        self.brightness_boost = getattr(config, 'CAMERA_BRIGHTNESS_BOOST', 1.8)

    def start(self) -> bool:
        if self.use_picamera2:
            return self._start_picamera2()
        return self._start_usb()

    def _start_picamera2(self) -> bool:
        try:
            from picamera2 import Picamera2

            self.picam2 = Picamera2()
            video_config = self.picam2.create_video_configuration(
                main={"size": (self.width, self.height), "format": "RGB888"},
                controls={
                    "FrameRate": self.fps,
                    "ExposureValue": self.exposure_value,
                },
            )
            self.picam2.configure(video_config)
            self.picam2.start()
            time.sleep(1.0)
            logger.info("PiCamera2 started: %dx%d @ %d FPS",
                        self.width, self.height, self.fps)
            return True
        except ImportError:
            logger.warning("picamera2 not installed, falling back to USB")
            self.use_picamera2 = False
            return self._start_usb()
        except Exception as e:
            logger.error("PiCamera2 init failed: %s", e)
            return False

    def _start_usb(self) -> bool:
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            logger.error("Cannot open USB camera")
            return False
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        logger.info("USB camera started")
        return True

    def capture(self) -> np.ndarray | None:
        frame = None
        if self.use_picamera2 and self.picam2 is not None:
            frame = self._capture_picamera2()
        elif self.cap is not None:
            frame = self._capture_usb()
        if frame is not None and self.brightness_boost != 1.0:
            frame = cv2.convertScaleAbs(frame, alpha=self.brightness_boost, beta=0)
        return frame

    def _capture_picamera2(self) -> np.ndarray | None:
        try:
            frame = self.picam2.capture_array()
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            return self._apply_flips(frame)
        except Exception as e:
            logger.error("PiCamera2 capture failed: %s", e)
            return None

    def _capture_usb(self) -> np.ndarray | None:
        ret, frame = self.cap.read()
        if not ret:
            return None
        return self._apply_flips(frame)

    def _apply_flips(self, frame: np.ndarray) -> np.ndarray:
        if self.flip_h:
            frame = cv2.flip(frame, 1)
        if self.flip_v:
            frame = cv2.flip(frame, 0)
        return frame

    def release(self):
        if self.picam2 is not None:
            try:
                self.picam2.stop()
                self.picam2.close()
            except Exception:
                pass
            self.picam2 = None
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        logger.info("Camera released")
