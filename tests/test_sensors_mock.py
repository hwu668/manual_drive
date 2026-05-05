"""Tests for Sensors mock mode."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from sensors import Sensors


class TestSensorsMock:
    """Verify Sensors in mock mode."""

    def test_init_defaults(self):
        s = Sensors(config)
        assert s.mode == "auto"
        assert not s.mock_active

    def test_setup_mock_mode_forced(self):
        s = Sensors(config)
        result = s.setup("mock")
        assert result is True
        assert s.mock_active is True
        assert s.mode == "mock"
        assert s.initialization_errors == []

    def test_setup_auto_mode(self):
        s = Sensors(config)
        result = s.setup("auto")
        assert result is True
        assert s.mode == "auto"

    def test_get_distance_mock(self):
        s = Sensors(config)
        s.setup("mock")
        dist = s.get_distance_cm()
        assert dist == 999.0  # mock default

    def test_ir_readings_mock(self):
        s = Sensors(config)
        s.setup("mock")
        ir = s.ir_all()
        assert isinstance(ir, dict)
        assert "left" in ir
        assert "middle" in ir
        assert "right" in ir
        # Mock returns False for all
        assert ir["left"] is False
        assert ir["middle"] is False
        assert ir["right"] is False

    def test_cleanup_no_crash(self):
        s = Sensors(config)
        s.setup("mock")
        s.cleanup()
        # Should not raise

    def test_hardware_mode_status(self):
        s = Sensors(config)
        result = s.setup("hardware")
        if not s.hardware_available:
            assert result is False
            assert len(s.initialization_errors) > 0
        else:
            assert result is True
