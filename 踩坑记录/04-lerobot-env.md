# 4. LeRobot 环境安装

## 4.1 Python 版本兼容性

**要求**：LeRobot v0.5+ 需要 Python 3.10+。本项目使用 Python 3.12 + conda。

**最佳实践**：使用 conda 创建独立环境，避免与系统 Python 冲突：

```bash
source ~/miniconda3/etc/profile.d/conda.sh
conda create -n lerobot python=3.12
conda activate lerobot
```

**验证**：

```bash
python --version             # 应显示 3.12.x
python -c "import lerobot; print(lerobot.__version__)"
```

---

## 4.2 LeRobot 安装方式选择

**两种方式**：

1. **pip install（简单但不便于修改源码）**：
   ```bash
   pip install lerobot
   ```
   优点：一键安装。缺点：源码在 site-packages 里，修改不方便。

2. **源码安装 - `pip install -e .`（推荐）**：
   ```bash
   cd ~/workspace/projects/lerobot
   pip install -e .
   ```
   优点：修改源码后立即生效，无需重装。本项目必须用此方式，因为需要修改 4 处源码。

3. **Docker 方式（可选，本项目未使用）**：
   ```bash
   docker build -t lerobot .
   ```
   官方推荐但本项目因硬盘空间和网络问题未采用。

---

## 4.3 系统依赖安装

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

## 4.4 feetech-servo-sdk vs scservo_sdk

两个包都用于 Feetech 舵机通信：
- `scservo_sdk`：通用 Feetech SDK
- `feetech-servo-sdk`：LeRobot 封装的版本

两者都需安装，但可能出现版本冲突。如果遇到问题，先卸载再重新安装：

```bash
pip uninstall scservo_sdk feetech-servo-sdk -y
pip install feetech-servo-sdk
```

---

## 4.5 磁盘空间注意事项

LeRobot 的数据集和模型文件很大：
- 预训练模型 `model.safetensors`：~906MB
- 单个录制 session（10 episodes，双摄像头）：几百 MB 到 1GB+
- 210 条完整数据集：数十 GB

确保工作目录有充足空间，否则录制/训练中途会因磁盘满而失败。

```bash
df -h /home/jer/ws/workspace/
```