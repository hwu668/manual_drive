"""
main.py — Manual Drive entry point for Freenove FNK0043B.

Keyboard-controlled 4WD driving with simultaneous 2D occupancy grid mapping.
Displays camera feed and top-down map in separate OpenCV windows.

Usage:
  python main.py                     # normal mode
  python main.py --no-display        # headless (SSH, logging only)
  python main.py --log-level DEBUG   # verbose logging
"""

import argparse
import logging
import signal
import sys
import time

import cv2
import numpy as np

import config
from camera import Camera
from mapping import Mapping
from motor_control import MotorControl
from sensors import Sensors

logger = logging.getLogger("manual_drive")


class ManualDrive:
    """Keyboard-controlled manual drive with real-time mapping."""

    def __init__(self, no_display: bool = False):
        self.no_display = no_display

        logger.info("=" * 55)
        logger.info("%s — %s", config.PRODUCT_NAME, config.PRODUCT_DESC)
        logger.info("=" * 55)

        self.camera = Camera(config)
        self.motor = MotorControl(config)
        self.sensors = Sensors(config)
        self.mapping = Mapping(config)

        self._running = False
        self._command = "stop"
        self._idle_frames = 0

        # FPS tracking
        self._fps_counter = 0
        self._fps_timer = time.time()
        self._fps_current = 0.0

    # ========================================================================
    # Lifecycle
    # ========================================================================

    def start(self):
        """Initialize all modules and enter main loop."""
        if not self.camera.start():
            logger.error("Camera init failed, exiting")
            sys.exit(1)

        if not self.motor.setup():
            logger.error("Motor init failed, exiting")
            sys.exit(1)

        if not self.sensors.setup():
            logger.error("Sensor init failed, exiting")
            sys.exit(1)

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self._running = True
        logger.info("Manual drive running. [W]fwd [S]back [A]left [D]right [Q]uit")

        try:
            self._main_loop()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        except Exception:
            logger.exception("Unhandled exception in main loop")
        finally:
            self.shutdown()

    def shutdown(self):
        """Release all resources."""
        logger.info("Shutting down...")
        self._running = False

        try:
            self.motor.stop()
        except Exception:
            pass

        try:
            self.camera.release()
        except Exception:
            pass

        try:
            self.sensors.cleanup()
        except Exception:
            pass

        try:
            self.motor.cleanup()
        except Exception:
            pass

        cv2.destroyAllWindows()
        logger.info("Manual Drive stopped.")

    # ========================================================================
    # Main loop
    # ========================================================================

    def _main_loop(self):
        prev_time = time.time()

        while self._running:
            loop_start = time.time()
            dt = loop_start - prev_time
            prev_time = loop_start

            # Clamp dt to avoid huge jumps (e.g. after debugger pause)
            if dt <= 0 or dt > 0.5:
                dt = 0.05

            # 1. Capture camera frame
            frame = self.camera.capture()

            # 2. Read sensors
            distance_cm = self.sensors.get_distance_cm()
            ir_data = self.sensors.ir_all()

            # 3. Update mapping
            self.mapping.update_pose(self._command, dt)
            self.mapping.update_map(distance_cm, ir_data)

            # 4. Display
            if not self.no_display:
                # Camera window
                if frame is not None:
                    display_frame = self._draw_camera_hud(frame, distance_cm, ir_data)
                    cv2.imshow(config.WINDOW_CAMERA, display_frame)
                else:
                    # Show a placeholder if camera is down
                    placeholder = 128 * np.ones((480, 640, 3), dtype=np.uint8)
                    cv2.putText(placeholder, "NO CAMERA", (200, 240),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    cv2.imshow(config.WINDOW_CAMERA, placeholder)

                # Map window
                map_img = self.mapping.render()
                cv2.imshow(config.WINDOW_MAP, map_img)

                # Keyboard input
                key = cv2.waitKey(1) & 0xFF
                self._handle_key(key)
            else:
                # Headless mode: just log periodically
                if self._fps_counter % 100 == 0:
                    logger.debug("Headless tick %d | cmd=%s dist=%.1f cm",
                                 self._fps_counter, self._command, distance_cm)

            # 5. Auto-stop: if no movement key for N frames, stop
            if self._command != "stop":
                self._idle_frames += 1
                if self._idle_frames >= config.AUTO_STOP_FRAMES:
                    self._command = "stop"
                    self.motor.stop()
                    self._idle_frames = 0

            # 6. FPS counter
            self._fps_counter += 1
            elapsed = time.time() - self._fps_timer
            if elapsed >= 1.0:
                self._fps_current = self._fps_counter / elapsed
                self._fps_counter = 0
                self._fps_timer = time.time()

            # 7. Rate limiting
            loop_time = time.time() - loop_start
            sleep_time = config.MAIN_LOOP_DELAY - loop_time
            if sleep_time > 0:
                time.sleep(sleep_time)

    # ========================================================================
    # Keyboard handling
    # ========================================================================

    def _handle_key(self, key: int):
        """Process keyboard input and issue motor commands."""
        if key == ord('q'):
            logger.info("User pressed 'q', quitting")
            self._running = False
            return

        # Movement keys
        command = None
        if key == ord('w'):
            command = "forward"
            self.motor.forward()
        elif key == ord('s'):
            command = "backward"
            self.motor.backward()
        elif key == ord('a'):
            command = "left"
            self.motor.turn_left()
        elif key == ord('d'):
            command = "right"
            self.motor.turn_right()
        elif key == ord(' '):
            # Space bar: immediate stop
            command = "stop"
            self.motor.stop()

        # Additional keys
        if key == ord('r'):
            # Reset map
            self.mapping = Mapping(config)
            logger.info("Map reset")

        if command is not None:
            self._command = command
            self._idle_frames = 0

    # ========================================================================
    # HUD overlay
    # ========================================================================

    def _draw_camera_hud(self, frame, distance_cm: float,
                         ir_data: dict[str, bool]) -> "np.ndarray":
        """Draw semi-transparent HUD on camera frame."""
        h, w = frame.shape[:2]

        # Semi-transparent bottom bar
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, h - 70), (w, h), (20, 20, 20), -1)
        frame = cv2.addWeighted(frame, 0.75, overlay, 0.25, 0).astype(np.uint8)

        # Text lines
        ir_str = f"IR L:{int(ir_data['left'])} M:{int(ir_data['middle'])} R:{int(ir_data['right'])}"
        lines = [
            f"Cmd: {self._command:10s}  Dist: {distance_cm:5.1f} cm  FPS: {self._fps_current:4.1f}",
            ir_str,
            "[W]fwd [S]back [A]left [D]right [SPACE]stop [R]eset [Q]uit",
        ]
        for i, line in enumerate(lines):
            cv2.putText(frame, line, (10, h - 52 + i * 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 255), 1)
        return frame

    def _signal_handler(self, signum, _frame):
        logger.info("Received signal %d, shutting down...", signum)
        self._running = False


# ============================================================================
# CLI
# ============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description=f"{config.PRODUCT_NAME} — {config.PRODUCT_DESC}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # normal mode with camera + map display
  python main.py --no-display       # headless mode (SSH, logging only)
  python main.py --log-level DEBUG  # verbose logging
        """,
    )
    parser.add_argument("--no-display", action="store_true",
                        help="Headless mode (no OpenCV windows)")
    parser.add_argument("--log-level", type=str, default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Logging level (default: INFO)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/manual_drive.log", encoding="utf-8"),
        ],
    )

    # Ensure log directory exists
    from pathlib import Path
    Path("logs").mkdir(parents=True, exist_ok=True)

    drive = ManualDrive(no_display=args.no_display)
    drive.start()
