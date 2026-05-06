"""
mapping.py — Dead-reckoning odometry + 2D occupancy grid map.

Estimates pose from motor commands × elapsed time (no wheel encoders).
Builds a top-down grid map from ultrasonic and infrared sensor data.
"""

import logging
import math

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Map cell values
CELL_UNKNOWN = 0
CELL_FREE = 1
CELL_OBSTACLE = 2
CELL_IR_EDGE = 3


class Mapping:
    """2D occupancy grid with dead-reckoning pose estimation."""

    def __init__(self, config):
        self.config = config
        self.resolution = config.MAP_RESOLUTION_CM       # cm per cell
        self.size = config.MAP_SIZE_CELLS                 # grid dimension
        self.origin = config.MAP_ORIGIN_CELL              # start cell index

        # Pose: x, y in cm (world frame), heading in radians (0 = right, π/2 = up)
        self.x_cm = 0.0
        self.y_cm = 0.0
        self.heading = math.pi / 2  # start facing "up" on screen

        # Grid
        self.grid = np.zeros((self.size, self.size), dtype=np.uint8)

        # Path history (trail of (cx, cy) cell positions)
        self.path: list[tuple[int, int]] = [(self.origin, self.origin)]

        # Pre-computed speed estimates
        self.forward_speed = config.SPEED_CM_PER_SEC      # cm/s
        self.turn_speed = math.radians(config.TURN_DEG_PER_SEC)  # rad/s

        self._last_update = 0.0

    # ========================================================================
    # Pose update (dead reckoning)
    # ========================================================================

    def update_pose(self, command: str, dt: float):
        """Update (x_cm, y_cm, heading) based on motor command and elapsed time.

        Args:
            command: 'forward', 'backward', 'left', 'right', or 'stop'
            dt: time delta in seconds
        """
        if command == "forward":
            self.x_cm += math.cos(self.heading) * self.forward_speed * dt
            self.y_cm -= math.sin(self.heading) * self.forward_speed * dt
        elif command == "backward":
            self.x_cm -= math.cos(self.heading) * self.forward_speed * dt
            self.y_cm += math.sin(self.heading) * self.forward_speed * dt
        elif command == "left":
            self.heading += self.turn_speed * dt
        elif command == "right":
            self.heading -= self.turn_speed * dt
        # "stop": no change

        # Normalize heading to [0, 2π)
        self.heading %= 2 * math.pi

    def update_pose_vo(self, dx_cm: float, dz_cm: float, dyaw_deg: float) -> None:
        """Update pose from visual-odometry ground-plane deltas.

        Parameters
        ----------
        dx_cm : float
            Lateral displacement in camera frame (right +), cm.
        dz_cm : float
            Forward displacement in camera frame (forward +), cm.
        dyaw_deg : float
            Yaw rotation in degrees (positive = left turn, negative = right).
        """
        heading = self.heading
        dyaw_rad = math.radians(dyaw_deg)

        # Project camera-frame deltas into world frame
        self.x_cm += dz_cm * math.cos(heading) - dx_cm * math.sin(heading)
        self.y_cm += -dz_cm * math.sin(heading) - dx_cm * math.cos(heading)

        # Positive dyaw = left turn = heading increases
        self.heading += dyaw_rad
        self.heading %= 2 * math.pi

    # ========================================================================
    # Map update
    # ========================================================================

    def update_map(self, ultrasonic_cm: float, ir_data: dict[str, bool]):
        """Fuse sensor readings into the occupancy grid.

        Args:
            ultrasonic_cm: distance from HC-SR04, -1 or >200 = ignore
            ir_data: dict with keys 'left', 'middle', 'right' → bool
        """
        # Current car cell position
        cx, cy = self._world_to_cell(self.x_cm, self.y_cm)

        # Mark current cell as free
        self._set_cell(cx, cy, CELL_FREE)

        # Mark path
        self.path.append((cx, cy))

        # Ultrasonic: project obstacle along heading
        if 0 < ultrasonic_cm < self.config.ULTRASONIC_MAX_DISTANCE_CM:
            obs_x = self.x_cm + math.cos(self.heading) * ultrasonic_cm
            obs_y = self.y_cm - math.sin(self.heading) * ultrasonic_cm
            ox, oy = self._world_to_cell(obs_x, obs_y)
            self._set_cell(ox, oy, CELL_OBSTACLE)

            # Mark cells between car and obstacle as free (simplified ray)
            steps = int(ultrasonic_cm / self.resolution)
            for s in range(1, steps):
                mx = self.x_cm + math.cos(self.heading) * s * self.resolution
                my = self.y_cm - math.sin(self.heading) * s * self.resolution
                gx, gy = self._world_to_cell(mx, my)
                if (gx, gy) != (ox, oy):
                    self._set_cell(gx, gy, CELL_FREE)

        # IR: mark ground edges at car's front bumper position
        ir_triggered = any(ir_data.values())
        if ir_triggered:
            # Front bumper is ~10 cm ahead of center
            bumper_x = self.x_cm + math.cos(self.heading) * 10
            bumper_y = self.y_cm - math.sin(self.heading) * 10
            bx, by = self._world_to_cell(bumper_x, bumper_y)
            self._set_cell(bx, by, CELL_IR_EDGE)

    # ========================================================================
    # Rendering
    # ========================================================================

    def render(self) -> np.ndarray:
        """Return a BGR image of the current map for display."""
        # Color palette (BGR)
        colors = {
            CELL_UNKNOWN: (140, 140, 140),   # mid grey (bright enough for VNC)
            CELL_FREE: (230, 230, 230),      # near white
            CELL_OBSTACLE: (60, 60, 60),     # dark grey
            CELL_IR_EDGE: (50, 50, 255),     # bright red
        }

        img = np.zeros((self.size, self.size, 3), dtype=np.uint8)
        for val, color in colors.items():
            img[self.grid == val] = color

        # Draw path trail (blue)
        for px, py in self.path:
            if 0 <= px < self.size and 0 <= py < self.size:
                img[py, px] = (180, 120, 50)  # blue-ish

        # Draw car as a green triangle
        cx, cy = self._world_to_cell(self.x_cm, self.y_cm)
        self._draw_triangle(img, cx, cy, self.heading, (0, 200, 0), size=4)

        # Scale up for display
        display_size = 600
        img = cv2.resize(img, (display_size, display_size),
                         interpolation=cv2.INTER_NEAREST)

        # Draw grid lines
        cell_display = display_size / self.size
        for i in range(self.size):
            pos = int(i * cell_display)
            cv2.line(img, (pos, 0), (pos, display_size), (120, 120, 120), 1)
            cv2.line(img, (0, pos), (display_size, pos), (120, 120, 120), 1)

        return img

    # ========================================================================
    # Helpers
    # ========================================================================

    def _world_to_cell(self, x_cm: float, y_cm: float) -> tuple[int, int]:
        """Convert world coordinates (cm) to grid cell indices."""
        cx = int(self.origin + x_cm / self.resolution)
        cy = int(self.origin - y_cm / self.resolution)  # y-axis inverted for image
        return self._clamp(cx), self._clamp(cy)

    def _clamp(self, val: int) -> int:
        return max(0, min(self.size - 1, val))

    def _set_cell(self, cx: int, cy: int, value: int):
        if 0 <= cx < self.size and 0 <= cy < self.size:
            # Don't overwrite obstacles with free
            if value == CELL_FREE and self.grid[cy, cx] == CELL_OBSTACLE:
                return
            # Don't overwrite IR edges with free
            if value == CELL_FREE and self.grid[cy, cx] == CELL_IR_EDGE:
                return
            self.grid[cy, cx] = value

    @staticmethod
    def _draw_triangle(img, cx: int, cy: int, heading: float,
                       color: tuple, size: int = 5):
        """Draw a triangle representing the car's pose."""
        # Triangle pointing along heading
        tip_x = cx + math.cos(heading) * size
        tip_y = cy - math.sin(heading) * size
        left_x = cx + math.cos(heading + 2.5) * size * 0.7
        left_y = cy - math.sin(heading + 2.5) * size * 0.7
        right_x = cx + math.cos(heading - 2.5) * size * 0.7
        right_y = cy - math.sin(heading - 2.5) * size * 0.7

        pts = np.array([
            [int(tip_x), int(tip_y)],
            [int(left_x), int(left_y)],
            [int(right_x), int(right_y)],
        ], dtype=np.int32)

        drawn = cv2.fillPoly(img, [pts], color)
        if drawn is None:
            # Fallback: draw a simple dot
            cv2.circle(img, (cx, cy), size, color, -1)
