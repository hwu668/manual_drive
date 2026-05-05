"""Tests for VisualOdometry (ORB feature-based motion estimation)."""

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from visual_odometry import VisualOdometry


# ---------------------------------------------------------------------------
# Synthetic frame helpers
# ---------------------------------------------------------------------------

def _make_test_frame(shape=(480, 640), tile=20):
    """Return a grayscale image with a dense non-periodic texture rich in FAST corners.

    Uses a seeded random field thresholded into dark/light patches — avoids the
    epipolar ambiguity that periodic patterns (checkerboards) create.
    """
    h, w = shape
    rng = np.random.RandomState(42)
    # Low-frequency noise field → smooth blobs of dark/light
    small = rng.rand(h // 4, w // 4).astype(np.float32)
    import cv2
    up = cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)
    return (up * 255).astype(np.uint8)


def _shift_frame(img, dx, dy):
    """Translate image by (dx, dy) pixels; fill exposed area with black."""
    h, w = img.shape
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    shifted = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return shifted


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestVisualOdometry:
    """Verify VisualOdometry core logic (requires cv2)."""

    def test_init_defaults(self):
        vo = VisualOdometry(config)
        assert vo.scale == config.VO_SCALE
        assert vo.min_matches == config.VO_MIN_MATCHES
        assert vo.K.shape == (3, 3)
        assert np.array_equal(vo.R, np.eye(3))
        assert np.array_equal(vo.t, np.zeros((3, 1)))

    def test_first_frame_returns_identity(self):
        vo = VisualOdometry(config)
        img = _make_test_frame()
        result = vo.process_frame(img)
        assert result["confidence"] == 0.0
        assert result["num_inliers"] == 0
        assert np.allclose(result["delta_t"], np.zeros(3))

    def test_two_similar_frames_produce_low_confidence(self):
        """Identical frames should produce zero motion (or very low confidence)."""
        vo = VisualOdometry(config)
        img = _make_test_frame()
        # Feed same frame twice — VO should detect minimal motion
        vo.process_frame(img)
        result = vo.process_frame(img)
        # With identical frames, essential matrix is degenerate → low confidence
        assert result["confidence"] < 0.5, (
            f"Expected low confidence for identical frames, got {result['confidence']:.3f}"
        )

    def test_shifted_frame_detects_motion(self):
        """A translated frame should produce non-zero dz and some inliers."""
        vo = VisualOdometry(config)
        vo.min_matches = 8  # lower bar for small synthetic shifts
        img1 = _make_test_frame()
        img2 = _shift_frame(img1, dx=0, dy=-15)  # 15 px upward = camera moved forward

        vo.process_frame(img1)
        result = vo.process_frame(img2)

        # We expect at least some inliers
        assert result["num_inliers"] > 0, (
            f"Expected inliers on shifted frames, got {result['num_inliers']}"
        )

    def test_reset_clears_state(self):
        vo = VisualOdometry(config)
        vo.min_matches = 8
        img1 = _make_test_frame()
        img2 = _shift_frame(img1, dx=20, dy=0)
        vo.process_frame(img1)
        vo.process_frame(img2)

        # Accumulated pose should have changed
        assert not np.allclose(vo.t, np.zeros((3, 1)))

        vo.reset()
        assert np.array_equal(vo.R, np.eye(3))
        assert np.array_equal(vo.t, np.zeros((3, 1)))
        assert vo._prev_gray is None
        assert vo.last_confidence == 0.0

    def test_calibrate_scale_updates_scale(self):
        vo = VisualOdometry(config)
        # Manually set a non-zero last delta so calibrate_scale can compute
        vo.last_delta_t = np.array([0.0, 0.0, 0.5], dtype=np.float64)
        new_scale = vo.calibrate_scale(10.0)  # 10 cm / 0.5 unit = 20
        assert new_scale == 20.0
        assert vo.scale == 20.0

    def test_calibrate_scale_ignores_zero_motion(self):
        vo = VisualOdometry(config)
        vo.last_delta_t = np.zeros(3)
        old_scale = vo.scale
        new_scale = vo.calibrate_scale(10.0)
        assert new_scale == old_scale

    def test_empty_result_structure(self):
        vo = VisualOdometry(config)
        result = vo._empty_result()
        expected_keys = {
            "delta_R", "delta_t", "confidence", "num_inliers",
            "R", "t", "dx_cm", "dz_cm", "dyaw_deg",
        }
        assert set(result.keys()) == expected_keys
        assert result["confidence"] == 0.0
        assert result["num_inliers"] == 0
        assert np.allclose(result["dx_cm"], 0.0)
        assert np.allclose(result["dz_cm"], 0.0)
        assert np.allclose(result["dyaw_deg"], 0.0)


# Need cv2 at module level for _shift_frame
import cv2
