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
from terminal_keyboard import TerminalKeyboard

logger = logging.getLogger("manual_drive")


class ManualDrive:
    """Keyboard-controlled manual drive with real-time mapping."""

    def __init__(self, no_display: bool = False, mode: str = "auto",
                 use_terminal_kb: bool = False,
                 command: str = None, duration: float = None,
                 no_camera: bool = False, require_camera: bool = False,
                 duty: int = None, max_runtime: float = None):
        self.no_display = no_display
        self.mode = mode
        self._use_terminal_kb = use_terminal_kb
        self._one_shot_command = command
        self._command_duration = duration
        self._no_camera = no_camera
        self._require_camera = require_camera
        self._max_runtime = max_runtime

        # Apply duty override if provided
        if duty is not None:
            config.MOTOR_DUTY_FORWARD = duty
            config.MOTOR_DUTY_TURN = duty
            logger.info("Duty override: %d", duty)

        logger.info("=" * 55)
        logger.info("%s — %s", config.PRODUCT_NAME, config.PRODUCT_DESC)
        logger.info("Run mode: %s", mode)
        logger.info("=" * 55)

        self.camera = Camera(config)
        self.motor = MotorControl(config)
        self.sensors = Sensors(config)
        self.mapping = Mapping(config)
        self._terminal_kb = None

        self._running = False
        self._command = "stop"
        self._last_command_time = 0.0
        self._start_time = 0.0

        # FPS tracking
        self._fps_counter = 0
        self._fps_timer = time.time()
        self._fps_current = 0.0

    # ========================================================================
    # Lifecycle
    # ========================================================================

    def start(self):
        """Initialize all modules and enter main loop or execute one-shot command."""
        # Camera
        if self._no_camera:
            logger.info("Camera: disabled (--no-camera)")
        else:
            if not self.camera.start():
                if self._require_camera:
                    logger.error("Camera init failed and --require-camera is set, exiting")
                    sys.exit(1)
                logger.warning("Camera init failed, continuing without camera")
                self._no_camera = True

        if not self.motor.setup(self.mode):
            logger.error("Motor init failed (mode=%s)", self.mode)
            sys.exit(1)

        if not self.sensors.setup(self.mode):
            logger.error("Sensor init failed (mode=%s)", self.mode)
            sys.exit(1)

        # Terminal keyboard
        if self._use_terminal_kb:
            try:
                self._terminal_kb = TerminalKeyboard()
                self._terminal_kb.start()
            except ImportError as e:
                logger.error("Terminal keyboard not available: %s", e)
                sys.exit(1)

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self._running = True
        self._start_time = time.monotonic()

        # One-shot command mode
        if self._one_shot_command:
            self._execute_one_shot()
            return

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

        if self._terminal_kb is not None:
            try:
                self._terminal_kb.stop()
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

            # 1. Capture camera frame (skip if --no-camera)
            frame = None
            if not self._no_camera:
                frame = self.camera.capture()

            # 2. Read sensors
            distance_cm = self.sensors.get_distance_cm()
            ir_data = self.sensors.ir_all()

            # 3. Obstacle safety check
            if self._command != "stop" and not self.sensors.mock_active:
                if 0 < distance_cm < config.SAFE_STOP_DISTANCE_CM:
                    logger.warning(
                        "SAFETY: obstacle at %.1f cm < %.0f cm, stopping",
                        distance_cm, config.SAFE_STOP_DISTANCE_CM,
                    )
                    self.motor.stop()
                    self._command = "stop"

            # 4. Time-based auto-stop
            if self._command != "stop":
                if time.monotonic() - self._last_command_time > config.AUTO_STOP_TIMEOUT_SEC:
                    self._command = "stop"
                    self.motor.stop()

            # 5. Max runtime check
            if self._max_runtime is not None:
                if time.monotonic() - self._start_time > self._max_runtime:
                    logger.info("Max runtime (%.1fs) reached, stopping", self._max_runtime)
                    self._running = False
                    break

            # 6. Update mapping
            self.mapping.update_pose(self._command, dt)
            self.mapping.update_map(distance_cm, ir_data)

            # 7. Display + input
            if self._terminal_kb is not None:
                # Terminal keyboard mode (SSH friendly)
                key_char = self._terminal_kb.read_key(timeout=0.02)
                if key_char is not None:
                    self._handle_terminal_key(key_char)
                if self._fps_counter % 50 == 0:
                    logger.debug("Terminal tick %d | cmd=%s dist=%.1f cm",
                                 self._fps_counter, self._command, distance_cm)
            elif not self.no_display:
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

            # 8. FPS counter
            self._fps_counter += 1
            elapsed = time.time() - self._fps_timer
            if elapsed >= 1.0:
                self._fps_current = self._fps_counter / elapsed
                self._fps_counter = 0
                self._fps_timer = time.time()

            # 9. Rate limiting
            loop_time = time.time() - loop_start
            sleep_time = config.MAIN_LOOP_DELAY - loop_time
            if sleep_time > 0:
                time.sleep(sleep_time)

    # ========================================================================
    # Command execution
    # ========================================================================

    def _execute_one_shot(self):
        """Execute a single command for a fixed duration, then stop and exit."""
        cmd = self._one_shot_command
        duration = min(self._command_duration or 1.0, 1.0)  # safety cap at 1s
        logger.info("One-shot: %s for %.1fs", cmd, duration)

        command_map = {
            "forward": self.motor.forward,
            "backward": self.motor.backward,
            "left": self.motor.turn_left,
            "right": self.motor.turn_right,
            "stop": self.motor.stop,
        }

        action = command_map.get(cmd)
        if action is None:
            logger.error("Unknown command: %s", cmd)
            sys.exit(1)

        if cmd != "stop":
            self._command = cmd
            action()
            time.sleep(duration)

        self.motor.stop()
        self._command = "stop"
        logger.info("One-shot complete: %s, motor stopped", cmd)

    # ========================================================================
    # Keyboard handling
    # ========================================================================

    def _handle_terminal_key(self, char: str):
        """Handle a single character from terminal keyboard."""
        if char == "q":
            logger.info("Terminal: 'q' pressed, quitting")
            self._running = False
            return

        command = None
        if char == "w":
            command = "forward"
            self.motor.forward()
        elif char == "s":
            command = "backward"
            self.motor.backward()
        elif char == "a":
            command = "left"
            self.motor.turn_left()
        elif char == "d":
            command = "right"
            self.motor.turn_right()
        elif char == " ":
            command = "stop"
            self.motor.stop()

        if command is not None:
            self._command = command
            self._last_command_time = time.monotonic()
            logger.debug("Terminal key: %s → %s", char, command)

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
            self._last_command_time = time.monotonic()

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
    parser.add_argument("--mode", type=str, default="auto",
                        choices=["auto", "mock", "hardware"],
                        help="Runtime mode: auto (default, fallback to mock), "
                             "mock (force emulated hardware), hardware (require real hardware)")
    parser.add_argument("--log-level", type=str, default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Logging level (default: INFO)")
    parser.add_argument("--keyboard-terminal", action="store_true",
                        help="Use terminal keyboard input (SSH friendly, Linux/macOS only)")
    parser.add_argument("--command", type=str, default=None,
                        choices=["stop", "forward", "backward", "left", "right"],
                        help="Execute a single command and exit (for CI/SSH smoke tests)")
    parser.add_argument("--duration", type=float, default=None,
                        help="Duration in seconds for --command (max 1.0)")
    parser.add_argument("--no-camera", action="store_true",
                        help="Skip camera initialization entirely")
    parser.add_argument("--require-camera", action="store_true",
                        help="Exit if camera initialization fails")
    parser.add_argument("--duty", type=int, default=None,
                        help="Override motor duty cycle (0-4096)")
    parser.add_argument("--max-runtime", type=float, default=None,
                        help="Maximum runtime in seconds before auto-stop and exit")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # Validate duration
    if args.duration is not None:
        if args.command is None:
            logger = logging.getLogger("cli")
            logger.error("--duration requires --command")
            sys.exit(1)
        if args.duration <= 0 or args.duration > 1.0:
            logger = logging.getLogger("cli")
            logger.error("--duration must be > 0 and <= 1.0 (got %.1f)", args.duration)
            sys.exit(1)
    duration = args.duration if args.command else None

    # Validate duty
    _cli_logger = logging.getLogger("cli")
    if args.duty is not None:
        if args.duty < 0 or args.duty > config.MOTOR_DUTY_MAX:
            _cli_logger.error(
                "--duty must be 0-%d (got %d)", config.MOTOR_DUTY_MAX, args.duty
            )
            sys.exit(1)

    # Ensure log directory exists before configuring FileHandler
    from pathlib import Path
    Path("logs").mkdir(parents=True, exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/manual_drive.log", encoding="utf-8"),
        ],
    )

    drive = ManualDrive(
        no_display=args.no_display,
        mode=args.mode,
        use_terminal_kb=args.keyboard_terminal,
        command=args.command,
        duration=duration,
        no_camera=args.no_camera,
        require_camera=args.require_camera,
        duty=args.duty,
        max_runtime=args.max_runtime,
    )
    drive.start()
