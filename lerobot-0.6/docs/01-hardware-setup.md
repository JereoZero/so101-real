# 01. 硬件连接与上电

## 硬件清单

- 幻尔 SO-101 双臂机械臂（主臂 + 从臂）
- USB 数据线 ×2（主臂控制器、从臂控制器）
- 电源适配器
- 摄像头（可选：爪子视角 + 顶部第三视角）

## 连接步骤

1. **连接主臂控制器**到电脑 USB 口
2. **连接从臂控制器**到电脑 USB 口
3. **接通机械臂电源**
4. 等待电机初始化完成（通常有提示音或指示灯）

## 确认串口

```bash
unset PYTHONPATH
conda activate lerobot
lerobot-find-port
```

按照提示断开/重连电机板，确认每个电机板对应的串口。

通常命名：

- 主臂：`/dev/ttyUSB0` 或 `/dev/ttyACM0`
- 从臂：`/dev/ttyUSB1` 或 `/dev/ttyACM1`

## 当前设备 ID 记录

> 记录时间：2026-07-19，最后更新：2026-07-20（主从臂已确认）

### 串口

Linux 已为这两个 USB 串口创建固定 by-id 链接，插拔后路径不变：

| 设备 | 角色 | 当前 `/dev` | `/dev/serial/by-id` 路径 |
|------|------|------------|--------------------------|
| `ttyACM0` | 从臂（Follower） | `/dev/ttyACM0` | `<FOLLOWER_PORT>` |
| `ttyACM1` | 主臂（Leader） | `/dev/ttyACM1` | `<LEADER_PORT>` |

> **已确认**：通过拔掉主臂 USB 验证，消失的是 `/dev/ttyACM1`（序列号 `<LEADER_SERIAL>`），因此该端口为主臂；
> 剩余 `/dev/ttyACM0`（序列号 `<FOLLOWER_SERIAL>`）为从臂。
> 如果后续更换 USB 口，可用 `lerobot-find-port` 重新确认。

### 摄像头

当前检测到两个 `icSpring` 摄像头：

| 摄像头 | 用途 | `/dev` | `/dev/v4l/by-id` 路径 | fourcc | 分辨率 |
|--------|------|-------|----------------------|--------|--------|
| `front` | 爪子视角 | `/dev/video0` | `<FRONT_CAM>` | YUYV | 640x480 |
| `top` | 顶部第三视角 | `/dev/video2` | `<TOP_CAM>` | MJPG | 640x480 |

> 实测第一个摄像头只支持 YUYV，第二个摄像头支持 MJPG，因此按参考项目的格式要求分配为 front/top。
> OpenCV 索引会随插拔变化，配置文件中已改用 `/dev/v4l/by-id/...` 固定路径。

## 使用 by-id 路径的好处

`/dev/serial/by-id/` 和 `/dev/v4l/by-id/` 是 Linux 根据设备唯一序列号创建的符号链接，插拔后不会变化。相比直接使用 `/dev/ttyACM0` 或 `/dev/video0`，更稳定，推荐在配置文件中直接使用 by-id 路径。

## 设置固定串口别名（可选）

如果希望用更短的名字（如 `/dev/ttySO101_LEADER`），可以创建 udev 规则：

```bash
# 查看设备信息
udevadm info -a -n /dev/ttyACM0 | grep -E "idVendor|idProduct|serial"
udevadm info -a -n /dev/ttyACM1 | grep -E "idVendor|idProduct|serial"
```

创建 `/etc/udev/rules.d/99-so101.rules`：

```
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="55d3", ATTRS{serial}=="<LEADER_SERIAL>", SYMLINK+="ttySO101_LEADER"
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="55d3", ATTRS{serial}=="<FOLLOWER_SERIAL>", SYMLINK+="ttySO101_FOLLOWER"
```

加载规则：

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## 摄像头连接与配置

参考项目使用两个 `icSpring` USB 摄像头：

| 摄像头 | 用途 | index | fourcc | 分辨率 |
|--------|------|-------|--------|--------|
| `front` | 爪子视角 | 2 | YUYV | 640x480 |
| `top` | 顶部第三视角 | 0 | MJPG | 640x480 |

> 注意：不同摄像头支持的格式不同，**爪子摄像头用 YUYV，顶部摄像头用 MJPG**。

### 当前实际配置

当前两个摄像头均正常识别，配置文件已更新为：

| 摄像头 | 用途 | by-id 路径 | fourcc | 分辨率 |
|--------|------|-----------|--------|--------|
| `front` | 爪子视角 | `<FRONT_CAM>` | YUYV | 640x480 |
| `top` | 顶部第三视角 | `<TOP_CAM>` | MJPG | 640x480 |

### 确认摄像头

```bash
unset PYTHONPATH
conda activate lerobot

# 列出 OpenCV 能识别的摄像头
lerobot-find-cameras opencv

# 查看 video 设备
ls /dev/video*
ls /dev/v4l/by-id/
```

### 摄像头测试

```bash
source /home/j/miniconda3/etc/profile.d/conda.sh
unset PYTHONPATH
conda activate lerobot

python - <<'PY'
import cv2
# 用 by-id 路径测试，避免 index 随插拔变化
cameras = {
    'front': '<FRONT_CAM>',
    'top': '<TOP_CAM>',
}
for name, path in cameras.items():
    cap = cv2.VideoCapture(path)
    if cap.isOpened():
        fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
        fourcc_str = "".join(chr((fourcc >> 8 * i) & 0xFF) for i in range(4))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        print(f'{name} ({path}): {w}x{h} @ {fps:.1f}fps, fourcc={fourcc_str}')
    else:
        print(f'{name} ({path}): FAILED')
    cap.release()
PY
```

### 摄像头配置已写入

项目配置文件 [`src/configs/so101.yaml`](../../src/configs/so101.yaml) 已写入当前检测到的设备 by-id 路径；
单臂测试配置见 [`src/configs/so101_single.yaml`](../../src/configs/so101_single.yaml)。

## 下一步

确认串口和摄像头无误后，进入 [02-calibration.md](02-calibration.md) 进行校准。
