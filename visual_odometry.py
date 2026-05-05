"""
visual_odometry.py — Monocular visual odometry using ORB features.

Estimates frame-to-frame camera motion (R, t direction) from ORB feature
matches between consecutive frames. Translation scale is unobservable from
monocular vision alone and must be calibrated externally (ultrasonic,
dead-reckoning, or known baseline).

Design notes
------------
- ORB is chosen for speed on Raspberry Pi 5; binary descriptors + Hamming
  distance matcher avoid the cost of float descriptor matching.
- cv2.findEssentialMat + cv2.recoverPose provide R, t up to scale.
- RANSAC inlier count serves as a confidence signal; low-confidence frames
  are skipped (identity delta returned).
- Frame-skip option reduces CPU load when the car moves slowly.

Camera coordinate convention (OpenCV, Pi camera facing forward):
    X → right,  Y → down,  Z → forward (depth)
For ground-plane motion the relevant components are:
    t_z  → forward/backward translation
    t_x  → lateral translation
    R_y  → yaw rotation
"""

from __future__ import annotations

import logging
import math

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class VisualOdometry:
    """ORB-based monocular visual odometry for Freenove FNK0043B."""

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def __init__(self, config):
        self.config = config

        # ---- camera intrinsics ----
        fx = getattr(config, "VO_FX", 530.0)
        fy = getattr(config, "VO_FY", 530.0)
        cx = getattr(config, "VO_CX", 320.0)
        cy = getattr(config, "VO_CY", 240.0)
        self.K = np.array([[fx, 0, cx],
                           [0, fy, cy],
                           [0,  0,  1]], dtype=np.float64)

        # ---- feature detector / matcher ----
        n_features = getattr(config, "VO_ORB_FEATURES", 1000)
        self.orb = cv2.ORB_create(nfeatures=n_features)

        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

        # ---- previous frame ----
        self._prev_gray: np.ndarray | None = None
        self._prev_kp: tuple[cv2.KeyPoint, ...] | None = None
        self._prev_des: np.ndarray | None = None

        # ---- accumulated pose (R ∈ SO(3), t ∈ ℝ³ in camera frame) ----
        self.R: np.ndarray = np.eye(3, dtype=np.float64)
        self.t: np.ndarray = np.zeros((3, 1), dtype=np.float64)

        # ---- scale (updated via calibrate_scale) ----
        self.scale: float = getattr(config, "VO_SCALE", 1.0)

        # ---- quality knobs ----
        self.min_matches: int = getattr(config, "VO_MIN_MATCHES", 30)
        self.frame_skip: int = getattr(config, "VO_FRAME_SKIP", 0)

        # ---- per-frame bookkeeping ----
        self._frame_count: int = 0

        # Last successful delta (for external scale calibration)
        self.last_delta_R: np.ndarray = np.eye(3, dtype=np.float64)
        self.last_delta_t: np.ndarray = np.zeros(3, dtype=np.float64)
        self.last_num_inliers: int = 0
        self.last_confidence: float = 0.0

        # Ground-plane deltas (cm) — extracted from camera-frame motion
        self.last_dx_cm: float = 0.0   # lateral (right +)
        self.last_dz_cm: float = 0.0   # forward
        self.last_dyaw_deg: float = 0.0

        logger.info(
            "VO init: ORB=%d features  K=fx=%.0f  min-matches=%d  "
            "frame-skip=%d  initial-scale=%.4f",
            n_features, fx, self.min_matches, self.frame_skip, self.scale,
        )

    # ------------------------------------------------------------------
    # Per-frame processing
    # ------------------------------------------------------------------

    def process_frame(self, frame: np.ndarray) -> dict:
        """Ingest a new BGR frame, match against previous, and return deltas.

        Parameters
        ----------
        frame : np.ndarray
            BGR image (H, W, 3) from the camera.

        Returns
        -------
        dict
            ``delta_R``      — (3,3) rotation matrix
            ``delta_t``      — (3,)  scaled translation vector (camera frame)
            ``confidence``   — float [0-1]
            ``num_inliers``  — int
            ``R``            — (3,3) accumulated rotation
            ``t``            — (3,1) accumulated translation
            ``dx_cm``        — lateral delta in ground plane (cm)
            ``dz_cm``        — forward delta in ground plane (cm)
            ``dyaw_deg``     — yaw delta (degrees)
        """
        self._frame_count += 1

        # Frame skip: still ingest the pair but return identity
        if self.frame_skip > 0 and self._frame_count % (self.frame_skip + 1) != 0:
            if self._prev_gray is None:
                self._prev_gray = self._to_gray(frame)
            return self._empty_result()

        gray = self._to_gray(frame)

        # --- first frame ---
        if self._prev_gray is None:
            self._prev_gray = gray.copy()
            self._prev_kp, self._prev_des = self.orb.detectAndCompute(gray, None)
            return self._empty_result()

        # --- detect features on current frame ---
        curr_kp, curr_des = self.orb.detectAndCompute(gray, None)

        # --- bail out if either frame has too few keypoints ---
        if (self._prev_des is None or curr_des is None
                or len(self._prev_kp) < self.min_matches
                or len(curr_kp) < self.min_matches):
            self._advance(gray, curr_kp, curr_des)
            return self._empty_result()

        # --- brute-force match ---
        raw_matches = self.matcher.match(self._prev_des, curr_des)
        raw_matches = sorted(raw_matches, key=lambda m: m.distance)

        if len(raw_matches) < self.min_matches:
            self._advance(gray, curr_kp, curr_des)
            return self._empty_result()

        # --- build point arrays ---
        pts_prev = np.float32([self._prev_kp[m.queryIdx].pt for m in raw_matches])
        pts_curr = np.float32([curr_kp[m.trainIdx].pt for m in raw_matches])

        # --- essential matrix ---
        E, mask_E = cv2.findEssentialMat(
            pts_prev, pts_curr, self.K,
            method=cv2.RANSAC, prob=0.999, threshold=1.0,
        )
        if E is None or mask_E is None:
            self._advance(gray, curr_kp, curr_des)
            return self._empty_result()

        inliers_E = mask_E.ravel().astype(bool)
        if np.sum(inliers_E) < self.min_matches:
            self._advance(gray, curr_kp, curr_des)
            return self._empty_result()

        # --- recover pose (camera motion from prev → curr) ---
        _, R, t_vec, mask_pose = cv2.recoverPose(
            E, pts_prev[inliers_E], pts_curr[inliers_E], self.K,
        )
        if mask_pose is None:
            self._advance(gray, curr_kp, curr_des)
            return self._empty_result()

        pose_inliers = int(np.sum(mask_pose.ravel() > 0))
        confidence = pose_inliers / max(len(pts_prev[inliers_E]), 1)

        if confidence < 0.4 or pose_inliers < self.min_matches:
            self._advance(gray, curr_kp, curr_des)
            return self._empty_result()

        # --- apply scale ---
        t_scaled = (t_vec.ravel() * self.scale).astype(np.float64)  # cm

        # --- accumulate ---
        self.R = self.R @ R
        self.t = self.t + self.R @ t_scaled.reshape(3, 1)

        # --- ground-plane extraction ---
        # Camera frame: X=right  Y=down  Z=forward
        # Yaw ≈ rotation around Y axis
        dyaw_rad = math.atan2(R[2, 0], R[2, 2])  # atan2(sin, cos)
        dyaw_deg = math.degrees(dyaw_rad)

        dx_cm = t_scaled[0]   # lateral
        dz_cm = t_scaled[2]   # forward

        # --- store last deltas ---
        self.last_delta_R = R.copy()
        self.last_delta_t = t_scaled.copy()
        self.last_num_inliers = pose_inliers
        self.last_confidence = confidence
        self.last_dx_cm = dx_cm
        self.last_dz_cm = dz_cm
        self.last_dyaw_deg = dyaw_deg

        logger.debug(
            "VO frame %d: %d inliers  conf=%.2f  "
            "dX=%.2f dZ=%.2f cm  dyaw=%.1f°",
            self._frame_count, pose_inliers, confidence,
            dx_cm, dz_cm, dyaw_deg,
        )

        # --- advance ---
        self._advance(gray, curr_kp, curr_des)

        return {
            "delta_R":      R,
            "delta_t":      t_scaled,
            "confidence":   confidence,
            "num_inliers":  pose_inliers,
            "R":            self.R.copy(),
            "t":            self.t.copy(),
            "dx_cm":        dx_cm,
            "dz_cm":        dz_cm,
            "dyaw_deg":     dyaw_deg,
        }

    # ------------------------------------------------------------------
    # Scale calibration
    # ------------------------------------------------------------------

    def calibrate_scale(self, distance_cm: float) -> float:
        """Update scale using a ground-truth distance measurement.

        Call this after ``process_frame`` when an external sensor (e.g.
        ultrasonic) provides a measured distance change between frames.

        Parameters
        ----------
        distance_cm : float
            Measured distance the car actually traveled (cm).

        Returns
        -------
        float
            New scale value.
        """
        t_mag = float(np.linalg.norm(self.last_delta_t))
        if t_mag > 1e-6 and distance_cm > 0.01:
            self.scale = distance_cm / t_mag
            logger.info(
                "VO scale calibrated: %.4f  (%.1f cm / %.4f unit-mag)",
                self.scale, distance_cm, t_mag,
            )
        return self.scale

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset accumulated pose and clear the previous-frame buffer."""
        self.R = np.eye(3, dtype=np.float64)
        self.t = np.zeros((3, 1), dtype=np.float64)
        self._prev_gray = None
        self._prev_kp = None
        self._prev_des = None
        self.last_confidence = 0.0
        self.last_num_inliers = 0
        self.last_dx_cm = 0.0
        self.last_dz_cm = 0.0
        self.last_dyaw_deg = 0.0
        logger.info("VO pose reset")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_gray(frame: np.ndarray) -> np.ndarray:
        if len(frame.shape) == 3:
            return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return frame

    def _advance(self, gray: np.ndarray,
                 kp: tuple[cv2.KeyPoint, ...] | None,
                 des: np.ndarray | None) -> None:
        self._prev_gray = gray.copy()
        self._prev_kp = kp
        self._prev_des = des

    def _empty_result(self) -> dict:
        return {
            "delta_R":      np.eye(3, dtype=np.float64),
            "delta_t":      np.zeros(3, dtype=np.float64),
            "confidence":   0.0,
            "num_inliers":  0,
            "R":            self.R.copy(),
            "t":            self.t.copy(),
            "dx_cm":        0.0,
            "dz_cm":        0.0,
            "dyaw_deg":     0.0,
        }
