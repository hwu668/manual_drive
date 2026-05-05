"""Tests for MotorControl mock mode."""

import sys
from pathlib import Path

# Allow imports from parent directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from motor_control import MotorControl


class TestMotorControlMock:
    """Verify MotorControl in mock mode."""

    def test_init_mock_mode(self):
        mc = MotorControl(config)
        assert mc.mode == "auto"
        assert not mc.mock_active

    def test_setup_mock_mode_forced(self):
        mc = MotorControl(config)
        result = mc.setup("mock")
        assert result is True
        assert mc.mock_active is True
        assert mc.mode == "mock"
        assert mc.initialization_errors == []

    def test_setup_auto_mode(self):
        mc = MotorControl(config)
        result = mc.setup("auto")
        assert result is True
        # On non-Pi without Freenove lib: should fall back to mock
        # On Pi with Freenove lib: should use hardware
        assert mc.mode == "auto"

    def test_forward_no_crash(self):
        mc = MotorControl(config)
        mc.setup("mock")
        mc.forward()
        # Should not raise

    def test_backward_no_crash(self):
        mc = MotorControl(config)
        mc.setup("mock")
        mc.backward()
        # Should not raise

    def test_turn_left_no_crash(self):
        mc = MotorControl(config)
        mc.setup("mock")
        mc.turn_left()
        # Should not raise

    def test_turn_right_no_crash(self):
        mc = MotorControl(config)
        mc.setup("mock")
        mc.turn_right()
        # Should not raise

    def test_stop_no_crash(self):
        mc = MotorControl(config)
        mc.setup("mock")
        mc.stop()
        # Should not raise

    def test_cleanup_no_crash(self):
        mc = MotorControl(config)
        mc.setup("mock")
        mc.cleanup()
        # Should not raise

    def test_hardware_mode_fails_without_library(self):
        mc = MotorControl(config)
        result = mc.setup("hardware")
        # Without Freenove library, hardware mode should fail
        if not mc.hardware_available:
            assert result is False
            assert len(mc.initialization_errors) > 0
