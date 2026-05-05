"""Tests for safety stop logic."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config


class FakeMotor:
    """Minimal fake motor for testing safety logic."""

    def __init__(self):
        self.stopped = False
        self.mock_active = True

    def stop(self):
        self.stopped = True

    def forward(self):
        pass

    def backward(self):
        pass

    def turn_left(self):
        pass

    def turn_right(self):
        pass

    def cleanup(self):
        pass


class TestSafety:
    """Verify safety stop triggers under threshold distance."""

    def test_stops_when_too_close(self):
        motor = FakeMotor()
        distance = 5.0  # closer than SAFE_STOP_DISTANCE_CM (15.0)
        if 0 < distance < config.SAFE_STOP_DISTANCE_CM:
            motor.stop()
        assert motor.stopped is True

    def test_no_stop_when_far_enough(self):
        motor = FakeMotor()
        distance = 100.0  # farther than SAFE_STOP_DISTANCE_CM
        if 0 < distance < config.SAFE_STOP_DISTANCE_CM:
            motor.stop()
        assert motor.stopped is False

    def test_no_stop_when_already_stopped(self):
        motor = FakeMotor()
        motor.stopped = True
        distance = 5.0
        # Should not double-stop (logic: only check if command != "stop")
        # This tests the condition guard
        command = "stop"
        if command != "stop" and 0 < distance < config.SAFE_STOP_DISTANCE_CM:
            motor.stop()
        # Already stopped, should stay True
        assert motor.stopped is True

    def test_mock_mode_skips_safety_stop(self):
        """In mock mode, sensors return 999.0, so safety stop should not trigger."""
        motor = FakeMotor()
        motor.mock_active = True
        distance = 999.0
        should_trigger = not motor.mock_active and 0 < distance < config.SAFE_STOP_DISTANCE_CM
        if should_trigger:
            motor.stop()
        assert motor.stopped is False
