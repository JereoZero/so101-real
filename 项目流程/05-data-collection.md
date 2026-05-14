# 5. 数据采集

## 物理环境

![实验环境](../images/环境.jpg)

![干扰环境示例](../images/干扰环境.jpg)

## 采集流程概览

```
启动录制 → 校准从臂 → 进入复位阶段
    ↓
循环：手动摆场景 → 按→开始录制 → 操作主臂完成抓放 → 按→结束录制
    ↓
按 ESC 停止 → 回放验证数据质量 → 复制数据集到正式目录
```

## 录制命令

```bash
sudo chmod 666 /dev/ttySO101_FOLLOWER /dev/ttySO101_LEADER

lerobot-record \
    --robot.type=so101_follower \
    --robot.port=/dev/ttySO101_FOLLOWER \
    --robot.id=j_follower \
    --robot.fixed_joints="{wrist_roll: -67.74}" \
    --robot.cameras="{front: {type: opencv, index_or_path: 2, fps: 30, width: 640,
  height: 480, fourcc: YUYV}, top: {type: opencv, index_or_path: 0, fps: 30, width: 640,
  height: 480, fourcc: MJPG}}" \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttySO101_LEADER \
    --teleop.id=j_leader \
    --display_data=true \
    --dataset.repo_id=jer/so101_3color_green_only_v6 \
    --dataset.push_to_hub=false \
    --dataset.num_episodes=10 \
    --dataset.single_task="put small green block in plate" \
    --dataset.episode_time_s=20 \
    --dataset.reset_time_s=9999
```

### 关键参数说明

| 参数 | 值 | 说明 |
|------|-----|------|
| `--robot.fixed_joints` | `wrist_roll: -67.74°` | 固定手腕旋转关节，防止抓取方向漂移 |
| `--dataset.episode_time_s` | 20 | 录制时间 20 秒，足够但不长，手动按键结束 |
| `--dataset.reset_time_s` | 9999 | 复位阶段超长时间，**实现完全手动控制** |
| `--display_data` | true | 实时预览摄像头和关节状态 |
| `--dataset.push_to_hub` | false | 不上传 HuggingFace，本地存储 |
| `--dataset.single_task` | 语言指令 | 标注任务，也是推理时的提示词 |

### 录制键位

| 按键 | 功能 |
|------|------|
| **→ 右箭头** | 结束当前阶段（录制→复位 / 复位→录制） |
| **← 左箭头** | 放弃当前 episode，重新录制本条的复位阶段 |
| **ESC** | 完全停止录制 |

## 录制迭代过程

数据采集不是一次性完成的。以绿色方块 only 为例，经历了多次迭代才得到可用数据：

| 版本 | 结果 | 改进点 |
|------|------|--------|
| v1 | 不可用 | 动作不够流畅，夹爪角度需调整 |
| v2 | 不可用 | 修改夹爪扭矩（50%→100%） |
| v3 | 不可用 | 光照一致性需要改善 |
| v4 | 不可用 | 发现需在录制命令中加入 teleop 参数 |
| v5 | 不可用 | wrist_roll 固定角度需微调 |
| v6 | ✅ | 最终可用版本 |

**经验**：前几次录制通常需要迭代调整，每次录制完应立刻用 `lerobot-replay` 回放确认质量。数据集 ID 带版本号（v1, v2...）方便追溯。

## 9 组 baseline 数据

| 颜色 | only | +1干扰 | +2干扰 | 每条 episodes |
|------|------|--------|--------|---------------|
| 绿色 | v6 | v2 | v2/v3 | 10 |
| 葡萄紫 | v1 | v1 | v1 | 10 |
| 橙色 | v1 | v1 | v1 | 10 |

**baseline 合计**：9 组 × 10 条 = 90 条

## 数据多样性策略

为了让模型具备良好的泛化能力，在录制时有意识地引入了大量变化。以下按维度说明。

### 干扰物多样性

目标始终是 3.5cm 小方块，但干扰物不限于同形状物体：

| 干扰物类型 | 说明 |
|-----------|------|
| 不同颜色小方块 | 与目标方块同形状、不同颜色，需要模型区分颜色指令 |
| 圆形块 | 形状完全不同的干扰物，测试模型是否过度依赖形状特征 |
| 更大体积方块 | 比目标方块大的积木块，考验空间感知能力 |

**干扰物数量分布**（因摆放随机，以下为大致估算）：

| 干扰等级 | 占比 | 说明 |
|----------|------|------|
| 1 个干扰物 | ~40% | 基础干扰场景 |
| 2 个或更多干扰物 | ~60% | 主要场景，桌面更杂乱，难度更高 |

