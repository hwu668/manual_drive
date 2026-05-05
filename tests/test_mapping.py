"""Tests for Mapping (dead-reckoning + occupancy grid)."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from mapping import Mapping


class TestMapping:
    """Verify Mapping core logic."""

    def test_init(self):
        m = Mapping(config)
        assert m.resolution == config.MAP_RESOLUTION_CM
        assert m.size == config.MAP_SIZE_CELLS
        assert m.origin == config.MAP_ORIGIN_CELL
        assert m.x_cm == 0.0
        assert m.y_cm == 0.0
        assert m.heading == math.pi / 2
        assert m.grid.shape == (m.size, m.size)
        assert len(m.path) == 1  # initial position

    def test_forward_updates_pose(self):
        m = Mapping(config)
        x_before = m.x_cm
        y_before = m.y_cm
        m.update_pose("forward", 1.0)
        # Moving "up" (heading = pi/2) should decrease y_cm
        assert m.y_cm < y_before
        # x should be ~unchanged (cos(pi/2) ≈ 0)
        assert abs(m.x_cm - x_before) < 1.0

    def test_left_turns_heading(self):
        m = Mapping(config)
        heading_before = m.heading
        m.update_pose("left", 1.0)
        assert m.heading > heading_before

    def test_right_turns_heading(self):
        m = Mapping(config)
        heading_before = m.heading
        m.update_pose("right", 1.0)
        assert m.heading < heading_before

    def test_stop_no_pose_change(self):
        m = Mapping(config)
        x_before = m.x_cm
        y_before = m.y_cm
        h_before = m.heading
        m.update_pose("stop", 10.0)
        assert m.x_cm == x_before
        assert m.y_cm == y_before
        assert m.heading == h_before

    def test_heading_normalized(self):
        m = Mapping(config)
        m.heading = 7.0  # > 2*pi
        m.update_pose("stop", 0.1)
        assert 0 <= m.heading < 2 * math.pi

    def test_grid_size_correct(self):
        m = Mapping(config)
        assert m.grid.shape == (config.MAP_SIZE_CELLS, config.MAP_SIZE_CELLS)

    def test_update_map_no_crash(self):
        m = Mapping(config)
        m.update_pose("forward", 0.1)
        m.update_map(50.0, {"left": False, "middle": False, "right": False})
        # Should not raise

    def test_update_map_with_ir(self):
        m = Mapping(config)
        m.update_pose("forward", 0.1)
        m.update_map(999.0, {"left": True, "middle": False, "right": False})
        # Should not raise; IR edge should be marked

    def test_render_returns_image(self):
        import numpy as np
        m = Mapping(config)
        img = m.render()
        assert isinstance(img, np.ndarray)
        assert img.shape[2] == 3  # BGR
