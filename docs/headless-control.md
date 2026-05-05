# Headless Control

本项目支持或计划支持以下无头运行方式。

## 1. No display mode

```bash
python main.py --no-display
```

不打开 OpenCV 窗口。日志写入 `logs/manual_drive.log`。

注意：`--no-display` 单独使用时**无法键盘控制**，因为默认键盘输入依赖 `cv2.waitKey()`。请配合 `--keyboard-terminal` 使用。

## 2. Terminal keyboard mode

```bash
python main.py --no-display --keyboard-terminal
```

按键：

| 按键 | 命令 |
|------|------|
| `w` | 前进 |
| `s` | 后退 |
| `a` | 左转 |
| `d` | 右转 |
| `空格` | 立即停车 |
| `q` | 退出 |

仅支持 Linux/macOS（termios）。在 Windows 上会报错退出。

## 3. Command mode

```bash
python main.py --command forward --duration 1
python main.py --command stop
```

执行指定动作后自动 exit。适合 SSH、短时硬件测试和自动化 smoke test。

- `--command` 支持：`stop`、`forward`、`backward`、`left`、`right`
- `--duration` 最大 1.0 秒（安全上限）
- `stop` 不需要 `--duration`
- 命令结束后自动调用 `motor.stop()` 和 cleanup
