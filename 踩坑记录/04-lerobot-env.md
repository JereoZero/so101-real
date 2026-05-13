# 4. LeRobot 环境安装

## 4.1 系统依赖安装

LeRobot 需要一些系统级依赖，缺少会导致安装失败或功能缺失：

```bash
sudo apt install -y python3-dev libevdev-dev swig ffmpeg libgtk2.0-dev pkg-config
```

各依赖的作用：
- `python3-dev`：Python 头文件，编译 C 扩展需要
- `libevdev-dev`：遥操作输入设备支持
- `swig`：SDK 绑定生成
- `ffmpeg`：视频编码/解码
- `libgtk2.0-dev`：录制时的 GUI 预览（`--display_data=true`）
- `pkg-config`：编译时查找库依赖

**如果缺少 libgtk2.0-dev，录制时无法实时预览摄像头画面**。

---

## 4.2 feetech-servo-sdk vs scservo_sdk

两个包都用于 Feetech 舵机通信：
- `scservo_sdk`：通用 Feetech SDK
- `feetech-servo-sdk`：LeRobot 封装的版本

两者都需安装，但可能出现版本冲突。如果遇到问题，先卸载再重新安装：

```bash
pip uninstall scservo_sdk feetech-servo-sdk -y
pip install feetech-servo-sdk
```

---

## 4.3 磁盘空间注意事项

LeRobot 的数据集和模型文件很大：
- 预训练模型 `model.safetensors`：~906MB
- 单个录制 session（10 episodes，双摄像头）：几百 MB 到 1GB+
- 210 条完整数据集：数十 GB

确保工作目录有充足空间，否则录制/训练中途会因磁盘满而失败。

```bash
df -h /home/jer/ws/workspace/
```