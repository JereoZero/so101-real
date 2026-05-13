# 5. 数据采集

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

## 第二批增强数据

在 baseline 基础上追加录制第二批数据（120 条，每色 40 条 = 20 only + 20 干扰），增强点包括：
- 加大随机放置范围（盘子位置更远、角度更偏）
- 部分 episodes 拉窗帘/改灯光（光照变化）
- 部分场景增加到 20 episodes（如橙色 +1干扰 round2）
- 混合圆形干扰物

## 数据回放验证

录制完成应立即回放验证质量，避免事后才发现问题需要重录：

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