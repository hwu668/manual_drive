# Hardware Checklist

实车测试前逐项检查。

## Power

- [ ] 电池已充电
- [ ] 电源开关已打开
- [ ] Raspberry Pi 供电稳定
- [ ] 电机供电正常

## Raspberry Pi

- [ ] I2C 已启用 (`sudo raspi-config`)
- [ ] SPI 已启用
- [ ] SSH 已启用
- [ ] 摄像头已识别 (`libcamera-hello --list-cameras`)

## Motor

- [ ] 前进方向正确
- [ ] 后退方向正确
- [ ] 左转方向正确
- [ ] 右转方向正确
- [ ] stop 可以立刻停止所有电机

## Sensors

- [ ] 超声波 TRIG/ECHO 接线正确
- [ ] 超声波读数稳定
- [ ] 红外传感器接线正确
- [ ] 红外传感器读数合理

## Camera

- [ ] 摄像头排线连接正确
- [ ] 摄像头可以采集图像
- [ ] no-camera 模式可以跳过摄像头

## Safety

- [ ] Ctrl+C 后停车
- [ ] q 退出后停车
- [ ] 空格急停有效
- [ ] max-runtime 超时后停车
- [ ] command mode 结束后停车
- [ ] 近距离障碍物触发强制停车
