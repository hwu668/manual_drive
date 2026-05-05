"""Tests for config defaults and safety ranges."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config


class TestConfig:
    """Verify config values are within safe ranges."""

    def test_duty_max_positive(self):
        assert config.MOTOR_DUTY_MAX > 0

    def test_duty_forward_in_range(self):
        assert 0 < config.MOTOR_DUTY_FORWARD <= config.MOTOR_DUTY_MAX

    def test_duty_turn_in_range(self):
        assert 0 < config.MOTOR_DUTY_TURN <= config.MOTOR_DUTY_MAX

    def test_duty_slow_in_range(self):
        assert 0 < config.MOTOR_DUTY_SLOW <= config.MOTOR_DUTY_MAX

    def test_auto_stop_timeout_positive(self):
        assert config.AUTO_STOP_TIMEOUT_SEC > 0

    def test_safe_stop_distance_positive(self):
        assert config.SAFE_STOP_DISTANCE_CM > 0

    def test_map_size_positive(self):
        assert config.MAP_SIZE_CELLS > 0

    def test_map_resolution_positive(self):
        assert config.MAP_RESOLUTION_CM > 0

    def test_main_loop_delay_positive(self):
        assert config.MAIN_LOOP_DELAY > 0

    def test_ultrasonic_max_distance_positive(self):
        assert config.ULTRASONIC_MAX_DISTANCE_CM > 0

    def test_speed_cm_per_sec_positive(self):
        assert config.SPEED_CM_PER_SEC > 0

    def test_turn_deg_per_sec_positive(self):
        assert config.TURN_DEG_PER_SEC > 0
