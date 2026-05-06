# Manual Drive — Freenove FNK0043B

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform: Raspberry Pi 5](https://img.shields.io/badge/platform-Raspberry%20Pi%205-red.svg)](https://www.raspberrypi.com/products/raspberry-pi-5/)
[![Hardware: Freenove FNK0043B](https://img.shields.io/badge/hardware-Freenove%20FNK0043B-orange.svg)](https://github.com/Freenove/Freenove_4WD_Smart_Car_Kit_for_Raspberry_Pi)

**Co-Contributors:** [hwu668](https://github.com/hwu668) · [DeepSeek](https://github.com/deepseek)

[English](#overview) | [中文](#概述)

---

## Table of Contents

- [Overview](#overview)
- [Hardware](#hardware)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Runtime Modes](#runtime-modes)
  - [Basic Commands](#basic-commands)
  - [Headless Keyboard Control](#headless-keyboard-control)
  - [MJPEG Camera Stream](#mjpeg-camera-stream)
  - [GUI Key Bindings](#gui-key-bindings)
  - [Full CLI Arguments](#full-cli-arguments)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Visual Odometry](#visual-odometry)
- [Safety](#safety)
- [Verified Environment](#verified-environment)
- [Development](#development)
- [License](#license)

---

## Overview

**Manual Drive** is a keyboard-controlled driving system for the **Raspberry Pi 5** and **Freenove FNK0043B** 4WD chassis, featuring real-time 2D occupancy grid mapping, optional monocular visual odometry, and a browser-based MJPEG camera stream.

> ⚠️ **Important:** This is a **dead-reckoning occupancy grid demo**, not a full SLAM system. No wheel encoders, no IMU, no loop closure. Pose drift is expected. The map is suitable for teaching, debugging, and demonstration — not for precise navigation.

### Key Features

- **WASD keyboard control** — forward, backward, left/right turning
- **Sensor fusion** — HC-SR04 ultrasonic + 3-channel IR integrated into occupancy grid
- **Dead-reckoning odometry** — pose estimated from motor commands × elapsed time
- **Visual odometry (optional)** — ORB feature-based monocular motion estimation (`--vo`)
- **Dual-window display** — camera feed + top-down occupancy grid map
- **MJPEG streaming server** — view camera in browser, bypasses VNC/X11 rendering issues
- **Headless mode** — terminal keyboard control over SSH (`--keyboard-terminal`)
- **Auto-stop** — automatic motor cut after configurable idle timeout
- **Emergency stop** — obstacle within safety threshold triggers immediate stop
- **Command mode** — execute single timed commands for CI/smoke testing

---

## 概述

**Manual Drive** 是基于 **Raspberry Pi 5 + Freenove FNK0043B** 4WD 底盘的键盘遥控驾驶系统，支持实时 2D 占据栅格建图、可选单目视觉里程计、以及基于浏览器的 MJPEG 摄像头流。

> ⚠️ **注意：** 这是**航位推算占据栅格演示项目**，并非完整 SLAM 系统。无轮速编码器、无 IMU、无闭环定位，位姿漂移是预期现象。地图适合教学、调试和演示，不应作为精确导航依据。

### 核心功能

- **WASD 键盘遥控** — 前进/后退/左转/右转
- **传感器融合** — HC-SR04 超声波 + 3 路红外数据融合进占据栅格
- **航位推算** — 基于电机命令 × 时间的位姿估计
- **视觉里程计（可选）** — 基于 ORB 特征的单目运动估计 (`--vo`)
- **双窗口显示** — 摄像头画面 + 俯视占据栅格地图
- **MJPEG 流服务器** — 浏览器查看摄像头，绕过 VNC/X11 渲染问题
- **无头模式** — SSH 终端键盘控制 (`--keyboard-terminal`)
- **自动停车** — 空闲超时后自动切断电机
- **紧急停车** — 障碍物进入安全距离内触发强制停车
- **命令模式** — 单次定时命令，适用于 CI/冒烟测试

---

## Hardware

| Component | Model | Notes |
|-----------|-------|-------|
| Controller | Raspberry Pi 5 | BCM2712, 8 GB |
| Chassis | Freenove FNK0043B | 4WD standard wheels (mecanum wheel version also supported) |
| Driver Board | Smart Car Board | PCA9685 I2C PWM driver |
| Ultrasonic | HC-SR04 | Range ~2–400 cm, GPIO 27 (Trig) / 22 (Echo) |
| Infrared | 3-channel line tracking | Front-facing downward, GPIO 14/15/23 |
| Camera | OV5647 (Pi Camera 2) | CSI interface, 640×480 @ 30 FPS |
| Display Server | labwc (Wayland) + XWayland | Default on Raspberry Pi OS |

### Hardware (中文)

| 组件 | 型号 | 备注 |
|------|------|------|
| 主控 | Raspberry Pi 5 | BCM2712，8 GB |
| 底盘 | Freenove FNK0043B | 4WD 标准车轮（也支持麦克纳姆轮版本） |
| 驱动板 | Smart Car Board | PCA9685 I2C PWM 驱动 |
| 超声波 | HC-SR04 | 量程 ~2–400 cm，GPIO 27 (Trig) / 22 (Echo) |
| 红外 | 3 路循线模块 | 前置向下，GPIO 14/15/23 |
| 摄像头 | OV5647 (Pi Camera 2) | CSI 接口，640×480 @ 30 FPS |
| 显示服务 | labwc (Wayland) + XWayland | Raspberry Pi OS 默认 |

---

## Quick Start

```bash
git clone https://github.com/hwu668/manual_drive.git
cd manual_drive

# Cross-platform runtime dependencies
pip install -r requirements.txt

# Raspberry Pi hardware dependencies (Pi only)
pip install -r requirements-rpi.txt

# Development tools (optional)
pip install -r requirements-dev.txt
```

## 快速开始

```bash
git clone https://github.com/hwu668/manual_drive.git
cd manual_drive

# 跨平台运行时依赖
pip install -r requirements.txt

# 树莓派硬件依赖
pip install -r requirements-rpi.txt

# 开发工具（可选）
pip install -r requirements-dev.txt
```

---

## Usage

### Runtime Modes

| Mode | Flag | Behavior |
|------|------|----------|
| Auto | `--mode auto` (default) | Try real hardware first, fall back to Mock |
| Mock | `--mode mock` | Force emulated hardware — suitable for PC debugging, CI |
| Hardware | `--mode hardware` | Require real hardware — exit on any init failure |

### 运行模式

| 模式 | 参数 | 行为 |
|------|------|------|
| 自动 | `--mode auto`（默认） | 优先尝试真实硬件，失败后降级 Mock |
| 模拟 | `--mode mock` | 强制模拟硬件 — 适用于 PC 调试、CI |
| 硬件 | `--mode hardware` | 强制真实硬件 — 初始化失败则退出 |

### Basic Commands

```bash
# Normal mode — camera + map dual window
python main.py

# Mock mode for PC debugging
python main.py --mode mock --no-camera --max-runtime 3

# Headless + terminal keyboard (SSH)
python main.py --mode hardware --no-display --keyboard-terminal

# Single command smoke test
python main.py --mode hardware --command forward --duration 0.5

# Low-speed safety test
python main.py --mode hardware --duty 1200 --max-runtime 30

# Enable visual odometry
python main.py --vo

# Pure visual odometry (replace dead reckoning)
python main.py --vo --vo-no-dead-reckoning

# MJPEG camera stream — view at http://localhost:8080
python main.py --keyboard-terminal

# Verbose logging
python main.py --log-level DEBUG
```

### 基本命令

```bash
# 正常模式 — 摄像头 + 地图双窗口
python main.py

# 模拟模式用于 PC 调试
python main.py --mode mock --no-camera --max-runtime 3

# 无头 + 终端键盘控制（SSH）
python main.py --mode hardware --no-display --keyboard-terminal

# 单命令冒烟测试
python main.py --mode hardware --command forward --duration 0.5

# 低速安全测试
python main.py --mode hardware --duty 1200 --max-runtime 30

# 启用视觉里程计
python main.py --vo

# 纯视觉里程计（替换航位推算）
python main.py --vo --vo-no-dead-reckoning

# MJPEG 摄像头流 — 浏览器 http://localhost:8080 查看
python main.py --keyboard-terminal

# 详细日志
python main.py --log-level DEBUG
```

### Headless Keyboard Control

```bash
python main.py --mode hardware --keyboard-terminal
```

| Key | Action |
|-----|--------|
| `w` | Forward |
| `s` | Backward |
| `a` | Turn Left |
| `d` | Turn Right |
| `Space` | Emergency Stop |
| `q` | Quit |

> Requires Linux/macOS (termios). The program auto-detects SSH sessions and headless environments, enabling terminal keyboard mode automatically.

### 无头键盘控制

```bash
python main.py --mode hardware --keyboard-terminal
```

| 按键 | 功能 |
|------|------|
| `w` | 前进 |
| `s` | 后退 |
| `a` | 左转 |
| `d` | 右转 |
| `空格` | 紧急停车 |
| `q` | 退出 |

> 需要 Linux/macOS（termios）。程序自动检测 SSH 会话和无显示器环境，自动启用终端键盘模式。

### MJPEG Camera Stream

The program starts an MJPEG streaming server at `http://localhost:8080` on launch. **Recommended for VNC / remote desktop** — OpenCV Qt5 on XWayland + wayvnc has known rendering issues.

| URL | Description |
|-----|-------------|
| `http://localhost:8080` | Live stream + status page |
| `http://localhost:8080/stream` | Raw MJPEG stream |
| `http://localhost:8080/snapshot` | Single frame snapshot |

Disable with `--stream-port 0`. Custom port: `--stream-port 9090`.

### MJPEG 摄像头流

程序启动后自动在 `http://localhost:8080` 启动 MJPEG 流服务器。**推荐在 VNC / 远程桌面环境下使用** — OpenCV Qt5 在 XWayland + wayvnc 下有已知渲染问题。

| URL | 说明 |
|-----|------|
| `http://localhost:8080` | 实时流 + 状态页面 |
| `http://localhost:8080/stream` | 纯 MJPEG 流 |
| `http://localhost:8080/snapshot` | 单帧快照 |

禁用: `--stream-port 0`。自定义端口: `--stream-port 9090`。

### GUI Key Bindings

When display windows are enabled:

| Key | Action |
|-----|--------|
| `W` | Forward |
| `S` | Backward |
| `A` | Turn Left |
| `D` | Turn Right |
| `Space` | Emergency Stop |
| `R` | Reset Map |
| `Q` | Quit |

### GUI 窗口键位

显示窗口启用时：

| 按键 | 功能 |
|------|------|
| `W` | 前进 |
| `S` | 后退 |
| `A` | 左转 |
| `D` | 右转 |
| `空格` | 紧急停车 |
| `R` | 重置地图 |
| `Q` | 退出 |

### Full CLI Arguments

```
--mode auto|mock|hardware    Runtime mode (default: auto)
--no-display                 Disable OpenCV windows
--keyboard-terminal          Terminal keyboard mode (SSH friendly)
--no-terminal-keyboard       Disable terminal keyboard auto-detection
--stream-port PORT           MJPEG stream HTTP port (default: 8080, 0 = disable)
--command stop|forward|...   Execute a single command and exit
--duration SECONDS           Command duration (max 1.0s)
--no-camera                  Skip camera initialization
--require-camera             Exit if camera init fails
--duty 0-4096                Override motor duty cycle
--max-runtime SECONDS        Auto-stop and exit after N seconds
--vo                         Enable visual odometry (ORB feature matching)
--vo-no-dead-reckoning       Pure VO mode (replace dead reckoning)
--log-level DEBUG|INFO|...   Log level
```

### 全部命令行参数

```
--mode auto|mock|hardware    运行模式（默认 auto）
--no-display                 不打开 OpenCV 窗口
--keyboard-terminal          终端键盘模式（SSH 友好）
--no-terminal-keyboard       禁用终端键盘自动检测
--stream-port PORT           MJPEG 流 HTTP 端口（默认 8080，0=禁用）
--command stop|forward|...   执行单条命令后退出
--duration SECONDS           命令持续时间（最大 1.0s）
--no-camera                  跳过摄像头初始化
--require-camera             摄像头失败则退出
--duty 0-4096                覆盖电机 duty 值
--max-runtime SECONDS        最大运行时间后自动退出
--vo                         启用视觉里程计 (ORB 特征匹配)
--vo-no-dead-reckoning       纯 VO 模式（替换航位推算）
--log-level DEBUG|INFO|...   日志级别
```

---

## Architecture

```
┌─────────────────┐    ┌─────────────────┐
│  Keyboard Input  │    │  Camera (CSI)   │
│  terminal / GUI  │    │  PiCamera2/USB  │
└────────┬─────────┘    └────────┬─────────┘
         │ command               │ frame
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  motor_control   │    │     camera      │    │    sensors      │
│  PCA9685 PWM     │    │  capture/bright │    │  HC-SR04 + IR   │
└────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                         main.py                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────────────┐  │
│  │   mapping   │  │ visual_odo  │  │    mjpeg_server         │  │
│  │ dead-reckon │  │ metry (opt) │  │  HTTP :8080 stream      │  │
│  │ + grid map  │  │ ORB + R,t   │  │                         │  │
│  └──────┬──────┘  └──────┬──────┘  └────────────┬────────────┘  │
│         │                │                       │               │
│         ▼                ▼                       ▼               │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                     Display / Output                     │    │
│  │   OpenCV windows (camera + map)  │  MJPEG browser stream │    │
│  └──────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Code Structure

```
manual_drive/
├── main.py                # Entry point — loop, display, keyboard dispatch
├── config.py              # All tunable parameters
├── motor_control.py       # PCA9685 motor driver (mock fallback built-in)
├── sensors.py             # HC-SR04 ultrasonic + 3-channel IR
├── camera.py              # PiCamera2 CSI / USB camera manager
├── mapping.py             # Dead-reckoning odometry + 2D occupancy grid
├── visual_odometry.py     # Monocular visual odometry (ORB)
├── mjpeg_server.py        # Lightweight MJPEG HTTP streaming server
├── terminal_keyboard.py   # Non-blocking terminal keyboard (SSH headless)
├── requirements.txt       # Cross-platform runtime dependencies
├── requirements-rpi.txt   # Raspberry Pi hardware dependencies
├── requirements-dev.txt   # Development tools (pytest, ruff)
├── pyproject.toml         # Ruff configuration
└── tests/                 # Unit tests
```

### 代码结构

```
manual_drive/
├── main.py                # 主入口 — 循环、显示、键盘调度
├── config.py              # 所有可调参数
├── motor_control.py       # PCA9685 电机驱动（内置 mock 回退）
├── sensors.py             # HC-SR04 超声波 + 3 路红外
├── camera.py              # PiCamera2 CSI / USB 摄像头管理
├── mapping.py             # 航位推算 + 2D 占据栅格地图
├── visual_odometry.py     # 单目视觉里程计 (ORB)
├── mjpeg_server.py        # 轻量 MJPEG HTTP 流服务器
├── terminal_keyboard.py   # 非阻塞终端键盘（SSH 无头控制）
├── requirements.txt       # 跨平台运行时依赖
├── requirements-rpi.txt   # 树莓派硬件依赖
├── requirements-dev.txt   # 开发工具 (pytest, ruff)
├── pyproject.toml         # Ruff 配置
└── tests/                 # 单元测试
```

---

## Configuration

All tunable parameters are centralized in `config.py`.

| Category | Key Parameters |
|----------|---------------|
| Motor | `MOTOR_LEFT_FRONT_CH`, `MOTOR_LEFT_REAR_CH`, `MOTOR_RIGHT_FRONT_CH`, `MOTOR_RIGHT_REAR_CH`, `MOTOR_DUTY_FORWARD`, `MOTOR_DUTY_TURN`, `MOTOR_INVERT` |
| Ultrasonic | `ULTRASONIC_TRIG_PIN` (27), `ULTRASONIC_ECHO_PIN` (22), `ULTRASONIC_TIMEOUT_US`, `ULTRASONIC_MAX_DISTANCE_CM` |
| Infrared | `IR_LEFT_PIN` (14), `IR_MIDDLE_PIN` (15), `IR_RIGHT_PIN` (23) |
| Camera | `CAMERA_WIDTH`, `CAMERA_HEIGHT`, `CAMERA_FPS`, `CAMERA_USE_PICAMERA2`, `CAMERA_EXPOSURE_VALUE`, `CAMERA_BRIGHTNESS_BOOST` |
| Mapping | `MAP_RESOLUTION_CM`, `MAP_SIZE_CELLS`, `MAP_ORIGIN_CELL` |
| Dead Reckoning | `SPEED_CM_PER_SEC`, `TURN_DEG_PER_SEC` |
| Control | `AUTO_STOP_TIMEOUT_SEC`, `MAIN_LOOP_DELAY` |
| Safety | `SAFE_STOP_DISTANCE_CM` |
| Visual Odometry | `VO_FX`, `VO_FY`, `VO_CX`, `VO_CY`, `VO_ORB_FEATURES`, `VO_MIN_MATCHES`, `VO_CONFIDENCE_THRESHOLD`, `VO_SCALE` |

### Low-Light / VNC Camera Tuning

| Parameter | Default | Description |
|-----------|---------|-------------|
| `CAMERA_EXPOSURE_VALUE` | 4.0 | EV compensation (-8 to +8). Higher values brighten dark scenes. |
| `CAMERA_BRIGHTNESS_BOOST` | 2.5 | Software brightness multiplier (1.0 = no change). Applied post-capture. |

### 低光 / VNC 环境摄像头调节

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `CAMERA_EXPOSURE_VALUE` | 4.0 | EV 补偿 (-8 ~ +8)。值越大画面越亮。 |
| `CAMERA_BRIGHTNESS_BOOST` | 2.5 | 软件亮度增强倍数 (1.0 = 不变)。在捕获后应用。 |

---

## Visual Odometry

Monocular visual odometry using ORB features to estimate inter-frame motion from consecutive camera frames.

基于 ORB 特征的单目视觉里程计，从连续摄像头帧中估计帧间运动。

### Pipeline

1. **Feature extraction** — detect up to `VO_ORB_FEATURES` ORB keypoints per frame
2. **Matching** — brute-force Hamming distance between consecutive frames
3. **Pose recovery** — RANSAC essential matrix → `cv2.recoverPose` → rotation `R`, translation `t`
4. **Scale calibration** — `t` is unit-norm; auto-calibrated using dead-reckoning speed during forward motion
5. **World projection** — camera-frame motion transformed to world coordinates

### 流水线

1. **特征提取** — 每帧提取最多 `VO_ORB_FEATURES` 个 ORB 关键点
2. **特征匹配** — 连续帧间暴力 Hamming 距离匹配
3. **位姿恢复** — RANSAC 本质矩阵 → `cv2.recoverPose` → 旋转 `R`、平移 `t`
4. **尺度校准** — `t` 为单位向量；前进时使用航位推算速度自动校准
5. **世界投影** — 相机坐标系运动变换到世界坐标系

### Confidence & Fallback / 置信度与回退

- Inlier ratio < `VO_CONFIDENCE_THRESHOLD` (default 0.4) → fall back to dead reckoning
- Pure VO mode (`--vo-no-dead-reckoning`): low-confidence frames are skipped entirely

- 内点比例 < `VO_CONFIDENCE_THRESHOLD`（默认 0.4）→ 回退到航位推算
- 纯 VO 模式（`--vo-no-dead-reckoning`）：低置信度帧直接跳过

### HUD Status Line / HUD 状态行

```
VO:0.85 in:200 dZ:+2.3 Y:-1.2° s:1.52
```

| Field | Meaning |
|-------|---------|
| `VO:0.85` | Confidence (0–1) |
| `in:200` | RANSAC inlier count |
| `dZ:+2.3` | Forward displacement (cm) |
| `Y:-1.2°` | Yaw delta (degrees) |
| `s:1.52` | Current scale factor |

| 字段 | 含义 |
|------|------|
| `VO:0.85` | 置信度 (0–1) |
| `in:200` | RANSAC 内点数 |
| `dZ:+2.3` | 前向位移 (cm) |
| `Y:-1.2°` | 偏航角变化 (度) |
| `s:1.52` | 当前尺度因子 |

---

## Safety

### Before First Real Test / 首次实车测试前

1. **Lift the car** — ensure wheels are off the ground / **架空小车** — 确保轮子离地
2. **Use low duty** — `--duty 1200` or lower / **使用低 duty** — `--duty 1200` 或更低
3. **Test `stop` first** — verify motors cut immediately / **先测试 `stop`** — 验证电机立即停止
4. **Short forward test** — incremental duration / **短时间前进测试** — 逐步增加时长

```bash
# Step 1: Verify stop
python main.py --mode hardware --command stop

# Step 2: Short forward pulse
python main.py --mode hardware --command forward --duration 0.3

# Step 3: Incremental increase
python main.py --mode hardware --command forward --duration 0.5

# Step 4: Full test with safety limits
python main.py --mode hardware --duty 1200 --max-runtime 30
```

### Safety Features / 安全功能

| Feature | Trigger | Behavior |
|---------|---------|----------|
| Obstacle Stop | Object < `SAFE_STOP_DISTANCE_CM` (15 cm) | Immediate motor stop |
| Auto-Stop | No key press > `AUTO_STOP_TIMEOUT_SEC` (0.4s) | Motors cut automatically |
| Max Runtime | `--max-runtime` reached | Graceful shutdown |
| Ctrl+C | SIGINT received | Stop motors → cleanup → exit |

| 功能 | 触发条件 | 行为 |
|------|----------|------|
| 障碍物停车 | 物体 < `SAFE_STOP_DISTANCE_CM` (15 cm) | 立即停止电机 |
| 自动停车 | 无按键 > `AUTO_STOP_TIMEOUT_SEC` (0.4s) | 自动切断电机 |
| 最长运行 | `--max-runtime` 到达 | 优雅关闭 |
| Ctrl+C | 收到 SIGINT | 停车 → 清理 → 退出 |

---

## Verified Environment

| Item | Status |
|------|--------|
| Raspberry Pi | Raspberry Pi 5 (BCM2712) |
| OS | Raspberry Pi OS (Debian 12 "Bookworm") |
| Kernel | Linux 6.6 |
| Python | 3.13 |
| Display Server | labwc (Wayland) + XWayland |
| Remote Desktop | Raspberry Pi Connect (wayvnc) |
| Camera | OV5647 (Pi Camera 2) via CSI — **confirmed working** |
| Camera Library | libcamera v0.6.0 + PiCamera2 |
| OpenCV | Qt5 backend, XCB platform plugin |
| Chassis | Freenove FNK0043B (standard wheels) |
| Driver | PCA9685 I2C — **confirmed working** |
| Ultrasonic | HC-SR04 — **confirmed working** |
| IR Sensors | 3-channel line tracking — **confirmed working** |
| Terminal Keyboard | termios — **confirmed working** |
| MJPEG Stream | HTTP server on port 8080 — **confirmed working** |
| VNC Camera Display | ⚠️ Known issue — OpenCV Qt5 on XWayland + wayvnc renders black. Use MJPEG stream as workaround. |

### 已验证环境

| 项目 | 状态 |
|------|------|
| 树莓派 | Raspberry Pi 5 (BCM2712) |
| 操作系统 | Raspberry Pi OS (Debian 12 "Bookworm") |
| 内核 | Linux 6.6 |
| Python | 3.13 |
| 显示服务 | labwc (Wayland) + XWayland |
| 远程桌面 | Raspberry Pi Connect (wayvnc) |
| 摄像头 | OV5647 (Pi Camera 2) via CSI — **已验证可用** |
| 摄像头库 | libcamera v0.6.0 + PiCamera2 |
| OpenCV | Qt5 后端，XCB 平台插件 |
| 底盘 | Freenove FNK0043B（标准车轮） |
| 驱动 | PCA9685 I2C — **已验证可用** |
| 超声波 | HC-SR04 — **已验证可用** |
| 红外传感器 | 3 路循线 — **已验证可用** |
| 终端键盘 | termios — **已验证可用** |
| MJPEG 流 | HTTP 服务器端口 8080 — **已验证可用** |
| VNC 摄像头显示 | ⚠️ 已知问题 — OpenCV Qt5 在 XWayland + wayvnc 上渲染黑屏。替代方案：使用 MJPEG 流。 |

---

## Development

```bash
# Syntax check
python -m py_compile main.py config.py motor_control.py sensors.py camera.py mapping.py visual_odometry.py terminal_keyboard.py mjpeg_server.py

# Lint
ruff check .

# Format
ruff format .

# Run tests
pytest
```

### Development Dependencies

```bash
pip install -r requirements-dev.txt
```

---

## License

MIT — see [LICENSE](LICENSE.txt).

---
