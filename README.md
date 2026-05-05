# Manual Drive — Freenove FNK0043B 手动驾驶 + 实时建图

**Co-Contributors:** [hwu668](https://github.com/hwu668) · [DeepSeek](https://github.com/deepseek)

[中文](#中文) | [English](#english)

---

## 项目定位 | Project Positioning

本项目是 Raspberry Pi 5 + Freenove FNK0043B 小车的手动驾驶与简单 2D 地图演示项目。地图功能基于电机命令、时间估算、超声波和红外传感器进行简单更新，属于 **dead-reckoning occupancy grid demo**，不是完整 SLAM。

由于没有轮速编码器、IMU 或闭环定位，位姿漂移是预期现象。地图适合教学、调试和演示，不应作为精确导航依据。

> This is a manual driving + dead-reckoning 2D map demo, **not a full SLAM system**. No wheel encoders, no IMU, no loop closure. Pose drift is expected.

---

## 中文

### 简介

基于 **树莓派 5 + Freenove FNK0043B (4WD 普通车轮)** 的键盘遥控驾驶系统，支持**实时 2D 占据栅格建图**。

- 键盘 WASD 控制小车前进/后退/左转/右转
- HC-SR04 超声波 + 3 路红外传感器融合进栅格地图
- 航位推算 (dead-reckoning) 实时估计小车位姿
- 双窗口显示：摄像头画面 + 俯视栅格地图
- 松开按键超过指定时间后自动停车
- 支持无头模式、终端键盘控制、命令式控制
- 强制停车：前方障碍物距离小于阈值时自动停止

### 硬件要求

| 组件 | 型号 |
|------|------|
| 主控 | Raspberry Pi 5 |
| 小车底盘 | Freenove FNK0043B (4WD 普通车轮) |
| 驱动板 | Smart Car Board (PCA9685 I2C) |
| 超声波 | HC-SR04 |
| 红外 | 3 通道循线模块 (前置向下) |
| 摄像头 | Pi Camera 2 (CSI) 或 USB 摄像头 |

### 安装

```bash
git clone https://github.com/hwu668/manual_drive.git
cd manual_drive

# 跨平台运行时依赖
pip install -r requirements.txt

# 树莓派硬件依赖（仅在 Pi 上需要）
pip install -r requirements-rpi.txt

# 开发工具（lint、测试）
pip install -r requirements-dev.txt
```

### 运行模式

支持三种运行模式：

| 模式 | 说明 |
|------|------|
| `--mode auto` | 默认。优先尝试真实硬件，失败后降级 Mock。 |
| `--mode mock` | 强制 Mock 模式，用于普通 PC 调试。 |
| `--mode hardware` | 强制硬件模式。缺少硬件库或初始化失败时直接退出。 |

### 使用

```bash
# 正常模式（摄像头 + 地图双窗口）
python main.py

# Mock 模式（普通 PC 调试，跳过摄像头）
python main.py --mode mock --no-camera --max-runtime 3

# 无头模式 + 终端键盘控制（SSH 可用）
python main.py --mode hardware --no-display --keyboard-terminal

# 命令式控制（SSH smoke test）
python main.py --mode hardware --command forward --duration 0.5
python main.py --mode mock --command stop

# 低速安全测试
python main.py --mode hardware --duty 1200 --max-runtime 30

# 详细日志
python main.py --log-level DEBUG
```

### Headless 键盘控制

```bash
python main.py --mode hardware --no-display --keyboard-terminal
```

| 按键 | 功能 |
|------|------|
| `w` | 前进 |
| `s` | 后退 |
| `a` | 左转 |
| `d` | 右转 |
| `空格` | 立即停车 |
| `q` | 退出 |

仅支持 Linux/macOS（termios）。

### GUI 模式键位

| 按键 | 功能 |
|------|------|
| `W` | 前进 |
| `S` | 后退 |
| `A` | 左转 |
| `D` | 右转 |
| `空格` | 立即停车 |
| `R` | 重置地图 |
| `Q` | 退出 |

### 命令行参数

```
--mode auto|mock|hardware    运行模式（默认 auto）
--no-display                 不打开 OpenCV 窗口
--keyboard-terminal          终端键盘模式（SSH 友好）
--command stop|forward|...   执行单条命令后退出
--duration SECONDS           命令持续时间（最大 1.0 秒）
--no-camera                  跳过摄像头初始化
--require-camera             摄像头失败则退出
--duty 0-4096                覆盖电机 duty 值
--max-runtime SECONDS        最大运行时间后自动退出
--log-level DEBUG|INFO|...   日志级别
```

### 实车安全建议

首次实车测试建议：
1. 把小车架空，确保轮子离地
2. 使用低 duty / speed
3. 先测试 `stop`
4. 再测试短时间前进

```bash
python main.py --mode hardware --command forward --duration 0.5
```

确认 Ctrl+C 后会停车。确认超声波近距离停车逻辑有效。确认 `q` 退出后会停车。

### 项目结构

```
manual_drive/
├── main.py                # 主程序入口
├── config.py              # 所有参数配置
├── motor_control.py       # PCA9685 电机驱动 (Mock 模式)
├── sensors.py             # HC-SR04 超声波 + 3 通道红外
├── camera.py              # PiCamera2 / USB 摄像头管理
├── mapping.py             # 航位推算 + 2D 占据栅格地图
├── terminal_keyboard.py   # 终端键盘输入 (SSH 无头控制)
├── requirements.txt       # 跨平台运行时依赖
├── requirements-rpi.txt   # 树莓派硬件依赖
├── requirements-dev.txt   # 开发工具 (pytest, ruff)
├── pyproject.toml         # Ruff 配置
└── tests/                 # 测试
```

### 已验证环境

| 项目 | 版本 / 状态 |
|---|---|
| Raspberry Pi | Raspberry Pi 5 |
| OS | TODO |
| Python | TODO |
| Camera | TODO |
| Freenove Kit | FNK0043B |
| Freenove library | TODO |
| I2C | TODO |
| SPI | TODO |
| SSH headless control | TODO |

### 实车验证清单

- [ ] 程序可以启动
- [ ] Mock 模式可以运行
- [ ] Hardware 模式可以识别硬件库
- [ ] 电机 stop 正常
- [ ] 小车可短时间前进
- [ ] 小车可短时间后退
- [ ] 小车可左转
- [ ] 小车可右转
- [ ] Ctrl+C 后小车停止
- [ ] q 退出后小车停止
- [ ] 空格急停有效
- [ ] 超声波距离读数正常
- [ ] 近距离障碍物触发强制停车
- [ ] 红外传感器读数正常
- [ ] 摄像头可以打开
- [ ] no-camera 模式可以运行
- [ ] no-display 模式行为符合 README 描述
- [ ] 地图窗口可以显示
- [ ] 无头模式日志正常

### 更多文档

- [Headless control](docs/headless-control.md)
- [Hardware checklist](docs/hardware-checklist.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Mapping limitations](docs/mapping-limitations.md)

---

## English

### Overview

A keyboard-controlled driving system for **Raspberry Pi 5 + Freenove FNK0043B (4WD standard wheels)** with **real-time 2D occupancy grid mapping**.

- WASD keyboard control: forward, backward, turn left/right
- HC-SR04 ultrasonic + 3-channel IR sensor fusion into occupancy grid
- Dead-reckoning odometry for real-time pose estimation
- Dual-window display: camera feed + top-down grid map
- Auto-stop after a configurable timeout when no key is pressed
- Headless, terminal keyboard, and command modes
- Emergency stop when an obstacle is closer than the safety threshold

### Hardware

| Component | Model |
|-----------|-------|
| Controller | Raspberry Pi 5 |
| Chassis | Freenove FNK0043B (4WD standard wheels) |
| Driver Board | Smart Car Board (PCA9685 I2C) |
| Ultrasonic | HC-SR04 |
| Infrared | 3-channel line tracking (front-facing, downward) |
| Camera | Pi Camera 2 (CSI) or USB camera |

### Installation

```bash
git clone https://github.com/hwu668/manual_drive.git
cd manual_drive

# Cross-platform runtime dependencies
pip install -r requirements.txt

# Raspberry Pi hardware dependencies (Pi only)
pip install -r requirements-rpi.txt

# Development tools (linting, testing)
pip install -r requirements-dev.txt
```

### Runtime Modes

Three modes are supported:

| Mode | Description |
|------|-------------|
| `--mode auto` | Default. Try real hardware first, fall back to mock. |
| `--mode mock` | Force emulated hardware for PC debugging. |
| `--mode hardware` | Require real hardware. Exit on any failure. |

### Usage

```bash
# Normal mode (camera + map dual window)
python main.py

# Mock mode (PC debugging, skip camera)
python main.py --mode mock --no-camera --max-runtime 3

# Headless + terminal keyboard (SSH)
python main.py --mode hardware --no-display --keyboard-terminal

# Command mode (SSH smoke test)
python main.py --mode hardware --command forward --duration 0.5
python main.py --mode mock --command stop

# Low-speed safety test
python main.py --mode hardware --duty 1200 --max-runtime 30

# Verbose logging
python main.py --log-level DEBUG
```

### Headless Keyboard Control

```bash
python main.py --mode hardware --no-display --keyboard-terminal
```

| Key | Action |
|-----|--------|
| `w` | Forward |
| `s` | Backward |
| `a` | Turn Left |
| `d` | Turn Right |
| `Space` | Emergency Stop |
| `q` | Quit |

Linux/macOS only (termios).

### GUI Key Bindings

| Key | Action |
|-----|--------|
| `W` | Forward |
| `S` | Backward |
| `A` | Turn Left |
| `D` | Turn Right |
| `Space` | Emergency Stop |
| `R` | Reset Map |
| `Q` | Quit |

### CLI Arguments

```
--mode auto|mock|hardware    Runtime mode (default: auto)
--no-display                 Disable OpenCV display windows
--keyboard-terminal          Terminal keyboard mode (SSH friendly)
--command stop|forward|...   Execute a single command and exit
--duration SECONDS           Command duration (max 1.0s)
--no-camera                  Skip camera initialization
--require-camera             Exit if camera init fails
--duty 0-4096                Override motor duty cycle
--max-runtime SECONDS        Auto-stop and exit after N seconds
--log-level DEBUG|INFO|...   Log level
```

### Real-Car Safety

Before the first real test:
1. Lift the car so wheels are off the ground
2. Use low duty / speed
3. Test `stop` first
4. Then test short forward movements

```bash
python main.py --mode hardware --command forward --duration 0.5
```

Verify Ctrl+C stops the car. Verify ultrasonic obstacle stop works. Verify `q` exit stops the car.

### Project Structure

```
manual_drive/
├── main.py                # Entry point
├── config.py              # All configuration parameters
├── motor_control.py       # PCA9685 motor driver (Mock supported)
├── sensors.py             # HC-SR04 ultrasonic + 3-channel IR
├── camera.py              # PiCamera2 / USB camera manager
├── mapping.py             # Dead-reckoning + 2D occupancy grid
├── terminal_keyboard.py   # Terminal keyboard input (SSH headless)
├── requirements.txt       # Cross-platform runtime deps
├── requirements-rpi.txt   # Raspberry Pi hardware deps
├── requirements-dev.txt   # Dev tools (pytest, ruff)
├── pyproject.toml         # Ruff config
└── tests/                 # Test suite
```

### Verified Environment

| Item | Version / Status |
|---|---|
| Raspberry Pi | Raspberry Pi 5 |
| OS | TODO |
| Python | TODO |
| Camera | TODO |
| Freenove Kit | FNK0043B |
| Freenove library | TODO |
| I2C | TODO |
| SPI | TODO |
| SSH headless control | TODO |

### Verification Checklist

- [ ] Program starts
- [ ] Mock mode runs
- [ ] Hardware mode detects libraries
- [ ] Motor stop works
- [ ] Short forward works
- [ ] Short backward works
- [ ] Left turn works
- [ ] Right turn works
- [ ] Ctrl+C stops car
- [ ] q exit stops car
- [ ] Space emergency stop works
- [ ] Ultrasonic readings valid
- [ ] Close obstacle triggers safety stop
- [ ] IR sensor readings valid
- [ ] Camera opens
- [ ] no-camera mode works
- [ ] no-display behavior matches README
- [ ] Map window displays
- [ ] Headless logs correct

### More Documentation

- [Headless control](docs/headless-control.md)
- [Hardware checklist](docs/hardware-checklist.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Mapping limitations](docs/mapping-limitations.md)

---

## Development Checks

```bash
# Syntax check
python -m py_compile main.py config.py motor_control.py sensors.py camera.py mapping.py terminal_keyboard.py

# Lint
ruff check .

# Format
ruff format .

# Tests
pytest
```

Install dev dependencies:

```bash
pip install -r requirements-dev.txt
```
