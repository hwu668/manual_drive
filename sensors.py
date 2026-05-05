"""
sensors.py — HC-SR04 ultrasonic rangefinder + 3-channel IR line tracking.

All sensors read on each call; mock mode returns safe defaults when running
without Raspberry Pi GPIO hardware.
"""

import logging
import time

logger = logging.getLogger(__name__)

# ---- Ultrasonic ----
try:
    import RPi.GPIO as GPIO

    _HAS_GPIO = True
except ImportError:
    _HAS_GPIO = False

# ---- IR line tracking (may also use GPIO) ----
# The 3 IR sensors output digital HIGH/LOW; we read them as GPIO inputs.


class Sensors:
    """Unified sensor interface: ultrasonic + 3× IR."""

    def __init__(self, config):
        self.config = config
        self._trig = config.ULTRASONIC_TRIG_PIN
        self._echo = config.ULTRASONIC_ECHO_PIN
        self._ir_pins = {
            "left": config.IR_LEFT_PIN,
            "middle": config.IR_MIDDLE_PIN,
            "right": config.IR_RIGHT_PIN,
        }
        self._setup_done = False

    def setup(self) -> bool:
        """Initialize GPIO pins. Returns True on success or mock."""
        if not _HAS_GPIO:
            logger.info("Sensors in MOCK mode (no RPi.GPIO)")
            return True

        try:
            GPIO.setmode(GPIO.BCM)
            # Ultrasonic
            GPIO.setup(self._trig, GPIO.OUT)
            GPIO.setup(self._echo, GPIO.IN)
            # IR sensors (digital input with pull-up)
            for pin in self._ir_pins.values():
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            self._setup_done = True
            logger.info("Sensors initialized (HC-SR04 + 3× IR)")
            return True
        except Exception as e:
            logger.error("Sensor GPIO setup failed: %s", e)
            return False

    # ========================================================================
    # Ultrasonic
    # ========================================================================

    def get_distance_cm(self) -> float:
        """Return distance in cm, -1 on failure, 999 in mock mode."""
        if not _HAS_GPIO or not self._setup_done:
            return 999.0

        try:
            # Send 10 µs trigger pulse
            GPIO.output(self._trig, GPIO.HIGH)
            time.sleep(0.00001)
            GPIO.output(self._trig, GPIO.LOW)

            # Measure echo pulse duration
            timeout = time.time() + 0.04
            while GPIO.input(self._echo) == GPIO.LOW:
                if time.time() > timeout:
                    return -1.0
            pulse_start = time.time()

            while GPIO.input(self._echo) == GPIO.HIGH:
                if time.time() > timeout:
                    return -1.0
            pulse_end = time.time()

            duration = pulse_end - pulse_start
            distance = duration * 17150  # speed of sound / 2 (cm/s)
            return round(distance, 1)
        except Exception as e:
            logger.error("Ultrasonic read failed: %s", e)
            return -1.0

    # ========================================================================
    # Infrared line tracking
    # ========================================================================

    def ir_left(self) -> bool:
        """True = dark surface / edge detected."""
        return self._read_ir("left")

    def ir_middle(self) -> bool:
        return self._read_ir("middle")

    def ir_right(self) -> bool:
        return self._read_ir("right")

    def ir_all(self) -> dict[str, bool]:
        """Return dict with all three IR readings."""
        return {
            "left": self.ir_left(),
            "middle": self.ir_middle(),
            "right": self.ir_right(),
        }

    def _read_ir(self, name: str) -> bool:
        if not _HAS_GPIO or not self._setup_done:
            return False
        try:
            # LOW = dark / edge (IR beam reflected or interrupted)
            return GPIO.input(self._ir_pins[name]) == GPIO.LOW
        except Exception:
            return False

    # ========================================================================
    # Cleanup
    # ========================================================================

    def cleanup(self):
        if _HAS_GPIO and self._setup_done:
            try:
                GPIO.cleanup()
            except Exception:
                pass
            self._setup_done = False
        logger.info("Sensor resources released")
