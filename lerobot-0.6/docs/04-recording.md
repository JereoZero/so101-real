# 04. 数据录制

> 参考项目：[JereoZero/so101-real](https://github.com/JereoZero/so101-real)  
> 参考项目文档：[05-data-collection.md](https://github.com/JereoZero/so101-real/blob/main/%E9%A1%B9%E7%9B%AE%E6%B5%81%E7%A8%8B/05-data-collection.md)

## 任务定义

本版本任务简化：

| 项目 | 内容 |
|------|------|
| 任务描述 | `"put grape block in plate"` |
| 目标物体 | 仅紫色方块（3.5cm） |
| 目标容器 | 白色小盘子（8.5cm 直径） |
| 干扰物 | 无（初期不加干扰） |
| 颜色数量 | 1 种（紫色） |
| 计划录制量 | 30~50 条 episode，分多组完成 |

## 手动录制机制说明

录制流程完全**手动控制**，满足你的需求：

### 1. 手动启停

- 按 **右箭头** 开始/结束录制一条 episode
- 按 **ESC** 完全停止录制

### 2. 复位阶段可继续遥操作

- 录制命令中包含 `--teleop.*` 参数，复位阶段主臂仍可控制从臂
- 可以自由摆场景、调整方块/盘子位置
- 这也是 v0.5.1 参考项目踩坑记录中的关键教训（必须加 `--teleop` 参数）

### 关于 `wrist_roll` 固定角度

参考项目 v0.5.1 中使用了 `--robot.fixed_joints="{wrist_roll: -67.74}"` 来固定手腕旋转角度。LeRobot v0.6.0 原版的 `SOFollowerConfig` 没有 `fixed_joints` 字段，但本项目已通过 patch 把它加回来了。

固定 `wrist_roll` 的配置已写入 [`src/configs/so101.yaml`](../../src/configs/so101.yaml)：

```yaml
robot:
  type: so101_follower
  fixed_joints:
    wrist_roll: -27.82
```

效果：

- 遥操作时，无论你如何旋转主臂的 `wrist_roll`，从臂的 `wrist_roll` 都会被覆盖为 `-27.82°`。
- 录制数据时，数据集记录的 `action.wrist_roll` 也始终是 `-27.82°`，模型不需要学习这个关节。
- 如果你希望模型学习 `wrist_roll`，把 `fixed_joints` 留空或删除即可。

> 配置里的角度单位是 **度**（因为 `use_degrees: true`）。

### ⚠️ 已知坑点：录制时 fixed_joints 必须作用于"实际发送的 action"

**问题**：LeRobot v0.6.0 源码 `lerobot_record.py` 的录制循环里，写入数据集用的是**主臂（teleop）的原始 action**，而不是从臂 `send_action()` 实际返回的动作。由于 `fixed_joints` 覆盖逻辑在 `send_action()` 内部（从臂执行时才生效），导致：
- 从臂实际运动时 wrist_roll 被锁到 -27.82°
- 但数据集里记录的 action.wrist_roll 却是主臂的原始值（16°~84° 变化）

**后果**：训练时模型学到的是"错误的" action（主臂值），推理时从臂执行的是"正确的" action（固定值），train/inference 不一致。

**修复**：本项目已 patch `lerobot_record.py`，将写入数据集的 action 从 `action_values`（主臂原始）改为 `_sent_action`（从臂实际执行的动作，含 fixed_joints 覆盖）。详见 [`apply_patches.py`](../../apply_patches.py) 的 patch 8b。

**验证**：录完后用以下命令确认 action.wrist_roll 唯一值为 -27.82：
```bash
conda run -n lerobot python3 -c "
import pandas as pd, numpy as np
df = pd.read_parquet('data/so101_grape_put_v0-1/data/chunk-000/file-000.parquet')
act = np.stack(df['action'].values)
print('wrist_roll 唯一值:', np.unique(np.round(act[:,4],2)))
"
# 应输出: [-27.82]
```

### 3. 每条可保存或重录

- 按 **右箭头** 结束录制 -> 本条 episode 保存，进入复位阶段
- 按 **左箭头** 放弃当前 episode -> 回到复位阶段重新录制本条
- 完全手动控制，每条都可以选择保留或重录

## SmolVLA 数据格式说明

录制的数据使用 LeRobot 标准格式，键名如下：

| 录制时（LeRobot 标准） | 训练时（SmolVLA 期望） | 说明 |
|------------------------|----------------------|------|
| `observation.images.front` | -> `observation.images.camera1` | 爪子视角摄像头 |
| `observation.images.top` | -> `observation.images.camera2` | 顶部第三视角摄像头 |
| `observation.state` | `observation.state` | 6 维关节状态 |
| `action` | `action` | 6 维动作 |

> 录制时仍使用 `front`/`top` 命名，训练时通过 `--rename_map` 映射为 `camera1`/`camera2`。详见 [05-training.md](05-training.md) 的 SmolVLA 训练部分。

## 前置条件

- 已完成 [03-teleoperation.md](03-teleoperation.md)
- 遥操作正常，`wrist_roll` 已锁定
- 摄像头已连接并测试正常
- 紫色方块、白色盘子已就位
- 桌面光照环境已布置好

## 数据命名规则

采用 `v{version}-{group}` 格式：

```
local/so101_grape_put_v{version}-{group}
```

| 含义 | 说明 |
|------|------|
| `version` | 版本号，从 0 开始递增，每次迭代调参后加 1 |
| `group` | 组号，同版本内每组 10 条 episode，从 1 开始 |
| 完整 repo_id | 如 `local/so101_grape_put_v0-1` |

### 命名示例

| 数据集 | 说明 |
|--------|------|
| `local/so101_grape_put_v0-1` | 第 0 版（初始版），第 1 组 —— **已废弃**（fixed_joints 录制 bug，数据录为主臂值） |
| `local/so101_grape_put_v1-1` | 第 1 版（修复录制 bug 后），第 1 组（前 10 条）✅ 已录制+回放验证 |
| `local/so101_grape_put_v1-2` | 第 1 版，第 2 组 ✅ 已录制（10 条，wrist_roll 锁定正常） |
| `local/so101_grape_put_v1-3` | 第 1 版，第 3 组 ✅ 已录制（10 条，累计 30 条达标） |
| `local/so101_grape_put_v1-4` | 第 1 版，第 4 组 ✅ 已录制（10 条） |
| `local/so101_grape_put_v1-5` | 第 1 版，第 5 组 ✅ 已录制（10 条） |
| `local/so101_grape_put_v1-6` | 第 1 版，第 6 组 ✅ 已录制（10 条） |
| `local/so101_grape_put_v1-7` | 第 1 版，第 7 组 ✅ 已录制（10 条） |
| `local/so101_grape_put_v1-8` | 第 1 版，第 8 组 ✅ 已录制（10 条） |
| `local/so101_grape_put_v1-9` | 第 1 版，第 9 组 ✅ 已录制（10 条） |
| `local/so101_grape_put_v1-10` | 第 1 版，第 10 组 ✅ 已录制（10 条） |
| `local/so101_grape_put_v1-11` | 第 1 版，第 11 组 ✅ 已录制（10 条） |
| `local/so101_grape_put_v1-12` | 第 1 版，第 12 组 ✅ 已录制（10 条） |
| `local/so101_grape_put_v1-13` | 第 1 版，第 13 组 ✅ 已录制（10 条） |
| `local/so101_grape_put_v1-14` | 第 1 版，第 14 组 ✅ 已录制（10 条） |
| `local/so101_grape_put_v1-15` | 第 1 版，第 15 组 ✅ 已录制（10 条） |
| `local/so101_grape_put_v1-16` | 第 1 版，第 16 组 ✅ 已录制（10 条） |
| `local/so101_grape_put_v1-17` | 第 1 版，第 17 组 ✅ 已录制（10 条） |
| `local/so101_grape_put_v1-18` | 第 1 版，第 18 组 ✅ 已录制（10 条） |
| `local/so101_grape_put_v1-19` | 第 1 版，第 19 组 ✅ 已录制（10 条） |
| `local/so101_grape_put_v1-20` | 第 1 版，第 20 组 ✅ 已录制（9 条，最后 1 条未保存） |
| `local/so101_grape_put_v1_merged` | v1-1 ~ v1-20 合并后数据集 ✅ 199 条 / 52,010 frames |
| `local/so101_grape_put_v3-2` | 第 3 版，第 2 组 |

> 注意：v0.6.0 会自动在 `repo_id` 后追加时间戳（如 `local/so101_grape_put_v0-1_20260720_123456`），但通过 `--dataset.root` 指定本地路径可以保持目录名稳定。

### 训练时合并多组数据

> ⚠️ **v0.6.0 变化**：v0.5.x 的 `--dataset.repo_id='["a","b"]'` 列表式合并已被禁用。需先用 `lerobot-edit-dataset --operation.type=merge` 物理合并，再训练。详见 [05-training.md](05-training.md) 的"数据集合并"小节。

```bash
# 合并 v1-1 ~ v1-20（199 条，52,010 frames）
lerobot-edit-dataset \
  --operation.type=merge \
  --operation.repo_ids='["local/so101_grape_put_v1-1","local/so101_grape_put_v1-2","local/so101_grape_put_v1-3","local/so101_grape_put_v1-4","local/so101_grape_put_v1-5","local/so101_grape_put_v1-6","local/so101_grape_put_v1-7","local/so101_grape_put_v1-8","local/so101_grape_put_v1-9","local/so101_grape_put_v1-10","local/so101_grape_put_v1-11","local/so101_grape_put_v1-12","local/so101_grape_put_v1-13","local/so101_grape_put_v1-14","local/so101_grape_put_v1-15","local/so101_grape_put_v1-16","local/so101_grape_put_v1-17","local/so101_grape_put_v1-18","local/so101_grape_put_v1-19","local/so101_grape_put_v1-20"]' \
  --operation.roots='["/home/j/ws/so101/data/so101_grape_put_v1-1","/home/j/ws/so101/data/so101_grape_put_v1-2","/home/j/ws/so101/data/so101_grape_put_v1-3","/home/j/ws/so101/data/so101_grape_put_v1-4","/home/j/ws/so101/data/so101_grape_put_v1-5","/home/j/ws/so101/data/so101_grape_put_v1-6","/home/j/ws/so101/data/so101_grape_put_v1-7","/home/j/ws/so101/data/so101_grape_put_v1-8","/home/j/ws/so101/data/so101_grape_put_v1-9","/home/j/ws/so101/data/so101_grape_put_v1-10","/home/j/ws/so101/data/so101_grape_put_v1-11","/home/j/ws/so101/data/so101_grape_put_v1-12","/home/j/ws/so101/data/so101_grape_put_v1-13","/home/j/ws/so101/data/so101_grape_put_v1-14","/home/j/ws/so101/data/so101_grape_put_v1-15","/home/j/ws/so101/data/so101_grape_put_v1-16","/home/j/ws/so101/data/so101_grape_put_v1-17","/home/j/ws/so101/data/so101_grape_put_v1-18","/home/j/ws/so101/data/so101_grape_put_v1-19","/home/j/ws/so101/data/so101_grape_put_v1-20"]' \
  --new_repo_id=local/so101_grape_put_v1_merged \
  --new_root=/home/j/ws/so101/data/so101_grape_put_v1_merged

# 用合并后的单个数据集训练
python src/scripts/train.py \
  --dataset.repo_id=local/so101_grape_put_v1_merged \
  --dataset.root=/home/j/ws/so101/data/so101_grape_put_v1_merged \
  --policy.type=smolvla \
  --policy.path=/home/j/ws/so101/checkpoints/smolvla_base_migrated \
  --rename_map=...
```

> 合并操作**不会删除原始数据目录**。`v1-1` ~ `v1-20` 会原样保留，方便后续需要重新合并或单独查看。

> 合并后各组的录制配置相同（相机、状态、动作维度一致），合并后就是完整的数据集。

## 录制命令

使用 `src/scripts/record.py`（包装了 LeRobot 的 `lerobot-record`）：

```bash
cd /home/j/ws/so101
unset PYTHONPATH
conda activate lerobot

python src/scripts/record.py \
  --display_data=true \
  --dataset.repo_id=local/so101_grape_put_v1-20 \
  --dataset.root=/home/j/ws/so101/data/so101_grape_put_v1-20 \
  --dataset.push_to_hub=false \
  --dataset.num_episodes=10 \
  --dataset.single_task="put grape block in plate" \
  --dataset.episode_time_s=60 \
  --dataset.reset_time_s=9999
```

> **端口/摄像头/固定关节自动加载**：`record.py` 会自动从 `src/configs/so101.yaml` 读取 `--robot.*`、`--teleop.*`、`--robot.cameras`、`--robot.fixed_joints`，无需手动传参。只有 `--dataset.*` 需要你指定。
>
> 如果你在 CLI 手动传了 `--robot.port` 等参数，脚本会以你传的为准（不覆盖）。

### 关键参数说明

| 参数                         | 参考值                          | 说明                   |
| -------------------------- | ---------------------------- | -------------------- |
| `--dataset.repo_id`        | `local/so101_grape_put_v0-1` | 按命名规则填写              |
| `--dataset.root`           | 本地路径                         | 数据集存储到项目 `data/` 目录  |
| `--dataset.single_task`    | `"put grape block in plate"` | 任务描述，也是训练时的提示词       |
| `--dataset.num_episodes`   | 10                           | 每组录 10 条             |
| `--dataset.episode_time_s` | 60                           | 单条最大时长（1分钟），主要手动按键结束 |
| `--dataset.reset_time_s`   | 9999                         | 复位阶段超长，完全手动控制        |
| `--display_data`           | true                         | 实时预览摄像头和关节状态         |
| `--dataset.push_to_hub`    | false                        | 仅本地保存                |

> **SSH/无显示环境注意**：`display_data=true` 需要 Rerun 可视化后端。如果 Ubuntu 主机是 headless（无桌面/无 Rerun 服务），建议改为 `display_data=false`，否则可能因连接 Rerun 失败而报错。本地有图形界面时可保持 `true`。无论是否显示，录制数据本身不受影响。

### v0.6.0 推荐特性

- **流式视频编码**：录制时实时编码视频，episode 保存几乎无等待。CPU 较强时可开启：
  ```bash
  --dataset.streaming_encoding=true \
  --dataset.encoder_threads=2
  ```
- **自动时间戳**：`repo_id` 会自动追加时间戳，但通过 `--dataset.root` 指定路径可保持目录名稳定
- **视频编码参数**：v0.5.x 的 `--dataset.vcodec` 已改为 `--dataset.rgb_encoder.vcodec`

## 录制键位

| 按键 | 功能 |
|------|------|
| **-> 右箭头** | 结束当前阶段（录制 -> 复位 / 复位 -> 录制） |
| **<- 左箭头** | 放弃当前 episode，回到复位阶段重新录制本条 |
| **ESC** | 完全停止录制 |

## 录制流程

```
启动录制 -> 校准从臂 -> 进入复位阶段
    |
    循环：
      1. 手动摆场景（方块+盘子，调整位置）
      2. 按 -> 开始录制
      3. 操作主臂完成"抓取方块 -> 放入盘子"
      4. 按 -> 结束录制（本条保存）
         - 若操作失误，按 <- 放弃本条，回到步骤 1
      5. 准备下一条，回到步骤 1
    |
按 ESC 停止 -> 回放验证数据质量 -> 整理数据集
```

### 每次录制操作步骤

1. 启动录制命令，等待校准完成
2. 进入复位阶段：
   - 从臂跟随主臂，可自由摆场景
   - 将紫色方块放在随机位置，盘子放在另一位置
3. 按 **右箭头** 开始录制本条 episode
4. 操作主臂完成"抓取方块 -> 放入盘子"的动作
5. 按 **右箭头** 结束录制，episode 自动保存，进入复位阶段
6. 重复 2~5，直到完成 10 条（一组）
7. 按 **ESC** 停止录制

### 重录说明

如果在步骤 4 中操作失误（如方块没抓稳、掉出盘子等）：
- 按 **左箭头** 放弃本条 episode
- 回到复位阶段，重新摆场景，重新录制
- 已放弃的 episode 不会保存

## 数据多样性策略（简化版）

本版本只录制紫色方块，无干扰物，但位置和初始状态仍需多样化：

### 1. 方块位置多样化

| 区域 | 建议占比 | 说明 |
|------|---------|------|
| 核心区（桌面中心约 25cm x 25cm） | ~70% | 正常操作区域 |
| 边缘区 | ~30% | 让模型适应不同位置 |

### 2. 盘子位置变化

- 左/中/右 三个大致位置
- 距离方块 5~15cm

### 3. 初始状态多样化

- 从臂起始位置：居中、偏左、偏右交替
- 避免每次都从完全相同的姿势开始

### 4. 光照变化

- 正常室内光照
- 适当拉开窗帘改变光照方向

## 数据质量检查

每录完一组数据，用 `src/scripts/check_data.py` 一键验证数据质量：

```bash
cd /home/j/ws/so101
conda run -n lerobot python src/scripts/check_data.py data/so101_grape_put_v1-13
```

检查内容：
- episodes 数 / frames 数
- wrist_roll 是否锁定在 -27.82°（关键！）
- gripper 开合范围是否正常
- 各关节 action / observation.state 范围
- front / top 视频文件是否存在

## 数据回放验证

录制完成后立即回放确认数据质量：

### 1. 驱动机械臂回放

使用 `src/scripts/replay.py`（自动从 `so101.yaml` 加载 robot 配置）：

```bash
unset PYTHONPATH
conda activate lerobot
cd /home/j/ws/so101

python src/scripts/replay.py \
  --dataset.repo_id=local/so101_grape_put_v1-1 \
  --dataset.root=/home/j/ws/so101/data/so101_grape_put_v1-1 \
  --dataset.episode=0 \
  --dataset.fps=30
```

> 回放会让从臂实际运动，请确保周围无碰撞风险。回放结束后可能出现
> `gripper Overload error` 警告（夹爪电机过热），这是已知硬件问题，不影响回放结果。

### 2. 纯可视化查看（无需连接机械臂）

```bash
lerobot-dataset-viz \
  --repo-id local/so101_grape_put_v1-1 \
  --episode-index 0
```

## 迭代录制

参考项目经验：前几次录制通常需要迭代调整。建议：

- 每次先录 1 组（10 条）
- 立即回放验证动作流畅度
- 根据效果调整：固定关节角度、光照、方块/盘子位置
- 下一组用新的命名 (`v0-2`, `v0-3`...)
- 大幅调整后开始新版本 (`v1-1`, `v1-2`...)

## 数据质量检查

每条 episode 确认：
- 动作流畅，无卡顿/抖动
- 方块被成功抓起并放入盘子
- 夹爪开合正常
- 两个摄像头画面清晰、亮度正常
- 没有多余干扰物/手指入镜

## 下一步

数据量足够且质量验证通过后，进入 [05-training.md](05-training.md) 训练模型。