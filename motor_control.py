"""
motor_control.py — 4WD DC motor control via PCA9685 (Freenove Smart Car Board).

Supports: forward, backward, turn left, turn right, stop.
Mock mode available when Freenove libraries are absent.
"""

import logging

logger = logging.getLogger(__name__)

# ---- Freenove Motor library (graceful degradation) ----
try:
    from Motor import Motor as _FreenoveMotor

    _HAS_MOTOR = True
except ImportError:
    _HAS_MOTOR = False


class MotorControl:
    """4WD motor control for Freenove FNK0043B (standard wheels)."""

    def __init__(self, config):
        self.config = config
        self._motor = None
        self.duty_max = config.MOTOR_DUTY_MAX
        self.duty_forward = config.MOTOR_DUTY_FORWARD
        self.duty_turn = config.MOTOR_DUTY_TURN

        # Mode state
        self.mode = "auto"
        self.hardware_available = _HAS_MOTOR
        self.mock_active = False
        self.initialization_errors: list[str] = []

    def setup(self, mode: str = "auto") -> bool:
        """Initialize motor hardware. Mode: 'auto', 'mock', or 'hardware'.

        Returns True if setup succeeded, False otherwise.
        In 'hardware' mode, returns False on any failure.
        In 'auto' mode, falls back to mock on failure.
        In 'mock' mode, forces mock unconditionally.
        """
        self.mode = mode
        self.initialization_errors = []

        if mode == "mock":
            self.mock_active = True
            logger.info("Motor: MOCK mode active (forced)")
            return True

        if mode == "hardware":
            if not _HAS_MOTOR:
                msg = "Freenove Motor library not available"
                self.initialization_errors.append(msg)
                logger.error("Motor: %s", msg)
                return False
            try:
                self._motor = _FreenoveMotor()
                self.mock_active = False
                logger.info("Motor: hardware mode active (PCA9685)")
                return True
            except Exception as e:
                msg = f"Motor hardware init failed: {e}"
                self.initialization_errors.append(msg)
                logger.error("Motor: %s", msg)
                return False

        # mode == "auto"
        if _HAS_MOTOR:
            try:
                self._motor = _FreenoveMotor()
                self.mock_active = False
                logger.info("Motor: auto mode → hardware (PCA9685)")
                return True
            except Exception as e:
                logger.warning(
                    "Motor: auto mode hardware init failed (%s), falling back to mock", e
                )
                self.initialization_errors.append(f"Hardware init failed: {e}")

        self.mock_active = True
        logger.info("Motor: auto mode → mock (no Freenove library)")
        return True

    def forward(self, duty: int = None):
        """All four wheels forward."""
        d = duty if duty is not None else self.duty_forward
        d = max(0, min(self.duty_max, d))
        self._set_raw(d, d, d, d)

    def backward(self, duty: int = None):
        """All four wheels backward."""
        d = duty if duty is not None else self.duty_forward
        d = max(0, min(self.duty_max, d))
        self._set_raw(-d, -d, -d, -d)

    def turn_left(self, duty: int = None):
        """Left wheels backward, right wheels forward → rotate left."""
        d = duty if duty is not None else self.duty_turn
        d = max(0, min(self.duty_max, d))
        self._set_raw(-d, -d, d, d)

    def turn_right(self, duty: int = None):
        """Left wheels forward, right wheels backward → rotate right."""
        d = duty if duty is not None else self.duty_turn
        d = max(0, min(self.duty_max, d))
        self._set_raw(d, d, -d, -d)

    def stop(self):
        """Stop all motors."""
        self._set_raw(0, 0, 0, 0)

    def cleanup(self):
        self.stop()
        if self._motor is not None:
            try:
                self._motor.close()
            except Exception:
                pass
        logger.info("Motor resources released")

    def _set_raw(self, lf: int, lr: int, rf: int, rr: int):
        lf = max(-self.duty_max, min(self.duty_max, lf))
        lr = max(-self.duty_max, min(self.duty_max, lr))
        rf = max(-self.duty_max, min(self.duty_max, rf))
        rr = max(-self.duty_max, min(self.duty_max, rr))
        if self.config.MOTOR_INVERT:
            lf, lr, rf, rr = -lf, -lr, -rf, -rr
        if self._motor is not None:
            try:
                self._motor.setMotorModel(lf, lr, rf, rr)
            except Exception as e:
                logger.error("setMotorModel failed: %s", e)
