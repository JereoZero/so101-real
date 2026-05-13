# 6. 摄像头配置

## 6.1 摄像头读取失败：缺少 fourcc

**现象**：遥操作/录制时摄像头报 `TimeoutError: OpenCVCamera(0) latest frame is too old`。

**原因**：某些 USB 摄像头默认使用 YUYV 格式时无法正常读取，需要显式指定 MJPG 格式。但反过来，有些摄像头只支持 YUYV 不支持 MJPG。

**解决**：需要逐个测试每个摄像头的支持格式。本项目最终配置：

```bash
--robot.cameras="{
  front: {type: opencv, index_or_path: 2, fps: 30, width: 640, height: 480, fourcc: YUYV},
  top:   {type: opencv, index_or_path: 0, fps: 30, width: 640, height: 480, fourcc: MJPG}
}"
```

即：**爪子摄像头用 YUYV，顶部摄像头用 MJPG**。两个摄像头支持的格式不同！

---

## 6.2 摄像头被占用

**现象**：摄像头无法打开。

**检查**：

```bash
# 关掉可能占用摄像头的应用（如 Cheese）
pkill cheese

# 检查摄像头是否被占用
lsof /dev/video0
lsof /dev/video2
```

---

## 6.3 by-id 路径 vs index 路径

**背景**：使用 `/dev/video0`、`/dev/video2` 这种 index 路径，USB 口换位置后 index 会变。

**建议**：使用 by-id 路径，序列号固定：

```bash
ls /dev/v4l/by-id/
# usb-icSpring_icspring_camera-video-index0
# usb-icSpring_icspring_camera_202404160005-video-index0
```

但在录制命令中，LeRobot 使用 index_or_path 参数，实际使用时发现 index 更稳定（by-id 路径有时无法被 OpenCV 正确识别）。所以**最终使用 index 而非 by-id**。

---

## 6.4 OpenCV GUI 依赖

如果需要在录制时实时预览（`--display_data=true`），需要安装：

```bash
sudo apt-get install -y libgtk2.0-dev pkg-config
```

---

## 6.5 找不到摄像头 / 不确定用哪个 index

**现象**：不确定摄像头设备是哪个 index，或者换 USB 口后 index 变了。

**排查**：

```bash
# 列出所有 OpenCV 能识别的摄像头
lerobot-find-cameras opencv

# 查看所有 video 设备
ls /dev/video*

# 查看 by-id 路径
ls /dev/v4l/by-id/
```

**最终决策**：虽然 by-id 路径不会变，但 OpenCV 有时无法正确识别 by-id 路径。实践下来 **index 方式（0, 2）更稳定**。本项目最终配置：

| 摄像头 | index | by-id 路径 |
|--------|-------|------------|
| top（顶部第三视角） | 0 | `usb-icSpring_icspring_camera-video-index0` |
| front（爪子视角） | 2 | `usb-icSpring_icspring_camera_202404160005-video-index0` |

**注意**：换 USB 口后 index 可能重新分配，用 `lerobot-find-cameras opencv` 重新确认。