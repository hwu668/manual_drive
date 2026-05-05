# Troubleshooting

## Program fails because logs/manual_drive.log does not exist

检查是否在配置 logging FileHandler 之前创建了 logs 目录。此问题已在当前版本修复（`Path("logs").mkdir(...)` 在 `logging.basicConfig()` 之前执行）。

## Car does not move

检查：
- 当前是否是 mock 模式（`--mode mock` 不会真的驱动电机）
- 是否真的进入 hardware 模式
- Freenove 硬件库是否加载成功
- 电池是否有电
- 电机线是否连接正确
- duty 值是否太低（建议 >= 1200）
- 是否触发了安全停车

## SSH 下无法控制小车

检查：
- 是否使用了 `--no-display`
- 是否启用了 `--keyboard-terminal`
- 默认 OpenCV `cv2.waitKey()` 依赖显示窗口
- 可以改用 `--command forward --duration 1` 做短时测试

## Camera cannot open

检查：
- 摄像头排线
- 摄像头是否被系统识别（`libcamera-hello --list-cameras`）
- 是否有其他进程占用摄像头
- 是否应该使用 `--no-camera`
- 如果必须用摄像头，可加 `--require-camera` 确保失败时报错

## Ultrasonic reading is invalid

检查：
- TRIG/ECHO 接线
- GPIO 编号模式（BCM）
- 电平是否安全
- 是否处于 mock 模式（mock 返回 999.0）
- hardware 模式初始化是否成功

## Car keeps moving after exit

检查：
- finally 中是否调用 `motor.stop()`
- KeyboardInterrupt 是否被捕获
- q 退出路径是否调用 stop
- command mode 结束是否调用 stop
- `motor.cleanup()` 是否执行
