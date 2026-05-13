# 附录

## A. 常用 LeRobot 命令

```bash
# 查找摄像头
lerobot-find-cameras opencv

# 查找串口设备
lerobot-find-port

# 遥操作测试（主臂控制从臂）
lerobot-teleoperate \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttySO101_LEADER \
    --teleop.id=j_leader \
    --robot.type=so101_follower \
    --robot.port=/dev/ttySO101_FOLLOWER \
    --robot.id=j_follower

# 校准主臂
lerobot-calibrate \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttySO101_LEADER \
    --teleop.id=j_leader

# 校准从臂
lerobot-calibrate \
    --robot.type=so101_follower \
    --robot.port=/dev/ttySO101_FOLLOWER \
    --robot.id=j_follower

# 回放录好的数据（驱动机械臂执行）
lerobot-replay \
    --robot.type=so101_follower \
    --robot.port=/dev/ttySO101_FOLLOWER \
    --robot.id=j_follower \
    --dataset.repo_id=jer/xxx \
    --dataset.episode=0

# 可视化数据集（不驱动机械臂）
python -m lerobot.scripts.lerobot_dataset_viz \
    --repo-id jer/xxx \
    --episode-index 0 \
    --mode local

# 查看数据集信息
lerobot-info --dataset.repo_id=jer/xxx

# 查看机器人信息
lerobot-info --robot.type=so101_follower

# 查看训练曲线
tensorboard --logdir=outputs/
# 然后打开浏览器访问 http://localhost:6006
```

## B. 常用诊断命令

```bash
# 系统硬件
nvidia-smi                         # GPU 状态
lsusb                              # USB 设备列表
ls -l /dev/serial/by-id/           # 串口设备序列号
lspci | grep -i nvidia             # PCIe 显卡信息
free -h                            # 内存使用

# 串口/摄像头
ls -l /dev/ttySO101_*              # SO101 串口设备
ls /dev/v4l/by-id/                 # 摄像头 by-id 路径
lsof /dev/video0                   # 检查摄像头是否被占用
lsof /dev/video2
pkill cheese                       # 关掉占用摄像头的应用

# 文件/缓存
ls ~/.cache/huggingface/lerobot/calibration/    # 校准文件
ls ~/.cache/huggingface/lerobot/jer/            # 录制缓存

# Python 环境
which python
pip list | grep lerobot
pip list | grep torch
python -c "import torch; print(torch.cuda.is_available())"

# 系统日志（排查驱动/硬件问题）
dmesg | tail
journalctl -xe
sudo tail -f /var/log/syslog
sudo tail -f /var/log/kern.log

# 网络诊断
ping -c 4 8.8.8.8
ip a show ens33
```

## C. 关键文件路径

| 用途 | 路径 |
|------|------|
| LeRobot 源码 | `/home/jer/ws/workspace/projects/lerobot/` |
| 校准文件 | `~/.cache/huggingface/lerobot/calibration/` |
| 录制缓存 | `~/.cache/huggingface/lerobot/jer/` |
| 数据集存储 | `/home/jer/ws/workspace/datasets/` |
| 模型权重 | `/home/jer/ws/workspace/models/` |
| so_follower.py | `src/lerobot/robots/so_follower/so_follower.py` |
| so_leader.py | `src/lerobot/teleoperators/so_leader/so_leader.py` |
| lerobot_record.py | `src/lerobot/scripts/lerobot_record.py` |
| udev 规则 | `/etc/udev/rules.d/99-so101.rules` |
| 中文下载文件夹 | `~/下载` |

## D. 项目最终参数配置

| 配置项 | 值 |
|--------|-----|
| 算法 | SmolVLA（基于 lerobot/smolvla_base 微调） |
| 任务 | 三色小方块放入盘子 |
| 方块尺寸 | 3.5cm 边长 |
| 盘子直径 | 8.5cm |
| 放置方式 | 盘子随机放置、方块随机放置 |
| 训练数据总量 | 210 条（每色约 70 条，含 baseline + 增强） |
| 训练轮次 | 3轮（10000 → 40000 → 40000 v3） |
| batch_size | 8（V1/V2）/ **36（V3）** |
| 学习率 | 默认（从预训练模型继承） |
| 摄像头 | front(YUYV) + top(MJPG)，640x480@30fps |
| wrist_roll | 固定 -67.74° |
| 光照控制 | 拉窗帘统一环境光 + 部分拉开/改变角度增强多样性 |
| 推理版本 | V1/V2（25000步/60s） + V3（40000步/120s） |

## E. 硬件配置

| 组件 | 型号 |
|------|------|
| 显卡 | NVIDIA RTX 5070 12GB |
| CPU | AMD Ryzen 7 3700X (8核16线程) |
| 内存 | 96GB DDR4 3200MHz |
| 系统 | Ubuntu 22.04 移动固态硬盘 |

## F. 训练产出汇总

| 版本 | 路径 | 步数 | batch_size | save_freq | 用途 |
|------|------|------|------------|-----------|------|
| smolvla210 | `smolvla_model/smolvla210/` | 10000→25000 | 8 | 1000 | V1/V2 推理 |
| smolvla210_40000 | `smolvla_model/smolvla210_40000/` | 40000 | 8 | 2000 | 重训版 |
| smolvla_v3_run2 | `smolvla_v3_run2/` | 40000 | **36** | 2000 | V3 推理 |

## G. 核心 Python 包版本

| 包名 | 版本 | 用途 |
|------|------|------|
| python | 3.10.x | 运行环境 |
| torch | 2.10.0+cu128 | 深度学习框架 |
| lerobot | 0.5.1 (dev) | 机器人学习框架 |
| numpy | 2.2.6 | 数值计算 |
| opencv-python-headless | 4.10.0.84 | 图像处理（无GUI） |
| mujoco | 3.6.0 | 机器人仿真 |
| scservo_sdk | 1.0.0 | Feetech 舵机通信 |
| feetech-servo-sdk | 1.0.0 | LeRobot 舵机驱动 |
| gymnasium | 1.2.3 | 强化学习环境 |

## H. single_task 指令完整对照表

SmolVLA 推理时需要根据任务指令判断操作哪个颜色的方块，因此必须使用分颜色指令：

| 颜色 | 指令 |
|------|------|
| 绿色方块 | `put small green block in plate` |
| 葡萄紫方块 | `put small grape block in plate` |
| 橙色方块 | `put small orange block in plate` |

**注意**：录制时的 `single_task` 指令必须与推理时一致，否则模型无法正确理解要操作的目标颜色。