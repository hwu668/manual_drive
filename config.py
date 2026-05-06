"""
config.py — Manual Drive project configuration.

Target: Raspberry Pi 5 + Freenove FNK0043B (4WD standard wheels)
       Smart Car Board (PCA9685 I2C motor driver).
"""

# ============================================================================
# Product identity
# ============================================================================
PRODUCT_NAME = "Freenove FNK0043B Manual Drive"
PRODUCT_DESC = "4WD Standard Wheel Manual Drive with Real-Time Mapping"

# ============================================================================
# PCA9685 motor channels
# ============================================================================
MOTOR_LEFT_FRONT_CH = 0
MOTOR_LEFT_REAR_CH = 1
MOTOR_RIGHT_FRONT_CH = 2
MOTOR_RIGHT_REAR_CH = 3

# ============================================================================
# Motor speed
# ============================================================================
MOTOR_DUTY_MAX = 4096
MOTOR_DUTY_FORWARD = 2000   # base forward speed
MOTOR_DUTY_TURN = 2000      # turning speed
MOTOR_DUTY_SLOW = 1200      # slow / precise
MOTOR_INVERT = True          # invert all motor directions (swap fwd↔back, left↔right)

# ============================================================================
# Ultrasonic (HC-SR04)
# ============================================================================
ULTRASONIC_TRIG_PIN = 27          # Freenove board: TRIG = GPIO 27
ULTRASONIC_ECHO_PIN = 22          # Freenove board: ECHO = GPIO 22
ULTRASONIC_TIMEOUT_US = 40000
ULTRASONIC_MAX_DISTANCE_CM = 200

# ============================================================================
# Infrared line tracking (3-channel, downward-facing at front bumper)
# ============================================================================
IR_LEFT_PIN = 14                  # Freenove board: left IR = GPIO 14
IR_MIDDLE_PIN = 15                # Freenove board: middle IR = GPIO 15
IR_RIGHT_PIN = 23                 # Freenove board: right IR = GPIO 23

# ============================================================================
# Camera
# ============================================================================
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30
CAMERA_USE_PICAMERA2 = True   # True = CSI camera; False = USB
CAMERA_FLIP_HORIZONTAL = False
CAMERA_FLIP_VERTICAL = False
CAMERA_EXPOSURE_VALUE = 4.0   # EV compensation for low-light (0=auto, range -8 to +8)
CAMERA_BRIGHTNESS_BOOST = 2.5 # Software brightness multiplier (1.0 = no change)

# ============================================================================
# Mapping
# ============================================================================
MAP_RESOLUTION_CM = 5.0       # cm per grid cell
MAP_SIZE_CELLS = 200           # 200×200 grid (10 m × 10 m)
MAP_ORIGIN_CELL = 100          # car starts at (100, 100) in grid coords
MAP_UPDATE_INTERVAL = 0.1      # seconds between map updates

# ============================================================================
# Dead reckoning
# ============================================================================
SPEED_CM_PER_SEC = 30.0        # estimated forward speed at MOTOR_DUTY_FORWARD
TURN_DEG_PER_SEC = 90.0        # estimated turn rate at MOTOR_DUTY_TURN

# ============================================================================
# Control
# ============================================================================
AUTO_STOP_FRAMES = 5              # stop after N frames with no movement key
AUTO_STOP_TIMEOUT_SEC = 0.4       # time-based auto-stop (replaces frame count)
MAIN_LOOP_DELAY = 0.05            # ~20 FPS control loop

# ============================================================================
# Safety
# ============================================================================
SAFE_STOP_DISTANCE_CM = 15.0      # emergency stop when obstacle closer than this
MAX_RUNTIME_SEC = 0               # max runtime in seconds (0 = unlimited)

# ============================================================================
# Visual Odometry (ORB-based monocular)
# ============================================================================
VO_FX = 530.0                 # camera focal length X (pixels) at 640×480
VO_FY = 530.0                 # camera focal length Y (pixels)
VO_CX = 320.0                 # principal point X
VO_CY = 240.0                 # principal point Y
VO_ORB_FEATURES = 1000        # max ORB features per frame
VO_MIN_MATCHES = 30           # minimum inliers for valid motion estimate
VO_FRAME_SKIP = 0             # process every N+1 frames (0 = every frame)
VO_SCALE = 1.0                # initial translation scale (cm per unit vector)
VO_CONFIDENCE_THRESHOLD = 0.4 # minimum inlier ratio to accept pose

# ============================================================================
# Display
# ============================================================================
WINDOW_CAMERA = "Manual Drive — Camera"
WINDOW_MAP = "Manual Drive — 2D Map"
