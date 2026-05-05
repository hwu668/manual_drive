# Manual Drive — Freenove FNK0043B 手动驾驶 + 实时建图

**Co-Contributors:** [hwu668](https://github.com/hwu668) · [DeepSeek](https://github.com/deepseek)

[中文](#中文) | [English](#english)

---

## 中文

### 简介

基于 **树莓派 5 + Freenove FNK0043B (4WD 普通车轮)** 的键盘遥控驾驶系统，支持**实时 2D 占据栅格建图**。

- 键盘 WASD 控制小车前进/后退/左转/右转
- HC-SR04 超声波 + 3 路红外传感器融合进栅格地图
- 航位推算 (dead-reckoning) 实时估计小车位姿
- 双窗口显示：摄像头画面 + 俯视栅格地图
- 自动停车：松开按键 N 帧后自动停止
- 无头模式支持 SSH 远程运行

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
# 克隆仓库
git clone https://github.com/hwu668/manual_drive.git
cd manual_drive

# 安装依赖
pip install -r requirements.txt

# (可选) 树莓派上安装 RPi.GPIO
sudo apt install python3-rpi.gpio
```

### 使用

```bash
# 正常模式（摄像头 + 地图双窗口）
python main.py

# 无头模式（SSH 远程，仅日志）
python main.py --no-display

# 详细日志
python main.py --log-level DEBUG
```

### 键位

| 按键 | 功能 |
|------|------|
| `W` | 前进 |
| `S` | 后退 |
| `A` | 左转 |
| `D` | 右转 |
| `空格` | 立即停车 |
| `R` | 重置地图 |
| `Q` | 退出 |

### 项目结构

```
manual_drive/
├── main.py            # 主程序入口
├── config.py          # 所有参数配置
├── motor_control.py   # PCA9685 电机驱动 (支持 Mock 模式)
├── sensors.py         # HC-SR04 超声波 + 3 通道红外
├── camera.py          # PiCamera2 / USB 摄像头管理
├── mapping.py         # 航位推算 + 2D 占据栅格地图
├── requirements.txt   # Python 依赖
└── .gitignore
```

---

## English

### Overview

A keyboard-controlled driving system for **Raspberry Pi 5 + Freenove FNK0043B (4WD standard wheels)** with **real-time 2D occupancy grid mapping**.

- WASD keyboard control: forward, backward, turn left/right
- HC-SR04 ultrasonic + 3-channel IR sensor fusion into occupancy grid
- Dead-reckoning odometry for real-time pose estimation
- Dual-window display: camera feed + top-down grid map
- Auto-stop: motors halt after N frames of no input
- Headless mode for SSH remote operation

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
# Clone the repo
git clone https://github.com/hwu668/manual_drive.git
cd manual_drive

# Install dependencies
pip install -r requirements.txt

# (Optional) Install RPi.GPIO on Raspberry Pi
sudo apt install python3-rpi.gpio
```

### Usage

```bash
# Normal mode (camera + map dual window)
python main.py

# Headless mode (SSH, logging only)
python main.py --no-display

# Verbose logging
python main.py --log-level DEBUG
```

### Key Bindings

| Key | Action |
|-----|--------|
| `W` | Forward |
| `S` | Backward |
| `A` | Turn Left |
| `D` | Turn Right |
| `Space` | Emergency Stop |
| `R` | Reset Map |
| `Q` | Quit |

### Project Structure

```
manual_drive/
├── main.py            # Entry point
├── config.py          # All configuration parameters
├── motor_control.py   # PCA9685 motor driver (Mock mode supported)
├── sensors.py         # HC-SR04 ultrasonic + 3-channel IR
├── camera.py          # PiCamera2 / USB camera manager
├── mapping.py         # Dead-reckoning + 2D occupancy grid
├── requirements.txt   # Python dependencies
└── .gitignore
```


