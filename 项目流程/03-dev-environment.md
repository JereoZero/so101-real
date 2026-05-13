# 3. LeRobot 开发环境

## 环境安装

### 创建 conda 环境

```bash
source ~/miniconda3/etc/profile.d/conda.sh
conda create -n lerobot python=3.12
conda activate lerobot
```

### 安装 LeRobot（源码方式）

先 clone 官方源码，再以可编辑模式安装。选择 `pip install -e .` 源码安装而非 `pip install lerobot`，因为项目需要修改 LeRobot 源码。

```bash
git clone https://github.com/huggingface/lerobot.git ~/workspace/projects/lerobot
cd ~/workspace/projects/lerobot
pip install -e .
```

### 系统依赖

```bash
sudo apt install -y python3-dev libevdev-dev swig ffmpeg libgtk2.0-dev pkg-config
```

| 依赖 | 用途 |
|------|------|
| python3-dev | Python C 扩展编译 |
| libevdev-dev | 遥操作输入设备 |
| swig | SDK 绑定生成 |
| ffmpeg | 视频编解码 |
| libgtk2.0-dev | 录制实时预览 |
| pkg-config | 编译链接配置 |

### 舵机驱动

```bash
pip install feetech-servo-sdk
```

## SO101 机械臂配置

### 主从臂识别与 udev 固定

两个 SO101 机械臂通过 USB 连接，需要区分主臂（Leader，人类操作）和从臂（Follower，执行动作）。USB 口换位置后 `/dev/ttyACM*` 编号会变，使用 udev 规则创建固定的符号链接。

在 `/etc/udev/rules.d/99-so101.rules` 中按设备序列号创建固定名称：

```
SUBSYSTEM=="tty", ENV{ID_SERIAL_SHORT}=="5B3E121553", SYMLINK+="ttySO101_LEADER"
SUBSYSTEM=="tty", ENV{ID_SERIAL_SHORT}=="5B3E121987", SYMLINK+="ttySO101_FOLLOWER"
```

最终固定名称：
- 主臂：`/dev/ttySO101_LEADER`
- 从臂：`/dev/ttySO101_FOLLOWER`

序列号通过 `ls -l /dev/serial/by-id/` 获取。

### 关节配置

SO101 每条机械臂有 6 个 Feetech STS3215 舵机：

| ID | 名称 | 功能 | 模式 |
|----|------|------|------|
| 1 | shoulder_pan | 肩膀水平旋转 | 角度模式 |
| 2 | shoulder_lift | 肩膀升降 | 角度模式 |
| 3 | elbow_flex | 肘部弯曲 | 角度模式 |
| 4 | wrist_flex | 腕部弯曲 | 角度模式 |
| 5 | wrist_roll | 腕部旋转（360°） | 角度模式 |
| 6 | gripper | 夹爪 | 百分比模式（0-100） |

### 电机 ID 校验

使用 Python 脚本逐个扫描确认 6 个电机 ID 正确响应。连接前如发现 ID 不对（出厂或被修改过），通过 SDK 写回正确 ID，断电重启生效。

### 校准

每次断电重新连接后必须校准，确定每个关节的运动范围：

```bash
# 校准主臂
lerobot-calibrate \
    --teleop.type=so101_leader --teleop.port=/dev/ttySO101_LEADER --teleop.id=j_leader

# 校准从臂
lerobot-calibrate \
    --robot.type=so101_follower --robot.port=/dev/ttySO101_FOLLOWER --robot.id=j_follower
```

校准过程：移动关节到中间位置 → 依次移动每个关节到最大范围 → 自动保存。

校准文件位置：
- 主臂：`~/.cache/huggingface/lerobot/calibration/teleoperators/so101_leader/j_leader.json`
- 从臂：`~/.cache/huggingface/lerobot/calibration/robots/so_follower/j_follower.json`

## LeRobot 源码修改

LeRobot 官方代码不完全适配 SO101 硬件，需要做 4 处修改：

| # | 修改内容 | 涉及文件 | 原因 |
|---|----------|----------|------|
| 1 | wrist_roll 关节参与校准 | `so_follower.py` `so_leader.py` | 原版硬编码跳过该关节的校准 |
| 2 | 夹爪扭矩限制提升 | `so_follower.py` | 默认 50% 扭矩不足以张开夹爪 |
| 3 | 电机通信异常容错 | `feetech.py` `motors_bus.py` | 单电机通信失败不应崩溃整个流程 |
| 4 | 录制复位阶段遥操作控制 | `lerobot_record.py` | 修复复位阶段从臂不跟随主臂 |

详细的修改前后对比见 [踩坑记录 - 源码修改](../踩坑记录/07-source-modifications.md)。

## 双摄像头配置

| 摄像头 | 来源 | 位置 | index | 格式 | 分辨率 | 帧率 |
|--------|------|------|-------|------|--------|------|
| front | 幻尔（Huaner） | 末端（爪子视角） | 2 | YUYV | 640×480 | 30fps |
| top | 幻尔（Huaner） | 顶部固定（第三视角） | 0 | MJPG | 640×480 | 30fps |

**注意**：两个摄像头均为普通 RGB 摄像头，不带深度功能。

```bash
# 查找可用摄像头
lerobot-find-cameras opencv
```

在 LeRobot 录制命令中，摄像头使用 index 方式（0/2）而非 by-id 路径，因为 OpenCV 对 by-id 路径的兼容性不稳定。

## 遥操作验证

连接完成后通过遥操作确认一切正常：

```bash
lerobot-teleoperate \
    --teleop.type=so101_leader --teleop.port=/dev/ttySO101_LEADER --teleop.id=j_leader \
    --robot.type=so101_follower --robot.port=/dev/ttySO101_FOLLOWER --robot.id=j_follower
```

操作员拖拽主臂，从臂应实时跟随。确认所有 6 个关节均可正常控制，夹爪能完全张开。