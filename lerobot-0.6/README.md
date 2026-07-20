# SO-101 真机项目

> 基于 LeRobot v0.6.0 + 幻尔 SO-101 双臂机械臂的模仿学习项目。
>
> 参考项目：[JereoZero/so101-real](https://github.com/JereoZero/so101-real)

## 参考项目说明

本项目大流程参考 [so101-real](https://github.com/JereoZero/so101-real)：

- 硬件：幻尔 SO-101 双臂机械臂（主从遥操作）
- 算法：SmolVLA / ACT / Diffusion 等模仿学习策略
- 任务：通过遥操作录制数据，训练模型，实现自主抓放

相比参考项目，当前环境使用 **LeRobot v0.6.0**（参考项目为 v0.5.1），因此部分源码需要 patch 适配。

## 目录结构

```
/home/j/ws/so101/
├── apply_patches.py          # 自动把 SO-101 patch 应用到 LeRobot 源码
├── README.md                 # 本文件
├── docs/                     # 详细操作步骤文档
│   ├── README.md
│   ├── 01-hardware-setup.md
│   ├── 02-calibration.md
│   ├── 03-teleoperation.md
│   ├── 04-recording.md
│   ├── 05-training.md
│   ├── 06-inference.md
│   └── 07-troubleshooting.md
├── patches/                  # 补丁相关说明（实际 patch 逻辑在 apply_patches.py）
├── src/
│   ├── configs/
│   │   └── so101.yaml        # SO-101 自定义配置
│   ├── scripts/
│   │   ├── teleoperate.py    # 遥操作测试
│   │   ├── record.py         # 数据录制
│   │   ├── train.py          # 训练
│   │   ├── eval.py           # 仿真评估（v0.6.0 lerobot-eval 包装）
│   │   └── rollout.py        # 真机推理/部署（v0.6.0 lerobot-rollout 包装）
│   └── utils/
│       └── __init__.py
├── data/                     # 录制数据集
├── outputs/                  # 训练输出
└── checkpoints/              # 模型检查点
```

## 环境准备

```bash
unset PYTHONPATH
conda activate lerobot
cd /home/j/ws/so101
```

LeRobot 源码位于 `/home/j/ws/repos/lerobot`，已通过 `pip install -e /home/j/ws/repos/lerobot` 以 editable 模式安装到当前环境。

## 应用 SO-101 Patch

```bash
cd /home/j/ws/so101
python apply_patches.py
```

这会修改 `/home/j/ws/repos/lerobot` 中的以下文件：

| 文件 | 修改内容 |
|------|----------|
| `src/lerobot/robots/so_follower/config_so_follower.py` | 新增 `fixed_joints` 字段，恢复 v0.5.1 固定关节能力 |
| `src/lerobot/robots/so_follower/so_follower.py` | `wrist_roll` 参与校准；范围裁剪到 `[0, 4095]`；`send_action` 中覆盖 `fixed_joints`；夹爪扭矩改为 100% |
| `src/lerobot/teleoperators/so_leader/so_leader.py` | `wrist_roll` 参与校准；范围裁剪到 `[0, 4095]`；适配 v0.6.0 电机列表类型 |
| `src/lerobot/scripts/lerobot_record.py` | 修复复位阶段 teleop 控制失效问题 |
| `src/lerobot/motors/feetech/feetech.py` | `enable_torque` / `disable_torque` 增加通信失败容错，避免单电机失败导致整体流程崩溃 |

> 由于使用 editable 安装，patch 后无需重新安装。

## 常用命令

### 1. 查找串口

```bash
lerobot-find-port
```

### 2. 遥操作测试

```bash
lerobot-teleoperate \
  --teleop.type=so101_leader \
  --teleop.port=/dev/ttySO101_LEADER \
  --robot.type=so101_follower \
  --robot.port=/dev/ttySO101_FOLLOWER
```

### 3. 录制数据

```bash
python src/scripts/record.py \
  --robot.type=so101_follower \
  --robot.port=/dev/ttySO101_FOLLOWER \
  --teleop.type=so101_leader \
  --teleop.port=/dev/ttySO101_LEADER \
  --dataset.repo_id=local/so101_pick_place \
  --dataset.root=/home/j/ws/so101/data/so101_pick_place
```

> v0.6.0 会自动在 `repo_id` 后追加时间戳（如 `local/so101_pick_place_20260720_123456`），训练时需使用实际生成的 repo_id。

### 4. 训练

```bash
python src/scripts/train.py \
  --dataset.repo_id=local/so101_pick_place \
  --policy.type=act \
  --output_dir=outputs/so101_act
```

### 5. 推理

v0.6.0 推荐用 `lerobot-rollout`（包装为 `src/scripts/rollout.py`）在真机上运行策略：

```bash
python src/scripts/rollout.py \
  --strategy.type=base \
  --policy.path=/home/j/ws/so101/checkpoints/so101_smolvla_infer \
  --robot.type=so101_follower \
  --robot.port=/dev/ttySO101_FOLLOWER \
  --robot.id=j_follower \
  --robot.fixed_joints="{wrist_roll: -27.82}" \
  --task="put small green block in plate" \
  --duration=60
```

> `src/scripts/eval.py` 对应 `lerobot-eval`，主要用于仿真 benchmark 评估。

## 下一步

详细操作步骤见 [docs/README.md](docs/README.md)：

1. [硬件连接与上电](docs/01-hardware-setup.md)
2. [机械臂校准](docs/02-calibration.md)
3. [遥操作测试](docs/03-teleoperation.md)
4. [数据录制](docs/04-recording.md)
5. [模型训练](docs/05-training.md)
6. [推理部署](docs/06-inference.md)
7. [常见问题排查](docs/07-troubleshooting.md)