### 位置分布策略

方块和盘子的摆放位置不是均匀分布的，有意识地在核心区和边缘区之间做了配比：

| 区域 | 范围 | 占比 | 目的 |
|------|------|------|------|
| **核心区** | 桌面中心约 25cm × 25cm | ~70% | 正常操作区域，机械臂关节在舒适范围内 |
| **边缘/极端区** | 核心区以外的边缘位置 | ~30% | 让模型见识关节在极限角度附近的状态，增强对边缘情况的处理能力 |

> 位置是手动随机摆放的，上述百分比为大致估算。极端位置的数据虽然少，但对于模型了解电机的角度边界很有价值。

### 初始状态多样性

每次 episode 开始时机械臂的初始位置**不固定**，有意识地在多种状态间切换：

| 初始状态类型 | 说明 |
|-------------|------|
| 居中起始 | 机械臂在桌面中间位置起步（常规状态） |
| 上次停止位置上方 | 不特意复位，从上一条录制结束位置附近开始，模拟连续操作 |
| 故意偏置 | 方块在左边时手臂初始位置特意靠右，迫使模型学会大范围移动 |

**目的**：如果每条数据初始位置都一样（居中），模型可能形成"机械臂总是从桌子中间出发"的先验，导致在实际推理时遇到不同起始位置就不知如何处理。制造多样的初始状态，迫使模型根据当前视觉信息动态决策，而非依赖位置惯性。

## 第二批增强数据

在 baseline 基础上追加录制第二批数据（120 条，每色 40 条 = 20 only + 20 干扰），进一步增强多样性：
- 加大随机放置范围（盘子位置更远、角度更偏）
- 部分 episodes 拉窗帘/改灯光（光照变化）
- 部分场景增加到 20 episodes（如橙色 +1干扰 round2）
- 混合圆形和大体积干扰物

## 数据回放验证

录制完成应立即回放验证质量，避免事后才发现问题需要重录。

![数据回放](../images/数据回放.mp4)

```bash
# 驱动机械臂回放
sudo chmod 666 /dev/ttySO101_FOLLOWER
lerobot-replay \
    --robot.type=so101_follower --robot.port=/dev/ttySO101_FOLLOWER --robot.id=j_follower \
    --dataset.repo_id=jer/so101_3color_green_only_v6 \
    --dataset.episode=0

# 纯可视化查看（不驱动机器臂）
python -m lerobot.scripts.lerobot_dataset_viz \
    --repo-id jer/so101_3color_green_only_v6 --episode-index 0 --mode local
```

## 数据集整理

录制数据默认存储在 HuggingFace 缓存目录，需要整理到正式目录并合并为训练集：

```
原始缓存：
  ~/.cache/huggingface/lerobot/jer/so101_3color_green_only_v6/
  ~/.cache/huggingface/lerobot/jer/so101_3color_green_plus1_v2/
  ... (9 组 + 第二批)

    ↓ 复制到分类目录

分类目录：
  datasets/so101_3color_put_into_plate/train/green/only_green/
  datasets/so101_3color_put_into_plate/train/green/plus_1_distractor/
  ... (按颜色/场景分类)

    ↓ 合并为训练集

训练集：
  smolvla90/   ← 90 条 baseline
  smolvla210/  ← 90 baseline + 120 增强 = 210 条（每色约 70 条）
```

> 训练集是将所有颜色（绿/葡萄紫/橙）和所有场景（only/+1/+2干扰）的数据合并在一起使用的，不再按颜色分集。模型通过每条 episode 附带的 `single_task` 语言指令（如 `"put small green block in plate"`）来区分当前任务该抓哪个颜色。

合并后的 LeRobot 数据集目录结构：

```
smolvla210/
├── data/
│   └── chunk-000/
│       ├── episode_000000.parquet
│       ├── episode_000001.parquet
│       └── ...
├── meta/
│   ├── info.json    # 数据集 feature 列表
│   └── stats.json   # 归一化统计信息
└── videos/
    ├── observation.images.front/
    │   └── episode_000000/
    │       ├── step_000000.mp4
    │       └── ...
    └── observation.images.top/
        └── ...
```

## wrist_roll 固定关节

录制时通过 `--robot.fixed_joints="{wrist_roll: -67.74}"` 固定第 5 关节（手腕旋转）。这个值是先遥操作测试把 wrist_roll 转到合适抓取角度后，读取终端打印的关节 position（norm 值）得到的。固定此关节消除了一个自由度，简化任务的同时保证抓取方向一致。